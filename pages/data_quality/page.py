"""
CarbonLens V8 — Data Quality Workspace.

Fourth production page. Operational centre for validation and issue resolution.
Follows the three reference implementation patterns exactly.

Architecture rules:
  - All service calls at the TOP of render() before any rendering
  - No calculations, no repository access, no st.session_state
  - Flagged field navigation via services.state_service.navigate_to() only

Permitted calls: state_service · audit_service
"""
from __future__ import annotations
import streamlit as st

import services.state_service as state_svc
import services.audit_service as audit_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer,
)
from components.confidence_chip import (
    quality_band, dual_confidence_row, confidence_chip,
)
from components.provenance_panel import provenance_panel, methodology_footnote
from components.tables.data_quality_table import data_quality_flags_table
from components.theme.colors import (
    ENV_COLOR, SOC_COLOR, GOV_COLOR, SUCCESS, WARNING, ERROR,
    SUCCESS_LIGHT, WARNING_LIGHT, ERROR_LIGHT,
)
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, TRACKING_WIDE


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching before rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        page_header("Data Quality", destination="data_quality")
        empty_state("◇", "No organisation configured",
                    "Set up an organisation profile to begin data quality analysis.")
        return

    # ── 2. Fetch ComputedState ────────────────────────────────────────────────
    di        = state_svc.get_disclosure_inputs()
    scope_inp = state_svc.get_scope_inputs()
    state     = state_svc.get_computed_state(
        org               = org,
        disclosure_inputs = di,
        scope_inputs      = scope_inp,
        force             = False,
    )

    # ── 3. Fetch validation result and quality history ────────────────────────
    validation = state_svc.get_validation_result()
    history    = state_svc.get_quality_history(limit=12)

    # ── 4. Extract all scalars ────────────────────────────────────────────────
    dq     = state.get("data_quality", {})
    conf   = state.get("confidence",   {})

    dq_conf      = float(dq.get("confidence_score",  0))
    dq_prov      = bool(dq.get("is_provisional",     True))
    completeness = float(dq.get("completeness_score", 0))
    consistency  = float(dq.get("consistency_score",  100))
    val_status   = str(dq.get("validation_status",   "Fail"))
    val_score    = float(dq.get("validation_score",   0))
    env_comp     = float(dq.get("env_completeness",   0))
    sg_comp      = float(dq.get("sg_completeness",    0))
    sg_disc      = int(dq.get("sg_disclosed",          0))
    sg_total     = int(dq.get("sg_total",              8))
    flags        = list(dq.get("flagged_fields",       []))
    summary      = str(dq.get("summary",              "No summary available."))

    esg_conf     = float(conf.get("esg_confidence",   0))
    esg_prov     = bool(conf.get("esg_is_provisional", True))

    # Validation result scalars
    val_errors   = list(validation.get("errors",   []))
    val_warnings = list(validation.get("warnings", []))
    val_cols     = list(validation.get("columns_present", []))
    rows_valid   = int(validation.get("rows_valid", 0))
    rows_total   = int(validation.get("rows_total", 0))
    normalised   = bool(validation.get("normalisation_applied", False))

    company = str(org.get("company_name",    ""))
    period  = str(org.get("reporting_period",""))

    # Build provenance rows — no arithmetic
    prov_rows = _build_dq_provenance_rows()

    # ── Render all 8 sections ─────────────────────────────────────────────────
    _s1_header(company, period, val_status, dq_prov)
    _s2_overall_quality(dq, dq_conf, dq_prov, completeness, consistency,
                        val_status, val_score)
    _s3_confidence_summary(esg_conf, esg_prov, dq_conf, dq_prov, dq)
    _s4_flagged_fields(flags)
    _s5_validation_summary(val_status, val_errors, val_warnings, val_cols,
                           rows_valid, rows_total, normalised)
    _s6_completeness(env_comp, sg_comp, sg_disc, sg_total, val_cols)
    _s7_quality_trends(history, dq_conf)
    _s8_methodology(prov_rows, dq_conf, dq_prov, summary)
    methodology_footnote()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_header(company: str, period: str, val_status: str, is_provisional: bool) -> None:
    status_badge = {
        "Pass":    ("Pass", "green"),
        "Warning": ("Warning", "yellow"),
        "Fail":    ("Fail", "red"),
    }.get(val_status, ("No data", "neutral"))
    page_header(
        title       = "Data Quality",
        subtitle    = f"{company}  ·  {period}" if period else company,
        badge       = status_badge[0],
        badge_type  = status_badge[1],
        destination = "data_quality",
    )


def _s2_overall_quality(
    dq: dict, dq_conf: float, dq_prov: bool,
    completeness: float, consistency: float,
    val_status: str, val_score: float,
) -> None:
    divider("Overall Data Quality")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        kpi_card(
            "DQ Confidence",
            f"{dq_conf:.0f}%",
            badge      = "Provisional" if dq_prov else "Substantive",
            badge_type = "yellow" if dq_prov else "green",
        )
    with c2:
        comp_type = "green" if completeness >= 80 else "yellow" if completeness >= 60 else "red"
        kpi_card("Completeness", f"{completeness:.0f}%",
                 badge=f"{'Good' if completeness >= 80 else 'Needs improvement'}",
                 badge_type=comp_type)
    with c3:
        cons_type = "green" if consistency >= 90 else "yellow" if consistency >= 70 else "red"
        kpi_card("Consistency", f"{consistency:.0f}%",
                 badge=f"{'Good' if consistency >= 90 else 'Review flagged'}",
                 badge_type=cons_type)
    with c4:
        val_types = {"Pass": "green", "Warning": "yellow", "Fail": "red"}
        kpi_card("Validation", val_status,
                 badge=f"{val_score:.0f} pts",
                 badge_type=val_types.get(val_status, "neutral"))
    with c5:
        n_high = sum(1 for f in dq.get("flagged_fields", []) if f.get("severity") == "high")
        n_med  = sum(1 for f in dq.get("flagged_fields", []) if f.get("severity") == "medium")
        kpi_card("Flagged Fields",
                 str(len(dq.get("flagged_fields", []))),
                 badge=f"{n_high} high · {n_med} medium",
                 badge_type="red" if n_high > 0 else "yellow" if n_med > 0 else "green")
    spacer(8)


def _s3_confidence_summary(
    esg_conf: float, esg_prov: bool,
    dq_conf:  float, dq_prov:  bool,
    dq:       dict,
) -> None:
    divider("Confidence Summary")
    quality_band(dq)
    spacer(8)
    dual_confidence_row(esg_conf, esg_prov, dq_conf, dq_prov)

    if dq_prov:
        spacer(4)
        info_banner(
            "Data Quality confidence is below 50%. This may affect the reliability "
            "of ESG and carbon calculations. Review flagged fields below.",
            variant="warning",
        )
    spacer(8)


def _s4_flagged_fields(flags: list) -> None:
    divider("Flagged Fields")

    if not flags:
        st.markdown(
            '<div style="text-align:center;padding:20px;color:#94A3B8;">'
            '✓  No data quality issues detected.</div>',
            unsafe_allow_html=True,
        )
        spacer(8)
        return

    # Group by severity
    high_flags = [f for f in flags if f.get("severity") == "high"]
    med_flags  = [f for f in flags if f.get("severity") == "medium"]
    low_flags  = [f for f in flags if f.get("severity") == "low"]

    severity_groups = [
        ("High Priority",   high_flags, ERROR,   ERROR_LIGHT),
        ("Medium Priority", med_flags,  WARNING, WARNING_LIGHT),
        ("Low Priority",    low_flags,  SUCCESS, SUCCESS_LIGHT),
    ]


    for group_label, group_flags, color, bg in severity_groups:
        if not group_flags:
            continue
        st.markdown(
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
            f'color:{color};margin:12px 0 6px;">{group_label} ({len(group_flags)})</div>',
            unsafe_allow_html=True,
        )
        for flag in group_flags:
            col_info, col_action = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f'<div style="background:{bg};border-left:3px solid {color};'
                    f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:4px;">'
                    f'<div style="font-size:11px;font-weight:{WEIGHT_BOLD};'
                    f'color:{color};font-family:monospace;">'
                    f'{flag.get("field_name","")}</div>'
                    f'<div style="font-size:{SIZE_SM};color:#475569;margin-top:2px;">'
                    f'{flag.get("description","")}</div>'
                    f'<div style="font-size:{SIZE_SM};color:{color};'
                    f'font-weight:{WEIGHT_BOLD};margin-top:4px;">'
                    f'→ {flag.get("suggested_action","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_action:
                fix_route = flag.get("fix_route", "esg_analytics")
                route_labels = {
                    "esg_analytics":   "◆ ESG Analytics",
                    "carbon_accounting": "◈ Carbon Accounting",
                }
                btn_label = route_labels.get(fix_route, f"→ {fix_route.replace('_',' ').title()}")
                if st.button(btn_label, key=f"fix_{flag.get('field_name','')}_{fix_route}",
                             use_container_width=True):
                    state_svc.navigate_to(fix_route)
                    st.rerun()

    spacer(8)


def _s5_validation_summary(
    val_status: str, errors: list, warnings: list,
    cols_present: list, rows_valid: int, rows_total: int,
    normalised: bool,
) -> None:
    divider("Validation Summary")

    status_colors = {"Pass": SUCCESS, "Warning": WARNING, "Fail": ERROR}
    color = status_colors.get(val_status, "#64748B")

    col_status, col_rows, col_cols = st.columns(3)

    with col_status:
        st.markdown(
            f'<div style="background:#F8FAFC;border:1.5px solid #E2E8F0;'
            f'border-radius:10px;padding:14px 16px;">'
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
            f'color:#94A3B8;margin-bottom:4px;">Upload Validation</div>'
            f'<div style="font-size:28px;font-weight:800;color:{color};">'
            f'{val_status}</div>'
            f'<div style="font-size:{SIZE_SM};color:#64748B;">'
            f'{len(errors)} errors · {len(warnings)} warnings</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_rows:
        pct = f"{rows_valid/rows_total*100:.0f}%" if rows_total > 0 else "—"
        metric_card("Valid Rows", f"{rows_valid}/{rows_total}",
                    f"rows ({pct} of upload)")

    with col_cols:
        metric_card("Columns Detected", str(len(cols_present)),
                    ", ".join(cols_present[:4]) + ("…" if len(cols_present) > 4 else ""))

    if normalised:
        spacer(4)
        info_banner(
            "Month column was normalised automatically (e.g. 'January' → 'Jan'). "
            "No data was changed.",
            variant="info",
        )

    if errors:
        spacer(4)
        with st.expander(f"Validation Errors ({len(errors)})", expanded=True):
            for err in errors:
                st.markdown(
                    f'<div style="background:{ERROR_LIGHT};border-left:3px solid {ERROR};'
                    f'padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:4px;'
                    f'font-size:{SIZE_SM};color:#7F1D1D;">{err}</div>',
                    unsafe_allow_html=True,
                )

    if warnings:
        spacer(4)
        with st.expander(f"Validation Warnings ({len(warnings)})", expanded=False):
            for w in warnings:
                st.markdown(
                    f'<div style="background:{WARNING_LIGHT};border-left:3px solid {WARNING};'
                    f'padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:4px;'
                    f'font-size:{SIZE_SM};color:#78350F;">{w}</div>',
                    unsafe_allow_html=True,
                )
    spacer(8)


def _s6_completeness(
    env_comp: float, sg_comp: float,
    sg_disc: int, sg_total: int, cols_present: list,
) -> None:
    divider("Data Completeness")

    col_env, col_sg = st.columns(2)

    with col_env:
        st.caption("**Environmental Data Coverage**")
        env_fields = {
            "Emission (monthly)": "Emission" in cols_present,
            "Energy consumption": "Energy" in cols_present,
            "Waste generated":    "Waste"  in cols_present,
            "Water consumption":  "Water"  in cols_present,
        }
        for field, present in env_fields.items():
            icon  = "✓" if present else "○"
            color = SUCCESS if present else "#DC2626"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 0;border-bottom:1px solid #F1F5F9;">'
                f'<span style="font-size:{SIZE_SM};color:#475569;">{field}</span>'
                f'<span style="font-size:12px;font-weight:{WEIGHT_BOLD};color:{color};">'
                f'{icon} {"Present" if present else "Missing"}</span></div>',
                unsafe_allow_html=True,
            )
        spacer(4)
        metric_card("Environmental Completeness", f"{env_comp:.0f}%", "out of 100")

    with col_sg:
        st.caption(f"**S/G Indicator Disclosure ({sg_disc}/{sg_total})**")
        sg_field_labels = {
            "water_recycled_pct":        "Water Recycling Rate",
            "employee_turnover_pct":     "Employee Turnover",
            "training_hours_per_employee": "Training Hours/Employee",
            "women_workforce_pct":       "Women in Workforce",
            "injury_rate":               "Injury Rate",
            "board_independence_pct":    "Board Independence",
            "women_board_pct":           "Women on Board",
            "has_code_of_conduct":       "Code of Conduct",
        }
        di = state_svc.get_disclosure_inputs()
        for key, label in sg_field_labels.items():
            val       = di.get(key)
            disclosed = val is not None and val is not False and val != 0
            icon      = "✓" if disclosed else "○"
            color     = SUCCESS if disclosed else "#DC2626"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 0;border-bottom:1px solid #F1F5F9;">'
                f'<span style="font-size:{SIZE_SM};color:#475569;">{label}</span>'
                f'<span style="font-size:11px;font-weight:{WEIGHT_BOLD};color:{color};">'
                f'{icon}</span></div>',
                unsafe_allow_html=True,
            )
        spacer(4)
        metric_card("S/G Completeness", f"{sg_comp:.0f}%", f"{sg_disc}/{sg_total} indicators")

    spacer(8)


def _s7_quality_trends(history: list, current_conf: float) -> None:
    divider("Quality Trends")

    if not history:
        info_banner(
            "No historical quality data available yet. "
            "Each time the ESG or carbon computation is triggered, "
            "a quality record is added to the audit trail.",
            variant="info",
        )
        spacer(8)
        return

    try:
        import plotly.graph_objects as go

        ts_labels  = [h["ts"] for h in history]
        conf_vals  = [float(h["confidence"]) for h in history]
        val_colors = {
            "Pass":    "#059669",
            "Warning": "#D97706",
            "Fail":    "#DC2626",
        }
        marker_colors = [
            val_colors.get(h["validation"], "#94A3B8") for h in history
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x     = ts_labels,
            y     = conf_vals,
            mode  = "lines+markers",
            name  = "DQ Confidence %",
            line  = dict(color="#0891B2", width=2.5),
            marker= dict(size=8, color=marker_colors,
                         line=dict(color="#FFFFFF", width=1.5)),
        ))
        # Provisional floor line
        fig.add_hline(y=50, line_dash="dot", line_color="#D97706",
                      annotation_text="Provisional floor (50%)",
                      annotation_position="bottom right")

        fig.update_layout(
            title        = dict(text="Data Quality Confidence History",
                                font=dict(size=13, color="#0F172A")),
            xaxis        = dict(showgrid=False, color="#94A3B8", tickangle=-30),
            yaxis        = dict(range=[0, 105], title="DQ Confidence %",
                                gridcolor="#F1F5F9", color="#94A3B8"),
            plot_bgcolor = "#FFFFFF",
            paper_bgcolor= "#FFFFFF",
            margin       = dict(l=0, r=0, t=40, b=0),
            showlegend   = False,
            height       = 240,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Mini summary table
        st.caption(f"{len(history)} computation(s) recorded in audit trail · "
                   f"Current: **{current_conf:.0f}%**")

    except ImportError:
        st.caption("plotly not installed — trend chart unavailable.")
    spacer(8)


def _s8_methodology(prov_rows: list, dq_conf: float, dq_prov: bool, summary: str) -> None:
    divider("Confidence Methodology")

    col_panel, col_status = st.columns([3, 1])

    with col_panel:
        provenance_panel(
            title            = "Data Quality Score",
            rows             = prov_rows,
            key              = "dq_prov",
            expanded         = False,
            methodology_note = "CarbonLens V8 Phase 2 · Four-part blended confidence model",
            show_download    = True,
        )

    with col_status:
        spacer(8)
        st.caption("Confidence status")
        confidence_chip(dq_conf, dq_prov, domain="dq", show_score=True)
        spacer(4)
        if summary:
            st.caption(summary)

    spacer(8)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◉ Executive Summary", use_container_width=True, key="dq_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col2:
        if st.button("◆ ESG Analytics", use_container_width=True, key="dq_qa_esg"):
            state_svc.navigate_to("esg_analytics"); st.rerun()
    with col3:
        if st.button("◎ Governance", use_container_width=True, key="dq_qa_gov"):
            state_svc.navigate_to("governance"); st.rerun()
    spacer(16)


# ─────────────────────────────────────────────────────────────────────────────
# Provenance row builder — no arithmetic
# ─────────────────────────────────────────────────────────────────────────────

def _build_dq_provenance_rows() -> list:
    """Build DQ methodology provenance rows. Reads from config constants only."""
    from config.constants import (
        DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION,
        DQ_CONFIDENCE_CAP_ON_FAIL, CONFIDENCE_PROVISIONAL_FLOOR,
        DQ_VALIDATION_SCORE_PASS, DQ_VALIDATION_SCORE_WARNING,
    )
    return [
        {
            "label":   "Completeness weight",
            "value":   f"{DQ_WEIGHT_COMPLETENESS*100:.0f}%",
            "source":  "CarbonLens V8 Phase 2",
            "formula": "env_completeness×0.60 + sg_completeness×0.40",
            "note":    "Env fields + S/G indicators",
        },
        {
            "label":   "Consistency weight",
            "value":   f"{DQ_WEIGHT_CONSISTENCY*100:.0f}%",
            "source":  "CarbonLens V8 Phase 2",
            "formula": "Outlier detection (z=2.0) + duplicate months",
            "note":    "Requires ≥ 3 rows for z-score",
        },
        {
            "label":   "Validation weight",
            "value":   f"{DQ_WEIGHT_VALIDATION*100:.0f}%",
            "source":  "CarbonLens V8 Phase 2",
            "formula": f"Pass={DQ_VALIDATION_SCORE_PASS:.0f} · Warning={DQ_VALIDATION_SCORE_WARNING:.0f} · Fail=0",
            "note":    "Upload schema validation result",
        },
        {
            "label":   "Fail confidence cap",
            "value":   f"{DQ_CONFIDENCE_CAP_ON_FAIL:.0f}%",
            "source":  "CarbonLens V8 Phase 2",
            "formula": "min(blended, cap) when validation==Fail",
            "note":    "Hard ceiling on Fail validation",
        },
        {
            "label":   "Provisional floor",
            "value":   f"{CONFIDENCE_PROVISIONAL_FLOOR:.0f}%",
            "source":  "CarbonLens V8 Phase 0 C3",
            "formula": "confidence < floor → Provisional",
            "note":    "Applies to both DQ and ESG confidence",
        },
    ]
