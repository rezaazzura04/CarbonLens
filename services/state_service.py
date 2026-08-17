"""
CarbonLens V8 — State service.

Primary entry point for all pages that need computed data.
Orchestrates: carbon_service → esg_service → data_quality_service → ComputedState.

Pages call get_computed_state(). They NEVER call the three sub-services directly.

Architecture rules:
  - ComputedState is IMMUTABLE once written (new recomputation → version+1)
  - force=False → cache lookup first; force=True → always recompute and emit audit events
  - All persistence through repository layer (never direct I/O here)
"""
from __future__ import annotations
import logging
import time
from typing import Optional

log = logging.getLogger("carbonlens.services.state")


def get_computed_state(
    org:               dict,
    df                 = None,
    validation:        Optional[dict] = None,
    disclosure_inputs: Optional[dict] = None,
    scope_inputs:      Optional[dict] = None,
    force:             bool = False,
) -> dict:
    """
    Return the current ComputedState for the given organisation.

    Sequence:
      1. Build input_hash from (org_id + period + df_hash)
      2. force=False → check cache; return cached state on hit
      3. Cache miss or force=True → orchestrate full recompute:
         a. carbon_service.compute_carbon_inventory()
         b. esg_service.compute_esg_score()
         c. data_quality_service.compute_data_quality()
         d. state.computed.assemble() → new ComputedState with version+1
      4. Persist to cache + session_repo + disk_repo
      5. Return ComputedState dict

    Parameters
    ----------
    org               : Organisation dict (required — must pass is_org_setup check first)
    df                : Uploaded DataFrame or None
    validation        : ValidationResult dict or None
    disclosure_inputs : S/G indicator values dict or None
    scope_inputs      : Carbon Accounting form values dict or None
    force             : If True, bypass cache and recompute with audit events

    Returns
    -------
    dict matching ComputedState TypedDict schema.
    Raises ValueError if ComputedState invariant validation fails.
    """
    from calculations.utilities import hash_dataframe, hash_inputs
    from state import cache as Cache
    from models.computed_state import make_empty_computed_state

    org_id = org.get("org_id", "")
    period = org.get("reporting_period", "")

    # Build input hash
    df_hash    = hash_dataframe(df) if df is not None else ""
    input_hash = hash_inputs(org_id, period, df_hash)

    # Cache lookup (skip on force)
    if not force:
        cached = Cache.get(input_hash)
        if cached:
            log.debug(f"ComputedState cache HIT org={org_id[:8]}")
            return cached

    # Full recompute
    log.info(f"Computing state: org={org_id[:8]} force={force}")
    start_ms = int(time.time() * 1000)

    carbon = _compute_carbon(org, df, scope_inputs, force)
    esg    = _compute_esg(org, disclosure_inputs, carbon, force)
    dq     = _compute_dq(df, validation, disclosure_inputs, force)

    # Load previous state for version chaining
    previous = _load_previous(org_id)

    from state.computed import assemble
    try:
        state = assemble(
            org_id  = org_id,
            period  = period,
            carbon  = carbon,
            esg     = esg,
            dq      = dq,
            previous= previous,
            computation_time_ms = int(time.time() * 1000) - start_ms,
        )
    except ValueError as exc:
        log.error(f"ComputedState invariant failed: {exc}")
        raise

    # Persist
    Cache.put(input_hash, state)
    _persist_state(state, org_id)

    log.info(
        f"ComputedState v{state['version']} assembled "
        f"for org={org_id[:8]} "
        f"({state['computation_time_ms']}ms)"
    )
    return state


def invalidate(org_id: str) -> None:
    """
    Invalidate the ComputedState cache for an organisation.
    Called when a new dataset is uploaded or org profile changes.
    """
    from state.cache import invalidate_org
    from repository.session_repo import invalidate_computed_state
    invalidate_org(org_id)
    invalidate_computed_state()
    log.info(f"State invalidated for org={org_id[:8]}")


def get_snapshot(org_id: str) -> Optional[dict]:
    """
    Return the latest persisted ComputedState for an org without recomputing.
    Used for report_service.build_snapshot(). Returns None if no state exists.
    """
    from repository.disk_repo import load_computed_state
    return load_computed_state(org_id)


def get_scope_results(org_id: str) -> dict:
    """
    Return the carbon scope summary from the cached ComputedState.
    Convenience accessor used by provenance panels and summary cards.
    Returns zero-value dict if no state exists.
    """
    from repository.session_repo import get_computed_state as _get
    state = _get()
    if state:
        carbon = state.get("carbon", {})
        return {
            "scope1_kg":  carbon.get("scope1_kg", 0.0),
            "scope2_kg":  carbon.get("scope2_kg", 0.0),
            "scope3_kg":  carbon.get("scope3_kg", 0.0),
            "total_kg":   carbon.get("total_kg",  0.0),
            "intens_m2":  carbon.get("intens_m2", 0.0),
            "source":     carbon.get("scope_source", "none"),
        }
    return {"scope1_kg": 0, "scope2_kg": 0, "scope3_kg": 0,
            "total_kg": 0, "intens_m2": 0, "source": "none"}


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_carbon(org, df, scope_inputs, force):
    from services.carbon_service import compute_carbon_inventory
    try:
        return compute_carbon_inventory(org, df, scope_inputs, force=force)
    except Exception as exc:
        log.error(f"carbon_service failed: {exc}", exc_info=True)
        from models.carbon import make_zero_inventory
        return make_zero_inventory(
            org.get("org_id", ""), org.get("reporting_period", ""),
            org.get("province", ""),
        )


def _compute_esg(org, disclosure_inputs, carbon, force):
    from services.esg_service import compute_esg_score
    try:
        return compute_esg_score(org, disclosure_inputs, carbon, force=force)
    except Exception as exc:
        log.error(f"esg_service failed: {exc}", exc_info=True)
        from models.esg import make_provisional_esg
        return make_provisional_esg(org.get("org_id", ""))


def _compute_dq(df, validation, disclosure_inputs, force):
    from services.data_quality_service import compute_data_quality
    try:
        return compute_data_quality(df, validation, disclosure_inputs, force=force)
    except Exception as exc:
        log.error(f"data_quality_service failed: {exc}", exc_info=True)
        from models.data_quality import make_no_data_quality
        return make_no_data_quality()


def _load_previous(org_id: str) -> Optional[dict]:
    """Load the previous ComputedState for version chaining."""
    try:
        from repository.session_repo import get_computed_state as _get
        return _get()
    except Exception:
        return None


def _persist_state(state: dict, org_id: str) -> None:
    """Persist ComputedState to all storage layers."""
    try:
        from repository.session_repo import set_computed_state
        set_computed_state(state)
    except Exception as exc:
        log.warning(f"session_repo persist failed: {exc}")
    try:
        from repository.disk_repo import save_computed_state
        save_computed_state(state, org_id)
    except Exception as exc:
        log.warning(f"disk_repo persist failed: {exc}")


def get_trend_data() -> dict:
    """
    Return pre-processed chart data for the Executive Summary trend chart.
    Calls calculations.forecasting internally — page never touches calculations.

    Returns
    -------
    dict with keys:
        months         : list[str]   — month labels from uploaded dataset
        emissions_tco2e: list[float] — monthly emissions in tCO2e
        forecast       : dict        — predict_next_emission() output
        trend          : dict        — detect_trend() output
        annual_tco2e   : float       — annual projection in tCO2e
        has_data       : bool        — False when no dataset is loaded
    """
    try:
        from repository.session_repo import get_uploaded_df
        import pandas as pd
        df = get_uploaded_df()
    except Exception:
        df = None

    _empty = {
        "months": [], "emissions_tco2e": [], "has_data": False,
        "forecast": {"next_month": 0, "trend": "insufficient_data", "r2": 0, "slope": 0},
        "trend":    {"direction": "insufficient_data", "slope_kg_mo": 0, "description": ""},
        "annual_tco2e": 0.0,
    }

    if df is None or df.empty or "Emission" not in df.columns:
        return _empty

    try:
        import pandas as pd
        from calculations.forecasting import predict_next_emission, detect_trend, annual_projection
        from calculations.utilities import kg_to_tonne

        emission_s = pd.to_numeric(df["Emission"], errors="coerce").fillna(0)
        months_    = df["Month"].astype(str).tolist() if "Month" in df.columns else \
                     [str(i+1) for i in range(len(emission_s))]

        # Convert tCO2e: if mean < 10000, assume values are in tCO2e already
        mean_val = emission_s.mean()
        if mean_val < 10000:
            emissions_tco2e = emission_s.tolist()
        else:
            emissions_tco2e = (emission_s / 1000).tolist()

        forecast   = predict_next_emission(df)
        trend      = detect_trend(df)
        annual_kg  = annual_projection(df)
        annual_t   = round(kg_to_tonne(annual_kg) if mean_val >= 10000 else annual_kg, 2)

        # Convert forecast to tCO2e
        if mean_val >= 10000 and forecast.get("next_month", 0) > 0:
            forecast = dict(forecast)
            forecast["next_month"] = round(kg_to_tonne(forecast["next_month"]), 2)

        return {
            "months":          months_,
            "emissions_tco2e": emissions_tco2e,
            "forecast":        forecast,
            "trend":           trend,
            "annual_tco2e":    annual_t,
            "has_data":        True,
        }
    except Exception as exc:
        log.warning(f"get_trend_data failed: {exc}")
        return _empty


def get_active_organisation() -> Optional[dict]:
    """
    Return the active Organisation dict for the current session.
    Exposed here so pages never import from state.session directly.
    Returns None if no org is configured.
    """
    try:
        from state.session import get_active_org
        return get_active_org()
    except Exception as exc:
        log.warning(f"get_active_organisation failed: {exc}")
        return None


def get_disclosure_inputs() -> dict:
    """
    Return the S/G disclosure inputs from the current session slot.
    Returns empty dict if none recorded yet.
    """
    try:
        from repository.session_repo import get
        return get("disclosure_inputs") or {}
    except Exception:
        return {}


def get_scope_inputs() -> dict:
    """
    Return the Carbon Accounting form inputs from the current session slot.
    Returns empty dict if none recorded yet.
    """
    try:
        from repository.session_repo import get
        return get("scope_inputs") or {}
    except Exception:
        return {}


def save_disclosure_inputs(di: dict) -> None:
    """
    Persist S/G disclosure inputs to the active session slot.
    Called by the ESG Analytics page after form submission.
    Pages must call this instead of accessing session_repo directly.
    """
    try:
        from repository.session_repo import set as _set
        _set("disclosure_inputs", di)
    except Exception as exc:
        log.warning(f"save_disclosure_inputs failed: {exc}")


def get_indicator_breakdown(
    org:    dict,
    di:     dict,
    carbon: dict,
) -> dict:
    """
    Return pre-computed sub-indicator scores for the ESG Analytics display.
    All arithmetic is delegated to calculations.esg_scoring and calculations.utilities.
    Pages never call this — they receive a plain dict of floats.

    Returns
    -------
    dict with keys:
        E: dict — Environmental sub-scores
        S: dict — Social sub-scores
        G: dict — Governance sub-scores
    """
    from calculations.esg_scoring import calculate_carbon_sub_score, score_indicator
    from calculations.utilities import clamp
    from calculations.benchmarking import get_benchmark

    di     = di     or {}
    carbon = carbon or {}
    org    = org    or {}

    sector    = org.get("sector", "Manufacturing")
    benchmark = float(carbon.get("benchmark") or get_benchmark(sector))
    intensity = float(carbon.get("intens_m2", 0))
    renew     = float(org.get("renew_pct",    0) or 0)
    recycle   = float(org.get("recycle_pct",  0) or 0)
    water     = float(di.get("water_recycled_pct", 0) or 0)

    env = {
        "carbon": calculate_carbon_sub_score(intensity, benchmark),
        "energy": clamp(renew),
        "waste":  clamp(recycle),
        "water":  clamp(water),
    }

    turnover = float(di.get("employee_turnover_pct",   0) or 0)
    training = float(di.get("training_hours_per_employee", 0) or 0)
    women_wf = float(di.get("women_workforce_pct",     0) or 0)
    injury   = float(di.get("injury_rate",             0) or 0)

    soc = {
        "retention":  clamp(100.0 - turnover * 5.0),
        "training":   clamp(training / 40.0 * 100.0),
        "diversity":  clamp(women_wf * 2.0),
        "safety":     clamp(100.0 - injury * 50.0),
    }

    board_ind = float(di.get("board_independence_pct", 0) or 0)
    women_bd  = float(di.get("women_board_pct",        0) or 0)
    has_coc   = bool(di.get("has_code_of_conduct", False))
    certs     = list(org.get("certifications") or [])
    disc_pct  = float(di.get("disclosure_score",       0) or 0)

    gov = {
        "board_ind":  clamp(board_ind * 2.0),
        "disclosure": clamp(disc_pct),
        "ethics":     100.0 if has_coc else 0.0,
        "board_div":  clamp(women_bd * 2.5),
        "certs":      clamp(len(certs) * 25.0),
    }

    return {"E": env, "S": soc, "G": gov}


def get_recommendations(state: dict) -> list:
    """
    Return a prioritised list of improvement recommendations derived from ComputedState.
    No arithmetic — rules are applied to pre-computed scores only.

    Returns
    -------
    list of dicts: [{priority, pillar, title, description, action}]
    """
    esg    = state.get("esg",    {})
    carbon = state.get("carbon", {})
    dq     = state.get("data_quality", {})
    conf   = state.get("confidence",   {})

    score       = float(esg.get("score",            0))
    env         = float(esg.get("env",              0))
    social      = float(esg.get("social",           0))
    gov         = float(esg.get("gov",              0))
    is_prov     = bool(esg.get("is_provisional",    True))
    n_disc      = int(esg.get("n_disclosed",        0))
    n_total     = int(esg.get("n_total_indicators", 8))
    gap         = carbon.get("gap", {})
    above_bench = bool(gap.get("above_benchmark",   False))
    gap_pct     = float(gap.get("gap_pct",          0))
    dq_conf     = float(dq.get("confidence_score",  0))
    flags       = dq.get("flagged_fields",          [])

    recs = []

    # Priority 1: Provisional score — most impactful fix
    if is_prov:
        missing = n_total - n_disc
        recs.append({
            "priority":    1,
            "pillar":      "All",
            "title":       f"Complete S/G disclosure ({missing} indicators missing)",
            "description": (
                f"Your ESG score is Provisional because only {n_disc} of {n_total} "
                "Social and Governance indicators are disclosed. "
                "Completing disclosure changes the score status to Substantive."
            ),
            "action":      "Enter missing indicators in ESG Analytics → Scoring & Indicators.",
        })

    # Priority 2: Above carbon benchmark
    if above_bench and gap_pct > 10:
        recs.append({
            "priority":    2,
            "pillar":      "E",
            "title":       f"Reduce carbon intensity ({gap_pct:.1f}% above benchmark)",
            "description": (
                f"Your carbon intensity exceeds the sector benchmark by {gap_pct:.1f}%. "
                "Key levers: increase renewable energy, improve energy efficiency, "
                "and develop a Scope 3 reduction roadmap."
            ),
            "action":      "Review Decarbonization → Scenario & Target Planner.",
        })

    # Priority 3: Weak pillar scores
    weak_pillars = [(p, s) for p, s in [("E", env), ("S", social), ("G", gov)] if s < 60]
    for pillar, pil_score in sorted(weak_pillars, key=lambda x: x[1]):
        labels = {"E": "Environmental", "S": "Social", "G": "Governance"}
        recs.append({
            "priority":    3,
            "pillar":      pillar,
            "title":       f"Improve {labels[pillar]} pillar score ({pil_score:.1f}/100)",
            "description": (
                f"The {labels[pillar]} pillar score is below the satisfactory threshold. "
                "Review indicator targets and disclosure completeness for this pillar."
            ),
            "action":      "Review indicator targets in ESG Analytics.",
        })

    # Priority 4: Data quality
    if dq_conf < 60:
        n_high = sum(1 for f in flags if f.get("severity") == "high")
        recs.append({
            "priority":    4,
            "pillar":      "DQ",
            "title":       f"Resolve data quality issues ({n_high} high-priority flags)",
            "description": (
                f"Dataset quality confidence is {dq_conf:.0f}%. "
                f"There are {n_high} high-priority data quality issues. "
                "Resolving them improves score accuracy."
            ),
            "action":      "Review flagged fields in Data Quality page.",
        })

    return recs[:5]   # cap at 5 recommendations


def get_validation_result() -> dict:
    """
    Return the ValidationResult dict from the active session slot.
    Returns a safe empty result if no upload has occurred.
    """
    try:
        from repository.session_repo import get_validation_result as _get
        result = _get()
        if result:
            return result
    except Exception as exc:
        log.warning(f"get_validation_result failed: {exc}")
    from models.dataset import make_empty_validation
    return make_empty_validation()


def get_quality_history(limit: int = 12) -> list:
    """
    Return a list of historical DQ confidence readings derived from audit events.
    Each entry: {ts: str, confidence: float, validation: str, summary: str}
    Returns empty list if no DQ recomputation events exist.
    """
    try:
        from audit.reader import get_audit_log
        events = get_audit_log(event_type="dq_score_recalculated", limit=limit)
        history = []
        for ev in reversed(events):   # oldest first
            detail = ev.get("detail", {})
            history.append({
                "ts":         str(ev.get("ts", ""))[:16].replace("T", " "),
                "confidence": float(detail.get("confidence", 0)),
                "validation": str(detail.get("validation", "Unknown")),
                "summary":    str(ev.get("summary", "")),
            })
        return history
    except Exception as exc:
        log.warning(f"get_quality_history failed: {exc}")
        return []


def get_methodology_library() -> list:
    """
    Return the complete CarbonLens V8 methodology library.
    28 entries covering ESG scoring, DQ confidence, and GHG inventory methodology.
    All values sourced from approved config constants — no arithmetic.
    """
    from config.constants import (
        ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV,
        ENV_WEIGHT_CARBON, ENV_WEIGHT_ENERGY, ENV_WEIGHT_WASTE, ENV_WEIGHT_WATER,
        SOCIAL_WEIGHT_TURNOVER, SOCIAL_WEIGHT_TRAINING,
        SOCIAL_WEIGHT_DIVERSITY, SOCIAL_WEIGHT_SAFETY,
        GOV_WEIGHT_BOARD_IND, GOV_WEIGHT_DISCLOSURE, GOV_WEIGHT_ETHICS,
        GOV_WEIGHT_BOARD_DIV, GOV_WEIGHT_CERTS,
        CONFIDENCE_PROVISIONAL_FLOOR, CURRENT_METHODOLOGY_VERSION,
        DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION,
        DQ_CONFIDENCE_CAP_ON_FAIL, OUTLIER_REVIEW_Z,
        SCOPE3_CATEGORIES_COVERED, SCOPE3_CATEGORIES_TOTAL,
    )

    def _pct(v): return f"{v*100:.0f}%"

    entries = [
        # ── ESG composite ────────────────────────────────────────────────────
        {"entry_id":"env-pillar-weight", "category":"ESG Composite Weights",
         "name":"Environmental pillar weight", "value":_pct(ESG_WEIGHT_ENV),
         "formula":f"E × {ESG_WEIGHT_ENV}", "gri_reference":"GRI 305, 302, 306, 303",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Environmental factors most material to GHG disclosures."},

        {"entry_id":"soc-pillar-weight", "category":"ESG Composite Weights",
         "name":"Social pillar weight", "value":_pct(ESG_WEIGHT_SOCIAL),
         "formula":f"S × {ESG_WEIGHT_SOCIAL}", "gri_reference":"GRI 401, 403, 404, 405",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Social indicators include workforce and health & safety metrics."},

        {"entry_id":"gov-pillar-weight", "category":"ESG Composite Weights",
         "name":"Governance pillar weight", "value":_pct(ESG_WEIGHT_GOV),
         "formula":f"G × {ESG_WEIGHT_GOV}", "gri_reference":"GRI 2-9, 2-10, 205",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Governance indicators reflect board composition and ethics policies."},

        # ── Environmental sub-indicators ──────────────────────────────────────
        {"entry_id":"env-carbon-weight", "category":"Environmental Sub-indicators",
         "name":"Carbon sub-indicator weight", "value":_pct(ENV_WEIGHT_CARBON),
         "formula":"Score = max(0, 100×(2 − intensity/benchmark))",
         "gri_reference":"GRI 305-4",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Carbon intensity relative to sector benchmark is the primary E driver."},

        {"entry_id":"env-energy-weight", "category":"Environmental Sub-indicators",
         "name":"Energy sub-indicator weight", "value":_pct(ENV_WEIGHT_ENERGY),
         "formula":"Score = renew_pct (0–100)", "gri_reference":"GRI 302-3",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Renewable energy percentage as proxy for energy transition progress."},

        {"entry_id":"env-waste-weight", "category":"Environmental Sub-indicators",
         "name":"Waste sub-indicator weight", "value":_pct(ENV_WEIGHT_WASTE),
         "formula":"Score = recycle_pct (0–100)", "gri_reference":"GRI 306-4",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Waste diversion rate as proxy for circular economy progress."},

        {"entry_id":"env-water-weight", "category":"Environmental Sub-indicators",
         "name":"Water sub-indicator weight", "value":_pct(ENV_WEIGHT_WATER),
         "formula":"Score = water_recycled_pct (0–100)", "gri_reference":"GRI 303-3",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Water recycling rate reflects resource stewardship."},

        # ── Social sub-indicators ─────────────────────────────────────────────
        {"entry_id":"soc-retention-weight", "category":"Social Sub-indicators",
         "name":"Employee retention weight", "value":_pct(SOCIAL_WEIGHT_TURNOVER),
         "formula":"Score = max(0, 100 − turnover_pct × 5)",
         "gri_reference":"GRI 401-1",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Lower turnover indicates higher workforce stability."},

        {"entry_id":"soc-training-weight", "category":"Social Sub-indicators",
         "name":"Training sub-indicator weight", "value":_pct(SOCIAL_WEIGHT_TRAINING),
         "formula":"Score = min(100, training_hrs / 40 × 100)",
         "gri_reference":"GRI 404-1",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"40 hours/year represents adequate training baseline."},

        {"entry_id":"soc-diversity-weight", "category":"Social Sub-indicators",
         "name":"Gender diversity weight", "value":_pct(SOCIAL_WEIGHT_DIVERSITY),
         "formula":"Score = min(100, women_pct × 2)",
         "gri_reference":"GRI 405-1",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"50% women in workforce = full score; linear below."},

        {"entry_id":"soc-safety-weight", "category":"Social Sub-indicators",
         "name":"Safety sub-indicator weight", "value":_pct(SOCIAL_WEIGHT_SAFETY),
         "formula":"Score = max(0, 100 − injury_rate × 50)",
         "gri_reference":"GRI 403-9",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Zero injuries = 100; ≥ 2 per 100 workers = 0."},

        # ── Governance sub-indicators ──────────────────────────────────────────
        {"entry_id":"gov-board-ind-weight", "category":"Governance Sub-indicators",
         "name":"Board independence weight", "value":_pct(GOV_WEIGHT_BOARD_IND),
         "formula":"Score = min(100, board_ind_pct × 2)",
         "gri_reference":"GRI 2-9",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"50% independent directors = full score."},

        {"entry_id":"gov-disclosure-weight", "category":"Governance Sub-indicators",
         "name":"Disclosure score weight", "value":_pct(GOV_WEIGHT_DISCLOSURE),
         "formula":"Score = disclosure_score (0–100)",
         "gri_reference":"GRI 2-3",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Rewards transparency in ESG disclosure process."},

        {"entry_id":"gov-ethics-weight", "category":"Governance Sub-indicators",
         "name":"Ethics policy weight", "value":_pct(GOV_WEIGHT_ETHICS),
         "formula":"Score = 100 if has_code_of_conduct else 0",
         "gri_reference":"GRI 205-2",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Binary: ethics/anti-corruption policy is a baseline governance requirement."},

        {"entry_id":"gov-board-div-weight", "category":"Governance Sub-indicators",
         "name":"Board diversity weight", "value":_pct(GOV_WEIGHT_BOARD_DIV),
         "formula":"Score = min(100, women_board_pct × 2.5)",
         "gri_reference":"GRI 2-10",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"40% women on board = full score."},

        {"entry_id":"gov-certs-weight", "category":"Governance Sub-indicators",
         "name":"Certifications weight", "value":_pct(GOV_WEIGHT_CERTS),
         "formula":"Score = min(100, n_certs × 25)",
         "gri_reference":"GRI 2-24",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C1",
         "rationale":"Each recognised certification adds 25 points; max 4 certs."},

        # ── ESG grade bands ───────────────────────────────────────────────────
        {"entry_id":"grade-a", "category":"ESG Grade Bands",
         "name":"Grade A — Industry Leader", "value":"≥ 85",
         "formula":"score ≥ 85", "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Top-quartile ESG performance relative to CarbonLens scoring model."},

        {"entry_id":"grade-bplus", "category":"ESG Grade Bands",
         "name":"Grade B+ — Above Average", "value":"75 – 84",
         "formula":"75 ≤ score < 85", "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Strong performance across most pillars with minor gaps."},

        {"entry_id":"grade-b", "category":"ESG Grade Bands",
         "name":"Grade B — Satisfactory", "value":"60 – 74",
         "formula":"60 ≤ score < 75", "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Meets baseline expectations; improvement opportunities exist."},

        {"entry_id":"grade-c", "category":"ESG Grade Bands",
         "name":"Grade C — Developing", "value":"45 – 59",
         "formula":"45 ≤ score < 60", "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Below-average performance; structured improvement plan required."},

        {"entry_id":"grade-d", "category":"ESG Grade Bands",
         "name":"Grade D — Needs Improvement", "value":"< 45",
         "formula":"score < 45", "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C2",
         "rationale":"Material ESG gaps; immediate action required."},

        # ── Confidence model ──────────────────────────────────────────────────
        {"entry_id":"esg-provisional-floor", "category":"Confidence Model",
         "name":"ESG provisional floor", "value":f"{CONFIDENCE_PROVISIONAL_FLOOR:.0f}%",
         "formula":"esg_confidence < floor → Provisional label",
         "gri_reference":"",
         "source":"CarbonLens V8 Methodology", "introduced_in":"Phase 0 C3",
         "rationale":"Scores below 50% S/G disclosure are flagged as Provisional."},

        {"entry_id":"dq-completeness-weight", "category":"Data Quality Model",
         "name":"DQ Completeness weight", "value":_pct(DQ_WEIGHT_COMPLETENESS),
         "formula":"env_completeness×0.60 + sg_completeness×0.40",
         "gri_reference":"",
         "source":"CarbonLens V8 Phase 2", "introduced_in":"Phase 2",
         "rationale":"Environmental data completeness weighted higher than S/G."},

        {"entry_id":"dq-consistency-weight", "category":"Data Quality Model",
         "name":"DQ Consistency weight", "value":_pct(DQ_WEIGHT_CONSISTENCY),
         "formula":"% rows passing outlier + duplicate checks",
         "gri_reference":"",
         "source":"CarbonLens V8 Phase 2", "introduced_in":"Phase 2",
         "rationale":"Consistency of monthly data is primary data integrity measure."},

        {"entry_id":"dq-validation-weight", "category":"Data Quality Model",
         "name":"DQ Validation weight", "value":_pct(DQ_WEIGHT_VALIDATION),
         "formula":"Pass=100 · Warning=70 · Fail=0",
         "gri_reference":"",
         "source":"CarbonLens V8 Phase 2", "introduced_in":"Phase 2",
         "rationale":"Upload schema validation is a hard gate; Fail is penalised."},

        {"entry_id":"dq-fail-cap", "category":"Data Quality Model",
         "name":"DQ Fail confidence cap", "value":f"{DQ_CONFIDENCE_CAP_ON_FAIL:.0f}%",
         "formula":"min(blended, cap) when validation == Fail",
         "gri_reference":"",
         "source":"CarbonLens V8 Phase 2", "introduced_in":"Phase 2",
         "rationale":"Hard ceiling ensures Fail validation is visible in the score."},

        {"entry_id":"dq-outlier-z", "category":"Data Quality Model",
         "name":"Outlier detection z-threshold", "value":str(OUTLIER_REVIEW_Z),
         "formula":"z_score = (x − μ) / σ; flag if |z| > threshold",
         "gri_reference":"",
         "source":"CarbonLens V8 Phase 2", "introduced_in":"Phase 2",
         "rationale":"z=2.0 is the standard REVIEW tier; z=3.0 is ALERT tier."},

        # ── Scope 3 coverage ──────────────────────────────────────────────────
        {"entry_id":"scope3-coverage", "category":"GHG Inventory",
         "name":"Scope 3 category coverage",
         "value":f"{SCOPE3_CATEGORIES_COVERED} of {SCOPE3_CATEGORIES_TOTAL}",
         "formula":"Cats 11, 14, 15 screened and excluded with rationale",
         "gri_reference":"GHG Protocol Scope 3 Standard Ch.7",
         "source":"GHG Protocol Corporate Value Chain Standard",
         "introduced_in":"Phase 0 H2",
         "rationale":"Categories screened as not relevant to platform/service provider model."},

        {"entry_id":"scope2-ef-kepmen", "category":"GHG Inventory",
         "name":"Scope 2 grid factor source", "value":"Kepmen ESDM No.18/2023",
         "formula":"Electricity kWh × PLN grid EF (province-specific)",
         "gri_reference":"",
         "source":"Kepmen ESDM No.18/2023, Appendix II",
         "introduced_in":"Phase 0 H3",
         "rationale":"Indonesian regulatory grid factor replacing generic 0.85 default."},
    ]
    return entries


def get_emission_factor_library() -> list:
    """
    Return the emission factor library for the Governance Emission Factor tab.
    Values read from config.settings — never duplicated here.
    """
    from config.settings import (
        EMISSION_FACTORS as EF,
        EMISSION_FACTORS_CO2_ONLY as EF_CO2,
        SCOPE3_EMISSION_FACTORS as S3EF,
        PLN_SUBSYSTEM_FACTORS,
    )

    entries = []

    # Scope 1 combustion
    scope1_map = [
        ("diesel_kgco2_per_liter",    "Diesel (automotive)",  "kg CO₂e/L",   "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", "Kepmen ESDM No.18/2023"),
        ("petrol_kgco2_per_liter",    "Petrol / RON95",        "kg CO₂e/L",   "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", ""),
        ("lpg_kgco2_per_kg",          "LPG",                   "kg CO₂e/kg",  "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", ""),
        ("natural_gas_kgco2_per_m3",  "Natural Gas",           "kg CO₂e/m³",  "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", ""),
        ("cng_kgco2_per_m3",          "CNG",                   "kg CO₂e/m³",  "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", ""),
        ("coal_kgco2_per_kg",         "Coal (bituminous)",     "kg CO₂e/kg",  "CO₂+CH₄+N₂O", "IPCC 2006 Vol.2 Table 2.4", ""),
        ("biomass_kgco2_per_kg",      "Biomass (biogenic)",    "kg CO₂e/kg",  "Biogenic CO₂", "GHG Protocol Biogenic Accounting", ""),
    ]
    for key, name, unit, gases, source, reg in scope1_map:
        entries.append({
            "name": name, "category": "Scope 1 — Combustion",
            "key": key, "value": EF.get(key, 0),
            "unit": unit, "gas_coverage": gases,
            "source": source, "source_year": 2006,
            "gwp_basis": "IPCC AR6 (2021) GWP100",
            "regulation": reg,
            "co2_only_value": EF_CO2.get(key, 0.0),
            "effective_from": "2024-01-01", "last_reviewed": "Phase 0 H3",
            "notes": "Phase 0 H3 fix: updated from CO₂-only to full CO₂e" if EF_CO2.get(key, 0) else "",
        })

    # Scope 2 PLN grid
    entries.append({
        "name": "PLN National Grid (average)", "category": "Scope 2 — Grid Electricity",
        "key": "electricity_pln_kwh", "value": EF.get("electricity_pln_kwh", 0.716),
        "unit": "kg CO₂e/kWh", "gas_coverage": "CO₂+CH₄+N₂O",
        "source": "Kepmen ESDM No.18/2023, Appendix II",
        "source_year": 2023, "gwp_basis": "IPCC AR6 (2021) GWP100",
        "regulation": "Kepmen ESDM No.18/2023",
        "co2_only_value": 0.85, "effective_from": "2023-01-01",
        "last_reviewed": "Phase 0 H3",
        "notes": "National average; regional subsystem factors also applied where province is known.",
    })

    for subsys, ef_val in PLN_SUBSYSTEM_FACTORS.items():
        pretty = subsys.replace("electricity_pln_","").replace("_"," ").title()
        entries.append({
            "name": f"PLN — {pretty} Subsystem", "category": "Scope 2 — Grid Electricity",
            "key": subsys, "value": ef_val,
            "unit": "kg CO₂e/kWh", "gas_coverage": "CO₂+CH₄+N₂O",
            "source": "Kepmen ESDM No.18/2023, Appendix II",
            "source_year": 2023, "gwp_basis": "IPCC AR6 (2021) GWP100",
            "regulation": "Kepmen ESDM No.18/2023",
            "co2_only_value": 0.0, "effective_from": "2023-01-01",
            "last_reviewed": "Phase 0 H3",
            "notes": "",
        })

    # Scope 3 categories
    for cat_key, cat_data in S3EF.items():
        entries.append({
            "name": cat_key.replace("_"," ").title(),
            "category": "Scope 3 — Value Chain",
            "key": cat_key,
            "value": cat_data["ef"],
            "unit": cat_data["unit"],
            "gas_coverage": "CO₂e",
            "source": cat_data["source"],
            "source_year": 2023,
            "gwp_basis": "IPCC AR6 (2021) GWP100",
            "regulation": "",
            "co2_only_value": 0.0,
            "effective_from": "2024-01-01",
            "last_reviewed": "Phase 0 H3",
            "notes": "",
        })

    return entries


def get_governance_metrics() -> dict:
    """
    Return platform governance metrics for the Governance Metrics section.
    Reads from audit log and config — no calculations.
    """
    from config.constants import (
        CURRENT_METHODOLOGY_VERSION, APPROVED_EVENT_TYPES,
    )
    try:
        from audit.reader import get_audit_log
        all_events = get_audit_log(limit=500)
        n_events     = len(all_events)
        n_uploads    = sum(1 for e in all_events if e.get("event_type") == "data_uploaded")
        n_reports    = sum(1 for e in all_events
                          if e.get("event_type") in ("report_exported","pdf_generated"))
        n_recomps    = sum(1 for e in all_events
                          if e.get("event_type") in (
                              "carbon_recalculated","esg_score_recalculated",
                              "dq_score_recalculated"))
        last_event_ts = all_events[0].get("ts","—")[:16].replace("T"," ") if all_events else "—"
    except Exception:
        n_events = n_uploads = n_reports = n_recomps = 0
        last_event_ts = "—"

    return {
        "total_audit_events":    n_events,
        "data_uploads":          n_uploads,
        "reports_generated":     n_reports,
        "recomputations":        n_recomps,
        "last_event_ts":         last_event_ts,
        "methodology_version":   CURRENT_METHODOLOGY_VERSION,
        "approved_event_types":  len(APPROVED_EVENT_TYPES),
        "ef_scope1_count":       7,
        "ef_scope2_count":       7,   # 1 national + 6 subsystem
        "ef_scope3_count":       12,
        "methodology_entries":   len(get_methodology_library()),
    }


def complete_onboarding(
    org_data:   dict,
    df          = None,
    val_result: dict = None,
    slot:       int  = 0,
) -> dict:
    """
    Persist a completed onboarding form to session + disk and emit audit event.
    Called by the Onboarding page wizard — never by other pages directly.

    Parameters
    ----------
    org_data   : Organisation dict assembled from the onboarding form.
    df         : Uploaded DataFrame (optional — may be None if skipped).
    val_result : ValidationResult dict (optional).
    slot       : Organisation slot index (0–4, default 0).

    Returns the persisted Organisation dict.
    """
    import datetime, uuid

    # Ensure required fields are present
    org_data.setdefault("org_id",    str(uuid.uuid4()))
    org_data.setdefault("created_at", datetime.datetime.now().isoformat(timespec="seconds"))
    org_data["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    org_data["slot_index"] = slot

    try:
        from repository.session_repo import (
            set_organisation, mark_onboarding_complete,
            set_uploaded_df, set_validation_result, set as _set,
        )
        from repository.disk_repo import save_organisation
        set_organisation(org_data, slot)
        save_organisation(org_data, slot)
        mark_onboarding_complete(slot)
        if df is not None:
            set_uploaded_df(df)
        if val_result is not None:
            set_validation_result(val_result, slot=slot)
        # Clear disclosure/scope inputs so fresh org starts clean
        _set("disclosure_inputs", {}, slot=slot)
        _set("scope_inputs",      {}, slot=slot)
        log.info(f"Onboarding complete for slot {slot}: {org_data.get('company_name','')}")
    except Exception as exc:
        log.error(f"complete_onboarding persistence failed: {exc}", exc_info=True)

    try:
        from audit.writer import write_audit_event
        write_audit_event(
            event_type = "onboarding_completed",
            summary    = (
                f"Organisation configured: {org_data.get('company_name','')} "
                f"({org_data.get('sector','')})"
            ),
            detail = {
                "company_name":     org_data.get("company_name",""),
                "sector":           org_data.get("sector",""),
                "province":         org_data.get("province",""),
                "reporting_period": org_data.get("reporting_period",""),
                "slot":             slot,
            },
            org_id       = org_data.get("org_id",""),
            company_name = org_data.get("company_name",""),
        )
    except Exception as exc:
        log.warning(f"complete_onboarding audit event failed: {exc}")

    return org_data


def check_permission(permission: str) -> bool:
    """
    Return True if the current user has the given permission.
    Pages call this to gate sensitive sections.
    Delegates to auth_service — pages never import auth_service directly.
    """
    try:
        from services.auth_service import has_permission
        return has_permission(permission)
    except Exception:
        return False


def is_admin() -> bool:
    """Return True if the current user has admin role."""
    return check_permission("can_manage_users")


def get_current_username() -> str:
    """Return the current user's display name, or 'Guest' if unauthenticated."""
    try:
        from services.auth_service import get_current_user
        user = get_current_user()
        if user:
            return user.get("display_name", user.get("username", "User"))
    except Exception:
        pass
    return "Guest"


def navigate_to(destination: str) -> None:
    """
    Navigate to a V8 destination.
    APPROVED navigation abstraction — pages call this instead of session_repo directly.
    Validates destination against APPROVED_DESTINATIONS before writing.

    Usage:
        state_svc.navigate_to("carbon_accounting")
        st.rerun()
    """
    from config.constants import APPROVED_DESTINATIONS
    from repository.session_repo import set_active_page
    if destination in APPROVED_DESTINATIONS:
        set_active_page(destination)
        log.debug(f"navigate_to: {destination}")
    else:
        log.warning(f"navigate_to: rejected unknown destination {destination!r}")


def get_gri_analysis() -> list:
    """
    Run GRI 2021 gap analysis and return the result list.
    Delegates to calculations.gri_framework — pages never call calculations directly.

    Returns
    -------
    list of gap analysis dicts (see calculations.gri_framework.run_gap_analysis).
    """
    try:
        from calculations.gri_framework import run_gap_analysis
        from repository.session_repo import get_uploaded_df, get as _get
        di  = _get("disclosure_inputs") or {}
        df  = get_uploaded_df()
        return run_gap_analysis(di, df)
    except Exception as exc:
        log.warning(f"get_gri_analysis failed: {exc}")
        return []


def get_regulatory_alignment(state: dict) -> list:
    """
    Return a list of regulatory alignment status items based on ComputedState.
    Rules-based — no arithmetic. Returns pre-classified alignment dicts.

    Returns
    -------
    list of dicts: {framework, standard, status, coverage, note, action}
    """
    esg    = state.get("esg",    {})
    carbon = state.get("carbon", {})
    dq     = state.get("data_quality", {})

    score       = float(esg.get("score",           0))
    is_prov     = bool(esg.get("is_provisional",   True))
    src         = str(carbon.get("scope_source",   "none"))
    dq_conf     = float(dq.get("confidence_score", 0))
    val_status  = str(dq.get("validation_status",  "Fail"))

    def _status(ok: bool) -> str:
        return "Aligned" if ok else "Partial"

    def _color(ok: bool) -> str:
        return "green" if ok else "yellow"

    results = [
        {
            "framework":  "OJK POJK 51/2017",
            "standard":   "Sustainable Finance Roadmap — ESG Disclosure",
            "status":     _status(score >= 45 and not is_prov),
            "badge_type": _color(score >= 45 and not is_prov),
            "coverage":   f"{score:.1f}/100 ESG Score",
            "note": (
                "ESG score meets threshold and disclosure is Substantive."
                if score >= 45 and not is_prov else
                "Complete S/G disclosure and improve ESG score to ≥ 45."
            ),
            "action": "ESG Analytics → Scoring & Indicators" if is_prov else "",
        },
        {
            "framework":  "GHG Protocol",
            "standard":   "Corporate Accounting and Reporting Standard",
            "status":     _status(src != "none"),
            "badge_type": _color(src != "none"),
            "coverage":   f"Source: {src.replace('_',' ').title()}",
            "note": (
                "Scope 1/2/3 inventory calculated per GHG Protocol."
                if src != "none" else
                "Upload activity data or enter scope values in Carbon Accounting."
            ),
            "action": "Carbon Accounting" if src == "none" else "",
        },
        {
            "framework":  "GRI 2021",
            "standard":   "Global Reporting Initiative — Universal Standards",
            "status":     _status(not is_prov and dq_conf >= 60),
            "badge_type": _color(not is_prov and dq_conf >= 60),
            "coverage":   f"DQ Confidence: {dq_conf:.0f}%",
            "note": (
                "S/G disclosure complete and dataset quality acceptable."
                if not is_prov and dq_conf >= 60 else
                "Improve S/G disclosure and resolve data quality flags."
            ),
            "action": "ESG Analytics · Data Quality" if is_prov or dq_conf < 60 else "",
        },
        {
            "framework":  "ISSB IFRS S2",
            "standard":   "Climate-related Disclosures",
            "status":     _status(src != "none" and dq_conf >= 70),
            "badge_type": _color(src != "none" and dq_conf >= 70),
            "coverage":   f"Scope data: {'Available' if src != 'none' else 'Missing'}",
            "note": (
                "Climate-related disclosure data is available."
                if src != "none" and dq_conf >= 70 else
                "IFRS S2 requires complete Scope 1/2/3 data with high-quality dataset."
            ),
            "action": "Carbon Accounting · Data Quality" if src == "none" else "",
        },
    ]
    return results


def get_active_page() -> str:
    """Return the current V8 destination ID. Used by app.py routing."""
    try:
        from repository.session_repo import get_active_page as _get
        from config.constants import DEFAULT_DESTINATION
        return _get() or DEFAULT_DESTINATION
    except Exception:
        from config.constants import DEFAULT_DESTINATION
        return DEFAULT_DESTINATION


def is_onboarding_complete(slot: int = None) -> bool:
    """Return True if onboarding is complete for the active (or specified) slot."""
    try:
        from repository.session_repo import is_onboarding_complete as _chk, get_active_slot
        _slot = slot if slot is not None else get_active_slot()
        return _chk(_slot)
    except Exception:
        return False


def is_org_setup(org: dict | None) -> bool:
    """Return True if the organisation dict is valid and non-placeholder."""
    from state.session import is_org_setup as _check
    return _check(org)


# ── Phase 5-A: Decarbonization state access ───────────────────────────────────

def get_decarb_state() -> dict:
    """Return the DecarbonizationState for the current session. App uses this wrapper."""
    from services.decarbonization_service import get_decarb_state as _get
    return _get()


def save_decarb_state(state: dict) -> None:
    """Persist the DecarbonizationState. App uses this wrapper."""
    from services.decarbonization_service import save_decarb_state as _save
    _save(state)


# ── Phase 5-B: Hardened forecast ──────────────────────────────────────────────

def get_forecast_validation() -> dict:
    """
    Return the full Phase 5-B validated forecast result.
    Integrates existing Phase 2 Data Quality validation status.

    Data confidence and model validation remain SEPARATE concepts:
      - dq_validation_status : from Phase 2 upload validation pipeline
      - gate.valid           : Phase 5-B historical coverage check
      - validation.*         : holdout MAE/RMSE (model accuracy on unseen data)

    Pages call this; never import calculations.forecasting directly.
    """
    try:
        from repository.session_repo import get_uploaded_df
        df = get_uploaded_df()
    except Exception:
        df = None

    # Read DQ validation status from session (Phase 2 pipeline output)
    dq_status = None
    try:
        from repository.session_repo import get as _get
        val_result = _get("validation_result")
        if val_result and isinstance(val_result, dict):
            dq_status = val_result.get("status")    # "Pass"|"Warning"|"Fail"
    except Exception:
        pass

    from calculations.forecasting import forecast_with_validation
    return forecast_with_validation(df, dq_validation_status=dq_status)
