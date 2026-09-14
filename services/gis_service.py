"""
CarbonLens — Spatial / Land-Use Context service (Phase 5-C, Experimental).

Orchestration layer for the Spatial Context tab inside Carbon Accounting.
Owns: attempting a real Google Earth Engine query, falling back to clearly-
labeled synthetic data when GEE is unavailable or unauthenticated, calling
the pure calculations in calculations/gis_math.py, and emitting the
gis_query_run audit event.

CRITICAL — never called on initial page render. The page only calls
run_spatial_query() from inside an explicit user action (a button click),
never unconditionally in render(). This module does not enforce that itself
(it can't — it has no knowledge of when it's called), so the calling page is
responsible; see pages/carbon_accounting/page.py::_s8_spatial_context().

Graceful degradation status (read before claiming this "works with real
satellite data" anywhere, including a thesis or a portfolio conversation):
  - earthengine-api IS a genuine, installed, active dependency — `import ee`
    succeeds in this environment.
  - ee.Initialize() requires real Earth Engine credentials (a service account
    or `earthengine authenticate`) that are NOT bundled with this repository
    and were not available in the environment this feature was built in.
    Without them, ee.Initialize() raises a clean EEException, which this
    module catches and falls back to synthetic data — the exact same
    graceful-degradation pattern the original V7 audit called "honestly good
    engineering," reproduced deliberately here rather than faked.
  - This means: the live-GEE code path is real and structurally correct, but
    has not been exercised against actual satellite data in this build
    environment. Whether it has been exercised in a real deployment depends
    on whether Earth Engine credentials were configured there — check
    services.gis_service.LAST_QUERY_DATA_SOURCE (or a query's own
    "data_source" field) rather than assuming.
"""
from __future__ import annotations
import logging
import random
from typing import Optional

log = logging.getLogger("carbonlens.services.gis")

# Set by the most recent run_spatial_query() call — lets tests and honest
# self-reporting distinguish "real GEE call succeeded" from "fell back to
# synthetic data" without re-parsing the whole result dict.
LAST_QUERY_DATA_SOURCE: str = "never_run"


def _synthetic_spatial_data(lat: float, lon: float, radius_km: float) -> dict:
    """
    Deterministic, clearly-synthetic land-cover + NDVI + forest-loss data,
    seeded from the query location so repeated queries for the same site are
    stable within a session (not re-randomised on every click) but different
    sites produce different (still synthetic) numbers.

    This is a fallback, not a simulation of real satellite output — every
    caller of this function must propagate "data_source": "synthetic_fallback"
    to the UI, never presented with the same visual confidence as a real
    query result.
    """
    seed = int((abs(lat) * 1000 + abs(lon) * 1000) % 100000)
    rng = random.Random(seed)

    forest_pct = round(rng.uniform(15, 65), 1)
    remainder  = 100.0 - forest_pct
    agri_pct   = round(remainder * rng.uniform(0.35, 0.55), 1)
    water_pct  = round(remainder * rng.uniform(0.05, 0.20), 1)
    built_pct  = round(remainder * rng.uniform(0.15, 0.35), 1)
    other_pct  = round(max(0.0, remainder - agri_pct - water_pct - built_pct), 1)

    land_cover = {
        "forest_pct": forest_pct, "agriculture_pct": agri_pct,
        "water_pct": water_pct, "built_up_pct": built_pct, "other_pct": other_pct,
    }
    ndvi_by_class = {
        "forest":      round(rng.uniform(0.55, 0.85), 3),
        "agriculture": round(rng.uniform(0.25, 0.55), 3),
        "water":       round(rng.uniform(0.0, 0.10), 3),
        "built_up":    round(rng.uniform(0.05, 0.20), 3),
        "other":       round(rng.uniform(0.10, 0.30), 3),
    }
    # 5 synthetic annual loss figures (hectares), mildly increasing trend
    base_loss = rng.uniform(20, 80)
    annual_loss_ha = [round(base_loss * (1 + 0.08 * i) * rng.uniform(0.9, 1.1), 1)
                       for i in range(5)]

    return {
        "land_cover": land_cover,
        "ndvi_by_class": ndvi_by_class,
        "annual_loss_ha": annual_loss_ha,
    }


def _try_live_earth_engine(lat: float, lon: float, radius_km: float) -> Optional[dict]:
    """
    Attempt a real Earth Engine query. Returns None (never raises) if the
    library isn't installed, isn't authenticated, or the call fails for any
    reason — the caller falls back to synthetic data either way.

    Structured so that a deployment WITH real Earth Engine credentials
    configured would exercise this path for real, without any code change
    here — only the environment's credentials need to change.
    """
    try:
        import ee
    except ImportError:
        log.info("gis_service: earthengine-api not importable — using synthetic fallback")
        return None

    try:
        ee.Initialize()
    except Exception as exc:
        log.info(f"gis_service: ee.Initialize() failed ({type(exc).__name__}) — "
                  f"no Earth Engine credentials configured, using synthetic fallback")
        return None

    try:
        point  = ee.Geometry.Point([lon, lat])
        buffer = point.buffer(radius_km * 1000)

        # Sentinel-2 surface reflectance, cloud-filtered, most recent composite.
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(buffer)
            .filterDate(ee.Date.fromYMD(2024, 1, 1), ee.Date.fromYMD(2024, 12, 31))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
            .median()
        )
        ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")

        # Hansen Global Forest Change — tree cover / loss layers for masking.
        hansen = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
        tree_cover_2000 = hansen.select("treecover2000")
        forest_mask = tree_cover_2000.gte(30)   # ≥30% canopy cover = "forest"

        ndvi_forest_mean = ndvi.updateMask(forest_mask).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=buffer, scale=30, maxPixels=1e9,
        ).get("NDVI").getInfo()

        forest_area_frac = forest_mask.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=buffer, scale=30, maxPixels=1e9,
        ).get("treecover2000").getInfo()

        if ndvi_forest_mean is None or forest_area_frac is None:
            log.info("gis_service: live Earth Engine query returned no data for this AOI")
            return None

        return {
            "ndvi_forest_live": float(ndvi_forest_mean),
            "forest_area_frac_live": float(forest_area_frac) / 100.0,
        }
    except Exception as exc:
        log.warning(f"gis_service: live Earth Engine query failed mid-request: {exc}")
        return None


def run_spatial_query(
    lat: float, lon: float, radius_km: float,
    province: str, org_id: str = "", company_name: str = "",
) -> dict:
    """
    Run (or fall back on) a spatial land-use / biomass query for an
    approximate site location and return a fully-labeled result dict.

    This is the single entry point pages call — it internally decides
    real-vs-synthetic and never lets a page branch on that itself.
    """
    global LAST_QUERY_DATA_SOURCE
    from calculations.gis_math import estimate_forest_carbon_stock, classify_forest_loss_trend

    aoi_area_ha = math_area_ha(radius_km)

    live = _try_live_earth_engine(lat, lon, radius_km)
    if live is not None:
        data_source = "earth_engine_live"
        # A live query gives us forest NDVI and forest-area fraction directly —
        # build a minimal land_cover/ndvi_by_class shape so the SAME masked
        # calculation path (estimate_forest_carbon_stock) runs either way.
        forest_pct = round(live["forest_area_frac_live"] * 100, 1)
        land_cover = {
            "forest_pct": forest_pct, "agriculture_pct": max(0.0, 100 - forest_pct),
            "water_pct": 0.0, "built_up_pct": 0.0, "other_pct": 0.0,
        }
        ndvi_by_class = {"forest": live["ndvi_forest_live"], "agriculture": 0.0,
                          "water": 0.0, "built_up": 0.0, "other": 0.0}
        annual_loss_ha = []   # live Hansen loss-year breakdown not wired in this pass
    else:
        data_source = "synthetic_fallback"
        synth = _synthetic_spatial_data(lat, lon, radius_km)
        land_cover, ndvi_by_class, annual_loss_ha = (
            synth["land_cover"], synth["ndvi_by_class"], synth["annual_loss_ha"],
        )

    LAST_QUERY_DATA_SOURCE = data_source

    biomass = estimate_forest_carbon_stock(land_cover, ndvi_by_class, aoi_area_ha)
    loss_trend = classify_forest_loss_trend(annual_loss_ha)

    result = {
        "data_source": data_source,
        "lat": lat, "lon": lon, "radius_km": radius_km, "province": province,
        "aoi_area_ha": aoi_area_ha,
        "land_cover": land_cover,
        **biomass,
        "loss_trend": loss_trend,
        "annual_loss_ha": annual_loss_ha,
    }

    try:
        from audit.writer import write_audit_event
        write_audit_event(
            event_type = "gis_query_run",
            summary    = f"Spatial context query run for {province} "
                         f"({data_source.replace('_', ' ')})",
            detail     = {"lat": lat, "lon": lon, "radius_km": radius_km,
                          "data_source": data_source, "province": province},
            org_id       = org_id,
            company_name = company_name,
        )
    except Exception as exc:
        log.warning(f"gis_service: audit event for gis_query_run failed: {exc}")

    return result


def math_area_ha(radius_km: float) -> float:
    """Area of a circle of the given radius, in hectares. Pure arithmetic
    helper kept here (not gis_math.py) since it's query-geometry plumbing,
    not a scientific formula requiring citation."""
    import math
    radius_km = max(0.01, float(radius_km))
    area_km2 = math.pi * radius_km ** 2
    return round(area_km2 * 100, 1)   # 1 km² = 100 ha
