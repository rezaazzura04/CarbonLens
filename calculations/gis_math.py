"""
CarbonLens — Spatial / Land-Use Context calculations (Phase 5-C, Experimental).

Pure functions only — no Streamlit, no session state, no I/O, no audit calls.
Isolated deliberately (per the technical spec) so that any future
methodology correction is a one-file change.

Two credibility fixes this module exists to enforce structurally, not just
by convention:

  Fix C4 — the NDVI-AGB formula is honestly labeled as a simplified proxy
  (see config.constants.NDVI_AGB_PROXY_CITATION), never presented as a
  reproduction of Saatchi et al. (2011)'s actual ensemble regression.

  Fix M5 — estimate_forest_carbon_stock() REQUIRES a per-land-cover-class
  breakdown and only ever uses the forest-class NDVI for the biomass
  calculation. There is no function in this module that accepts a single
  blended whole-AOI NDVI value for biomass estimation — that was the
  specific mistake being fixed, so the mistake is structurally unavailable
  here, not just discouraged in a docstring.
"""
from __future__ import annotations
import math
from typing import TypedDict


class LandCoverBreakdown(TypedDict):
    forest_pct:     float   # % of AOI classified as forest/tree cover
    agriculture_pct: float
    water_pct:      float
    built_up_pct:   float
    other_pct:      float


def ndvi_to_agb_proxy(ndvi_forest: float) -> dict:
    """
    Estimate above-ground biomass (Mg/ha) from a FOREST-CLASS-ONLY NDVI value
    using a simplified single-variable proxy (Fix C4 — see
    config.constants.NDVI_AGB_PROXY_CITATION for the honest attribution).

    Parameters
    ----------
    ndvi_forest : NDVI value for forest pixels only (0.0-1.0). Must already
                  be masked to forest land cover by the caller — this
                  function does not know how to mask, only how to convert.

    Returns
    -------
    dict with:
      agb_mg_ha        : estimated above-ground biomass, Mg/ha
      saturated        : True if ndvi_forest is at/above the known NDVI
                          saturation threshold for dense biomass — the
                          returned value is a floor estimate, not precise
      formula           : the exact equation used, for provenance display
      citation          : honest attribution string
    """
    from config.constants import (
        NDVI_AGB_PROXY_A, NDVI_AGB_PROXY_B,
        NDVI_AGB_PROXY_CITATION, NDVI_SATURATION_THRESHOLD,
    )

    ndvi_clamped = max(0.0, min(1.0, float(ndvi_forest)))
    agb_mg_ha = math.exp(NDVI_AGB_PROXY_A * ndvi_clamped + NDVI_AGB_PROXY_B)
    saturated = ndvi_clamped >= NDVI_SATURATION_THRESHOLD

    return {
        "agb_mg_ha": round(agb_mg_ha, 2),
        "saturated": saturated,
        "agb_formula": f"AGB = exp({NDVI_AGB_PROXY_A} × NDVI_forest + {NDVI_AGB_PROXY_B})",
        "citation":  NDVI_AGB_PROXY_CITATION,
    }


def agb_to_carbon_stock(agb_mg_ha: float, forest_area_ha: float) -> dict:
    """
    Convert an above-ground biomass density estimate to a total carbon stock
    and CO2-equivalent for the forested portion of the AOI only.

    Uses IPCC 2006 Guidelines Vol.4 Ch.4 default biomass-to-carbon fraction
    (0.47) and the standard CO2/C molecular weight ratio — both real,
    citable constants (unlike the AGB proxy itself, which is illustrative).

    Parameters
    ----------
    agb_mg_ha       : above-ground biomass density, Mg/ha (from ndvi_to_agb_proxy)
    forest_area_ha  : forested area within the AOI, hectares — NOT total AOI area

    Returns
    -------
    dict with carbon_stock_tc, co2e_stock_t, formula
    """
    from config.constants import BIOMASS_TO_CARBON_FACTOR, CARBON_TO_CO2_RATIO

    agb_mg_ha      = max(0.0, float(agb_mg_ha))
    forest_area_ha = max(0.0, float(forest_area_ha))

    total_agb_mg  = agb_mg_ha * forest_area_ha
    carbon_stock_tc = total_agb_mg * BIOMASS_TO_CARBON_FACTOR
    co2e_stock_t    = carbon_stock_tc * CARBON_TO_CO2_RATIO

    return {
        "carbon_stock_tc": round(carbon_stock_tc, 1),
        "co2e_stock_t":    round(co2e_stock_t, 1),
        "carbon_formula": (
            f"C (tC) = AGB (Mg/ha) × forest area (ha) × {BIOMASS_TO_CARBON_FACTOR} "
            f"(IPCC 2006 Vol.4 Ch.4 default) · CO2e = C × {CARBON_TO_CO2_RATIO:.3f}"
        ),
    }


def estimate_forest_carbon_stock(
    land_cover: LandCoverBreakdown,
    ndvi_by_class: dict,
    aoi_area_ha: float,
) -> dict:
    """
    Single entry point for the whole spatial biomass/carbon estimate.
    Fix M5: this function is the ONLY way this module produces a biomass or
    carbon-stock figure, and it structurally cannot blend land-cover classes
    — it always extracts the forest class before calling ndvi_to_agb_proxy(),
    never accepts a pre-blended whole-AOI NDVI.

    Parameters
    ----------
    land_cover    : LandCoverBreakdown — percentages per class, must sum to ~100
    ndvi_by_class : {"forest": float, "agriculture": float, "water": float,
                     "built_up": float, "other": float} — mean NDVI per class
    aoi_area_ha   : total area of the queried buffer, hectares

    Returns
    -------
    dict combining the AGB estimate, carbon stock estimate, and the forest
    area actually used — so a reader can see exactly how much of the AOI
    the estimate is (and is not) claiming to represent.
    """
    forest_pct = max(0.0, min(100.0, float(land_cover.get("forest_pct", 0))))
    forest_area_ha = aoi_area_ha * (forest_pct / 100.0)
    ndvi_forest = float(ndvi_by_class.get("forest", 0.0))

    agb = ndvi_to_agb_proxy(ndvi_forest)
    carbon = agb_to_carbon_stock(agb["agb_mg_ha"], forest_area_ha)

    return {
        **agb,
        **carbon,
        "forest_pct":     round(forest_pct, 1),
        "forest_area_ha": round(forest_area_ha, 1),
        "aoi_area_ha":    round(aoi_area_ha, 1),
        "masking_note": (
            f"Biomass/carbon estimate uses ONLY the {forest_pct:.0f}% of this "
            f"area classified as forest — the remaining {100 - forest_pct:.0f}% "
            f"(agriculture, water, built-up, other) is excluded, not averaged in."
        ),
    }


def classify_forest_loss_trend(annual_loss_ha: list[float]) -> dict:
    """
    Classify a simple year-over-year forest-loss trend from a list of
    annual tree-cover-loss figures (hectares), oldest-first.

    Deliberately minimal: returns a direction and a plain percentage change,
    not a fabricated "risk score" — the original codebase's authored 60/40
    risk-index blend (loss × 0.6 + NDVI × 0.4) was never calibrated against
    an actual degradation outcome and is not reproduced here.
    """
    if not annual_loss_ha or len(annual_loss_ha) < 2:
        return {"direction": "insufficient_data", "change_pct": None}

    first, last = annual_loss_ha[0], annual_loss_ha[-1]
    if first <= 0:
        return {"direction": "insufficient_data", "change_pct": None}

    change_pct = ((last - first) / first) * 100.0
    if change_pct > 10:
        direction = "increasing"
    elif change_pct < -10:
        direction = "decreasing"
    else:
        direction = "stable"

    return {"direction": direction, "change_pct": round(change_pct, 1)}
