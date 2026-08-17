"""
CarbonLens V8 — Trend detection and emission forecasting.
Pure functions. Uses numpy for linear regression.
"""
from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.calculations.forecasting")

_MIN_ROWS_FOR_FORECAST = 3


def detect_trend(df) -> dict:
    """
    COMPATIBILITY FUNCTION — retained for state_service.get_trend_data() (trend viz only).
    Not to be used as a forecast output. For forecasting use forecast_with_validation().
    
    Detect emission trend direction from dataset time series.

    Parameters
    ----------
    df : pandas DataFrame with "Emission" column and at least 3 rows.

    Returns
    -------
    dict with keys:
        direction   : "rising" | "falling" | "stable" | "insufficient_data"
        slope_kg_mo : float — monthly change in kg CO2e (positive = rising)
        description : str   — human-readable trend description
    """
    import numpy as np
    import pandas as pd

    if df is None or df.empty or "Emission" not in df.columns:
        return _no_trend("insufficient_data")
    emission = pd.to_numeric(df["Emission"], errors="coerce").dropna()
    if len(emission) < _MIN_ROWS_FOR_FORECAST:
        return _no_trend("insufficient_data")

    x = np.arange(len(emission), dtype=float)
    try:
        coeffs = np.polyfit(x, emission.values.astype(float), 1)
    except (np.linalg.LinAlgError, ValueError):
        return _no_trend("insufficient_data")

    slope = float(round(coeffs[0], 4))
    mean  = float(emission.mean())
    threshold = mean * 0.02   # 2% of mean = "stable" band

    if abs(slope) < threshold:
        direction   = "stable"
        description = f"Emissions stable (±{abs(slope):.1f} kg/month)"
    elif slope > 0:
        direction   = "rising"
        annual_rise = slope * 12
        description = f"Rising trend: +{annual_rise:.0f} kg CO2e/year estimated"
    else:
        direction   = "falling"
        annual_fall = abs(slope) * 12
        description = f"Falling trend: −{annual_fall:.0f} kg CO2e/year estimated"

    return {
        "direction":    direction,
        "slope_kg_mo":  slope,
        "description":  description,
    }


def predict_next_emission(df) -> dict:
    """
    COMPATIBILITY FUNCTION — Phase 5-B internal use only.
    Do NOT call from UI pages or export pipeline.
    For user-facing forecast output use: forecast_with_validation()
    This function is retained for internal use by forecast_with_validation() only.
    
    Predict next-month emission using OLS linear regression.

    Parameters
    ----------
    df : pandas DataFrame with "Emission" column.

    Returns
    -------
    dict with keys:
        next_month : float — predicted next month emission (kg CO2e)
        trend      : str   — "rising" | "falling" | "stable" | "insufficient_data"
        r2         : float — coefficient of determination (0–1)
        slope      : float — monthly slope
        intercept  : float
        n_months   : int   — months used for regression
    """
    import numpy as np
    import pandas as pd

    if df is None or df.empty or "Emission" not in df.columns:
        return _empty_forecast()
    emission = pd.to_numeric(df["Emission"], errors="coerce").dropna()
    n = len(emission)
    if n < _MIN_ROWS_FOR_FORECAST:
        return _empty_forecast()

    x = np.arange(n, dtype=float)
    y = emission.values.astype(float)
    try:
        coeffs   = np.polyfit(x, y, 1)
        slope    = float(round(coeffs[0], 4))
        intercept= float(round(coeffs[1], 4))
        y_pred   = np.polyval(coeffs, x)
        ss_res   = float(np.sum((y - y_pred) ** 2))
        ss_tot   = float(np.sum((y - y.mean()) ** 2))
        r2       = float(round(1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0, 4))
        next_val = float(round(max(0.0, np.polyval(coeffs, n)), 2))
    except (np.linalg.LinAlgError, ValueError, ZeroDivisionError):
        return _empty_forecast()

    trend = detect_trend(df)
    return {
        "next_month": next_val,
        "trend":      trend["direction"],
        "r2":         r2,
        "slope":      slope,
        "intercept":  intercept,
        "n_months":   n,
    }


def annual_projection(df) -> float:
    """
    Return annualised emission projection in kg CO2e.
    Uses the mean of the uploaded period if fewer than 12 months are present,
    otherwise returns the sum of the most recent 12 months.

    Parameters
    ----------
    df : pandas DataFrame with "Emission" column.

    Returns
    -------
    float : Annual emission projection in kg CO2e.
    """
    import pandas as pd

    if df is None or df.empty or "Emission" not in df.columns:
        return 0.0
    emission = pd.to_numeric(df["Emission"], errors="coerce").dropna()
    if len(emission) == 0:
        return 0.0
    if len(emission) >= 12:
        return float(round(emission.tail(12).sum(), 2))
    # Fewer than 12 months: annualise from mean
    return float(round(emission.mean() * 12, 2))


# ── Private helpers ───────────────────────────────────────────────────────────

def _no_trend(direction: str) -> dict:
    return {
        "direction":   direction,
        "slope_kg_mo": 0.0,
        "description": "Insufficient data for trend analysis (minimum 3 months required).",
    }


def _empty_forecast() -> dict:
    return {
        "next_month": 0.0,
        "trend":      "insufficient_data",
        "r2":         0.0,
        "slope":      0.0,
        "intercept":  0.0,
        "n_months":   0,
    }


# ── Phase 5-B: Forecast Hardening ─────────────────────────────────────────────
# DO NOT change the existing detect_trend(), predict_next_emission(),
# annual_projection() functions above. These remain unchanged (Phase invariant).
# The functions below ADD validation and honest assessment on top.

_MIN_PERIODS_FOR_FORECAST = 6   # M3 gate: minimum unique valid periods

FORECAST_LIMITATION = (
    "Forecasts are model-based estimates derived from historical emissions "
    "and should not be interpreted as guaranteed future outcomes. "
    "The model uses ordinary least-squares linear regression on historical "
    "emission data. No seasonal decomposition or exogenous variables are used. "
    "Accuracy degrades significantly outside the historical range."
)

FORECAST_MODEL_TYPE = "OLS linear regression (numpy.polyfit degree=1)"


def _detect_missing_months(sorted_keys: list) -> list:
    """
    Given a list of (year, month_idx) sort keys, identify any gaps
    within the same year (full 12-month span assumed per year present).
    Returns list of human-readable missing period labels.
    """
    _IDX_TO_ABBR = {v: k.title() for k, v in _MONTH_ORDER.items()}
    if not sorted_keys:
        return []
    years = sorted({yr for yr, _ in sorted_keys})
    missing = []
    for yr in years:
        present = {mi for (y, mi) in sorted_keys if y == yr}
        min_m   = min(present)
        max_m   = max(present)
        for mi in range(min_m, max_m + 1):
            if mi not in present:
                lbl = f"{_IDX_TO_ABBR.get(mi, str(mi))} {yr}" if yr else _IDX_TO_ABBR.get(mi, str(mi))
                missing.append(lbl)
    return missing


def validate_forecast_history(df, dq_validation_status: str = None) -> dict:
    """
    Phase 5-B data gate. Determines whether the dataset is sufficient for
    defensible forecast output.

    Gate criteria (ALL must pass):
      1. DataFrame is not None / empty
      2. 'Emission' column present and numeric
      3. 'Month' column present
      4. At least MIN_PERIODS unique chronological periods
      5. No duplicate period entries
      6. No all-zero or all-NaN emission column
      7. Data Quality validation_status is not 'Fail' (if provided)

    Parameters
    ----------
    df                   : Emission DataFrame.
    dq_validation_status : Optional — 'Pass'|'Warning'|'Fail' from DQ service.

    Returns
    -------
    dict with valid, n_unique_periods, n_required, has_duplicates,
    has_missing_periods, missing_periods, reason, coverage_label.
    """
    import pandas as pd, numpy as np

    base = {
        "valid":               False,
        "n_unique_periods":    0,
        "n_required":          _MIN_PERIODS_FOR_FORECAST,
        "has_duplicates":      False,
        "has_missing_periods": False,
        "missing_periods":     [],
        "reason":              "",
        "coverage_label":      "",
    }

    # Gate 7: DQ validation failure
    if dq_validation_status == "Fail":
        return {**base,
                "reason": "Forecast unavailable because data quality validation failed. "
                          "Resolve validation errors in the Data Quality page first."}

    if df is None or (hasattr(df, "empty") and df.empty):
        return {**base, "reason": "No dataset uploaded."}

    if "Emission" not in df.columns:
        return {**base, "reason": "Dataset is missing the required 'Emission' column."}

    if "Month" not in df.columns:
        return {**base, "reason": "Dataset is missing the required 'Month' column."}

    emission   = pd.to_numeric(df["Emission"], errors="coerce")
    valid_mask = emission.notna() & (emission >= 0)
    n_valid    = valid_mask.sum()

    if n_valid == 0:
        return {**base, "reason": "No valid (non-null, non-negative) emission values found."}

    if emission[valid_mask].sum() == 0:
        return {**base, "reason": "All emission values are zero — forecast not meaningful."}

    months         = df["Month"].astype(str).str.strip()
    unique_periods = months[valid_mask].unique()
    n_unique       = len(unique_periods)
    has_duplicates = months[valid_mask].duplicated().any()

    label = f"{n_unique} valid period(s) of {_MIN_PERIODS_FOR_FORECAST} required"

    if has_duplicates:
        return {**base, "has_duplicates": True, "n_unique_periods": n_unique,
                "coverage_label": label,
                "reason": ("Duplicate reporting periods detected. "
                           "Resolve duplicates in Data Quality before running forecast.")}

    if n_unique < _MIN_PERIODS_FOR_FORECAST:
        return {**base, "n_unique_periods": n_unique, "coverage_label": label,
                "reason": (f"Insufficient historical coverage: {n_unique} valid period(s) found, "
                           f"{_MIN_PERIODS_FOR_FORECAST} required. "
                           f"Upload at least {_MIN_PERIODS_FOR_FORECAST - n_unique} more period(s).")}

    # Gap detection — sort keys chronologically then find missing months
    sort_keys     = [_parse_period_sort_key(p) for p in unique_periods]
    missing_list  = _detect_missing_months(sort_keys)
    has_gaps      = len(missing_list) > 0

    # Gaps are a warning (not a hard block) unless they exceed 20% of coverage
    if has_gaps and len(missing_list) > max(1, n_unique // 5):
        return {**base, "n_unique_periods": n_unique, "coverage_label": label,
                "has_missing_periods": True, "missing_periods": missing_list,
                "reason": (f"Historical series has {len(missing_list)} missing period(s): "
                           f"{', '.join(missing_list[:3])}{'...' if len(missing_list) > 3 else ''}. "
                           "Upload missing periods or note this limitation in disclosures.")}

    return {
        "valid":               True,
        "n_unique_periods":    n_unique,
        "n_required":          _MIN_PERIODS_FOR_FORECAST,
        "has_duplicates":      False,
        "has_missing_periods": has_gaps,
        "missing_periods":     missing_list,
        "reason":              "",
        "coverage_label":      label,
    }


# Canonical month ordering for chronological sort
_MONTH_ORDER = {
    "jan": 0,  "feb": 1,  "mar": 2,  "apr": 3,
    "may": 4,  "jun": 5,  "jul": 6,  "aug": 7,
    "sep": 8,  "oct": 9,  "nov": 10, "dec": 11,
}

# Full month name → abbreviated
_MONTH_FULL = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
}


def _parse_period_sort_key(period_str: str):
    """
    Parse a period string into a (year, month_idx) sort key.
    Handles: "Jan", "February", "Jan 2024", "2024-01", "2024-01-01".
    Returns (0, month_idx) when no year is detected.
    """
    import re
    s = str(period_str).strip().lower()

    # Try YYYY-MM or YYYY-MM-DD
    m = re.match(r"(\d{4})[-/](\d{1,2})", s)
    if m:
        return (int(m.group(1)), int(m.group(2)) - 1)

    # Extract 4-digit year if present
    year_m = re.search(r"\b(20\d{2}|19\d{2})\b", s)
    year   = int(year_m.group(1)) if year_m else 0

    # Try 3-letter month abbreviation
    abbr_m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", s)
    if abbr_m:
        return (year, _MONTH_ORDER[abbr_m.group(1)])

    # Try full month name
    for full, idx in _MONTH_FULL.items():
        if full in s:
            return (year, idx - 1)

    # Fallback: return (0, 0) — unknown period sorts to beginning
    return (0, 0)


def _sort_df_chronologically(df):
    """Return df with rows sorted by canonical (year, month) order. No shuffle."""
    import pandas as pd
    if df is None or df.empty or "Month" not in df.columns:
        return df
    keys = [_parse_period_sort_key(p) for p in df["Month"]]
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    return df.iloc[order].reset_index(drop=True)


def chronological_train_test_split(df, holdout_n: int = 2):
    """
    Sort dataset chronologically, then split. Holdout = LAST N periods.
    No random shuffle is ever applied.

    Parameters
    ----------
    df        : DataFrame with Month and Emission columns.
    holdout_n : Number of periods to hold out (default 2).

    Returns
    -------
    (train_df, test_df) — both DataFrames, chronologically ordered, never shuffled.
    """
    import pandas as pd
    if df is None or len(df) <= holdout_n:
        return df, pd.DataFrame()
    sorted_df = _sort_df_chronologically(df)
    train = sorted_df.iloc[:-holdout_n].copy()
    test  = sorted_df.iloc[-holdout_n:].copy()
    return train, test


def _fit_ols(df):
    """Fit OLS to emission series. Returns (coeffs, x, y)."""
    import numpy as np, pandas as pd
    emission = pd.to_numeric(df["Emission"], errors="coerce").fillna(0)
    x = np.arange(len(emission), dtype=float)
    coeffs = np.polyfit(x, emission.values.astype(float), 1)
    return coeffs, x, emission.values.astype(float)


def evaluate_holdout(train_df, test_df) -> dict:
    """
    Evaluate the OLS forecast model on holdout test periods.
    Uses the model fitted on train_df to predict test_df values.

    Returns MAE, RMSE, R² (on holdout), and raw predictions.
    R² is reported as None when n_test < 3 (not statistically meaningful).
    Training R² is never labelled as validation accuracy.
    """
    import numpy as np, pandas as pd

    empty = {
        "mae": None, "rmse": None, "r2_holdout": None,
        "n_train": 0, "n_test": 0,
        "predictions": [], "actuals": [],
        "status": "insufficient_data",
    }

    if train_df is None or test_df is None or train_df.empty or test_df.empty:
        return empty

    try:
        coeffs, _, _ = _fit_ols(train_df)
        n_train = len(train_df)

        test_emission = pd.to_numeric(test_df["Emission"], errors="coerce").fillna(0)
        n_test        = len(test_emission)

        x_test      = np.arange(n_train, n_train + n_test, dtype=float)
        predictions  = np.polyval(coeffs, x_test).tolist()
        actuals      = test_emission.values.tolist()

        errors = [p - a for p, a in zip(predictions, actuals)]
        mae    = float(np.mean([abs(e) for e in errors]))
        rmse   = float(np.sqrt(np.mean([e**2 for e in errors])))

        # R² only when statistically meaningful (≥3 holdout points)
        r2 = None
        if n_test >= 3:
            ss_res = sum((p - a)**2 for p, a in zip(predictions, actuals))
            ss_tot = sum((a - float(np.mean(actuals)))**2 for a in actuals)
            r2 = round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else None

        return {
            "mae":          round(mae,  2),
            "rmse":         round(rmse, 2),
            "r2_holdout":   r2,
            "n_train":      n_train,
            "n_test":       n_test,
            "predictions":  [round(p, 2) for p in predictions],
            "actuals":      [round(a, 2) for a in actuals],
            "status":       "evaluated",
        }
    except Exception as exc:
        log.warning(f"evaluate_holdout failed: {exc}")
        return {**empty, "status": "evaluation_failed"}


def naive_baseline(train_df, test_df) -> dict:
    """
    Naive baseline: predict each test period using the previous period's value.
    If test has n periods, the baseline uses the last training value for period 1,
    and each test actual for subsequent periods (random walk).

    Returns naive MAE and RMSE for honest comparison against the OLS model.
    """
    import numpy as np, pandas as pd

    if train_df is None or test_df is None or train_df.empty or test_df.empty:
        return {"mae": None, "rmse": None, "status": "insufficient_data"}

    try:
        train_emission = pd.to_numeric(train_df["Emission"], errors="coerce").fillna(0)
        test_emission  = pd.to_numeric(test_df["Emission"],  errors="coerce").fillna(0)

        # Naive = previous period value (lag-1 random walk)
        last_train = float(train_emission.iloc[-1])
        all_vals   = [last_train] + test_emission.values.tolist()
        preds      = all_vals[:-1]   # shifted by 1
        actuals    = test_emission.values.tolist()

        errors = [p - a for p, a in zip(preds, actuals)]
        mae    = float(np.mean([abs(e) for e in errors]))
        rmse   = float(np.sqrt(np.mean([e**2 for e in errors])))

        return {
            "mae":    round(mae,  2),
            "rmse":   round(rmse, 2),
            "status": "evaluated",
        }
    except Exception as exc:
        log.warning(f"naive_baseline failed: {exc}")
        return {"mae": None, "rmse": None, "status": "failed"}


def forecast_with_validation(df, dq_validation_status: str = None) -> dict:
    """
    Phase 5-B entry point for hardened forecast computation.

    Steps:
      1. validate_forecast_history()   → data gate (includes DQ status check)
      2. chronological_train_test_split() → canonical chronological sort + split
      3. evaluate_holdout()            → model validation metrics
      4. naive_baseline()              → baseline comparison
      5. predict_next_emission()       → next-period forecast on full series

    Returns a comprehensive dict suitable for UI rendering and provenance panel.
    All labels are honest — no training R² presented as validation accuracy.

    Parameters
    ----------
    df                   : Emission DataFrame.
    dq_validation_status : Optional Phase 2 DQ validation status string.
    """
    gate = validate_forecast_history(df, dq_validation_status=dq_validation_status)
    if not gate["valid"]:
        return {
            "valid":              False,
            "gate":               gate,
            "forecast":           {},
            "validation":         {},
            "naive":              {},
            "outperforms_baseline": None,
            "next_period_value":  None,
            "model_type":         FORECAST_MODEL_TYPE,
            "limitation":         FORECAST_LIMITATION,
        }

    train_df, test_df = chronological_train_test_split(df, holdout_n=2)
    validation        = evaluate_holdout(train_df, test_df)
    naive             = naive_baseline(train_df, test_df)
    forecast          = predict_next_emission(df)    # full-series forecast

    # Baseline comparison
    outperforms = None
    if (validation.get("mae") is not None and naive.get("mae") is not None
            and naive["mae"] > 0):
        outperforms = validation["mae"] < naive["mae"]

    return {
        "valid":                True,
        "gate":                 gate,
        "forecast":             forecast,
        "validation":           validation,
        "naive":                naive,
        "outperforms_baseline": outperforms,
        "next_period_value":    forecast.get("next_month"),
        "model_type":           FORECAST_MODEL_TYPE,
        "limitation":           FORECAST_LIMITATION,
        "n_train":              validation.get("n_train", 0),
        "n_test":               validation.get("n_test",  0),
    }
