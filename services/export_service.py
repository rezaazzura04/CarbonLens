"""
CarbonLens — Export service.
Wraps report_service output with audit event emission.
No st.* imports.
Pages call these to get export data + trigger audit events in one call.
"""
from __future__ import annotations
import datetime
import logging
from typing import Tuple

log = logging.getLogger("carbonlens.services.export")


def prepare_csv_export(state: dict, org: dict) -> Tuple[str, str]:
    """
    Build CSV export data and emit report_exported audit event.

    Parameters
    ----------
    state : ComputedState dict.
    org   : Organisation dict.

    Returns
    -------
    Tuple[str, str] : (csv_string, suggested_filename)
    """
    from services.report_service import build_report_context, build_csv, build_snapshot

    ctx      = build_report_context(state, org)
    csv_data = build_csv(ctx)
    filename = _filename(org, "csv")

    _emit_export_event("report_exported", "csv", state, org, build_snapshot(state, org))
    log.info(f"CSV export prepared: {filename} ({len(csv_data)} chars)")
    return csv_data, filename


def prepare_json_export(state: dict, org: dict) -> Tuple[str, str]:
    """
    Build JSON export data and emit report_exported audit event.

    Returns
    -------
    Tuple[str, str] : (json_string, suggested_filename)
    """
    from services.report_service import build_report_context, build_json, build_snapshot

    ctx       = build_report_context(state, org)
    json_data = build_json(ctx)
    filename  = _filename(org, "json")

    _emit_export_event("report_exported", "json", state, org, build_snapshot(state, org))
    log.info(f"JSON export prepared: {filename} ({len(json_data)} chars)")
    return json_data, filename


def prepare_excel_export(state: dict, org: dict) -> Tuple[bytes, str]:
    """
    Build Excel export data and emit report_exported audit event.

    Returns
    -------
    Tuple[bytes, str] : (excel_bytes, suggested_filename)
    """
    from services.report_service import build_report_context, build_excel, build_snapshot

    ctx        = build_report_context(state, org)
    excel_data = build_excel(ctx)
    filename   = _filename(org, "xlsx")

    _emit_export_event("report_exported", "excel", state, org, build_snapshot(state, org))
    log.info(f"Excel export prepared: {filename} ({len(excel_data)} bytes)")
    return excel_data, filename


def prepare_pdf_export(state: dict, org: dict, sections: list) -> Tuple[bytes, str]:
    """
    Build PDF export data and emit report_exported audit event (Fix F-04).

    Uses the same canonical build_report_context() as every other export
    format — no independent ESG/DQ/carbon recalculation happens for PDF.

    Parameters
    ----------
    state    : ComputedState dict.
    org      : Organisation dict.
    sections : list of section ids (subset of config.constants.APPROVED_REPORT_SECTIONS).

    Returns
    -------
    Tuple[bytes, str] : (pdf_bytes, suggested_filename)
    """
    from services.report_service import build_report_context, build_pdf, build_snapshot
    from config.constants import APPROVED_REPORT_SECTIONS

    valid_sections = [s for s in (sections or []) if s in APPROVED_REPORT_SECTIONS]

    ctx      = build_report_context(state, org)
    pdf_data = build_pdf(ctx, valid_sections)
    filename = _filename(org, "pdf")

    _emit_export_event("report_exported", "pdf", state, org, build_snapshot(state, org))
    log.info(f"PDF export prepared: {filename} ({len(pdf_data)} bytes, sections={valid_sections})")
    return pdf_data, filename


# ── Private helpers ───────────────────────────────────────────────────────────

def _filename(org: dict, ext: str) -> str:
    """Generate a clean suggested filename for an export."""
    company = (org.get("company_name") or "CarbonLens").replace(" ", "_")
    period  = (org.get("reporting_period") or "period").replace(" ", "_")
    date    = datetime.date.today().isoformat()
    return f"{company}_{period}_{date}_CarbonLens.{ext}"


def _emit_export_event(
    event_type: str,
    fmt:        str,
    state:      dict,
    org:        dict,
    snapshot:   dict,
) -> None:
    """Emit an export audit event. Failure is silent (never blocks export)."""
    try:
        from audit.writer import write_audit_event
        company = org.get("company_name", "")
        period  = org.get("reporting_period", "")
        write_audit_event(
            event_type    = event_type,
            summary       = (
                f"{fmt.upper()} report exported for {company} ({period})"
            ),
            detail        = {
                "format":        fmt,
                "company":       company,
                "period":        period,
                "state_id":      state.get("state_id", ""),
                "state_version": state.get("version", 0),
                "esg_score":     state.get("esg", {}).get("score", 0),
                "is_provisional":state.get("esg", {}).get("is_provisional", True),
                "snapshot":      snapshot,
            },
            state_version = state.get("version"),
        )
    except Exception as exc:
        log.warning(f"Export audit event failed: {exc}")
