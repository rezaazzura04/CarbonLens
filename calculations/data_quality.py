"""
CarbonLens V8 — Four-part Data Quality score calculation.
Pure functions. Phase 2 implementation.

Four components:
  Completeness  (40%) — % of expected fields present
  Consistency   (35%) — % of rows passing outlier + duplicate checks
  Validation    (25%) — Pass/Warning/Fail from upload validation
  Confidence         — blended, hard-capped at 40% on Fail
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.calculations.data_quality")


# ── Outlier detection ─────────────────────────────────────────────────────────

def detect_outliers(df, z_thresh: float = 2.0):
    """
    Return rows of df where the Emission column is a statistical outlier.
    Uses z-score method. z_thresh=2.0 = REVIEW tier (Phase 0 M2 fix).
    Requires minimum 3 rows to compute meaningful z-scores.

    Parameters
    ----------
    df       : pandas DataFrame with at least an "Emission" column.
    z_thresh : Z-score threshold. Default 2.0 (REVIEW tier).

    Returns
    -------
    DataFrame : Subset of df with outlier rows. Empty DataFrame if none.
    """
    import pandas as pd
    import numpy as np

    if df is None or df.empty or "Emission" not in df.columns:
        return pd.DataFrame()
    if len(df) < 3:
        return pd.DataFrame()

    emission = pd.to_numeric(df["Emission"], errors="coerce").dropna()
    if emission.std() == 0:
        return pd.DataFrame()

    z_scores = (emission - emission.mean()) / emission.std()
    outlier_idx = z_scores[z_scores.abs() > z_thresh].index
    return df.loc[df.index.intersection(outlier_idx)].copy()


# ── Completeness scoring ──────────────────────────────────────────────────────

def score_env_completeness(df) -> tuple:
    """
    Score environmental data completeness.
    Base: non-null Emission rows / total rows.
    Optional column bonuses: Energy+8pts, Water+5pts, Waste+5pts (max 100).

    Parameters
    ----------
    df : pandas DataFrame or None.

    Returns
    -------
    tuple : (env_completeness: float, flags: list[dict])
    """
    flags = []
    if df is None or df.empty or "Emission" not in df.columns:
        flags.append(_make_flag(
            "Emission", "missing", "high",
            "No emission dataset loaded. Upload a CSV to begin analysis.",
            "Upload a CSV with Month and Emission (tCO2e) columns.",
            "esg_analytics",
        ))
        return 0.0, flags

    import pandas as pd
    total = len(df)
    valid = pd.to_numeric(df["Emission"], errors="coerce").notna().sum()
    base  = round(valid / total * 100.0, 1) if total > 0 else 0.0

    bonus = 0.0
    optional = {"Energy": 8.0, "Water": 5.0, "Waste": 5.0}
    for col, pts in optional.items():
        if col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().any():
            bonus += pts
        else:
            flags.append(_make_flag(
                col, "missing", "low",
                f"{col} column not found. Including it improves resource intensity metrics.",
                f"Add a {col} column to your CSV and re-upload.",
                "carbon_accounting",
            ))

    env_complete = min(100.0, base + bonus)
    return round(env_complete, 1), flags


def score_sg_completeness(disclosure_inputs: dict) -> tuple:
    """
    Score S/G indicator completeness.
    Returns (sg_completeness_pct, n_disclosed, n_total, flags).

    Parameters
    ----------
    disclosure_inputs : Dict mapping session state S/G keys to their values.

    Returns
    -------
    tuple : (sg_pct: float, n_disclosed: int, n_total: int, flags: list[dict])
    """
    _SG_FIELDS = {
        "water_recycled":     ("Water Recycling Rate",       "water_recycled_pct",         "esg_analytics"),
        "employee_turnover":  ("Employee Turnover Rate",     "employee_turnover_pct",       "esg_analytics"),
        "training_hours":     ("Training Hours / Employee",  "training_hours_per_employee", "esg_analytics"),
        "gender_diversity":   ("Gender Diversity",           "women_workforce_pct",         "esg_analytics"),
        "injury_rate":        ("Injury Rate",                "injury_rate",                 "esg_analytics"),
        "board_independence": ("Board Independence",         "board_independence_pct",      "esg_analytics"),
        "board_diversity":    ("Board Gender Diversity",     "women_board_pct",             "esg_analytics"),
        "ethics_policies":    ("Ethics Policies",            "has_code_of_conduct",         "esg_analytics"),
    }

    n_disclosed = 0
    flags = []
    for dkey, (label, skey, route) in _SG_FIELDS.items():
        val = disclosure_inputs.get(skey)
        if val is not None and val is not False and val != 0 and val != "":
            n_disclosed += 1
        else:
            flags.append(_make_flag(
                dkey, "estimated_default", "medium",
                f"{label} not disclosed. A conservative default reduces the score.",
                f"Enter your {label} in ESG Analytics — Scoring.",
                route,
            ))

    n_total = len(_SG_FIELDS)
    sg_pct  = round(n_disclosed / n_total * 100.0, 1)
    return sg_pct, n_disclosed, n_total, flags


def score_completeness(df, disclosure_inputs: dict) -> tuple:
    """
    Score blended completeness (env 60% + S/G 40%).

    Returns
    -------
    tuple : (blended_pct, env_pct, sg_pct, n_sg_disclosed, n_sg_total, flags)
    """
    env_pct,  env_flags = score_env_completeness(df)
    sg_pct, n_sg, n_total, sg_flags = score_sg_completeness(disclosure_inputs)
    blended = round(env_pct * 0.60 + sg_pct * 0.40, 1)
    return blended, env_pct, sg_pct, n_sg, n_total, env_flags + sg_flags


# ── Consistency scoring ───────────────────────────────────────────────────────

def score_consistency(df) -> tuple:
    """
    Score dataset consistency: proportion of rows passing quality checks.
    Checks: outlier detection (z=2.0) and duplicate month detection.

    Parameters
    ----------
    df : pandas DataFrame or None.

    Returns
    -------
    tuple : (consistency_score: float, flags: list[dict])
    """
    import pandas as pd

    if df is None or df.empty or "Emission" not in df.columns or len(df) < 3:
        return 100.0, []

    flags  = []
    score  = 100.0
    n_rows = len(df)

    # Outlier check (z=2.0, REVIEW tier)
    outliers = detect_outliers(df, z_thresh=2.0)
    n_out    = len(outliers)
    if n_out > 0:
        penalty = (n_out / n_rows) * 100.0
        score   = max(0.0, score - penalty)
        months  = (
            outliers["Month"].tolist()
            if "Month" in outliers.columns else []
        )
        month_str = ", ".join(str(m) for m in months[:5])
        flags.append(_make_flag(
            "Emission", "outlier",
            "high" if n_out >= 2 else "medium",
            f"{n_out} month(s) with statistically unusual emission values"
            + (f" ({month_str})" if month_str else "")
            + ". May indicate data entry errors.",
            "Review and verify the flagged months in your source data.",
            "carbon_accounting",
        ))

    # Duplicate month check
    if "Month" in df.columns and len(df) >= 6:
        n_unique = df["Month"].nunique()
        if n_unique < n_rows:
            dup_penalty = min(30.0, (n_rows - n_unique) / n_rows * 100.0)
            score = max(0.0, score - dup_penalty)
            flags.append(_make_flag(
                "Month", "out_of_range", "medium",
                "Duplicate month entries detected. Each month should appear once.",
                "Remove duplicate rows and re-upload.",
                "esg_analytics",
            ))

    return round(score, 1), flags


# ── Confidence blending ───────────────────────────────────────────────────────

def blend_dq_confidence(
    completeness:      float,
    consistency:       float,
    validation_score:  float,
    validation_failed: bool,
) -> float:
    """
    Blend four-part DQ confidence score.
    Formula: completeness×0.40 + consistency×0.35 + validation×0.25.
    Hard-capped at 40% when validation has failed.

    Parameters
    ----------
    completeness      : Completeness sub-score (0–100).
    consistency       : Consistency sub-score (0–100).
    validation_score  : Numeric validation score: Pass=100, Warning=70, Fail=0.
    validation_failed : True when ValidationResult.status == "Fail".
    """
    from config.constants import (
        DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION,
        DQ_CONFIDENCE_CAP_ON_FAIL,
    )
    score = (
        completeness    * DQ_WEIGHT_COMPLETENESS +
        consistency     * DQ_WEIGHT_CONSISTENCY  +
        validation_score* DQ_WEIGHT_VALIDATION
    )
    if validation_failed:
        score = min(score, DQ_CONFIDENCE_CAP_ON_FAIL)
    return round(score, 1)


def validation_to_score(status: str) -> float:
    """Convert validation status string to numeric score."""
    from config.constants import (
        DQ_VALIDATION_SCORE_PASS, DQ_VALIDATION_SCORE_WARNING, DQ_VALIDATION_SCORE_FAIL,
        VALIDATION_PASS, VALIDATION_WARNING,
    )
    if status == VALIDATION_PASS:
        return DQ_VALIDATION_SCORE_PASS
    if status == VALIDATION_WARNING:
        return DQ_VALIDATION_SCORE_WARNING
    return DQ_VALIDATION_SCORE_FAIL


def compute_full_dq_score(
    df,
    disclosure_inputs: dict,
    validation_status: str,
    validation_errors: list  = None,
    validation_warnings: list = None,
) -> dict:
    """
    Compute the complete four-part Data Quality score.
    Single entry point that calls all sub-scorers and assembles the result dict.

    Parameters
    ----------
    df                 : Uploaded DataFrame or None.
    disclosure_inputs  : S/G indicator session state values.
    validation_status  : "Pass" | "Warning" | "Fail".
    validation_errors  : List of hard error strings from validation.
    validation_warnings: List of warning strings from validation.

    Returns
    -------
    dict matching DataQualityScore TypedDict schema.
    """
    from config.constants import (
        CONFIDENCE_PROVISIONAL_FLOOR, VALIDATION_FAIL,
    )

    errors   = validation_errors   or []
    warnings = validation_warnings or []

    val_score = validation_to_score(validation_status)
    val_failed = validation_status == VALIDATION_FAIL

    blended, env_pct, sg_pct, n_sg, n_total, comp_flags = score_completeness(
        df, disclosure_inputs
    )
    consistency, cons_flags = score_consistency(df)

    # Add validation error flags
    val_flags = []
    for err in errors:
        val_flags.append(_make_flag(
            "upload", "out_of_range", "high", err,
            "Fix the error in your CSV and re-upload.", "esg_analytics",
        ))

    all_flags = comp_flags + cons_flags + val_flags
    # Dedup on (field_name, reason)
    seen, deduped = set(), []
    for f in all_flags:
        k = (f["field_name"], f["reason"])
        if k not in seen:
            seen.add(k)
            deduped.append(f)
    _sev = {"high": 0, "medium": 1, "low": 2}
    deduped.sort(key=lambda x: _sev.get(x.get("severity", "low"), 9))

    confidence = blend_dq_confidence(blended, consistency, val_score, val_failed)
    is_prov    = confidence < CONFIDENCE_PROVISIONAL_FLOOR

    high_n = sum(1 for f in deduped if f.get("severity") == "high")
    med_n  = sum(1 for f in deduped if f.get("severity") == "medium")
    summary = (
        f"Confidence {confidence:.0f}% — "
        f"{high_n} high and {med_n} medium priority issue(s)."
        if deduped else
        f"Confidence {confidence:.0f}% — no data quality issues detected."
    )

    return {
        "completeness_score": blended,
        "consistency_score":  consistency,
        "validation_status":  validation_status,
        "validation_score":   val_score,
        "confidence_score":   confidence,
        "is_provisional":     is_prov,
        "env_completeness":   env_pct,
        "sg_completeness":    sg_pct,
        "sg_disclosed":       n_sg,
        "sg_total":           n_total,
        "flagged_fields":     deduped,
        "summary":            summary,
    }


# ── Flag factory helper ───────────────────────────────────────────────────────

def _make_flag(
    field_name: str, reason: str, severity: str,
    description: str, suggested_action: str, fix_route: str,
) -> dict:
    return {
        "field_name":       field_name,
        "reason":           reason,
        "severity":         severity,
        "description":      description,
        "suggested_action": suggested_action,
        "fix_route":        fix_route,
    }
