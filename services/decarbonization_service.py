"""
CarbonLens V8 — Decarbonization service. Phase 5-A.

Orchestrates scenario creation, lever application, and target tracking.
All calculations delegated to calculations/decarbonization.py.
All state persistence through repository layer.
All audit events emitted through audit/writer.py.

No formulas. No Streamlit. No direct session_state access.
"""
from __future__ import annotations
import datetime
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.decarbonization")


# ── Scenario state management ──────────────────────────────────────────────────

def get_decarb_state() -> dict:
    """
    Return the current DecarbonizationState from the active session slot.
    Returns make_empty_decarb_state() if nothing is persisted yet.
    """
    try:
        from repository.session_repo import get
        state = get("decarb_state")
        if state and isinstance(state, dict):
            return state
    except Exception as exc:
        log.warning(f"get_decarb_state failed: {exc}")
    from models.decarbonization import make_empty_decarb_state
    return make_empty_decarb_state()


def save_decarb_state(state: dict) -> None:
    """Persist the DecarbonizationState to the active session slot."""
    try:
        from repository.session_repo import set
        state["last_modified"] = datetime.datetime.now().isoformat(timespec="seconds")
        set("decarb_state", state)
    except Exception as exc:
        log.warning(f"save_decarb_state failed: {exc}")


# ── Target management ─────────────────────────────────────────────────────────

def set_reduction_target(
    baseline_kg:         float,
    baseline_period:     str,
    target_year:         str,
    reduction_target_pct: float,
) -> dict:
    """
    Define or update the reduction target.

    Delegates target_kg calculation to calculations.decarbonization.
    Persists to session. Returns the full target dict.

    Parameters
    ----------
    baseline_kg          : From ComputedState — never re-computed here.
    baseline_period      : Reporting period label (e.g. "2024").
    target_year          : Target year string (e.g. "2030").
    reduction_target_pct : Target reduction percentage (0–100).
    """
    from calculations.decarbonization import calculate_target_emissions

    target_kg = calculate_target_emissions(baseline_kg, reduction_target_pct)

    target = {
        "baseline_period":      baseline_period,
        "target_year":          target_year,
        "reduction_target_pct": round(reduction_target_pct, 2),
        "baseline_kg":          round(baseline_kg, 4),
        "target_kg":            target_kg,
        "assumption_type":      "user-provided",
    }

    state = get_decarb_state()
    state["target"] = target
    save_decarb_state(state)
    log.info(f"Target set: {reduction_target_pct:.1f}% reduction by {target_year}")
    return target


# ── Scenario management ───────────────────────────────────────────────────────

def create_scenario(
    scenario_id:  str,
    name:         str,
    description:  str = "",
) -> dict:
    """
    Create or overwrite a scenario. Emits scenario_created audit event.

    Parameters
    ----------
    scenario_id : "A" | "B" | "C"
    name        : User-visible scenario name.
    description : Optional description.
    """
    if scenario_id not in ("A", "B", "C"):
        raise ValueError(f"scenario_id must be 'A', 'B', or 'C', got {scenario_id!r}")

    now = datetime.datetime.now().isoformat(timespec="seconds")
    scenario = {
        "id":          scenario_id,
        "name":        name,
        "description": description,
        "levers":      [],
        "created_at":  now,
        "modified_at": now,
    }

    state = get_decarb_state()
    state["scenarios"][scenario_id] = scenario
    state["active_scenario_id"]     = scenario_id
    save_decarb_state(state)

    _emit("scenario_created",
          f"Scenario {scenario_id} '{name}' created",
          {"scenario_id": scenario_id, "name": name})
    return scenario


def update_scenario_levers(scenario_id: str, levers: list) -> dict:
    """
    Update the lever list for a scenario. Emits scenario_modified audit event.
    Validates each lever config before saving.

    Parameters
    ----------
    scenario_id : "A" | "B" | "C"
    levers      : List of lever config dicts.
    """
    from calculations.decarbonization import validate_lever_config

    warnings_all = []
    for lever in levers:
        warnings_all.extend(validate_lever_config(lever))
    if warnings_all:
        log.warning(f"Lever validation warnings for scenario {scenario_id}: {warnings_all}")

    state    = get_decarb_state()
    scenario = state.get("scenarios", {}).get(scenario_id)
    if not scenario:
        raise KeyError(f"Scenario {scenario_id!r} not found — create it first")

    scenario["levers"]      = levers
    scenario["modified_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    state["scenarios"][scenario_id] = scenario
    save_decarb_state(state)

    _emit("scenario_modified",
          f"Scenario {scenario_id} updated — {len(levers)} lever(s)",
          {"scenario_id": scenario_id, "n_levers": len(levers),
           "lever_ids": [l.get("lever_id") for l in levers],
           "validation_warnings": warnings_all})
    return scenario


def save_named_scenario(scenario_id: str) -> dict:
    """
    Mark a scenario as explicitly saved (user action). Emits scenario_saved.
    """
    state    = get_decarb_state()
    scenario = state.get("scenarios", {}).get(scenario_id)
    if not scenario:
        raise KeyError(f"Scenario {scenario_id!r} not found")

    scenario["modified_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    state["scenarios"][scenario_id] = scenario
    save_decarb_state(state)

    target = state.get("target") or {}
    _emit("scenario_saved",
          f"Scenario {scenario_id} '{scenario['name']}' saved",
          {"scenario_id": scenario_id, "name": scenario["name"],
           "n_levers": len(scenario["levers"]),
           "target_year": target.get("target_year",""),
           "reduction_target_pct": target.get("reduction_target_pct", 0)})
    return scenario


# ── Scenario calculation ───────────────────────────────────────────────────────

def calculate_scenario_result(
    scenario:  dict,
    scope1_kg: float,
    scope2_kg: float,
    scope3_kg: float,
    pln_ef:    float,
    target:    Optional[dict] = None,
) -> dict:
    """
    Compute the emissions result for one scenario against the baseline.

    All arithmetic delegated to calculations.decarbonization.apply_levers_to_baseline().
    Returns a ScenarioResult dict.

    Parameters
    ----------
    scenario  : ScenarioConfig dict from get_decarb_state().
    scope1/2/3_kg : Baseline scope values from ComputedState.
    pln_ef    : PLN emission factor from ComputedState (for electrification lever).
    target    : ReductionTarget dict or None.
    """
    from calculations.decarbonization import apply_levers_to_baseline, calculate_target_gap

    baseline_total = scope1_kg + scope2_kg + scope3_kg
    levers         = scenario.get("levers", [])

    result = apply_levers_to_baseline(scope1_kg, scope2_kg, scope3_kg, levers, pln_ef)

    gap = {}
    if target:
        target_kg = float(target.get("target_kg", 0))
        gap       = calculate_target_gap(result["total_kg"], target_kg)

    return {
        "scenario_id":     scenario.get("id",   ""),
        "scenario_name":   scenario.get("name", ""),
        "scope1_kg":       result["scope1_kg"],
        "scope2_kg":       result["scope2_kg"],
        "scope3_kg":       result["scope3_kg"],
        "total_kg":        result["total_kg"],
        "reduction_kg":    result["reduction_kg"],
        "reduction_pct":   result["reduction_pct"],
        "target_gap_kg":   gap.get("gap_kg",       0.0),
        "above_target":    gap.get("above_target",  True),
        "gap_label":       gap.get("label",         ""),
        "lever_breakdown": result["lever_breakdown"],
        "assumption":      result["assumption"],
    }


def get_all_scenario_results(
    scope1_kg: float,
    scope2_kg: float,
    scope3_kg: float,
    pln_ef:    float,
) -> list:
    """
    Return computed results for all defined scenarios.

    Parameters come from ComputedState — never re-read from session.
    Returns list of ScenarioResult dicts.
    """
    state   = get_decarb_state()
    target  = state.get("target")
    results = []
    for sid in ("A", "B", "C"):
        scenario = state.get("scenarios", {}).get(sid)
        if scenario:
            results.append(
                calculate_scenario_result(
                    scenario, scope1_kg, scope2_kg, scope3_kg, pln_ef, target
                )
            )
    return results


# ── Available levers ──────────────────────────────────────────────────────────

def get_available_levers(
    scope1_kg: float = 0,
    scope2_kg: float = 0,
    scope3_kg: float = 0,
) -> list:
    """
    Return the full lever catalogue with availability flags.
    Levers requiring scope data that is zero are flagged as unavailable.

    Parameters from ComputedState baseline — never re-computed.
    """
    from models.decarbonization import LEVER_CATALOGUE
    enriched = []
    for lever in LEVER_CATALOGUE:
        lid = lever["lever_id"]
        available = True
        note      = ""
        if lid in ("energy_efficiency",) and (scope1_kg + scope2_kg) == 0:
            available = False
            note      = "No Scope 1+2 emissions in baseline."
        elif lid == "renewable_electricity" and scope2_kg == 0:
            available = False
            note      = "No Scope 2 electricity in baseline."
        elif lid in ("fuel_switching", "electrification") and scope1_kg == 0:
            available = False
            note      = "No Scope 1 combustion in baseline."
        elif lid in ("waste_reduction", "supply_chain") and scope3_kg == 0:
            available = False
            note      = "No Scope 3 emissions in baseline."
        enriched.append({**lever, "available": available, "unavailable_note": note})
    return enriched


# ── Trajectory ────────────────────────────────────────────────────────────────

def get_trajectory(
    baseline_kg:   float,
    scenario_kg:   float,
    baseline_year: int,
    target_year:   int,
    target_kg:     Optional[float] = None,
) -> list:
    """
    Return the annual trajectory for chart rendering.
    Delegates to calculations.decarbonization.build_annual_trajectory().
    """
    from calculations.decarbonization import build_annual_trajectory
    tgt = target_kg if target_kg is not None else scenario_kg
    return build_annual_trajectory(baseline_kg, tgt, scenario_kg,
                                   baseline_year, target_year)


# ── Private helpers ───────────────────────────────────────────────────────────

def _emit(event_type: str, summary: str, detail: dict) -> None:
    """Emit audit event. Never raises — failure is silent."""
    try:
        from audit.writer import write_audit_event
        write_audit_event(event_type=event_type, summary=summary, detail=detail)
    except Exception as exc:
        log.warning(f"Decarbonization audit event failed: {exc}")
