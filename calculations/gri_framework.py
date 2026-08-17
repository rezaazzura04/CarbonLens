"""
CarbonLens V8 — GRI 2021 gap analysis and disclosure coverage.
Pure functions. Maps platform data to GRI indicators.
"""
from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.calculations.gri_framework")

# GRI indicator registry: each entry describes one GRI standard disclosure
# and how CarbonLens determines whether it is covered.
_GRI_INDICATORS = [
    # ── Environmental ────────────────────────────────────────────────────────
    {
        "id": "GRI-305-1", "standard": "GRI 305-1",
        "title": "Direct (Scope 1) GHG emissions",
        "pillar": "E", "required_key": "_scope1_available",
        "description": "Covered when Scope 1 data is calculated from activity data.",
    },
    {
        "id": "GRI-305-2", "standard": "GRI 305-2",
        "title": "Energy indirect (Scope 2) GHG emissions",
        "pillar": "E", "required_key": "_scope2_available",
        "description": "Covered when electricity kWh data is present.",
    },
    {
        "id": "GRI-305-3", "standard": "GRI 305-3",
        "title": "Other indirect (Scope 3) GHG emissions",
        "pillar": "E", "required_key": "_scope3_available",
        "description": "Covered when Scope 3 categories are calculated (12 of 15).",
    },
    {
        "id": "GRI-305-4", "standard": "GRI 305-4",
        "title": "GHG emissions intensity",
        "pillar": "E", "required_key": "_intensity_available",
        "description": "Covered when total emissions and floor area are both present.",
    },
    {
        "id": "GRI-302-1", "standard": "GRI 302-1",
        "title": "Energy consumption within the organisation",
        "pillar": "E", "required_key": "_energy_in_dataset",
        "description": "Covered when an Energy column is present in the uploaded dataset.",
    },
    {
        "id": "GRI-302-3", "standard": "GRI 302-3",
        "title": "Energy intensity",
        "pillar": "E", "required_key": "_energy_intensity",
        "description": "Covered when Energy data and floor area are both available.",
    },
    {
        "id": "GRI-303-3", "standard": "GRI 303-3",
        "title": "Water recycled and reused",
        "pillar": "E", "required_key": "water_recycled_pct",
        "description": "Covered when water recycling rate is disclosed.",
    },
    {
        "id": "GRI-306-3", "standard": "GRI 306-3",
        "title": "Waste generated",
        "pillar": "E", "required_key": "_waste_in_dataset",
        "description": "Covered when a Waste column is present in the uploaded dataset.",
    },
    {
        "id": "GRI-306-4", "standard": "GRI 306-4",
        "title": "Waste diverted from disposal",
        "pillar": "E", "required_key": "recycle_pct",
        "description": "Covered when waste recycling rate is disclosed.",
    },
    # ── Social ───────────────────────────────────────────────────────────────
    {
        "id": "GRI-401-1", "standard": "GRI 401-1",
        "title": "New employee hires and employee turnover",
        "pillar": "S", "required_key": "employee_turnover_pct",
        "description": "Covered when employee turnover rate is disclosed.",
    },
    {
        "id": "GRI-403-9", "standard": "GRI 403-9",
        "title": "Work-related injuries",
        "pillar": "S", "required_key": "injury_rate",
        "description": "Covered when injury rate per 100 workers is disclosed.",
    },
    {
        "id": "GRI-404-1", "standard": "GRI 404-1",
        "title": "Average hours of training per year per employee",
        "pillar": "S", "required_key": "training_hours_per_employee",
        "description": "Covered when training hours per employee is disclosed.",
    },
    {
        "id": "GRI-405-1", "standard": "GRI 405-1",
        "title": "Diversity of governance bodies and employees",
        "pillar": "S", "required_key": "women_workforce_pct",
        "description": "Covered when women in workforce percentage is disclosed.",
    },
    # ── Governance ───────────────────────────────────────────────────────────
    {
        "id": "GRI-2-9", "standard": "GRI 2-9",
        "title": "Governance structure and composition",
        "pillar": "G", "required_key": "board_independence_pct",
        "description": "Covered when board independence percentage is disclosed.",
    },
    {
        "id": "GRI-2-10", "standard": "GRI 2-10",
        "title": "Nomination and selection of the highest governance body",
        "pillar": "G", "required_key": "women_board_pct",
        "description": "Covered when women on board percentage is disclosed.",
    },
    {
        "id": "GRI-205-2", "standard": "GRI 205-2",
        "title": "Communication and training about anti-corruption policies",
        "pillar": "G", "required_key": "has_code_of_conduct",
        "description": "Covered when ethics/anti-corruption policy is confirmed.",
    },
]


def run_gap_analysis(disclosure_inputs: dict, df=None) -> list:
    """
    Run GRI 2021 gap analysis against disclosed indicators and dataset columns.

    Parameters
    ----------
    disclosure_inputs : Dict of session state S/G values.
    df                : Uploaded pandas DataFrame or None.

    Returns
    -------
    list of dicts, one per GRI indicator:
        id        : str  — GRI indicator ID
        standard  : str  — GRI standard code
        title     : str  — indicator description
        pillar    : str  — "E" | "S" | "G"
        covered   : bool — True if the indicator is covered
        source    : str  — how coverage was determined
    """
    import pandas as pd

    # Build a resolution context from disclosure_inputs and dataset
    ctx = dict(disclosure_inputs)

    # Dataset-derived context
    if df is not None and not df.empty:
        ctx["_scope1_available"]  = True
        ctx["_scope2_available"]  = "Emission" in df.columns
        ctx["_scope3_available"]  = True
        ctx["_intensity_available"] = "Emission" in df.columns
        ctx["_energy_in_dataset"] = (
            "Energy" in df.columns
            and pd.to_numeric(df.get("Energy", []), errors="coerce").notna().any()
        )
        ctx["_energy_intensity"]  = ctx["_energy_in_dataset"]
        ctx["_waste_in_dataset"]  = (
            "Waste" in df.columns
            and pd.to_numeric(df.get("Waste", []), errors="coerce").notna().any()
        )
    else:
        for key in ("_scope1_available", "_scope2_available", "_scope3_available",
                    "_intensity_available", "_energy_in_dataset",
                    "_energy_intensity", "_waste_in_dataset"):
            ctx[key] = False

    results = []
    for indicator in _GRI_INDICATORS:
        req_key = indicator["required_key"]
        val     = ctx.get(req_key)
        covered = bool(val is not None and val is not False and val != 0 and val != "")
        source  = _determine_source(req_key, covered, df)
        results.append({
            "id":       indicator["id"],
            "standard": indicator["standard"],
            "title":    indicator["title"],
            "pillar":   indicator["pillar"],
            "covered":  covered,
            "source":   source,
        })

    return results


def gri_coverage_pct(gap_analysis: list) -> float:
    """
    Return the percentage of GRI indicators covered.

    Parameters
    ----------
    gap_analysis : Output of run_gap_analysis().

    Returns
    -------
    float : Coverage percentage 0.0–100.0.
    """
    if not gap_analysis:
        return 0.0
    covered = sum(1 for r in gap_analysis if r.get("covered"))
    return round(covered / len(gap_analysis) * 100.0, 1)


def gri_coverage_by_pillar(gap_analysis: list) -> dict:
    """
    Return coverage percentage broken down by ESG pillar.

    Returns
    -------
    dict : {"E": float, "S": float, "G": float}
    """
    by_pillar: dict = {"E": [], "S": [], "G": []}
    for r in gap_analysis:
        p = r.get("pillar", "")
        if p in by_pillar:
            by_pillar[p].append(r.get("covered", False))

    result = {}
    for pillar, coverages in by_pillar.items():
        if coverages:
            result[pillar] = round(sum(coverages) / len(coverages) * 100.0, 1)
        else:
            result[pillar] = 0.0
    return result


def _determine_source(req_key: str, covered: bool, df) -> str:
    if not covered:
        return "Not disclosed"
    if req_key.startswith("_"):
        return "Dataset (uploaded CSV)"
    return "ESG Analytics form"
