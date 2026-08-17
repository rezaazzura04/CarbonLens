"""
CarbonLens V8 — Carbon service.
Orchestrates Scope 1/2/3 inventory computation.
No formulas. All calculations delegated to calculations/ghg.py.
"""
from __future__ import annotations
import datetime
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.carbon")

# Default Scope split ratios for csv_estimate source
# Used when only a total emission figure is available.
# Documented limitation: hardcoded ratios are a known anti-pattern.
# Future: replace with sector-specific ratios from config.
_ESTIMATE_SCOPE1_RATIO = 0.20
_ESTIMATE_SCOPE2_RATIO = 0.60
_ESTIMATE_SCOPE3_RATIO = 0.20


def determine_scope_source(
    org:          dict,
    df=None,
    scope_inputs: Optional[dict] = None,
) -> str:
    """
    Determine which carbon data source is available, in priority order.

    Priority:
      1. "carbon_accounting" — Carbon Accounting form has non-zero fuel/electricity values
      2. "csv_scope_columns" — uploaded CSV has Scope1/Scope2/Scope3 columns
      3. "csv_estimate"      — uploaded CSV has Emission column (total only)
      4. "none"              — no data available

    Parameters
    ----------
    org          : Organisation dict.
    df           : Uploaded DataFrame or None.
    scope_inputs : Dict of Carbon Accounting form values or None.

    Returns
    -------
    str : One of the four approved scope source strings.
    """
    from config.constants import APPROVED_SCOPE_SOURCES

    # Priority 1: Carbon Accounting form
    if scope_inputs:
        fuel_keys = [
            "diesel_liters", "petrol_liters", "lpg_kg",
            "natural_gas_m3", "cng_m3", "coal_kg",
            "electricity_kwh",
        ]
        has_fuel = any(
            float(scope_inputs.get(k, 0) or 0) > 0
            for k in fuel_keys
        )
        if has_fuel:
            return "carbon_accounting"

    # Priority 2: CSV with explicit scope columns
    if df is not None and not df.empty:
        scope_cols = {"Scope1", "Scope2", "Scope3"}
        if scope_cols.issubset(set(df.columns)):
            return "csv_scope_columns"

    # Priority 3: CSV with total emission only
    if df is not None and not df.empty and "Emission" in df.columns:
        return "csv_estimate"

    return "none"


def compute_carbon_inventory(
    org:          dict,
    df=None,
    scope_inputs: Optional[dict] = None,
    force:        bool = False,
) -> dict:
    """
    Orchestrate GHG inventory computation for one organisation.

    Delegates all arithmetic to calculations.ghg.
    Resolves PLN EF from org.province via calculations.ghg.resolve_pln_ef().
    Emits carbon_recalculated audit event when force=True.

    Parameters
    ----------
    org          : Organisation dict with area_m2, province, sector, etc.
    df           : Uploaded DataFrame or None.
    scope_inputs : Carbon Accounting form values (Scope 1/2/3 activity data).
    force        : If True, emit audit event (indicates user-triggered recompute).

    Returns
    -------
    dict matching CarbonInventory TypedDict schema.
    """
    import pandas as pd
    from calculations import ghg, benchmarking

    org_id   = org.get("org_id", "")
    period   = org.get("reporting_period", "")
    area_m2  = float(org.get("area_m2", 0) or 0)
    province = org.get("province", "")
    sector   = org.get("sector", "Manufacturing")

    pln_ef   = ghg.resolve_pln_ef(province)
    source   = determine_scope_source(org, df, scope_inputs)

    log.info(f"compute_carbon_inventory: org={org_id[:8]} source={source}")

    # ── Branch by source ──────────────────────────────────────────────────────

    if source == "carbon_accounting":
        si = scope_inputs or {}
        s1 = ghg.calculate_scope1(
            diesel_liters   = float(si.get("diesel_liters",   0) or 0),
            petrol_liters   = float(si.get("petrol_liters",   0) or 0),
            lpg_kg          = float(si.get("lpg_kg",          0) or 0),
            natural_gas_m3  = float(si.get("natural_gas_m3",  0) or 0),
            cng_m3          = float(si.get("cng_m3",          0) or 0),
            coal_kg         = float(si.get("coal_kg",         0) or 0),
            biomass_kg      = float(si.get("biomass_kg",      0) or 0),
        )
        s2 = ghg.calculate_scope2(
            electricity_kwh = float(si.get("electricity_kwh", 0) or 0),
            pln_ef          = pln_ef,
        )
        s3 = ghg.calculate_scope3(
            cat1_spend             = float(si.get("cat1_spend",             0) or 0),
            cat2_spend             = float(si.get("cat2_spend",             0) or 0),
            cat3_kwh               = float(si.get("cat3_kwh",               0) or 0),
            cat4_tonne_km          = float(si.get("cat4_tonne_km",          0) or 0),
            cat5_waste_kg          = float(si.get("cat5_waste_kg",          0) or 0),
            cat6_travel_km         = float(si.get("cat6_travel_km",         0) or 0),
            cat7_commute_km        = float(si.get("cat7_commute_km",        0) or 0),
            cat8_leased_spend      = float(si.get("cat8_leased_spend",      0) or 0),
            cat9_downstream_tkm    = float(si.get("cat9_downstream_tkm",    0) or 0),
            cat10_processing_spend = float(si.get("cat10_processing_spend", 0) or 0),
            cat12_eol_kg           = float(si.get("cat12_eol_kg",           0) or 0),
            cat13_downstream_spend = float(si.get("cat13_downstream_spend", 0) or 0),
        )

    elif source == "csv_scope_columns":
        s1_kg = float(pd.to_numeric(df["Scope1"], errors="coerce").sum() or 0)
        s2_kg = float(pd.to_numeric(df["Scope2"], errors="coerce").sum() or 0)
        s3_kg = float(pd.to_numeric(df["Scope3"], errors="coerce").sum() or 0)
        s1 = {"total_kg": s1_kg, "breakdown": {}, "inputs": {}}
        s2 = {"total_kg": s2_kg, "ef_used": pln_ef, "inputs": {}}
        s3 = {"total_kg": s3_kg, "breakdown": {}, "screened_excluded": [], "inputs": {}}

    elif source == "csv_estimate":
        total_kg = float(pd.to_numeric(df["Emission"], errors="coerce").sum() or 0)
        # Convert tCO2e → kg if values are clearly in tonnes (typical CSV unit)
        # Heuristic: if mean > 10,000 treat as kg already; else multiply by 1000
        mean_val = float(pd.to_numeric(df["Emission"], errors="coerce").mean() or 0)
        if mean_val < 10000:
            total_kg *= 1000.0   # tCO2e → kg CO2e
        s1_kg = round(total_kg * _ESTIMATE_SCOPE1_RATIO, 4)
        s2_kg = round(total_kg * _ESTIMATE_SCOPE2_RATIO, 4)
        s3_kg = round(total_kg * _ESTIMATE_SCOPE3_RATIO, 4)
        s1 = {"total_kg": s1_kg, "breakdown": {}, "inputs": {}}
        s2 = {"total_kg": s2_kg, "ef_used": pln_ef, "inputs": {}}
        s3 = {
            "total_kg": s3_kg, "breakdown": {},
            "screened_excluded": ["Estimate — no category breakdown available"],
            "inputs": {},
        }

    else:   # "none"
        s1 = {"total_kg": 0.0, "breakdown": {}, "inputs": {}}
        s2 = {"total_kg": 0.0, "ef_used": pln_ef, "inputs": {}}
        s3 = {"total_kg": 0.0, "breakdown": {}, "screened_excluded": [], "inputs": {}}

    totals   = ghg.aggregate_scope_totals(s1, s2, s3, area_m2)
    bench    = benchmarking.get_benchmark(sector)
    gap      = benchmarking.benchmark_gap(totals["intens_m2"], bench) if bench > 0 else {}
    screened = s3.get("screened_excluded", [])

    inventory = {
        "org_id":            org_id,
        "period":            period,
        "scope1_kg":         totals["scope1_kg"],
        "scope2_kg":         totals["scope2_kg"],
        "scope3_kg":         totals["scope3_kg"],
        "total_kg":          totals["total_kg"],
        "intens_m2":         totals["intens_m2"],
        "scope_source":      source,
        "province":          province,
        "pln_ef_used":       pln_ef,
        "scope3_breakdown":  s3.get("breakdown", {}),
        "screened_excluded": screened,
        "benchmark":         bench,
        "gap":               gap,
        "computed_at":       datetime.datetime.now().isoformat(timespec="seconds"),
    }

    if force:
        _emit_carbon_event(inventory)

    return inventory


def _emit_carbon_event(inventory: dict) -> None:
    """Emit carbon_recalculated audit event. Called only on force recompute."""
    try:
        from audit.writer import write_audit_event
        total_t = round(inventory["total_kg"] / 1000, 2)
        write_audit_event(
            event_type = "carbon_recalculated",
            summary    = (
                f"Carbon inventory recomputed: {total_t:.2f} tCO2e "
                f"(source: {inventory['scope_source']})"
            ),
            detail = {
                "source":    inventory["scope_source"],
                "total_tco2e": total_t,
                "scope1_tco2e": round(inventory["scope1_kg"] / 1000, 2),
                "scope2_tco2e": round(inventory["scope2_kg"] / 1000, 2),
                "scope3_tco2e": round(inventory["scope3_kg"] / 1000, 2),
                "intens_m2": inventory["intens_m2"],
            },
        )
    except Exception as exc:
        log.warning(f"carbon audit event failed: {exc}")
