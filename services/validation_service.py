"""
CarbonLens V8 — Validation service.
Orchestrates CSV upload validation. No formulas. No st.* imports.
All normalisation delegated to calculations.utilities.
"""
from __future__ import annotations
import io
import logging
from typing import Optional, Tuple

log = logging.getLogger("carbonlens.services.validation")

REQUIRED_COLUMNS = {"Month", "Emission"}
OPTIONAL_COLUMNS = {"Energy", "Waste", "Water"}
SCOPE_COLUMNS    = {"Scope1", "Scope2", "Scope3"}


def validate_upload(
    file_bytes: bytes,
    filename:   str,
) -> Tuple[Optional[object], dict]:
    """
    Validate an uploaded CSV file.

    Steps:
      1. Parse CSV bytes → raw DataFrame
      2. Check required columns (Month, Emission minimum)
      3. Check Emission column is numeric
      4. Check for negative emission values
      5. Detect duplicate months
      6. Normalise month column ("January" → "Jan")
      7. Return (normalised_df, ValidationResult dict)

    Parameters
    ----------
    file_bytes : Raw bytes of the uploaded file.
    filename   : Original filename (used for extension check).

    Returns
    -------
    Tuple[Optional[DataFrame], dict]
        df     is None when status is "Fail" and the file is unparseable.
        result is always a ValidationResult dict.
    """
    import pandas as pd
    from calculations.utilities import normalise_month_column, hash_dataframe
    from config.constants import (
        VALIDATION_PASS, VALIDATION_WARNING, VALIDATION_FAIL,
    )

    errors:   list[str] = []
    warnings: list[str] = []
    normalised = False

    # Step 1: Extension check
    if not filename.lower().endswith(".csv"):
        errors.append(
            f"Invalid file type: {filename!r}. CarbonLens accepts .csv files only."
        )

    # Step 2: Parse
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        errors.append(f"Could not parse CSV: {exc}")
        return None, _make_result(VALIDATION_FAIL, errors, warnings, [], 0, 0, False)

    if df.empty:
        errors.append("The uploaded file contains no data rows.")
        return None, _make_result(VALIDATION_FAIL, errors, warnings, [], 0, 0, False)

    rows_total = len(df)

    # Step 3: Required column check
    missing_req = REQUIRED_COLUMNS - set(df.columns)
    if missing_req:
        errors.append(
            f"Missing required column(s): {', '.join(sorted(missing_req))}. "
            "The file must contain at least 'Month' and 'Emission' columns."
        )
        return None, _make_result(
            VALIDATION_FAIL, errors, warnings,
            list(df.columns), 0, rows_total, False,
        )

    # Step 4: Normalise month column
    df_norm = normalise_month_column(df)
    if not df["Month"].equals(df_norm["Month"]):
        normalised = True
        warnings.append(
            "Month column contained long-form month names (e.g. 'January'). "
            "Normalised to short form (e.g. 'Jan') automatically."
        )
    df = df_norm

    # Step 5: Emission numeric check
    df["Emission"] = pd.to_numeric(df["Emission"], errors="coerce")
    n_invalid = df["Emission"].isna().sum()
    if n_invalid == rows_total:
        errors.append(
            "The Emission column contains no valid numeric values. "
            "Check the column name and ensure values are numbers (tCO2e)."
        )
        return None, _make_result(
            VALIDATION_FAIL, errors, warnings,
            list(df.columns), 0, rows_total, normalised,
        )
    if n_invalid > 0:
        warnings.append(
            f"{n_invalid} row(s) had non-numeric Emission values — "
            "these rows will be excluded from calculations."
        )
        df = df.dropna(subset=["Emission"]).reset_index(drop=True)

    # Step 6: Negative emission check
    n_negative = (df["Emission"] < 0).sum()
    if n_negative > 0:
        warnings.append(
            f"{n_negative} row(s) have negative Emission values. "
            "These will be treated as zero for calculation purposes."
        )
        df["Emission"] = df["Emission"].clip(lower=0)

    # Step 7: Duplicate month check
    if "Month" in df.columns:
        n_unique = df["Month"].nunique()
        if n_unique < len(df):
            n_dupes = len(df) - n_unique
            warnings.append(
                f"{n_dupes} duplicate month entry(ies) detected. "
                "Each calendar month should appear at most once. "
                "Duplicates are retained — review in Data Quality."
            )

    # Step 8: Optional column reporting
    found_optional = sorted(OPTIONAL_COLUMNS & set(df.columns))
    missing_optional = sorted(OPTIONAL_COLUMNS - set(df.columns))
    if missing_optional:
        warnings.append(
            f"Optional column(s) not found: {', '.join(missing_optional)}. "
            "Including them improves resource intensity metrics."
        )

    # Step 9: Scope column detection (informational)
    found_scope = sorted(SCOPE_COLUMNS & set(df.columns))
    if found_scope:
        warnings.append(
            f"Scope breakdown column(s) detected: {', '.join(found_scope)}. "
            "These will be used for Scope 1/2/3 attribution if present."
        )

    rows_valid = len(df)
    status     = VALIDATION_PASS if not warnings and not errors else (
        VALIDATION_FAIL if errors else VALIDATION_WARNING
    )

    result = _make_result(
        status, errors, warnings,
        list(df.columns), rows_valid, rows_total, normalised,
    )
    log.info(
        f"Validation complete: {filename!r} "
        f"status={status} rows={rows_valid}/{rows_total} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    return df, result


def _make_result(
    status:                str,
    errors:                list,
    warnings:              list,
    columns_present:       list,
    rows_valid:            int,
    rows_total:            int,
    normalisation_applied: bool,
) -> dict:
    """Build a ValidationResult dict from components."""
    return {
        "status":                status,
        "errors":                errors,
        "warnings":              warnings,
        "columns_present":       columns_present,
        "rows_valid":            rows_valid,
        "rows_total":            rows_total,
        "normalisation_applied": normalisation_applied,
    }
