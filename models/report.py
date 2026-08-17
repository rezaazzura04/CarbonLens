"""
CarbonLens V8 — GeneratedReport model.
"""
from __future__ import annotations
from typing import TypedDict


class GeneratedReport(TypedDict):
    """Record of one report generation event with section manifest."""
    report_id:         str
    org_id:            str
    format:            str          # "pdf" | "csv" | "excel" | "json"
    sections_included: list[str]   # Subset of APPROVED_REPORT_SECTIONS
    state_id:          str          # FK → ComputedState.state_id
    snapshot:          dict         # ReportSnapshot dict embedded at generation time
    generated_at:      str          # ISO 8601
    generated_by:      str          # Username
