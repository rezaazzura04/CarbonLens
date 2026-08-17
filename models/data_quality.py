"""
CarbonLens V8 — DataQualityScore and FlaggedField models.
"""
from __future__ import annotations
from typing import TypedDict


class FlaggedField(TypedDict):
    """One data quality issue with actionable routing metadata."""
    field_name:       str    # e.g. "Emission", "water_recycled"
    reason:           str    # "missing"|"out_of_range"|"outlier"|"estimated_default"
    severity:         str    # "high" | "medium" | "low"
    description:      str    # Plain English, one sentence
    suggested_action: str    # What the user should do
    fix_route:        str    # V8 destination ID: "esg_analytics"|"carbon_accounting"


class DataQualityScore(TypedDict):
    """Four-part dataset integrity score. Independent of ESGScore.confidence_score."""
    completeness_score:  float         # % of expected env + S/G fields present (0–100)
    consistency_score:   float         # % of rows passing outlier + duplicate checks (0–100)
    validation_status:   str           # "Pass" | "Warning" | "Fail"
    validation_score:    float         # Pass=100, Warning=70, Fail=0
    confidence_score:    float         # Blended 0–100
    is_provisional:      bool          # True when confidence < 50%
    env_completeness:    float         # Environmental fields sub-score
    sg_completeness:     float         # S/G indicators sub-score
    sg_disclosed:        int
    sg_total:            int
    flagged_fields:      list[FlaggedField]
    summary:             str


def make_no_data_quality() -> DataQualityScore:
    """Return a zero DQ score for sessions with no uploaded dataset."""
    return DataQualityScore(
        completeness_score = 0.0,
        consistency_score  = 100.0,
        validation_status  = "Fail",
        validation_score   = 0.0,
        confidence_score   = 0.0,
        is_provisional     = True,
        env_completeness   = 0.0,
        sg_completeness    = 0.0,
        sg_disclosed       = 0,
        sg_total           = 8,
        flagged_fields     = [
            FlaggedField(
                field_name       = "Emission",
                reason           = "missing",
                severity         = "high",
                description      = "No dataset uploaded. Upload a CSV to begin analysis.",
                suggested_action = "Upload a CSV with Month and Emission columns.",
                fix_route        = "esg_analytics",
            )
        ],
        summary = "Confidence 0% — no dataset loaded.",
    )
