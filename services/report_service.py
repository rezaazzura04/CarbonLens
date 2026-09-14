"""
CarbonLens — Report service.
Assembles all export formats from a single ComputedState.
PDF, CSV, JSON, and Excel export are all implemented here (Fix F-04: PDF
export was previously a NotImplementedError stub). No formulas. No st.* imports.
"""
from __future__ import annotations
import datetime
import json
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.report")


def build_report_context(state: dict, org: dict) -> dict:
    """
    Build the unified report context dict from a ComputedState.

    This is the SINGLE data source for ALL export formats.
    No export format may query ComputedState directly.

    Parameters
    ----------
    state : ComputedState dict from state_service.get_computed_state().
    org   : Organisation dict.

    Returns
    -------
    dict with all fields required by every export format.
    """
    from calculations.utilities import kg_to_tonne
    from calculations.gri_framework import run_gap_analysis, gri_coverage_pct, gri_coverage_by_pillar
    from calculations.benchmarking import benchmark_gap, get_benchmark

    carbon = state.get("carbon", {})
    esg    = state.get("esg",    {})
    dq     = state.get("data_quality", {})
    conf   = state.get("confidence", {})

    org_id  = org.get("org_id", "")
    sector  = org.get("sector", "Manufacturing")
    area_m2 = float(org.get("area_m2", 0) or 0)

    # Attempt GRI gap analysis (requires disclosure inputs from session)
    try:
        from repository.session_repo import get as _get
        di     = _get("disclosure_inputs") or {}
        df_raw = _get("uploaded_df")
        gri    = run_gap_analysis(di, df_raw)
        gri_pct= gri_coverage_pct(gri)
        gri_bp = gri_coverage_by_pillar(gri)
    except Exception:
        gri, gri_pct, gri_bp = [], 0.0, {"E": 0.0, "S": 0.0, "G": 0.0}

    # Forecast — Fix F-03: the validated Phase 5-B forecast MUST come from the
    # single canonical entry point (state_service.get_forecast_validation()).
    # This report service must never independently reconstruct the DQ-gated
    # forecast_with_validation() call — that duplicated the exact same gate
    # logic in two places, risking silent drift if the canonical rules ever
    # change here-but-not-there. annual_projection()/detect_trend() are
    # separate, simpler trend helpers (not the validated forecast contract),
    # so computing them directly here is fine — Executive Summary/Carbon
    # Accounting do the same for their historical trend chart.
    try:
        from services.state_service import get_forecast_validation
        fcast_validated = get_forecast_validation()
        forecast        = fcast_validated.get("forecast", {})
    except Exception as exc:
        log.warning(f"build_report_context: canonical forecast unavailable, report will omit it: {exc}")
        fcast_validated, forecast = {}, {}

    try:
        df_raw2 = None
        try:
            from repository.session_repo import get_uploaded_df
            df_raw2 = get_uploaded_df()
        except Exception as exc:
            log.debug(f"build_report_context: no uploaded_df available for trend section: {exc}")
        from calculations.forecasting import annual_projection, detect_trend
        annual_proj = annual_projection(df_raw2)
        trend       = detect_trend(df_raw2)
    except Exception:
        annual_proj, trend = 0.0, {"direction": "insufficient_data"}

    # Benchmark
    bench = float(carbon.get("benchmark") or get_benchmark(sector))
    gap   = carbon.get("gap") or (
        benchmark_gap(carbon.get("intens_m2", 0), bench) if bench > 0 else {}
    )

    scope1_t = round(kg_to_tonne(carbon.get("scope1_kg", 0)), 2)
    scope2_t = round(kg_to_tonne(carbon.get("scope2_kg", 0)), 2)
    scope3_t = round(kg_to_tonne(carbon.get("scope3_kg", 0)), 2)
    total_t  = round(scope1_t + scope2_t + scope3_t, 2)

    return {
        # Identity
        "org_id":           org_id,
        "company":          org.get("company_name", ""),
        "sector":           sector,
        "area_m2":          area_m2,
        "employees":        org.get("employees", 0),
        "province":         org.get("province", ""),
        "reporting_period": org.get("reporting_period", ""),
        "generated_at":     datetime.datetime.now().isoformat(timespec="seconds"),
        "platform_version": "CarbonLens",
        # ESG
        "esg":              esg,
        "esg_score":        esg.get("score", 0.0),
        "esg_grade":        esg.get("grade", "--"),
        "esg_label":        esg.get("label", "--"),
        "esg_env":          esg.get("env", 0.0),
        "esg_social":       esg.get("social", 0.0),
        "esg_gov":          esg.get("gov", 0.0),
        "esg_confidence":   esg.get("confidence_score", 0.0),
        "is_provisional":   esg.get("is_provisional", True),
        "methodology_disclaimer": esg.get("methodology_disclaimer", ""),
        # Carbon
        "carbon":           carbon,
        "scope1_tco2e":     scope1_t,
        "scope2_tco2e":     scope2_t,
        "scope3_tco2e":     scope3_t,
        "total_tco2e":      total_t,
        "intensity_kg_m2":  carbon.get("intens_m2", 0.0),
        "scope_source":     carbon.get("scope_source", "none"),
        "pln_ef_used":      carbon.get("pln_ef_used", 0.0),
        # Benchmark
        "benchmark":        bench,
        "gap":              gap,
        "gap_pct":          gap.get("gap_pct", 0.0),
        "above_benchmark":  gap.get("above_benchmark", False),
        # Data Quality
        "dq":               dq,
        "dq_confidence":    dq.get("confidence_score", 0.0),
        "dq_validation":    dq.get("validation_status", "--"),
        "dq_flags":         dq.get("flagged_fields", []),
        # Confidence
        "confidence":       conf,
        # GRI
        "gri":              gri,
        "gri_pct":          gri_pct,
        "gri_by_pillar":    gri_bp,
        # Forecast
        "forecast":         forecast,
        "forecast_valid":   fcast_validated.get("valid", False),
        "forecast_limitation": fcast_validated.get("limitation", ""),
        "annual_tco2e":     round(kg_to_tonne(annual_proj), 2),
        "trend":            trend,
        # ComputedState metadata
        "state_id":         state.get("state_id", ""),
        "state_version":    state.get("version", 0),
        "computed_at":      state.get("computed_at", ""),
    }


def build_snapshot(state: dict, org: dict) -> dict:
    """
    Build a lightweight ReportSnapshot dict for the audit trail.
    Used as the detail payload for report_exported / pdf_generated events.
    Read-only. No side effects.

    Parameters
    ----------
    state : ComputedState dict.
    org   : Organisation dict.

    Returns
    -------
    dict : Compact snapshot capturing key platform state at export time.
    """
    esg    = state.get("esg",          {})
    carbon = state.get("carbon",       {})
    dq     = state.get("data_quality", {})
    from calculations.utilities import kg_to_tonne

    return {
        "snapshot_ts":       datetime.datetime.now().isoformat(timespec="seconds"),
        "state_id":          state.get("state_id", ""),
        "state_version":     state.get("version", 0),
        "company_name":      org.get("company_name", ""),
        "sector":            org.get("sector", ""),
        "reporting_period":  org.get("reporting_period", ""),
        "esg_score":         esg.get("score", 0.0),
        "esg_grade":         esg.get("grade", "--"),
        "is_provisional":    esg.get("is_provisional", True),
        "total_tco2e":       round(kg_to_tonne(carbon.get("total_kg", 0)), 2),
        "intensity_kg_m2":   carbon.get("intens_m2", 0.0),
        "dq_confidence":     dq.get("confidence_score", 0.0),
        "dq_validation":     dq.get("validation_status", "--"),
        "platform_version":  "CarbonLens",
    }


def build_csv(context: dict) -> str:
    """
    Build a summary CSV string from the report context.
    Returns a UTF-8 CSV string suitable for st.download_button.
    """
    import csv, io
    buf = io.StringIO()
    w   = csv.writer(buf)

    # Header block
    w.writerow(["CarbonLens — ESG & Carbon Summary Report"])
    w.writerow(["Generated at", context.get("generated_at", "")])
    w.writerow(["Organisation",  context.get("company", "")])
    w.writerow(["Reporting period", context.get("reporting_period", "")])
    w.writerow(["Sector",        context.get("sector", "")])
    w.writerow([])

    # ESG section
    w.writerow(["ESG RESULTS"])
    w.writerow(["Metric", "Value"])
    w.writerow(["ESG Score",           f"{context.get('esg_score', 0):.1f} / 100"])
    w.writerow(["ESG Grade",           context.get("esg_grade", "--")])
    w.writerow(["ESG Status",          "Provisional" if context.get("is_provisional") else "Substantive"])
    w.writerow(["Environmental Score", f"{context.get('esg_env', 0):.1f}"])
    w.writerow(["Social Score",        f"{context.get('esg_social', 0):.1f}"])
    w.writerow(["Governance Score",    f"{context.get('esg_gov', 0):.1f}"])
    w.writerow(["Score Confidence",    f"{context.get('esg_confidence', 0):.0f}%"])
    w.writerow([])

    # Carbon section
    w.writerow(["CARBON ACCOUNTING"])
    w.writerow(["Metric", "Value", "Unit"])
    w.writerow(["Scope 1 (Direct)",    f"{context.get('scope1_tco2e', 0):.2f}", "tCO2e"])
    w.writerow(["Scope 2 (Grid)",      f"{context.get('scope2_tco2e', 0):.2f}", "tCO2e"])
    w.writerow(["Scope 3 (Value chain)",f"{context.get('scope3_tco2e', 0):.2f}","tCO2e"])
    w.writerow(["Total Emissions",     f"{context.get('total_tco2e', 0):.2f}",  "tCO2e"])
    w.writerow(["Carbon Intensity",    f"{context.get('intensity_kg_m2', 0):.2f}", "kg CO2e/m²"])
    w.writerow(["Sector Benchmark",    f"{context.get('benchmark', 0):.0f}",     "kg CO2e/m²"])
    w.writerow(["Gap to Benchmark",    f"{context.get('gap_pct', 0):+.1f}%",    ""])
    w.writerow([])

    # Data Quality
    w.writerow(["DATA QUALITY"])
    w.writerow(["DQ Confidence",       f"{context.get('dq_confidence', 0):.0f}%"])
    w.writerow(["Validation Status",   context.get("dq_validation", "--")])
    w.writerow(["GRI Coverage",        f"{context.get('gri_pct', 0):.1f}%"])

    return buf.getvalue()


def build_json(context: dict) -> str:
    """Build a JSON summary from the report context. Uses NumpyEncoder for safety."""
    from calculations.utilities import NumpyEncoder
    # Remove DataFrame object (not JSON-serialisable)
    safe_ctx = {k: v for k, v in context.items()
                if not hasattr(v, "to_csv")}
    return json.dumps(safe_ctx, cls=NumpyEncoder, indent=2, ensure_ascii=False)


def build_excel(context: dict) -> bytes:
    """
    Build an Excel workbook from the report context.
    Returns bytes suitable for st.download_button(data=..., mime='application/vnd.openxmlformats...').
    Three sheets: Summary, Carbon Detail, ESG Detail.
    """
    import io
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        log.error("openpyxl not installed — Excel export unavailable")
        return b""

    wb    = openpyxl.Workbook()
    _TEAL = "FF0891B2"
    _HEAD = Font(bold=True, color="FFFFFFFF")
    _FILL = PatternFill("solid", fgColor=_TEAL)

    def _header_row(ws, row_idx, values):
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.font  = _HEAD
            cell.fill  = _FILL
            cell.alignment = Alignment(horizontal="center")

    # ── Sheet 1: Summary ─────────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Summary"
    ws1.append(["CarbonLens ESG & Carbon Report"])
    ws1.append(["Organisation", context.get("company", "")])
    ws1.append(["Reporting period", context.get("reporting_period", "")])
    ws1.append(["Generated", context.get("generated_at", "")])
    ws1.append([])
    _header_row(ws1, 6, ["Metric", "Value"])
    summary_rows = [
        ("ESG Score",          f"{context.get('esg_score', 0):.1f} / 100"),
        ("ESG Grade",          context.get("esg_grade", "--")),
        ("ESG Status",         "Provisional" if context.get("is_provisional") else "Substantive"),
        ("Total Emissions",    f"{context.get('total_tco2e', 0):.2f} tCO2e"),
        ("Carbon Intensity",   f"{context.get('intensity_kg_m2', 0):.2f} kg/m²"),
        ("Benchmark Gap",      f"{context.get('gap_pct', 0):+.1f}%"),
        ("DQ Confidence",      f"{context.get('dq_confidence', 0):.0f}%"),
        ("GRI Coverage",       f"{context.get('gri_pct', 0):.1f}%"),
    ]
    for row in summary_rows:
        ws1.append(row)
    ws1.column_dimensions["A"].width = 25
    ws1.column_dimensions["B"].width = 25

    # ── Sheet 2: Carbon Detail ────────────────────────────────────────────────
    ws2 = wb.create_sheet("Carbon")
    _header_row(ws2, 1, ["Scope", "Emissions (tCO2e)", "% of Total"])
    total = context.get("total_tco2e", 0) or 1
    for scope, val in [
        ("Scope 1 — Direct Combustion", context.get("scope1_tco2e", 0)),
        ("Scope 2 — Grid Electricity",  context.get("scope2_tco2e", 0)),
        ("Scope 3 — Value Chain",       context.get("scope3_tco2e", 0)),
    ]:
        ws2.append([scope, round(val, 2), f"{val/total*100:.1f}%"])
    ws2.append(["Total", context.get("total_tco2e", 0), "100%"])

    # ── Sheet 3: ESG Detail ───────────────────────────────────────────────────
    ws3 = wb.create_sheet("ESG")
    _header_row(ws3, 1, ["Pillar", "Score", "Weight"])
    for pillar, score, wt in [
        ("Environmental", context.get("esg_env",    0), "40%"),
        ("Social",        context.get("esg_social", 0), "30%"),
        ("Governance",    context.get("esg_gov",    0), "30%"),
        ("Composite",     context.get("esg_score",  0), "100%"),
    ]:
        ws3.append([pillar, round(score, 1), wt])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_pdf(context: dict, sections: list) -> bytes:
    """
    Build a PDF report from the unified report context (Fix F-04).

    Uses the SAME `context` dict every other export format uses — no
    independent ESG/DQ/carbon recalculation happens here, this function only
    lays out numbers that were already computed by build_report_context().

    Parameters
    ----------
    context  : dict from build_report_context() — single source for all
               numeric/text content in the PDF.
    sections : list of section ids to include, drawn from
               config.constants.APPROVED_REPORT_SECTIONS. Core sections
               (executive_summary, carbon_accounting, esg_score, data_quality,
               benchmarking) always render if present in `sections`; the
               three appendices (methodology_appendix, emission_factor_appendix,
               audit_summary) are optional and each fails gracefully on its
               own — a broken appendix never blocks the rest of the PDF.

    Returns
    -------
    bytes : a valid PDF document (starts with the %PDF- header).
    """
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    sections = set(sections or [])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18*mm, bottomMargin=16*mm, leftMargin=18*mm, rightMargin=18*mm,
        title=f"CarbonLens Report — {context.get('company','')}",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("CLH1", parent=styles["Heading1"], fontSize=18,
                         textColor=colors.HexColor("#17221C"), spaceAfter=4)
    h2 = ParagraphStyle("CLH2", parent=styles["Heading2"], fontSize=13,
                         textColor=colors.HexColor("#3E7C8C"), spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("CLBody", parent=styles["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("CLSmall", parent=styles["BodyText"], fontSize=8,
                            textColor=colors.HexColor("#64748B"), leading=11)
    caption = ParagraphStyle("CLCaption", parent=styles["BodyText"], fontSize=8.5,
                              textColor=colors.HexColor("#8A968D"), alignment=TA_CENTER)

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph("CarbonLens — ESG &amp; Carbon Report", h1))
    story.append(Paragraph(
        f"{context.get('company','—')} &nbsp;·&nbsp; "
        f"{context.get('sector','')} &nbsp;·&nbsp; "
        f"Reporting period {context.get('reporting_period','—')}",
        body,
    ))
    story.append(Paragraph(
        f"Generated {context.get('generated_at','')} · {context.get('platform_version','CarbonLens')}",
        small,
    ))
    story.append(Spacer(1, 10*mm))

    def _kv_table(rows, col_widths=None):
        t = Table(rows, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#66736B")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE5DE")),
        ]))
        return t

    def _section_header_table(rows, col_widths=None):
        t = Table(rows, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3E7C8C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE5DE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7F2")]),
        ]))
        return t

    # ── executive_summary ───────────────────────────────────────────────────
    if "executive_summary" in sections:
        try:
            story.append(Paragraph("Executive Summary", h2))
            status = "Provisional" if context.get("is_provisional") else "Substantive"
            story.append(_kv_table([
                ["ESG Score", f"{context.get('esg_score', 0):.1f} / 100  (Grade {context.get('esg_grade','--')}, {status})"],
                ["Total Emissions", f"{context.get('total_tco2e', 0):.2f} tCO2e"],
                ["Data Quality Confidence", f"{context.get('dq_confidence', 0):.0f}%"],
                ["Benchmark Gap", f"{context.get('gap_pct', 0):+.1f}% vs. sector benchmark"],
            ], col_widths=[55*mm, 110*mm]))
            if context.get("is_provisional"):
                story.append(Spacer(1, 3*mm))
                story.append(Paragraph(
                    "⚠ Score is Provisional — fewer than the required proportion of "
                    "Social/Governance indicators have been disclosed. " +
                    (context.get("methodology_disclaimer") or ""), small,
                ))
        except Exception as exc:
            log.warning(f"build_pdf: executive_summary section failed: {exc}")
            story.append(Paragraph("Executive Summary section unavailable.", small))

    # ── carbon_accounting ────────────────────────────────────────────────────
    if "carbon_accounting" in sections:
        try:
            story.append(Paragraph("Carbon Accounting", h2))
            total = context.get("total_tco2e", 0) or 1
            rows = [["Scope", "Emissions (tCO2e)", "% of Total"]]
            for label, val in [
                ("Scope 1 — Direct Combustion", context.get("scope1_tco2e", 0)),
                ("Scope 2 — Grid Electricity",  context.get("scope2_tco2e", 0)),
                ("Scope 3 — Value Chain",       context.get("scope3_tco2e", 0)),
            ]:
                rows.append([label, f"{val:.2f}", f"{(val/total*100):.1f}%"])
            rows.append(["Total", f"{context.get('total_tco2e', 0):.2f}", "100%"])
            story.append(_section_header_table(rows, col_widths=[80*mm, 45*mm, 40*mm]))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(
                f"Carbon intensity: {context.get('intensity_kg_m2', 0):.2f} kg CO2e/m² "
                f"(sector benchmark: {context.get('benchmark', 0):.0f} kg CO2e/m²). "
                f"Emission factor source: PLN national grid "
                f"{context.get('pln_ef_used', 0):.4f} kg CO2e/kWh (Kepmen ESDM No. 18/2023).",
                small,
            ))
        except Exception as exc:
            log.warning(f"build_pdf: carbon_accounting section failed: {exc}")
            story.append(Paragraph("Carbon Accounting section unavailable.", small))

    # ── esg_score ────────────────────────────────────────────────────────────
    if "esg_score" in sections:
        try:
            story.append(Paragraph("ESG Score Breakdown", h2))
            rows = [["Pillar", "Score", "Weight"],
                    ["Environmental", f"{context.get('esg_env', 0):.1f}", "40%"],
                    ["Social",        f"{context.get('esg_social', 0):.1f}", "30%"],
                    ["Governance",    f"{context.get('esg_gov', 0):.1f}", "30%"],
                    ["Composite",     f"{context.get('esg_score', 0):.1f}", "100%"]]
            story.append(_section_header_table(rows, col_widths=[80*mm, 45*mm, 40*mm]))
        except Exception as exc:
            log.warning(f"build_pdf: esg_score section failed: {exc}")
            story.append(Paragraph("ESG Score section unavailable.", small))

    # ── data_quality ─────────────────────────────────────────────────────────
    if "data_quality" in sections:
        try:
            story.append(Paragraph("Data Quality", h2))
            story.append(_kv_table([
                ["DQ Confidence", f"{context.get('dq_confidence', 0):.0f}%"],
                ["Validation Status", context.get("dq_validation", "--")],
                ["GRI Coverage", f"{context.get('gri_pct', 0):.1f}%"],
            ], col_widths=[55*mm, 110*mm]))
        except Exception as exc:
            log.warning(f"build_pdf: data_quality section failed: {exc}")
            story.append(Paragraph("Data Quality section unavailable.", small))

    # ── benchmarking ─────────────────────────────────────────────────────────
    if "benchmarking" in sections:
        try:
            story.append(Paragraph("Sector Benchmarking", h2))
            above = context.get("above_benchmark", False)
            story.append(_kv_table([
                ["Your Intensity", f"{context.get('intensity_kg_m2', 0):.2f} kg CO2e/m²"],
                ["Sector Benchmark", f"{context.get('benchmark', 0):.0f} kg CO2e/m²"],
                ["Gap", f"{context.get('gap_pct', 0):+.1f}% ({'above' if above else 'below'} benchmark)"],
            ], col_widths=[55*mm, 110*mm]))
        except Exception as exc:
            log.warning(f"build_pdf: benchmarking section failed: {exc}")
            story.append(Paragraph("Benchmarking section unavailable.", small))

    # ── reporting_compliance ─────────────────────────────────────────────────
    if "reporting_compliance" in sections:
        try:
            story.append(Paragraph("Reporting & Compliance Notes", h2))
            story.append(Paragraph(
                f"GRI disclosure coverage: {context.get('gri_pct', 0):.1f}%. "
                f"Alignment status shown in-app is indicative only — CarbonLens "
                f"is not a certified assurance tool. Formal regulatory submissions "
                f"require independent verification.",
                body,
            ))
        except Exception as exc:
            log.warning(f"build_pdf: reporting_compliance section failed: {exc}")
            story.append(Paragraph("Reporting & Compliance section unavailable.", small))

    # ── methodology_appendix (optional) ─────────────────────────────────────
    if "methodology_appendix" in sections:
        try:
            from services.state_service import get_methodology_library
            entries = get_methodology_library()
            story.append(PageBreak())
            story.append(Paragraph("Appendix A — Methodology", h2))
            story.append(Paragraph(
                "All weights, formulas, and scoring bands below are CarbonLens's own "
                "internal methodology — not published by, endorsed by, or derived from "
                "GRI. The GRI column identifies the related disclosure topic only "
                "(e.g. GRI 305 = Emissions), not the source of the specific weight or formula.",
                small,
            ))
            story.append(Spacer(1, 2*mm))
            rows = [["Category", "Metric", "Value", "Related GRI Topic"]]
            for e in entries[:40]:
                rows.append([e.get("category",""), e.get("name",""),
                             str(e.get("value","")), e.get("gri_reference","")])
            story.append(_section_header_table(rows, col_widths=[42*mm,52*mm,26*mm,45*mm]))
        except Exception as exc:
            log.warning(f"build_pdf: methodology_appendix failed: {exc}")
            story.append(Paragraph(
                "Appendix A — Methodology: this section could not be generated for this report.",
                small,
            ))

    # ── emission_factor_appendix (optional) ─────────────────────────────────
    if "emission_factor_appendix" in sections:
        try:
            from services.state_service import get_emission_factor_library
            entries = get_emission_factor_library()
            story.append(PageBreak())
            story.append(Paragraph("Appendix B — Emission Factors", h2))
            rows = [["Category", "Factor", "Value", "Unit", "Source"]]
            for e in entries[:40]:
                rows.append([e.get("category",""), e.get("name",""),
                             str(e.get("value","")), e.get("unit",""), e.get("source","")])
            story.append(_section_header_table(rows, col_widths=[34*mm,34*mm,20*mm,22*mm,55*mm]))
        except Exception as exc:
            log.warning(f"build_pdf: emission_factor_appendix failed: {exc}")
            story.append(Paragraph(
                "Appendix B — Emission Factors: this section could not be generated for this report.",
                small,
            ))

    # ── audit_summary (optional) ─────────────────────────────────────────────
    if "audit_summary" in sections:
        try:
            import services.audit_service as audit_svc
            events = audit_svc.get_events_for_org(context.get("org_id",""), limit=15)
            story.append(PageBreak())
            story.append(Paragraph("Appendix C — Audit Summary", h2))
            if events:
                rows = [["Timestamp", "Event", "Summary"]]
                for ev in events[:15]:
                    rows.append([
                        str(ev.get("timestamp",""))[:19],
                        ev.get("event_type",""),
                        (ev.get("summary","") or "")[:70],
                    ])
                story.append(_section_header_table(rows, col_widths=[34*mm,34*mm,97*mm]))
            else:
                story.append(Paragraph("No audit events recorded for this organisation yet.", small))
        except Exception as exc:
            log.warning(f"build_pdf: audit_summary failed: {exc}")
            story.append(Paragraph(
                "Appendix C — Audit Summary: this section could not be generated for this report.",
                small,
            ))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        "CarbonLens — This report is generated for internal ESG and carbon "
        "management purposes and does not constitute a certified assurance statement.",
        caption,
    ))

    doc.build(story)
    return buf.getvalue()
