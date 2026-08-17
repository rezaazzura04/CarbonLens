"""
CarbonLens V8 — Decarbonization calculations.
Phase 5-A: Target Tracker + Scenario Simulator.

Pure functions. No Streamlit. No I/O. No side effects.
All inputs must be explicitly provided — no session state reads.

IMPORTANT LABELLING RULE (blueprint §6):
  Every modelled value carries an assumption_type label.
  "Measured"           — from actual meter/bill data
  "User-provided"      — entered by user in this session
  "CarbonLens default" — platform default assumption
  "Modelled estimate"  — derived by scenario calculation
  Never present a modelled reduction as a measured reduction.
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.calculations.decarbonization")


# ── Target calculation ────────────────────────────────────────────────────────

def calculate_target_emissions(baseline_kg: float, reduction_pct: float) -> float:
    """
    Compute target emissions as: baseline × (1 − reduction_pct / 100).

    Parameters
    ----------
    baseline_kg   : Canonical baseline emissions in kg CO2e from ComputedState.
    reduction_pct : Desired reduction percentage (0–100).

    Returns
    -------
    float : Target emissions in kg CO2e. Never negative.
    """
    if baseline_kg < 0:
        raise ValueError(f"baseline_kg must be ≥ 0, got {baseline_kg}")
    if not (0 <= reduction_pct <= 100):
        raise ValueError(f"reduction_pct must be in [0, 100], got {reduction_pct}")
    return round(max(0.0, baseline_kg * (1.0 - reduction_pct / 100.0)), 4)


def calculate_target_gap(scenario_kg: float, target_kg: float) -> dict:
    """
    Calculate the gap between a scenario result and the reduction target.

    Parameters
    ----------
    scenario_kg : Scenario total emissions in kg CO2e.
    target_kg   : Target emissions in kg CO2e.

    Returns
    -------
    dict:
        gap_kg        : scenario − target (positive = above target)
        above_target  : bool
        gap_pct       : gap as % of target
        label         : human-readable interpretation
    """
    gap_kg = round(scenario_kg - target_kg, 4)
    above  = gap_kg > 0
    gap_pct = round(gap_kg / target_kg * 100, 2) if target_kg > 0 else 0.0
    if abs(gap_kg) < 0.01:
        label = "Scenario meets the target exactly."
    elif above:
        label = (
            f"Scenario is {abs(gap_pct):.1f}% above target — "
            f"{abs(gap_kg)/1000:.2f} tCO2e additional reduction needed."
        )
    else:
        label = (
            f"Scenario exceeds the target by {abs(gap_pct):.1f}% — "
            f"{abs(gap_kg)/1000:.2f} tCO2e below target."
        )
    return {
        "gap_kg":       gap_kg,
        "above_target": above,
        "gap_pct":      gap_pct,
        "label":        label,
    }


# ── Lever application ─────────────────────────────────────────────────────────

def apply_energy_efficiency_lever(
    scope1_kg: float,
    scope2_kg: float,
    reduction_pct: float,
) -> dict:
    """
    Apply proportional energy efficiency reduction to Scope 1 and Scope 2.

    Assumption type: typically "CarbonLens default" or "User-provided".
    Limitation: proportional reduction across all sources — actual savings
    depend on which specific equipment is retrofitted.

    Returns dict with new_scope1_kg, new_scope2_kg, reduction_kg.
    """
    _validate_pct("reduction_pct", reduction_pct)
    factor = 1.0 - reduction_pct / 100.0
    new_s1 = round(scope1_kg * factor, 4)
    new_s2 = round(scope2_kg * factor, 4)
    return {
        "new_scope1_kg":  new_s1,
        "new_scope2_kg":  new_s2,
        "reduction_kg":   round((scope1_kg - new_s1) + (scope2_kg - new_s2), 4),
        "assumption":     "Modelled estimate",
    }


def apply_renewable_lever(scope2_kg: float, renewable_pct: float) -> dict:
    """
    Apply renewable electricity substitution to Scope 2.

    Logic: renewable_pct of electricity assumed to come from zero-emission source.
    Remaining (1 − renewable_pct/100) retains the PLN grid factor already embedded
    in scope2_kg.

    Limitation: actual renewable tariff and residual PLN vary by PPA contract.
    """
    _validate_pct("renewable_pct", renewable_pct)
    new_s2      = round(scope2_kg * (1.0 - renewable_pct / 100.0), 4)
    reduction   = round(scope2_kg - new_s2, 4)
    return {
        "new_scope2_kg": new_s2,
        "reduction_kg":  reduction,
        "assumption":    "Modelled estimate",
    }


def apply_fuel_switching_lever(scope1_kg: float, diesel_share: float, switching_pct: float) -> dict:
    """
    Apply diesel → biodiesel switching reduction to Scope 1.

    Parameters
    ----------
    scope1_kg     : Total Scope 1 in kg CO2e.
    diesel_share  : % of Scope 1 attributable to diesel (0–100).
    switching_pct : % of diesel fleet switched to B30 (0–100).

    B30 net reduction: 20% vs pure diesel (biogenic exclusion per GHG Protocol).
    Limitation: actual blend ratio and supply availability vary.
    """
    _validate_pct("diesel_share",   diesel_share)
    _validate_pct("switching_pct",  switching_pct)
    B30_NET_REDUCTION = 0.20   # 20% lower CO2e than pure diesel
    diesel_kg   = scope1_kg * (diesel_share / 100.0)
    switched_kg = diesel_kg * (switching_pct / 100.0)
    reduction   = round(switched_kg * B30_NET_REDUCTION, 4)
    return {
        "new_scope1_kg": round(scope1_kg - reduction, 4),
        "reduction_kg":  reduction,
        "assumption":    "Modelled estimate",
    }


def apply_electrification_lever(
    scope1_kg:      float,
    scope2_kg:      float,
    petrol_share:   float,
    electrify_pct:  float,
    pln_ef:         float,
    vehicle_kwhkm:  float = 0.2,
    annual_km:      float = 50000,
) -> dict:
    """
    Electrification of mobile fleet — moves emissions from S1 to S2.

    Net effect depends on PLN grid carbon intensity at time of electrification.
    Limitation: high uncertainty — result is a directional modelled estimate only.
    """
    _validate_pct("petrol_share",  petrol_share)
    _validate_pct("electrify_pct", electrify_pct)
    if pln_ef <= 0:
        raise ValueError(f"pln_ef must be > 0, got {pln_ef}")

    petrol_kg        = scope1_kg * (petrol_share / 100.0)
    fleet_to_elec    = petrol_kg * (electrify_pct / 100.0)
    s1_reduction     = round(fleet_to_elec, 4)

    # Approximate electricity consumption for electrified fleet
    kwh_needed       = annual_km * vehicle_kwhkm
    s2_increase      = round(kwh_needed * pln_ef, 4)

    net_reduction    = round(s1_reduction - s2_increase, 4)
    return {
        "new_scope1_kg":  round(scope1_kg - s1_reduction, 4),
        "new_scope2_kg":  round(scope2_kg + s2_increase, 4),
        "s1_reduction_kg": s1_reduction,
        "s2_increase_kg":  s2_increase,
        "net_reduction_kg": net_reduction,
        "assumption":      "Modelled estimate",
    }


def apply_waste_reduction_lever(scope3_kg: float, waste_share: float, reduction_pct: float) -> dict:
    """
    Apply waste generation reduction to Scope 3 (Cat 5 proxy).

    Parameters
    ----------
    scope3_kg    : Total Scope 3 in kg CO2e.
    waste_share  : % of Scope 3 attributable to waste (0–100).
    reduction_pct: Target waste reduction percentage (0–100).

    Limitation: applied proportionally to waste share of total S3.
    Requires waste tonnage data for meaningful projection.
    """
    _validate_pct("waste_share",   waste_share)
    _validate_pct("reduction_pct", reduction_pct)
    waste_kg  = scope3_kg * (waste_share / 100.0)
    reduction = round(waste_kg * (reduction_pct / 100.0), 4)
    return {
        "new_scope3_kg": round(scope3_kg - reduction, 4),
        "reduction_kg":  reduction,
        "assumption":    "Modelled estimate",
    }


def apply_supply_chain_lever(scope3_kg: float, upstream_share: float, reduction_pct: float) -> dict:
    """
    Apply supply chain engagement reduction to Scope 3 (Cat 1 proxy).

    HIGH UNCERTAINTY. Modelled estimate only.
    Actual reductions require supplier-level data and verification.
    """
    _validate_pct("upstream_share", upstream_share)
    _validate_pct("reduction_pct",  reduction_pct)
    upstream_kg = scope3_kg * (upstream_share / 100.0)
    reduction   = round(upstream_kg * (reduction_pct / 100.0), 4)
    return {
        "new_scope3_kg": round(scope3_kg - reduction, 4),
        "reduction_kg":  reduction,
        "assumption":    "Modelled estimate",
    }


# ── Scenario total assembly ───────────────────────────────────────────────────

def apply_levers_to_baseline(
    scope1_kg: float,
    scope2_kg: float,
    scope3_kg: float,
    levers:    list,
    pln_ef:    float = 0.716,
) -> dict:
    """
    Apply an ordered list of lever configs to the baseline.

    Each lever is processed sequentially — lever N operates on the
    emissions remaining after levers 0..(N-1) have been applied.
    This is conservative: subsequent levers have diminishing returns.

    Parameters
    ----------
    scope1_kg, scope2_kg, scope3_kg : Baseline scope values in kg CO2e.
    levers  : list of lever config dicts (from ScenarioConfig.levers).
    pln_ef  : PLN grid emission factor (for electrification lever net calc).

    Returns
    -------
    dict with final scope1/2/3/total, reduction_kg, reduction_pct, lever_breakdown.
    """
    orig_total = scope1_kg + scope2_kg + scope3_kg
    s1, s2, s3 = scope1_kg, scope2_kg, scope3_kg
    lever_breakdown = []

    for lever in levers:
        lid  = lever.get("lever_id", "")
        pct  = float(lever.get("reduction_pct", 0))
        before_total = s1 + s2 + s3

        if lid == "energy_efficiency":
            r = apply_energy_efficiency_lever(s1, s2, pct)
            s1 = r["new_scope1_kg"]
            s2 = r["new_scope2_kg"]
            reduction = r["reduction_kg"]

        elif lid == "renewable_electricity":
            r = apply_renewable_lever(s2, pct)
            s2 = r["new_scope2_kg"]
            reduction = r["reduction_kg"]

        elif lid == "fuel_switching":
            r = apply_fuel_switching_lever(s1, 60.0, pct)   # 60% diesel share default
            s1 = r["new_scope1_kg"]
            reduction = r["reduction_kg"]

        elif lid == "electrification":
            r = apply_electrification_lever(s1, s2, 30.0, pct, pln_ef)
            s1 = r["new_scope1_kg"]
            s2 = r["new_scope2_kg"]
            reduction = r["net_reduction_kg"]

        elif lid == "waste_reduction":
            r = apply_waste_reduction_lever(s3, 20.0, pct)  # 20% waste share default
            s3 = r["new_scope3_kg"]
            reduction = r["reduction_kg"]

        elif lid == "supply_chain":
            r = apply_supply_chain_lever(s3, 30.0, pct)     # 30% upstream share default
            s3 = r["new_scope3_kg"]
            reduction = r["reduction_kg"]

        else:
            log.warning(f"Unknown lever_id {lid!r} — skipped")
            reduction = 0.0

        lever_breakdown.append({
            "lever_id":     lid,
            "reduction_kg": reduction,
            "pct_contribution": round(reduction / orig_total * 100, 2) if orig_total else 0,
            "assumption":   "Modelled estimate",
        })

    total_new  = round(s1 + s2 + s3, 4)
    total_red  = round(orig_total - total_new, 4)
    red_pct    = round(total_red / orig_total * 100, 2) if orig_total else 0.0

    return {
        "scope1_kg":      round(s1, 4),
        "scope2_kg":      round(s2, 4),
        "scope3_kg":      round(s3, 4),
        "total_kg":       total_new,
        "reduction_kg":   total_red,
        "reduction_pct":  red_pct,
        "lever_breakdown": lever_breakdown,
        "assumption":      "Modelled estimate — see lever assumptions for details",
    }


# ── Trajectory ────────────────────────────────────────────────────────────────

def build_annual_trajectory(
    baseline_kg:  float,
    target_kg:    float,
    scenario_kg:  float,
    baseline_year: int,
    target_year:   int,
) -> list:
    """
    Build a linear annual trajectory from baseline to target/scenario.

    Returns a list of {year: int, target_kg: float, scenario_kg: float}.
    Trajectory is linear interpolation — actual pathway will differ.

    Limitation: linear interpolation only. Real decarbonisation pathways
    are non-linear and depend on investment schedules.
    """
    if target_year <= baseline_year:
        return []
    years = list(range(baseline_year, target_year + 1))
    n     = len(years) - 1
    trajectory = []
    for i, yr in enumerate(years):
        frac = i / n if n > 0 else 1.0
        t_val = round(baseline_kg + (target_kg   - baseline_kg) * frac, 2)
        s_val = round(baseline_kg + (scenario_kg - baseline_kg) * frac, 2)
        trajectory.append({"year": yr, "target_kg": t_val, "scenario_kg": s_val})
    return trajectory


# ── Validation ────────────────────────────────────────────────────────────────

def validate_lever_config(lever: dict) -> list:
    """
    Validate a lever configuration dict. Returns list of warning strings (empty = valid).
    """
    warnings = []
    pct = float(lever.get("reduction_pct", 0))
    if not (0 < pct <= 100):
        warnings.append(
            f"reduction_pct={pct} is out of range (0–100). "
            "No reduction will be applied."
        )
    yr = int(lever.get("implementation_year", 0))
    if yr < 2024 or yr > 2050:
        warnings.append(
            f"implementation_year={yr} is unusual (expected 2024–2050)."
        )
    return warnings


# ── Private helpers ───────────────────────────────────────────────────────────

def _validate_pct(name: str, value: float) -> None:
    if not (0 <= value <= 100):
        raise ValueError(f"{name} must be in [0, 100], got {value}")
