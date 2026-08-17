"""
CarbonLens V8 — UploadedDataset and ValidationResult models.
"""
from __future__ import annotations
from typing import Optional
from typing import TypedDict


class ValidationResult(TypedDict):
    """Schema and content validation outcome for an uploaded dataset."""
    status:           str         # "Pass" | "Warning" | "Fail"
    errors:           list[str]   # Hard errors that must be resolved before use
    warnings:         list[str]   # Non-blocking issues
    columns_present:  list[str]   # Column names confirmed after normalisation
    rows_valid:       int         # Rows passing all type and range checks
    rows_total:       int
    normalisation_applied: bool   # True if month column was normalised (e.g. "January"→"Jan")


class UploadedDataset(TypedDict):
    """Represents one uploaded CSV file and its derived metadata."""
    dataset_id:    str
    org_id:        str             # FK → Organisation.org_id
    filename:      str
    upload_ts:     str             # ISO 8601 timestamp
    row_count:     int
    column_names:  list[str]
    validation:    ValidationResult
    df_hash:       str             # SHA-256 of CSV bytes — used for cache invalidation


def make_empty_validation() -> ValidationResult:
    """Return a Fail ValidationResult for sessions with no upload yet."""
    return ValidationResult(
        status                = "Fail",
        errors                = ["No dataset uploaded."],
        warnings              = [],
        columns_present       = [],
        rows_valid            = 0,
        rows_total            = 0,
        normalisation_applied = False,
    )
