"""
CarbonLens V8 — ESGScore, ConfidenceScore, PillarScore models.
"""
from __future__ import annotations
from typing import TypedDict


class ESGScore(TypedDict):
    """Composite ESG score with pillar breakdown and confidence metadata."""
    org_id:                  str
    score:                   float    # 0.0 – 100.0
    grade:                   str      # "A" | "B+" | "B" | "C" | "D"
    label:                   str      # Human label e.g. "Above Average"
    env:                     float    # Environmental pillar 0–100
    social:                  float    # Social pillar 0–100
    gov:                     float    # Governance pillar 0–100
    confidence_score:        float    # % of S/G indicators disclosed
    is_provisional:          bool     # True when confidence < PROVISIONAL_FLOOR
    n_disclosed:             int      # Count of disclosed S/G indicators
    n_total_indicators:      int      # Total available (8)
    disclosure_summary:      str      # Human-readable disclosure status
    methodology_version:     str      # Links to MethodologyEntry
    methodology_disclaimer:  str
    computed_at:             str      # ISO 8601


class ConfidenceScore(TypedDict):
    """
    Formal declaration of the dual-confidence architecture.

    ESG confidence and Data Quality confidence are INDEPENDENT metrics.
    A dataset may have high DQ confidence (clean data) while having low
    ESG confidence (no S/G disclosure). These must NEVER be merged.
    Source: Phase 2 design review; confirmed by Methodology Board.
    """
    esg_confidence:     float   # S/G disclosure ratio (0–100%) — score trustworthiness
    esg_is_provisional: bool    # True when esg_confidence < CONFIDENCE_PROVISIONAL_FLOOR
    dq_confidence:      float   # Four-part blended dataset integrity (0–100%)
    dq_is_provisional:  bool    # True when dq_confidence < CONFIDENCE_PROVISIONAL_FLOOR
    interpretation:     str     # Combined human-readable status for display


def make_provisional_esg(org_id: str) -> ESGScore:
    """Return a zero/provisional ESG score for sessions with no S/G data yet."""
    import datetime
    from config.constants import CURRENT_METHODOLOGY_VERSION
    return ESGScore(
        org_id                 = org_id,
        score                  = 0.0,
        grade                  = "D",
        label                  = "Needs Improvement",
        env                    = 0.0,
        social                 = 0.0,
        gov                    = 0.0,
        confidence_score       = 0.0,
        is_provisional         = True,
        n_disclosed            = 0,
        n_total_indicators     = 8,
        disclosure_summary     = "0% disclosed — 0 of 8 S/G indicators provided",
        methodology_version    = CURRENT_METHODOLOGY_VERSION,
        methodology_disclaimer = (
            "Score not yet computed. Upload data and complete ESG Analytics "
            "to generate a score."
        ),
        computed_at            = datetime.datetime.now().isoformat(timespec="seconds"),
    )
