"""
CarbonLens V8 — ESG service.
Orchestrates ESG score computation. No formulas.
All arithmetic delegated to calculations/esg_scoring.py and calculations/confidence.py.
"""
from __future__ import annotations
import datetime
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.esg")


def compute_esg_score(
    org:               dict,
    disclosure_inputs: Optional[dict] = None,
    carbon:            Optional[dict] = None,
    force:             bool = False,
) -> dict:
    """
    Orchestrate ESG score computation for one organisation.

    Delegates all arithmetic to calculations.esg_scoring and calculations.confidence.
    Emits esg_score_recalculated audit event when force=True.

    Parameters
    ----------
    org               : Organisation dict (area_m2, sector, renew_pct, recycle_pct, certifications).
    disclosure_inputs : S/G indicator session state values dict.
    carbon            : CarbonInventory dict from carbon_service (for intensity / benchmark).
    force             : If True, emit audit event.

    Returns
    -------
    dict matching ESGScore TypedDict schema.
    """
    from calculations import esg_scoring, confidence, benchmarking
    from config.constants import CURRENT_METHODOLOGY_VERSION

    di     = disclosure_inputs or {}
    carbon = carbon or {}
    org_id = org.get("org_id", "")
    sector = org.get("sector", "Manufacturing")

    area_m2  = float(org.get("area_m2", 5000) or 5000)
    renew    = float(org.get("renew_pct", 0) or 0)
    recycle  = float(org.get("recycle_pct", 0) or 0)
    certs    = list(org.get("certifications") or [])

    # Resolve intensity and benchmark from carbon result
    intens   = float(carbon.get("intens_m2", 0) or 0)
    bench    = float(carbon.get("benchmark") or benchmarking.get_benchmark(sector))
    water    = float(di.get("water_recycled_pct", 0) or 0)

    # Social indicators
    turnover  = float(di.get("employee_turnover_pct",   0) or 0)
    training  = float(di.get("training_hours_per_employee", 0) or 0)
    women_wf  = float(di.get("women_workforce_pct",     0) or 0)
    injury    = float(di.get("injury_rate",              0) or 0)

    # Governance indicators
    board_ind = float(di.get("board_independence_pct",  0) or 0)
    women_bd  = float(di.get("women_board_pct",         0) or 0)
    has_coc   = bool(di.get("has_code_of_conduct", False))
    disc_pct  = float(di.get("disclosure_score", 0) or 0)

    # ── Pillar scores ─────────────────────────────────────────────────────────
    env    = esg_scoring.calculate_env_score(intens, bench, renew, recycle, water)
    social = esg_scoring.calculate_social_score(turnover, training, women_wf, injury)
    gov    = esg_scoring.calculate_gov_score(board_ind, disc_pct, has_coc, women_bd, certs)
    score  = esg_scoring.calculate_composite_esg_score(env, social, gov)
    grade, label = esg_scoring.assign_grade(score)

    # ── Confidence and provisional status ────────────────────────────────────
    esg_conf = confidence.compute_esg_confidence(di)
    is_prov  = confidence.is_esg_provisional(esg_conf)
    n_disc, n_total = confidence.count_disclosed(di)

    # ── Methodology disclaimer ────────────────────────────────────────────────
    if is_prov:
        meth_note = (
            f"Score is Provisional: only {n_disc} of {n_total} "
            "S/G indicators disclosed. Conservative defaults applied "
            "for undisclosed indicators."
        )
    else:
        meth_note = (
            f"Score is Substantive: {n_disc}/{n_total} S/G indicators disclosed. "
            "GRI 2021-aligned pillar weighting: E=40%, S=30%, G=30%."
        )

    result = {
        "org_id":               org_id,
        "score":                score,
        "grade":                grade,
        "label":                label,
        "env":                  env,
        "social":               social,
        "gov":                  gov,
        "confidence_score":     esg_conf,
        "is_provisional":       is_prov,
        "n_disclosed":          n_disc,
        "n_total_indicators":   n_total,
        "disclosure_summary":   f"{n_disc} of {n_total} S/G indicators disclosed",
        "methodology_version":  CURRENT_METHODOLOGY_VERSION,
        "methodology_disclaimer": meth_note,
        "computed_at":          datetime.datetime.now().isoformat(timespec="seconds"),
    }

    log.info(
        f"compute_esg_score: org={org_id[:8]} "
        f"score={score:.1f} grade={grade} provisional={is_prov}"
    )

    if force:
        _emit_esg_event(result)

    return result


def _emit_esg_event(esg: dict) -> None:
    """Emit esg_score_recalculated audit event."""
    try:
        from audit.writer import write_audit_event
        write_audit_event(
            event_type = "esg_score_recalculated",
            summary    = (
                f"ESG score recomputed: {esg['score']:.1f} "
                f"(Grade {esg['grade']}) — "
                f"{'Provisional' if esg['is_provisional'] else 'Substantive'}"
            ),
            detail = {
                "score":         esg["score"],
                "grade":         esg["grade"],
                "env":           esg["env"],
                "social":        esg["social"],
                "gov":           esg["gov"],
                "is_provisional":esg["is_provisional"],
                "confidence":    esg["confidence_score"],
                "n_disclosed":   esg["n_disclosed"],
            },
        )
    except Exception as exc:
        log.warning(f"ESG audit event failed: {exc}")
