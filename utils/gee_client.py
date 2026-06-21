"""
CarbonLens V7 — Google Earth Engine Client
Sentinel-2 NDVI/EVI + Hansen deforestation + Mangrove Atlas
for real geospatial carbon intelligence.

Architecture:
- Requires a GEE service account JSON key OR personal token (ee.Authenticate).
- Falls back gracefully to synthetic data when credentials absent — platform
  stays functional, GEE badge shows "Offline".
- All GEE calls are cached by (lat, lon, buffer_km, year) to avoid re-querying
  on every Streamlit rerun.
- Sentinel-2 SR mosaic: cloud-masked, median composite, per-pixel NDVI/EVI.
- Carbon stock estimated via NDVI-to-AGB regression (Saatchi 2011 pantropical
  coefficients) then converted to Mg C/ha and tCO₂e/ha.
"""

from __future__ import annotations
import os, json, math, hashlib, functools
from typing import Optional

# ── GEE availability flag ────────────────────────────────────────────────────
_GEE_AVAILABLE = False
_GEE_ERROR: str = ""
ee = None

try:
    import ee
    _GEE_AVAILABLE = True
except ImportError:
    _GEE_ERROR = "earthengine-api not installed (pip install earthengine-api)"
except Exception as _e:
    _GEE_ERROR = str(_e)


# ── Constants ─────────────────────────────────────────────────────────────────
# Sentinel-2 SR (Level 2A) — available from 2017 onward
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
NDVI_BAND     = "NDVI"
EVI_BAND      = "EVI"
MAX_CLOUD_PCT = 20

# Hansen GFC (Global Forest Change)
HANSEN_COLLECTION = "UMD/hansen/global_forest_change_2023_v1_11"

# Global Mangrove Watch (JAXA)
MANGROVE_COLLECTION = "JAXA/GFWC/GMWC/v20240511"

# NDVI → AGB regression (Saatchi 2011, pantropical, tropical moist forest)
# AGB (Mg/ha) = exp(a * NDVI + b)
NDVI_AGB_A = 3.8
NDVI_AGB_B = -0.75
BGB_FRACTION = 0.26   # Below-ground biomass = 26% of AGB (IPCC Tier 1)
C_FRACTION   = 0.47   # Carbon = 47% of biomass dry weight
CO2_FACTOR   = 3.67   # C → CO₂e

_CACHE: dict = {}


def _cache_key(*args) -> str:
    return hashlib.md5(json.dumps(args, default=str).encode()).hexdigest()[:12]


# ── Auth ─────────────────────────────────────────────────────────────────────
_INITIALIZED = False

def initialize(service_account_json: Optional[str] = None,
               service_account_email: Optional[str] = None) -> tuple[bool, str]:
    """
    Initialize GEE. Tries three paths in order:
    1. Service account JSON key (string content or path to file)
    2. GOOGLE_APPLICATION_CREDENTIALS env var
    3. Personal credentials from ~/.config/earthengine/credentials (ee.Authenticate)

    Returns (success: bool, message: str)
    """
    global _INITIALIZED, _GEE_AVAILABLE, _GEE_ERROR

    if not _GEE_AVAILABLE:
        return False, _GEE_ERROR

    if _INITIALIZED:
        return True, "Already initialized"

    # Path 1: explicit service account JSON
    if service_account_json:
        try:
            # Could be raw JSON string or a file path
            if service_account_json.strip().startswith("{"):
                key_data = json.loads(service_account_json)
            else:
                key_data = json.load(open(service_account_json))

            email = service_account_email or key_data.get("client_email", "")
            credentials = ee.ServiceAccountCredentials(email, key_data=json.dumps(key_data))
            ee.Initialize(credentials)
            _INITIALIZED = True
            return True, f"Initialized via service account: {email}"
        except Exception as e:
            return False, f"Service account auth failed: {e}"

    # Path 2: GOOGLE_APPLICATION_CREDENTIALS env var
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac and os.path.exists(gac):
        try:
            key_data = json.load(open(gac))
            email    = key_data.get("client_email", "")
            credentials = ee.ServiceAccountCredentials(email, key_data=json.dumps(key_data))
            ee.Initialize(credentials)
            _INITIALIZED = True
            return True, f"Initialized via env credentials: {email}"
        except Exception as e:
            return False, f"Env credentials failed: {e}"

    # Path 3: personal ee.Authenticate() credentials
    try:
        ee.Initialize(project="carbonlens")
        _INITIALIZED = True
        return True, "Initialized via personal credentials"
    except Exception as e:
        # Try without project
        try:
            ee.Initialize()
            _INITIALIZED = True
            return True, "Initialized via default credentials"
        except Exception as e2:
            return False, (
                f"GEE not authenticated. Run `earthengine authenticate` in terminal, "
                f"or provide a service account JSON key in Settings. Error: {e2}"
            )


def is_ready() -> bool:
    return _GEE_AVAILABLE and _INITIALIZED


# ── Core GEE analysis ─────────────────────────────────────────────────────────

def _mask_s2_clouds(img):
    """Mask clouds and cirrus from Sentinel-2 SCL band."""
    scl = img.select("SCL")
    # SCL values: 3=cloud shadow, 8=cloud medium, 9=cloud high, 10=cirrus
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return img.updateMask(mask).divide(10000)


def _ndvi_evi(img):
    """Compute NDVI and EVI from Sentinel-2 SR bands."""
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    evi  = img.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {"NIR": img.select("B8"), "RED": img.select("B4"), "BLUE": img.select("B2")},
    ).rename("EVI")
    return img.addBands([ndvi, evi])


def _ndvi_to_agb(ndvi: float) -> float:
    """NDVI → AGB (Mg dry matter/ha) via exponential regression (Saatchi 2011)."""
    import math
    agb = math.exp(NDVI_AGB_A * ndvi + NDVI_AGB_B)
    return max(0.0, min(agb, 600.0))   # cap at 600 Mg/ha (tropical dense forest)


def fetch_sentinel2(lat: float, lon: float, buffer_km: float = 10,
                    year: int = 2024) -> dict:
    """
    Fetch Sentinel-2 NDVI/EVI median composite for a circular AOI.
    Returns dict with mean/median NDVI, EVI, and cloud coverage.
    Uses _CACHE to avoid repeated GEE calls.
    """
    if not is_ready():
        return {"error": "GEE not initialized", "ndvi": None, "evi": None}

    ck = _cache_key("s2", lat, lon, buffer_km, year)
    if ck in _CACHE:
        return _CACHE[ck]

    try:
        aoi    = ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)
        start  = f"{year}-01-01"
        end    = f"{year}-12-31"

        col = (
            ee.ImageCollection(S2_COLLECTION)
            .filterBounds(aoi)
            .filterDate(start, end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PCT))
            .map(_mask_s2_clouds)
            .map(_ndvi_evi)
        )

        size = col.size().getInfo()
        if size == 0:
            # Fallback: expand date range to ±1 year
            col = (
                ee.ImageCollection(S2_COLLECTION)
                .filterBounds(aoi)
                .filterDate(f"{year-1}-01-01", f"{year+1}-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
                .map(_mask_s2_clouds)
                .map(_ndvi_evi)
            )
            size = col.size().getInfo()

        median = col.select(["NDVI", "EVI"]).median()
        stats  = median.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.percentile([25, 75]), "", True),
            geometry=aoi, scale=20, maxPixels=1e8,
        ).getInfo()

        result = {
            "ndvi":      round(stats.get("NDVI_mean", 0.0) or 0.0, 4),
            "evi":       round(stats.get("EVI_mean",  0.0) or 0.0, 4),
            "ndvi_p25":  round(stats.get("NDVI_p25",  0.0) or 0.0, 4),
            "ndvi_p75":  round(stats.get("NDVI_p75",  0.0) or 0.0, 4),
            "n_images":  size,
            "year":      year,
            "source":    f"Sentinel-2 SR (n={size}, {year})",
            "error":     None,
        }
        _CACHE[ck] = result
        return result

    except Exception as e:
        return {"error": str(e), "ndvi": None, "evi": None}


def fetch_forest_loss(lat: float, lon: float, buffer_km: float = 10) -> dict:
    """
    Hansen GFC: tree cover (2000 baseline) + annual loss 2001-2023.
    Returns treecover2000 pct, total loss ha, loss by year.
    """
    if not is_ready():
        return {"error": "GEE not initialized"}

    ck = _cache_key("hansen", lat, lon, buffer_km)
    if ck in _CACHE:
        return _CACHE[ck]

    try:
        aoi  = ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)
        gfc  = ee.Image(HANSEN_COLLECTION)
        area_img = ee.Image.pixelArea().divide(10000)  # m² → ha

        # Tree cover 2000
        tc2000 = gfc.select("treecover2000")
        tc_pct = tc2000.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi, scale=30, maxPixels=1e8
        ).getInfo().get("treecover2000", 0) or 0

        # Loss area (binary mask × pixel area)
        loss_mask = gfc.select("loss")
        loss_ha   = loss_mask.multiply(area_img).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=30, maxPixels=1e8
        ).getInfo().get("loss", 0) or 0

        # Loss year breakdown (2001-2023 = lossyear values 1-23)
        loss_by_year = {}
        lossyear = gfc.select("lossyear")
        for yr_off in range(1, 24):
            ha = (lossyear.eq(yr_off)
                  .multiply(area_img)
                  .reduceRegion(
                      reducer=ee.Reducer.sum(),
                      geometry=aoi, scale=30, maxPixels=1e8)
                  .getInfo().get("lossyear", 0) or 0)
            if ha > 0:
                loss_by_year[2000 + yr_off] = round(ha, 1)

        result = {
            "treecover2000_pct": round(tc_pct, 1),
            "total_loss_ha":     round(loss_ha, 1),
            "loss_by_year":      loss_by_year,
            "source":            "Hansen GFC v1.11 (UMD/Google, 2023)",
            "error":             None,
        }
        _CACHE[ck] = result
        return result

    except Exception as e:
        return {"error": str(e)}


def fetch_mangrove_extent(lat: float, lon: float, buffer_km: float = 10,
                          year: int = 2020) -> dict:
    """
    JAXA Global Mangrove Watch: mangrove extent in AOI.
    Closest available year to requested year is used.
    """
    if not is_ready():
        return {"error": "GEE not initialized", "mangrove_ha": 0}

    ck = _cache_key("mangrove", lat, lon, buffer_km, year)
    if ck in _CACHE:
        return _CACHE[ck]

    try:
        aoi       = ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)
        area_img  = ee.Image.pixelArea().divide(10000)
        col       = ee.ImageCollection(MANGROVE_COLLECTION).filterBounds(aoi)
        closest   = col.sort(
            ee.Number(year).subtract(col.aggregate_array("system:time_start")
                                     .map(lambda t: ee.Number(t).divide(1000*86400*365).add(1970)))
            .abs()
        ).first()

        mg_ha = (closest.select("landsat_band").gt(0)
                 .multiply(area_img)
                 .reduceRegion(
                     reducer=ee.Reducer.sum(),
                     geometry=aoi, scale=25, maxPixels=1e8)
                 .getInfo().get("landsat_band", 0) or 0)

        result = {
            "mangrove_ha": round(mg_ha, 1),
            "year":        year,
            "source":      "JAXA GFWC Mangrove Watch 2024",
            "error":       None,
        }
        _CACHE[ck] = result
        return result

    except Exception as e:
        return {"error": str(e), "mangrove_ha": 0}


# ── Full carbon stock analysis ────────────────────────────────────────────────

def compute_real_gis(lat: float, lon: float, buffer_km: float = 10,
                     year: int = 2024, study_area_ha: float = 50000) -> dict:
    """
    Full GEE-based GIS analysis. Combines:
    - Sentinel-2 NDVI/EVI (spectral vegetation health)
    - NDVI → AGB → carbon stock conversion
    - Hansen deforestation (loss ha, tree cover baseline)
    - JAXA Mangrove Watch extent

    Returns dict compatible with existing gis_intelligence.py result schema,
    enriched with _gee_source flags for UI display.
    """
    s2     = fetch_sentinel2(lat, lon, buffer_km, year)
    hansen = fetch_forest_loss(lat, lon, buffer_km)
    mg     = fetch_mangrove_extent(lat, lon, buffer_km, year)

    if s2.get("error") or s2.get("ndvi") is None:
        return {"error": s2.get("error", "GEE fetch failed"), "gee_source": False}

    ndvi = s2["ndvi"]
    evi  = s2["evi"]

    # AGB from NDVI
    agb_ha   = _ndvi_to_agb(ndvi)
    bgb_ha   = agb_ha * BGB_FRACTION
    c_ha     = (agb_ha + bgb_ha) * C_FRACTION       # Mg C/ha
    co2e_ha  = c_ha * CO2_FACTOR                     # Mg CO₂e/ha

    # Total carbon stock for study area
    carbon_total_tg = c_ha * study_area_ha / 1e6    # Tg C

    # Annual deforestation rate
    if hansen.get("loss_by_year"):
        recent_years = sorted(hansen["loss_by_year"].keys())[-5:]
        recent_loss  = sum(hansen["loss_by_year"].get(y,0) for y in recent_years)
        annual_loss_ha = recent_loss / max(len(recent_years), 1)
        loss_pct       = annual_loss_ha / study_area_ha * 100
    else:
        annual_loss_ha = 0
        loss_pct       = 0.0

    # Risk index from deforestation rate + EVI
    risk_from_loss = min(1.0, loss_pct / 2)
    risk_from_ndvi = max(0.0, 1 - ndvi)   # low NDVI = high degradation risk
    risk_index     = round((risk_from_loss * 0.6 + risk_from_ndvi * 0.4), 3)
    risk_label     = ("Critical" if risk_index > 0.75 else "High" if risk_index > 0.55
                      else "Moderate" if risk_index > 0.35 else "Low")

    # Land cover estimate from tree cover
    tc_pct   = hansen.get("treecover2000_pct", 0)
    forest   = int(tc_pct)
    mangrove = min(20, int(mg.get("mangrove_ha",0) / study_area_ha * 100))
    agri     = max(5, int((100 - forest - mangrove) * 0.5))
    built    = max(2, int((100 - forest - mangrove) * 0.1))
    water    = max(3, int((100 - forest - mangrove) * 0.1))
    other    = max(0, 100 - forest - mangrove - agri - built - water)

    land_cover = {
        "Forest":      forest,
        "Mangrove":    mangrove,
        "Water":       water,
        "Agriculture": agri,
        "Built-up":    built,
        "Other":       other,
    }

    # 6-year trend: derive from deforestation loss series
    years = list(range(2019, 2025))
    if hansen.get("loss_by_year"):
        base_c    = c_ha
        c_trend   = []
        running_c = base_c
        for yr in years:
            yr_loss   = hansen["loss_by_year"].get(yr, annual_loss_ha)
            running_c = max(0, running_c - (yr_loss / study_area_ha) * base_c * 0.1)
            c_trend.append(round(running_c, 1))
    else:
        c_trend = [round(c_ha, 1)] * len(years)

    mangrove_ha      = mg.get("mangrove_ha", 0)
    biodiversity_idx = min(1.0, max(0.0, ndvi * 0.6 + (mangrove_ha/study_area_ha)*0.4))

    return {
        # Core metrics
        "carbon_stock":       round(c_ha, 1),           # Mg C/ha
        "carbon_stock_total": round(carbon_total_tg, 3), # Tg C
        "carbon_density":     round(co2e_ha, 1),         # Mg CO₂e/ha
        "risk_index":         risk_index,
        "risk_label":         risk_label,
        "biodiversity":       round(biodiversity_idx, 3),
        "protected_pct":      0,                          # not from GEE in this build
        "mangrove_ha":        mangrove_ha,
        "study_area_ha":      study_area_ha,
        "redd_eligible_ha":   round(mangrove_ha * 0.26),
        "annual_loss_pct":    round(loss_pct, 2),
        "sequestration":      round(c_ha * 0.006, 3),
        "years":              years,
        "carbon_trend":       c_trend,
        "land_cover":         land_cover,
        "hotspots":           [],                         # GEE hotspots added separately if needed
        "lat_center":         lat,
        "lon_center":         lon,
        "active_layers":      [],
        # GEE provenance
        "gee_source":         True,
        "ndvi":               ndvi,
        "evi":                evi,
        "ndvi_p25":           s2.get("ndvi_p25", 0),
        "ndvi_p75":           s2.get("ndvi_p75", 0),
        "n_s2_images":        s2.get("n_images", 0),
        "s2_source":          s2.get("source", ""),
        "hansen_source":      hansen.get("source", ""),
        "mangrove_source":    mg.get("source", ""),
        "agb_mg_ha":          round(agb_ha, 1),
        "bgb_mg_ha":          round(bgb_ha, 1),
        "error":              None,
    }


def clear_cache():
    """Clear all cached GEE results."""
    global _CACHE
    _CACHE = {}
