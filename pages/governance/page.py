"""
CarbonLens V8 — Governance Workspace.

Fifth production page. Operationalises all Phase 3 Auditability features:
  - Complete audit trail with filters
  - Methodology Library (28 entries)
  - Emission Factor Library (Scope 1/2/3)
  - Methodology transparency panels
  - System activity summary
  - Governance metrics KPIs

Architecture rules:
  - All service calls at TOP of render() before rendering
  - No calculations, no repository access, no st.session_state
  - Navigation via services.state_service.navigate_to() only

Permitted calls: audit_service · state_service
"""
from __future__ import annotations
import streamlit as st

import services.state_service as state_svc
import services.audit_service as audit_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer,
)
from components.provenance_panel import provenance_panel, methodology_footnote
from components.tables.audit_table import audit_table, EVENT_ICONS
from components.theme.colors import (
    ENV_COLOR, SOC_COLOR, GOV_COLOR, BRAND_ACCENT,
    SUCCESS, WARNING, ERROR,
)
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, TRACKING_WIDE


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching before rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    company = str(org.get("company_name", "")) if org else ""
    period  = str(org.get("reporting_period", "")) if org else ""

    # ── 2. Fetch all governance data ──────────────────────────────────────────
    audit_events  = audit_svc.get_log(limit=200)
    report_events = audit_svc.get_report_events(limit=20)
    comp_events   = audit_svc.get_computation_events(limit=20)
    meth_library  = state_svc.get_methodology_library()
    ef_library    = state_svc.get_emission_factor_library()
    gov_metrics   = state_svc.get_governance_metrics()

    # ── 3. Render all 7 sections ──────────────────────────────────────────────
    _s1_header(company, period, gov_metrics)
    _s2_audit_trail(audit_events)
    _s3_methodology_library(meth_library)
    _s4_emission_factor_library(ef_library)
    _s5_methodology_transparency()
    _s6_system_activity(report_events, comp_events)
    _s7_governance_metrics(gov_metrics)
    methodology_footnote()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_header(company: str, period: str, metrics: dict) -> None:
    n_events = metrics.get("total_audit_events", 0)
    badge = f"{n_events} audit events" if n_events > 0 else "No events yet"
    page_header(
        title       = "Governance & Audit",
        subtitle    = f"{company}  ·  {period}" if period else "Platform governance dashboard",
        badge       = badge,
        badge_type  = "blue",
        destination = "governance",
    )


def _s2_audit_trail(events: list) -> None:
    divider("Audit Trail")
    audit_table(events, show_filters=True, max_rows=50)
    spacer(8)


def _s3_methodology_library(entries: list) -> None:
    divider("Methodology Library")

    if not entries:
        info_banner("Methodology library not available.", "info")
        return

    # Group by category
    categories: dict[str, list] = {}
    for e in entries:
        cat = e.get("category", "General")
        categories.setdefault(cat, []).append(e)

    cat_colors = {
        "ESG Composite Weights":       BRAND_ACCENT,
        "Environmental Sub-indicators": ENV_COLOR,
        "Social Sub-indicators":        SOC_COLOR,
        "Governance Sub-indicators":    GOV_COLOR,
        "ESG Grade Bands":              "#7C3AED",
        "Confidence Model":             "#D97706",
        "Data Quality Model":           "#0891B2",
        "GHG Inventory":                "#059669",
    }

    for cat, cat_entries in categories.items():
        color = cat_colors.get(cat, "#64748B")
        with st.expander(f"{cat} ({len(cat_entries)} entries)", expanded=False):
            # Header row
            st.markdown(
                f'<div style="display:grid;grid-template-columns:2fr 1fr 2fr 2fr;'
                f'gap:4px;padding:4px 0;border-bottom:1.5px solid #E2E8F0;'
                f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
                f'letter-spacing:{TRACKING_WIDE};color:#94A3B8;">'
                f'<div>Name</div><div>Value</div><div>Formula</div><div>Source · GRI</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for i, entry in enumerate(cat_entries):
                bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
                gri = entry.get("gri_reference","")
                src = entry.get("source","")
                intro = entry.get("introduced_in","")
                src_str = f"{src}" + (f" · {gri}" if gri else "") + (f" · {intro}" if intro else "")

                st.markdown(
                    f'<div style="display:grid;grid-template-columns:2fr 1fr 2fr 2fr;'
                    f'gap:4px;padding:7px 4px;background:{bg};'
                    f'border-bottom:1px solid #F1F5F9;font-size:{SIZE_BASE};">'
                    f'<div style="font-weight:{WEIGHT_BOLD};color:#0F172A;">'
                    f'{entry.get("name","")}</div>'
                    f'<div style="font-weight:{WEIGHT_BOLD};color:{color};">'
                    f'{entry.get("value","")}</div>'
                    f'<div style="color:#64748B;font-family:monospace;font-size:{SIZE_SM};">'
                    f'{entry.get("formula","")}</div>'
                    f'<div style="color:#94A3B8;font-size:{SIZE_SM};">{src_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if entry.get("rationale"):
                    st.markdown(
                        f'<div style="font-size:{SIZE_XS};color:#94A3B8;'
                        f'padding:2px 4px 6px 4px;background:{bg};">'
                        f'↳ {entry["rationale"]}</div>',
                        unsafe_allow_html=True,
                    )

    st.caption(f"{len(entries)} methodology entries · CarbonLens V8 · GRI 2021 aligned")
    spacer(8)


def _s4_emission_factor_library(entries: list) -> None:
    divider("Emission Factor Library")

    if not entries:
        info_banner("Emission factor library not available.", "info")
        return

    # Group by category
    categories: dict[str, list] = {}
    for e in entries:
        cat = e.get("category", "Other")
        categories.setdefault(cat, []).append(e)

    cat_colors = {
        "Scope 1 — Combustion":     ENV_COLOR,
        "Scope 2 — Grid Electricity": BRAND_ACCENT,
        "Scope 3 — Value Chain":    SOC_COLOR,
    }

    for cat, cat_entries in categories.items():
        color = cat_colors.get(cat, "#64748B")
        with st.expander(f"{cat} ({len(cat_entries)} factors)", expanded=False):
            st.markdown(
                f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 2fr 1fr;'
                f'gap:4px;padding:4px 0;border-bottom:1.5px solid #E2E8F0;'
                f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
                f'letter-spacing:{TRACKING_WIDE};color:#94A3B8;">'
                f'<div>Factor</div><div>Value</div><div>Unit</div>'
                f'<div>Source</div><div>GWP Basis</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for i, ef in enumerate(cat_entries):
                bg         = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
                co2_only   = ef.get("co2_only_value", 0)
                current_val= ef.get("value", 0)
                h3_note    = (
                    f'<span style="font-size:{SIZE_XS};color:#D97706;"> ↑ was {co2_only}</span>'
                    if co2_only and co2_only != current_val else ""
                )
                regulation = ef.get("regulation","")
                source_str = ef.get("source","")
                if regulation:
                    source_str += f" · {regulation}"

                st.markdown(
                    f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 2fr 1fr;'
                    f'gap:4px;padding:7px 4px;background:{bg};'
                    f'border-bottom:1px solid #F1F5F9;font-size:{SIZE_BASE};">'
                    f'<div style="font-weight:{WEIGHT_BOLD};color:#0F172A;">'
                    f'{ef.get("name","")}</div>'
                    f'<div style="font-weight:{WEIGHT_BOLD};color:{color};">'
                    f'{current_val}{h3_note}</div>'
                    f'<div style="color:#64748B;font-family:monospace;font-size:{SIZE_SM};">'
                    f'{ef.get("unit","")}</div>'
                    f'<div style="color:#94A3B8;font-size:{SIZE_SM};">{source_str}</div>'
                    f'<div style="color:#94A3B8;font-size:{SIZE_SM};">'
                    f'{ef.get("gwp_basis","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if ef.get("notes"):
                    st.markdown(
                        f'<div style="font-size:{SIZE_XS};color:#94A3B8;'
                        f'padding:2px 4px 6px 4px;background:{bg};">'
                        f'↳ {ef["notes"]}</div>',
                        unsafe_allow_html=True,
                    )

    st.caption(
        f"{len(entries)} emission factors · "
        "Sources: IPCC 2006, Kepmen ESDM No.18/2023, DEFRA 2023, USEEIO v2.0, GLEC v3"
    )
    spacer(8)


def _s5_methodology_transparency() -> None:
    divider("Methodology Transparency")

    esg_rows = [
        {"label":"Composite formula", "value":"E×0.40 + S×0.30 + G×0.30",
         "source":"CarbonLens V8 Phase 0 C2", "formula":"Weighted average",
         "note":"Weights sum to 1.0; sourced from constants.py"},
        {"label":"ESG confidence", "value":"n_disclosed / 8 × 100%",
         "source":"CarbonLens V8 Phase 0 C3", "formula":"S/G disclosure ratio",
         "note":"Provisional when < 50%"},
        {"label":"Provisional floor", "value":"50%",
         "source":"CarbonLens V8 Phase 0 C3", "formula":"Confidence < floor → Provisional",
         "note":"Applies independently to ESG and DQ confidence"},
    ]
    provenance_panel(
        title="ESG Scoring", rows=esg_rows, key="gov_esg_prov",
        expanded=False, methodology_note="GRI 2021 aligned · CarbonLens V8",
    )

    dq_rows = [
        {"label":"DQ confidence formula",
         "value":"completeness×0.40 + consistency×0.35 + validation×0.25",
         "source":"CarbonLens V8 Phase 2",
         "formula":"Weighted blend",
         "note":"Capped at 40% when validation == Fail"},
        {"label":"Outlier detection",
         "value":"z-score > 2.0 → flagged",
         "source":"CarbonLens V8 Phase 2",
         "formula":"z = (x − μ) / σ",
         "note":"Requires minimum 3 rows"},
        {"label":"Completeness blend",
         "value":"env×0.60 + sg×0.40",
         "source":"CarbonLens V8 Phase 2",
         "formula":"Weighted blend of env and S/G completeness",
         "note":""},
    ]
    provenance_panel(
        title="Data Quality Confidence", rows=dq_rows, key="gov_dq_prov",
        expanded=False, methodology_note="CarbonLens V8 Phase 2 · Four-part blended model",
    )

    carbon_rows = [
        {"label":"Scope 2 grid factor",
         "value":"Kepmen ESDM No.18/2023",
         "source":"Ministry of Energy and Mineral Resources, Indonesia",
         "formula":"Electricity kWh × PLN EF (province-specific)",
         "note":"34-province subsystem lookup; national average fallback"},
        {"label":"Phase 0 H3 fix",
         "value":"Full CO₂e (CO₂ + CH₄ + N₂O)",
         "source":"IPCC AR6 GWP100 (2021)",
         "formula":"CH₄-fossil=29.8 · N₂O=273",
         "note":"Previous factors were CO₂-only; updated to full CO₂e"},
    ]
    provenance_panel(
        title="GHG Inventory", rows=carbon_rows, key="gov_carbon_prov",
        expanded=False, methodology_note="GHG Protocol Corporate Standard · IPCC 2006 + AR6",
    )
    spacer(8)


def _s6_system_activity(report_events: list, comp_events: list) -> None:
    divider("System Activity")

    col_reports, col_comps = st.columns(2)

    with col_reports:
        st.caption("**Report Generation History**")
        if not report_events:
            st.caption("No reports generated yet.")
        else:
            for ev in report_events[:5]:
                ts    = str(ev.get("ts",""))[:16].replace("T"," ")
                etype = ev.get("event_type","")
                icon  = EVENT_ICONS.get(etype,"○")
                summ  = ev.get("summary","")
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid #F1F5F9;'
                    f'font-size:{SIZE_SM};">'
                    f'<span style="color:#94A3B8;font-family:monospace;">{ts}</span> '
                    f'{icon} {summ}</div>',
                    unsafe_allow_html=True,
                )

    with col_comps:
        st.caption("**Calculation History**")
        if not comp_events:
            st.caption("No recomputations recorded yet.")
        else:
            for ev in comp_events[:5]:
                ts    = str(ev.get("ts",""))[:16].replace("T"," ")
                etype = ev.get("event_type","")
                icon  = EVENT_ICONS.get(etype,"○")
                summ  = ev.get("summary","")
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid #F1F5F9;'
                    f'font-size:{SIZE_SM};">'
                    f'<span style="color:#94A3B8;font-family:monospace;">{ts}</span> '
                    f'{icon} {summ}</div>',
                    unsafe_allow_html=True,
                )
    spacer(8)


def _s7_governance_metrics(metrics: dict) -> None:
    divider("Governance Metrics")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Audit Events",
                 str(metrics.get("total_audit_events", 0)),
                 badge=f"{metrics.get('data_uploads',0)} uploads · "
                       f"{metrics.get('reports_generated',0)} reports",
                 badge_type="blue")
    with c2:
        kpi_card("Methodology Version",
                 metrics.get("methodology_version","—"),
                 badge=f"{metrics.get('methodology_entries',0)} entries",
                 badge_type="green")
    with c3:
        kpi_card("Emission Factors",
                 str(metrics.get("ef_scope1_count",0) +
                     metrics.get("ef_scope2_count",0) +
                     metrics.get("ef_scope3_count",0)),
                 badge=f"S1:{metrics.get('ef_scope1_count',0)} "
                       f"S2:{metrics.get('ef_scope2_count',0)} "
                       f"S3:{metrics.get('ef_scope3_count',0)}",
                 badge_type="blue")
    with c4:
        kpi_card("Recomputations",
                 str(metrics.get("recomputations",0)),
                 badge=f"Last: {metrics.get('last_event_ts','—')}",
                 badge_type="neutral")

    spacer(8)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◉ Executive Summary", use_container_width=True, key="gov_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col2:
        if st.button("◇ Data Quality", use_container_width=True, key="gov_qa_dq"):
            state_svc.navigate_to("data_quality"); st.rerun()
    with col3:
        if st.button("◎ Reporting", use_container_width=True, key="gov_qa_report"):
            state_svc.navigate_to("reporting_compliance"); st.rerun()
    spacer(16)
