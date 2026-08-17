"""
CarbonLens V8 — Data Quality service.
Orchestrates four-part DQ score computation. No formulas.
All arithmetic delegated to calculations/data_quality.py.
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.data_quality")


def compute_data_quality(
    df                  = None,
    validation:         Optional[dict] = None,
    disclosure_inputs:  Optional[dict] = None,
    force:              bool = False,
) -> dict:
    """
    Orchestrate the four-part Data Quality score.

    Delegates all arithmetic to calculations.data_quality.compute_full_dq_score().
    Emits dq_score_recalculated audit event when force=True.

    Parameters
    ----------
    df                : Uploaded DataFrame or None.
    validation        : ValidationResult dict from validation_service.
    disclosure_inputs : S/G indicator session state values dict.
    force             : If True, emit audit event.

    Returns
    -------
    dict matching DataQualityScore TypedDict schema.
    """
    from calculations.data_quality import compute_full_dq_score
    from config.constants import VALIDATION_FAIL

    val        = validation or {}
    di         = disclosure_inputs or {}
    val_status = val.get("status", VALIDATION_FAIL)
    val_errors = val.get("errors", [])
    val_warnings = val.get("warnings", [])

    result = compute_full_dq_score(
        df                 = df,
        disclosure_inputs  = di,
        validation_status  = val_status,
        validation_errors  = val_errors,
        validation_warnings= val_warnings,
    )

    log.info(
        f"compute_data_quality: "
        f"confidence={result['confidence_score']:.1f}% "
        f"validation={val_status} "
        f"flags={len(result['flagged_fields'])}"
    )

    if force:
        _emit_dq_event(result)

    return result


def _emit_dq_event(dq: dict) -> None:
    """Emit dq_score_recalculated audit event."""
    try:
        from audit.writer import write_audit_event
        high_n = sum(1 for f in dq.get("flagged_fields", [])
                     if f.get("severity") == "high")
        write_audit_event(
            event_type = "dq_score_recalculated",
            summary    = (
                f"Data Quality score recomputed: "
                f"{dq['confidence_score']:.0f}% confidence — "
                f"validation {dq['validation_status']}"
            ),
            detail = {
                "confidence":     dq["confidence_score"],
                "completeness":   dq["completeness_score"],
                "consistency":    dq["consistency_score"],
                "validation":     dq["validation_status"],
                "n_flags":        len(dq.get("flagged_fields", [])),
                "n_high_flags":   high_n,
                "is_provisional": dq["is_provisional"],
            },
        )
    except Exception as exc:
        log.warning(f"DQ audit event failed: {exc}")
