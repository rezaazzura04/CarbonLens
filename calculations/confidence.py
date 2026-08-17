"""
CarbonLens V8 — Dual confidence model.
Phase 0 C3 fix + Phase 2 design: two independent confidence dimensions.

ESG confidence  = S/G disclosure ratio → score trustworthiness.
DQ confidence   = four-part dataset integrity → data reliability.
These are NEVER merged. See Phase 2 Methodology Board decision.
"""
from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.calculations.confidence")


def compute_esg_confidence(disclosure_inputs: dict) -> float:
    """
    Compute ESG confidence as the proportion of S/G indicators disclosed.

    A disclosed indicator is any key in DISCLOSURE_FIELDS whose corresponding
    session state value is non-None, non-False, non-zero, and non-empty-string.
    Phase 0 C3 fix. Source: CarbonLens V8 Methodology Library.

    Parameters
    ----------
    disclosure_inputs : Dict mapping DISCLOSURE_FIELDS keys to their values.

    Returns
    -------
    float : Confidence percentage 0.0–100.0.
    """
    from config.constants import DISCLOSURE_FIELDS

    _SG_KEY_MAP = {
        "water_recycled":     "water_recycled_pct",
        "employee_turnover":  "employee_turnover_pct",
        "training_hours":     "training_hours_per_employee",
        "gender_diversity":   "women_workforce_pct",
        "injury_rate":        "injury_rate",
        "board_independence": "board_independence_pct",
        "board_diversity":    "women_board_pct",
        "ethics_policies":    "has_code_of_conduct",
    }

    n_disclosed = 0
    for dkey in DISCLOSURE_FIELDS:
        skey = _SG_KEY_MAP.get(dkey, dkey)
        val  = disclosure_inputs.get(skey)
        if val is not None and val is not False and val != 0 and val != "":
            n_disclosed += 1

    total = len(DISCLOSURE_FIELDS)
    return round(n_disclosed / total * 100.0, 1) if total > 0 else 0.0


def is_esg_provisional(confidence: float) -> bool:
    """
    Return True if ESG confidence is below the provisional floor (50%).
    Phase 0 C3 fix.
    """
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR
    return confidence < CONFIDENCE_PROVISIONAL_FLOOR


def build_confidence_score(esg_conf: float, dq_conf: float) -> dict:
    """
    Assemble a ConfidenceScore dict from independent ESG and DQ confidence values.

    These two metrics measure different phenomena:
    - esg_confidence: Are the S/G indicators disclosed? (score trustworthiness)
    - dq_confidence:  Is the dataset technically reliable? (data integrity)

    They must never be averaged or merged.

    Parameters
    ----------
    esg_conf : ESG confidence percentage (0–100).
    dq_conf  : Data Quality confidence percentage (0–100).

    Returns
    -------
    dict matching ConfidenceScore TypedDict schema.
    """
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR

    esg_prov = esg_conf < CONFIDENCE_PROVISIONAL_FLOOR
    dq_prov  = dq_conf  < CONFIDENCE_PROVISIONAL_FLOOR

    return {
        "esg_confidence":     round(esg_conf, 1),
        "esg_is_provisional": esg_prov,
        "dq_confidence":      round(dq_conf, 1),
        "dq_is_provisional":  dq_prov,
        "interpretation":     _interpret(esg_conf, esg_prov, dq_conf, dq_prov),
    }


def _interpret(
    esg_conf: float, esg_prov: bool,
    dq_conf:  float, dq_prov:  bool,
) -> str:
    if esg_prov and dq_prov:
        return "Both score confidence and dataset quality require improvement."
    if esg_prov:
        return (
            f"Dataset quality is {'Insufficient Data' if dq_conf < 50 else 'acceptable'} "
            f"({dq_conf:.0f}%); S/G disclosure incomplete — score is Provisional."
        )
    if dq_prov:
        return (
            f"S/G disclosure complete ({esg_conf:.0f}%); "
            "dataset has quality issues requiring review."
        )
    if esg_conf >= 80 and dq_conf >= 80:
        return "Full S/G disclosure and clean dataset — Substantive confidence."
    return (
        f"ESG confidence {esg_conf:.0f}% · "
        f"DQ confidence {dq_conf:.0f}%."
    )


def count_disclosed(disclosure_inputs: dict) -> tuple:
    """
    Return (n_disclosed, n_total) for the S/G indicator set.

    Parameters
    ----------
    disclosure_inputs : Dict with S/G session state keys.

    Returns
    -------
    tuple : (int n_disclosed, int n_total)
    """
    from config.constants import DISCLOSURE_FIELDS
    _SG_KEY_MAP = {
        "water_recycled":     "water_recycled_pct",
        "employee_turnover":  "employee_turnover_pct",
        "training_hours":     "training_hours_per_employee",
        "gender_diversity":   "women_workforce_pct",
        "injury_rate":        "injury_rate",
        "board_independence": "board_independence_pct",
        "board_diversity":    "women_board_pct",
        "ethics_policies":    "has_code_of_conduct",
    }
    n = sum(
        1 for dkey in DISCLOSURE_FIELDS
        if _is_disclosed(disclosure_inputs.get(_SG_KEY_MAP.get(dkey, dkey)))
    )
    return n, len(DISCLOSURE_FIELDS)


def _is_disclosed(val) -> bool:
    """Return True if the value represents an actual disclosure (not a default/empty)."""
    return val is not None and val is not False and val != 0 and val != ""
