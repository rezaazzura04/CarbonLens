"""
CarbonLens — Reporting & Compliance page.

Sprint 11 remediation: replaces "Coming Soon" placeholder with full
Phase 4 unified reporting pipeline implementation.

Four tabs (from config/navigation.py REPORTING_TABS):
  1. GRI Disclosure Readiness  — gap analysis + pillar coverage
  2. Regulatory Alignment      — POJK 51 / GHG Protocol / GRI / IFRS S2
  3. Report Builder            — section composer + PDF/document preview
  4. Exports                   — CSV / Excel / JSON download

Architecture rules:
  - All service calls at TOP of render()
  - report_service used for all content assembly
  - export_service used for all downloads
  - No calculations, no repository access, no st.session_state

Permitted calls: state_service · report_service · audit_service
"""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs

import services.state_service as state_svc
import services.report_service as report_svc
import services.audit_service  as audit_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer,
)
from components.confidence_chip import confidence_chip
from components.tables.report_summary_table import gri_coverage_table
from components.theme.colors import (
    SUCCESS, WARNING, ERROR, ENV_COLOR, SOC_COLOR, GOV_COLOR, BRAND_ACCENT,
)
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, TRACKING_WIDE
from components.theme.icons import icon
from config.navigation import REPORTING_TABS, tab_labels


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching before rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        page_header("Reporting & Compliance", destination="reporting_compliance")
        empty_state("reporting", "No organisation configured",
                    "Set up an organisation profile to generate reports.")
        return

    # ── 2. Fetch state and report data ────────────────────────────────────────
    di        = state_svc.get_disclosure_inputs()
    scope_inp = state_svc.get_scope_inputs()
    state     = state_svc.get_computed_state(
        org               = org,
        disclosure_inputs = di,
        scope_inputs      = scope_inp,
        force             = False,
    )
    gri_data  = state_svc.get_gri_analysis()
    reg_align = state_svc.get_regulatory_alignment(state)

    # ── 3. Build report context (unified — all exports share this) ────────────
    try:
        ctx = report_svc.build_report_context(state, org)
    except Exception as exc:
        ctx = {}
        st.warning(f"Report context could not be assembled: {exc}")

    # ── 4. Extract scalars ────────────────────────────────────────────────────
    esg    = state.get("esg",    {})
    carbon = state.get("carbon", {})
    conf   = state.get("confidence", {})
    dq     = state.get("data_quality", {})

    esg_score    = float(esg.get("score",            0))
    esg_grade    = str(esg.get("grade",              "D"))
    is_prov      = bool(esg.get("is_provisional",    True))
    esg_conf     = float(conf.get("esg_confidence",  0))
    dq_conf      = float(conf.get("dq_confidence",   0))
    total_tco2e  = float(ctx.get("total_tco2e",      0))
    gri_pct      = float(ctx.get("gri_pct",          0))
    company      = str(org.get("company_name",       ""))
    period       = str(org.get("reporting_period",   ""))
    can_export   = state_svc.check_permission("can_export")
    can_report   = state_svc.check_permission("can_report")

    # ── 5. Page header ────────────────────────────────────────────────────────
    status_badge = "Provisional" if is_prov else (
        "Substantive" if esg_score > 0 else "No data"
    )
    page_header(
        title       = "Reporting & Compliance",
        subtitle    = f"{company}  ·  {period}" if period else company,
        badge       = status_badge,
        badge_type  = "yellow" if is_prov else ("green" if esg_score > 0 else "neutral"),
        destination = "reporting_compliance",
    )

    # ── 6. Summary KPI strip ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("ESG Score", f"{esg_score:.1f}",
                 badge=esg_grade,
                 badge_type="green" if esg_grade in ("A","B+") else
                            "blue"  if esg_grade == "B" else "red",
                 icon_name="pie_chart")
    with c2:
        kpi_card("Total Emissions", f"{total_tco2e:.1f}",
                 delta_label="tCO2e", icon_name="activity")
    with c3:
        kpi_card("GRI Coverage", f"{gri_pct:.0f}%",
                 badge="Complete" if gri_pct >= 80 else "Partial",
                 badge_type="green" if gri_pct >= 80 else "yellow",
                 icon_name="pie_chart")
    with c4:
        kpi_card("Report Status",
                 "Substantive" if not is_prov and esg_score > 0 else "Provisional",
                 badge=f"DQ {dq_conf:.0f}%",
                 badge_type="green" if dq_conf >= 70 else "yellow",
                 icon_name="file_check")
    spacer(12)

    # ── 7. Four tabs ──────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs(tab_labels(REPORTING_TABS))

    with t1:
        _tab_gri(gri_data, gri_pct, ctx)

    with t2:
        _tab_regulatory(reg_align)

    with t3:
        section_flags = _tab_builder(state, org, ctx, can_report, is_prov, esg_conf, dq_conf)

    with t4:
        _tab_exports(state, org, ctx, can_export, section_flags)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — GRI Disclosure Readiness
# ─────────────────────────────────────────────────────────────────────────────

def _tab_gri(gri_data: list, gri_pct: float, ctx: dict) -> None:
    divider("GRI 2021 Disclosure Coverage")

    if not gri_data:
        info_banner(
            "GRI gap analysis requires uploaded data and S/G indicator disclosure. "
            "Complete ESG Analytics to see coverage.",
            variant="info",
        )
        return

    # Pillar summary cards
    by_pillar = ctx.get("gri_by_pillar", {})
    col_e, col_s, col_g, col_all = st.columns(4)
    for col, pillar, label, color in [
        (col_e,   "E", "Environmental", ENV_COLOR),
        (col_s,   "S", "Social",        SOC_COLOR),
        (col_g,   "G", "Governance",    GOV_COLOR),
        (col_all, "",  "Overall",       BRAND_ACCENT),
    ]:
        pct = by_pillar.get(pillar, gri_pct) if pillar else gri_pct
        with col:
            st.markdown(
                f'<div style="background:#F5F7F2;border:1.5px solid #DDE5DE;'
                f'border-radius:10px;padding:12px 14px;text-align:center;">'
                f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
                f'color:{color};">{label}</div>'
                f'<div style="font-size:26px;font-weight:800;color:{color};">'
                f'{pct:.0f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    spacer(12)
    gri_coverage_table(gri_data)

    st.caption(
        "GRI 2021 Universal Standards · Disclosure coverage based on uploaded dataset "
        "and S/G indicator entries. Source: GRI Standards 2021."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Regulatory Alignment
# ─────────────────────────────────────────────────────────────────────────────

def _tab_regulatory(reg_align: list) -> None:
    divider("Regulatory Alignment Status")

    if not reg_align:
        info_banner("Regulatory alignment requires computed ESG and carbon data.", "info")
        return

    for item in reg_align:
        status     = item.get("status",     "Partial")
        badge_type = item.get("badge_type", "yellow")
        color_map  = {"green": SUCCESS, "yellow": WARNING, "red": ERROR}
        color      = color_map.get(badge_type, WARNING)
        bg_map     = {"green": "#F0FDF4", "yellow": "#FEFCE8", "red": "#FFF1F2"}
        bg         = bg_map.get(badge_type, "#FEFCE8")

        col_status, col_detail = st.columns([1, 3])
        with col_status:
            st.markdown(
                f'<div style="background:{bg};border:1.5px solid {color};'
                f'border-radius:10px;padding:14px 12px;text-align:center;">'
                f'<div style="font-size:11px;font-weight:{WEIGHT_BOLD};'
                f'color:{color};">{status}</div>'
                f'<div style="font-size:{SIZE_XS};color:{color};margin-top:2px;">'
                f'{item.get("coverage","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_detail:
            st.markdown(
                f'<div style="padding:8px 0;">'
                f'<div style="font-size:13px;font-weight:{WEIGHT_BOLD};color:#17221C;">'
                f'{item.get("framework","")}</div>'
                f'<div style="font-size:{SIZE_SM};color:#64748B;">'
                f'{item.get("standard","")}</div>'
                f'<div style="font-size:{SIZE_SM};color:#66736B;margin-top:4px;">'
                f'{item.get("note","")}</div>'
                + (
                    f'<div style="font-size:{SIZE_SM};color:{BRAND_ACCENT};'
                    f'font-weight:{WEIGHT_BOLD};margin-top:2px;">'
                    f'→ {item["action"]}</div>'
                    if item.get("action") else ""
                )
                + f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div style="height:1px;background:#DDE5DE;margin:4px 0;"></div>',
            unsafe_allow_html=True,
        )

    st.caption(
        "Alignment status is indicative only. CarbonLens is not a certified assurance tool. "
        "Formal regulatory submissions require independent verification."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Report Builder
# ─────────────────────────────────────────────────────────────────────────────

def _tab_builder(
    state: dict, org: dict, ctx: dict,
    can_report: bool, is_prov: bool,
    esg_conf: float, dq_conf: float,
) -> dict:
    """Renders the Report Builder tab. Returns the chosen appendix flags so
    the Exports tab (rendered afterward, in the same script run) can compose
    the same section set for the actual PDF download — this keeps the two
    tabs in sync without either one touching st.session_state directly."""
    divider("Report Composition Engine")

    section_flags = {"methodology": True, "emission_factors": True, "audit_summary": True}

    if not ctx:
        info_banner(
            "No report context available. Upload data and complete ESG Analytics first.",
            variant="info",
        )
        return section_flags

    col_compose, col_preview = st.columns([1, 2])

    with col_compose:
        st.caption("**Select report sections**")
        include_methodology = st.checkbox(
            "Methodology Appendix (GRI weights, formulas, rationale)",
            value=True,
            key="rc_methodology",
        )
        include_ef = st.checkbox(
            "Emission Factor Appendix (IPCC, Kepmen ESDM, DEFRA sources)",
            value=True,
            key="rc_ef",
        )
        include_audit = st.checkbox(
            "Audit Summary (computation history, snapshot)",
            value=True,
            key="rc_audit",
        )
        spacer(8)

        if not can_report:
            info_banner(
                "Your role does not have permission to generate reports. "
                "Contact an admin.",
                variant="warning",
            )
        else:
            if is_prov:
                info_banner(
                    "Score is Provisional — fewer than 50% of S/G indicators disclosed. "
                    "Report will include Provisional label.",
                    variant="warning",
                )

            if st.button("Generate Report Preview", type="primary",
                         **width_stretch_kwargs(), key="rc_generate"):
                audit_svc.emit(
                    event_type = "pdf_generated",
                    summary    = (
                        f"Report preview generated for "
                        f"{org.get('company_name','')} "
                        f"({org.get('reporting_period','')})"
                    ),
                    detail = {
                        "include_methodology": include_methodology,
                        "include_ef":          include_ef,
                        "include_audit":       include_audit,
                        "esg_score":           state.get("esg",{}).get("score", 0),
                        "is_provisional":      is_prov,
                    },
                    state_version = state.get("version"),
                )
                st.success("Report context assembled. Use the Exports tab to download.")

    with col_preview:
        st.caption("**Report preview**")
        _render_report_preview(ctx, state, org, include_methodology, include_ef)

    section_flags["methodology"]       = include_methodology
    section_flags["emission_factors"]  = include_ef
    section_flags["audit_summary"]     = include_audit
    return section_flags


def _render_report_preview(
    ctx: dict, state: dict, org: dict,
    include_methodology: bool, include_ef: bool,
) -> None:
    """Render a structured preview of the report content."""
    from components.theme.colors import grade_color
    esg     = state.get("esg",    {})
    carbon  = state.get("carbon", {})
    grade   = esg.get("grade",    "--")
    gfg, gbg = grade_color(grade)

    st.markdown(
        f'<div style="background:#F5F7F2;border:1.5px solid #DDE5DE;'
        f'border-radius:12px;padding:16px 18px;">'
        f'<div style="font-size:10px;font-weight:{WEIGHT_BOLD};'
        f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
        f'color:#8A968D;margin-bottom:8px;">'
        f'CarbonLens — ESG & Carbon Report</div>'

        f'<div style="font-size:14px;font-weight:800;color:#17221C;">'
        f'{ctx.get("company","")}</div>'
        f'<div style="font-size:11px;color:#64748B;margin-bottom:12px;">'
        f'Reporting period: {ctx.get("reporting_period","")}</div>'

        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">'
        f'<div style="background:{gbg};border-radius:8px;padding:10px;text-align:center;">'
        f'<div style="font-size:9px;color:{gfg};text-transform:uppercase;">ESG Grade</div>'
        f'<div style="font-size:24px;font-weight:800;color:{gfg};">{grade}</div>'
        f'<div style="font-size:11px;color:{gfg};">{ctx.get("esg_score",0):.1f}/100</div>'
        f'</div>'
        f'<div style="background:#F0FDF4;border-radius:8px;padding:10px;text-align:center;">'
        f'<div style="font-size:9px;color:#037C38;text-transform:uppercase;">Total Emissions</div>'
        f'<div style="font-size:22px;font-weight:800;color:#037C38;">'
        f'{ctx.get("total_tco2e",0):.1f}</div>'
        f'<div style="font-size:11px;color:#037C38;">tCO2e</div>'
        f'</div>'
        f'</div>'

        f'<div style="font-size:{SIZE_XS};color:#8A968D;border-top:1px solid #DDE5DE;'
        f'padding-top:8px;display:flex;align-items:center;gap:4px;flex-wrap:wrap;">'
        + (f'{icon("check", size=11, color="#037C38")} Methodology Appendix &nbsp; ' if include_methodology else "")
        + (f'{icon("check", size=11, color="#037C38")} Emission Factor Appendix &nbsp; ' if include_ef else "")
        + f'{icon("check", size=11, color="#037C38")} Executive Summary &nbsp; {icon("check", size=11, color="#037C38")} Carbon &nbsp; {icon("check", size=11, color="#037C38")} ESG'
        + f'</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — Exports
# ─────────────────────────────────────────────────────────────────────────────

def _tab_exports(
    state: dict, org: dict, ctx: dict, can_export: bool, section_flags: dict,
) -> None:
    divider("Export Report")

    if not ctx:
        info_banner(
            "No data available for export. Upload a dataset and complete ESG Analytics.",
            variant="info",
        )
        return

    if not can_export:
        info_banner(
            "Your role (Viewer) does not have permission to export reports. "
            "Contact an administrator.",
            variant="warning",
        )
        return

    company = org.get("company_name","CarbonLens").replace(" ","_")
    period  = org.get("reporting_period","period").replace(" ","_")
    import datetime
    date_str = datetime.date.today().isoformat()

    st.caption("Choose an export format. All formats use the same unified report context.")
    spacer(4)

    col1, col2, col3, col4 = st.columns(4)

    # CSV
    with col1:
        st.markdown(
            f'<div style="background:#F5F7F2;border:1px solid #DDE5DE;'
            f'border-radius:10px;padding:14px;text-align:center;">'
            f'<div style="margin-bottom:6px;display:flex;justify-content:center;">{icon("database", size=20, color="#037C38")}</div>'
            f'<div style="font-size:12px;font-weight:{WEIGHT_BOLD};">CSV Summary</div>'
            f'<div style="font-size:{SIZE_XS};color:#8A968D;margin-top:4px;">'
            f'ESG + Carbon metrics · Spreadsheet compatible</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        try:
            csv_str = report_svc.build_csv(ctx)
            csv_fn  = f"{company}_{period}_{date_str}_CarbonLens.csv"
            st.download_button(
                "Download CSV", data=csv_str, file_name=csv_fn,
                mime="text/csv", **width_stretch_kwargs(), key="dl_csv",
            )
        except Exception as exc:
            st.error(f"CSV generation failed: {exc}")

    # Excel — deferred + cached (Phase 6): openpyxl workbook building is
    # real work, so this only runs on explicit request, not on every render
    # of this tab, and is cached by (org, ComputedState version) so
    # re-clicking without any underlying change doesn't rebuild it.
    with col2:
        st.markdown(
            f'<div style="background:#F5F7F2;border:1px solid #DDE5DE;'
            f'border-radius:10px;padding:14px;text-align:center;">'
            f'<div style="margin-bottom:6px;display:flex;justify-content:center;">{icon("file_check", size=20, color="#037C38")}</div>'
            f'<div style="font-size:12px;font-weight:{WEIGHT_BOLD};">Excel Workbook</div>'
            f'<div style="font-size:{SIZE_XS};color:#8A968D;margin-top:4px;">'
            f'3 sheets: Summary, Carbon, ESG</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        xl_fn = f"{company}_{period}_{date_str}_CarbonLens.xlsx"
        _render_deferred_export(
            fmt="excel", org=org, state=state, ctx=ctx,
            builder=lambda: report_svc.build_excel(ctx),
            filename=xl_fn,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            button_label="Generate Excel", download_label="Download Excel",
            key_suffix="excel",
        )

    # JSON
    with col3:
        st.markdown(
            f'<div style="background:#F5F7F2;border:1px solid #DDE5DE;'
            f'border-radius:10px;padding:14px;text-align:center;">'
            f'<div style="font-size:18px;font-weight:800;margin-bottom:6px;color:#037C38;">&#x7B;&#x7D;</div>'
            f'<div style="font-size:12px;font-weight:{WEIGHT_BOLD};">JSON Data</div>'
            f'<div style="font-size:{SIZE_XS};color:#8A968D;margin-top:4px;">'
            f'Machine-readable · API-compatible</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        try:
            json_str = report_svc.build_json(ctx)
            json_fn  = f"{company}_{period}_{date_str}_CarbonLens.json"
            st.download_button(
                "Download JSON", data=json_str, file_name=json_fn,
                mime="application/json", **width_stretch_kwargs(), key="dl_json",
            )
        except Exception as exc:
            st.error(f"JSON generation failed: {exc}")

    # PDF — deferred + cached (Phase 6): reportlab document building (up to
    # 3 appendices) is the most expensive export format, so this only runs
    # on explicit request. Cached by (org, ComputedState version, chosen
    # section flags) — different appendix selections are different exports.
    with col4:
        st.markdown(
            f'<div style="background:#F5F7F2;border:1px solid #DDE5DE;'
            f'border-radius:10px;padding:14px;text-align:center;">'
            f'<div style="margin-bottom:6px;display:flex;justify-content:center;">{icon("reporting", size=20, color="#037C38")}</div>'
            f'<div style="font-size:12px;font-weight:{WEIGHT_BOLD};">PDF Report</div>'
            f'<div style="font-size:{SIZE_XS};color:#8A968D;margin-top:4px;">'
            f'Formatted report + selected appendices</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        core_sections = [
            "executive_summary", "carbon_accounting", "esg_score",
            "data_quality", "benchmarking", "reporting_compliance",
        ]
        if section_flags.get("methodology"):
            core_sections.append("methodology_appendix")
        if section_flags.get("emission_factors"):
            core_sections.append("emission_factor_appendix")
        if section_flags.get("audit_summary"):
            core_sections.append("audit_summary")
        pdf_fn = f"{company}_{period}_{date_str}_CarbonLens.pdf"
        _render_deferred_export(
            fmt="pdf", org=org, state=state, ctx=ctx,
            builder=lambda: report_svc.build_pdf(ctx, core_sections),
            filename=pdf_fn, mime="application/pdf",
            button_label="Generate PDF", download_label="Download PDF",
            key_suffix="pdf", extra_fingerprint=",".join(sorted(core_sections)),
        )

    spacer(8)
    st.caption(
        "Appendices for the PDF (Methodology, Emission Factors, Audit Summary) "
        "are chosen in the Report Builder tab. All exports use the unified "
        "Phase 4 report context."
    )

    # Quick navigation
    spacer(8)
    col_nav1, col_nav2, col_nav3 = st.columns(3)
    with col_nav1:
        if st.button("Executive Summary", **width_stretch_kwargs(), key="rc_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col_nav2:
        if st.button("Governance", **width_stretch_kwargs(), key="rc_qa_gov"):
            state_svc.navigate_to("governance"); st.rerun()
    with col_nav3:
        if st.button("ESG Analytics", **width_stretch_kwargs(), key="rc_qa_esg"):
            state_svc.navigate_to("esg_analytics"); st.rerun()
    spacer(16)


def _render_deferred_export(
    fmt: str, org: dict, state: dict, ctx: dict, builder, filename: str, mime: str,
    button_label: str, download_label: str, key_suffix: str,
    extra_fingerprint: str = "",
) -> None:
    """
    Phase 6 — Staged Loading + Lazy Generation for expensive export formats.

    Generation only happens on explicit button click (never eagerly on tab
    render), shows a spinner while it runs, and the result is cached by
    (org_id, ComputedState version, format, extra_fingerprint) so
    re-rendering the page (or re-clicking without any underlying change)
    reuses the cached bytes instead of rebuilding. CSV/JSON stay eager —
    they're cheap string formatting, not worth the extra click.
    """
    cached = state_svc.get_cached_export(
        org.get("org_id", ""), state.get("version", 0), fmt, extra_fingerprint,
    )

    if cached is not None:
        data, cached_filename = cached
        st.download_button(
            download_label, data=data, file_name=cached_filename,
            mime=mime, **width_stretch_kwargs(), key=f"dl_{key_suffix}",
        )
        return

    if st.button(button_label, **width_stretch_kwargs(), key=f"gen_{key_suffix}"):
        try:
            with st.spinner(f"Generating {download_label.replace('Generate ', '').replace('Download ', '')}…"):
                data = builder()
            state_svc.cache_export(
                org.get("org_id", ""), state.get("version", 0), fmt, data, filename, extra_fingerprint,
            )
            st.rerun()
        except Exception as exc:
            st.error(f"{button_label} failed: {exc}")
