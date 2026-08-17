"""
CarbonLens V8 — ComputedState assembly and invariant enforcement.

Assembles a new ComputedState from service outputs.
Enforces all model invariants before returning.
A ComputedState that fails invariant checks is never stored.
"""

from __future__ import annotations
import datetime
import logging
import uuid
from typing import Optional

log = logging.getLogger("carbonlens.state.computed")


def assemble(
    org_id:   str,
    period:   str,
    carbon:   dict,
    esg:      dict,
    dq:       dict,
    previous: Optional[dict] = None,
    computation_time_ms: int = 0,
) -> dict:
    """
    Assemble an immutable ComputedState dict from three service output dicts.

    Parameters
    ----------
    org_id   : Organisation ID.
    period   : Reporting period string.
    carbon   : CarbonInventory dict from carbon_service.
    esg      : ESGScore dict from esg_service.
    dq       : DataQualityScore dict from data_quality_service.
    previous : Previous ComputedState dict (for version increment and audit chain).
    computation_time_ms : Time taken to compute all three components.

    Returns a new ComputedState dict with version = previous.version + 1 (or 1).

    Raises
    ------
    ValueError
        If any invariant check fails. Callers must handle this and not persist
        an invalid state.
    """
    from config.constants import (
        STATE_STATUS_PROVISIONAL,
        STATE_STATUS_SUBSTANTIVE,
        STATE_STATUS_NO_DATA,
    )

    # ── Compute dual confidence ───────────────────────────────────────────────
    esg_conf    = float(esg.get("confidence_score",       0.0))
    esg_is_prov = bool(esg.get("is_provisional",          True))
    dq_conf     = float(dq.get("confidence_score",        0.0))
    dq_is_prov  = bool(dq.get("is_provisional",           True))

    confidence = {
        "esg_confidence":     esg_conf,
        "esg_is_provisional": esg_is_prov,
        "dq_confidence":      dq_conf,
        "dq_is_provisional":  dq_is_prov,
        "interpretation":     _interpret_confidence(esg_conf, esg_is_prov, dq_conf, dq_is_prov),
    }

    # ── Determine status ──────────────────────────────────────────────────────
    if carbon.get("scope_source", "none") == "none":
        status = STATE_STATUS_NO_DATA
    elif esg_is_prov:
        status = STATE_STATUS_PROVISIONAL
    else:
        status = STATE_STATUS_SUBSTANTIVE

    # ── Version and audit chain ───────────────────────────────────────────────
    prev_version = previous.get("version", 0) if previous else 0
    prev_id      = previous.get("state_id")   if previous else None

    # ── Input hash (propagated from carbon scope source or empty state) ───────
    input_hash = _derive_input_hash(org_id, period, carbon)

    state = {
        "state_id":             str(uuid.uuid4()),
        "org_id":               org_id,
        "period":               period,
        "version":              prev_version + 1,
        "previous_version_id":  prev_id,
        "input_hash":           input_hash,
        "status":               status,
        "carbon":               carbon,
        "esg":                  esg,
        "data_quality":         dq,
        "confidence":           confidence,
        "computed_at":          datetime.datetime.now().isoformat(timespec="seconds"),
        "computation_time_ms":  computation_time_ms,
    }

    _validate_invariants(state)
    return state


def _derive_input_hash(org_id: str, period: str, carbon: dict) -> str:
    """
    Derive a stable input hash from the computation inputs.
    The hash changes when org_id, period, or the underlying dataset changes.
    """
    import hashlib
    raw = f"{org_id}:{period}:{carbon.get('scope_source', 'none')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _validate_invariants(state: dict) -> None:
    """
    Check all ComputedState invariants. Raises ValueError on failure.
    """
    carbon = state["carbon"]
    esg    = state["esg"]
    dq     = state["data_quality"]
    conf   = state["confidence"]

    # Carbon total invariant
    expected_total = (
        carbon["scope1_kg"] + carbon["scope2_kg"] + carbon["scope3_kg"]
    )
    actual_total = carbon["total_kg"]
    if abs(expected_total - actual_total) > 0.01:
        raise ValueError(
            f"Carbon invariant failed: total_kg={actual_total} != "
            f"scope1+scope2+scope3={expected_total:.4f}"
        )

    # ESG score range
    if not (0.0 <= esg["score"] <= 100.0):
        raise ValueError(f"ESG score out of range: {esg['score']}")

    # Confidence alignment
    if conf["esg_is_provisional"] != esg["is_provisional"]:
        raise ValueError(
            "ConfidenceScore.esg_is_provisional does not match ESGScore.is_provisional"
        )
    if conf["dq_is_provisional"] != dq["is_provisional"]:
        raise ValueError(
            "ConfidenceScore.dq_is_provisional does not match DataQualityScore.is_provisional"
        )

    # Version must be positive
    if state["version"] < 1:
        raise ValueError(f"ComputedState.version must be >= 1, got {state['version']}")


def _interpret_confidence(
    esg_conf: float, esg_prov: bool,
    dq_conf: float,  dq_prov: bool,
) -> str:
    """Return a one-sentence combined confidence interpretation."""
    if esg_prov and dq_prov:
        return "Score and dataset both require additional data for full confidence."
    if esg_prov:
        return "Dataset is reliable; S/G disclosure incomplete — score is Provisional."
    if dq_prov:
        return "S/G disclosure complete; dataset has quality issues requiring review."
    if esg_conf >= 80 and dq_conf >= 80:
        return "Full disclosure and clean dataset — Substantive confidence."
    return f"ESG confidence {esg_conf:.0f}%, DQ confidence {dq_conf:.0f}%."
