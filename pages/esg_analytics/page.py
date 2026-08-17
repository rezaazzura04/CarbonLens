"""
CarbonLens V8 — ESG Analytics page.

Third reference implementation. Follows Carbon Accounting pattern.
Adds one new pattern: S/G indicator form submission via state_service helpers.

Architecture rules:
  - All service calls at the TOP of render() before any rendering
  - Form submission handled in _handle_form_submission() — isolated pattern
  - S/G indicator persistence via state_svc.save_disclosure_inputs() only
  - Zero calculations, zero repository access, zero st.session_state reads

Permitted service calls:
  state_service · audit_service
"""
from __future__ import annotations
import streamlit as st

import services.state_service as state_svc
import services.audit_service as audit_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer, render_grade_badge,
)
from components.confidence_chip import (
    confidence_chip, dual_confidence_row, provisional_badge,
)
from components.provenance_panel import provenance_panel, methodology_footnote
from components.charts.radar_chart import esg_radar_chart, pillar_comparison_bar
from components.charts.bar_chart   import scope_bar_chart
from components.theme.colors       import (
    grade_color, ENV_COLOR, SOC_COLOR, GOV_COLOR,
    SOC_LIGHT, ENV_LIGHT, GOV_LIGHT,
)
from components.theme.typography   import SIZE_XS, WEIGHT_BOLD, TRACKING_WIDE


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching and form handling before any rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        page_header("ESG Analytics", destination="esg_analytics")
        empty_state("◆", "No organisation configured",
                    "Set up an organisation profile to begin ESG scoring.")
        return

    # ── 2. Load current disclosure inputs from session ────────────────────────
    di_current = state_svc.get_disclosure_inputs()

    # ── 3. Handle form submission (if any) ────────────────────────────────────
    di_current = _handle_form_submission(org, di_current)

    # ── 4. Fetch ComputedState ────────────────────────────────────────────────
    scope_inp = state_svc.get_scope_inputs()
    state     = state_svc.get_computed_state(
        org               = org,
        disclosure_inputs = di_current,
        scope_inputs      = scope_inp,
        force             = False,
    )

    # ── 5. Fetch indicator breakdown and recommendations ──────────────────────
    carbon    = state.get("carbon", {})
    breakdown = state_svc.get_indicator_breakdown(org, di_current, carbon)
    recs      = state_svc.get_recommendations(state)

    # ── 6. Extract all scalars from ComputedState ─────────────────────────────
    esg    = state.get("esg",          {})
    dq     = state.get("data_quality", {})
    conf   = state.get("confidence",   {})
    status = state.get("status",       "No data")

    score    = float(esg.get("score",            0))
    grade    = str(esg.get("grade",              "D"))
    label    = str(esg.get("label",              "--"))
    env_s    = float(esg.get("env",              0))
    social_s = float(esg.get("social",           0))
    gov_s    = float(esg.get("gov",              0))
    esg_conf = float(conf.get("esg_confidence",  0))
    esg_prov = bool(conf.get("esg_is_provisional", True))
    dq_conf  = float(conf.get("dq_confidence",   0))
    dq_prov  = bool(conf.get("dq_is_provisional", True))
    n_disc   = int(esg.get("n_disclosed",         0))
    n_total  = int(esg.get("n_total_indicators",  8))
    meth_ver = str(esg.get("methodology_version", "V8-Phase4"))
    meth_dis = str(esg.get("methodology_disclaimer", ""))

    intensity   = float(carbon.get("intens_m2",  0))
    benchmark   = float(carbon.get("benchmark",  0))
    gap         = dict(carbon.get("gap",         {}))
    gap_pct     = float(gap.get("gap_pct",       0))
    above_bench = bool(gap.get("above_benchmark", False))
    sector      = str(org.get("sector",          "Manufacturing"))
    company     = str(org.get("company_name",    ""))
    period      = str(org.get("reporting_period",""))
    certs       = list(org.get("certifications") or [])

    # Sub-indicator scalars (pre-computed by state_service.get_indicator_breakdown)
    e_bk = breakdown.get("E", {})
    s_bk = breakdown.get("S", {})
    g_bk = breakdown.get("G", {})

    # Build provenance rows — presentation only, no arithmetic
    prov_rows = _build_esg_provenance_rows(meth_ver, esg_conf, n_disc, n_total)

    # ── Render all 8 sections ─────────────────────────────────────────────────
    _s1_header(company, period, status, esg_prov)
    _s2_overall_score(score, grade, label, env_s, social_s, gov_s,
                      esg_conf, esg_prov, n_disc, n_total)
    _s3_environmental(env_s, e_bk, intensity, benchmark, sector)
    _s4_social(social_s, s_bk, di_current, n_disc)
    _s5_governance(gov_s, g_bk, di_current, certs)
    _s6_confidence_methodology(esg_conf, esg_prov, dq_conf, dq_prov,
                               prov_rows, meth_dis)
    _s7_benchmark(intensity, benchmark, gap_pct, above_bench, sector, score)
    _s8_recommendations(recs)
    methodology_footnote(version=meth_ver)


# ─────────────────────────────────────────────────────────────────────────────
# Form submission handler
# ─────────────────────────────────────────────────────────────────────────────

def _handle_form_submission(org: dict, di_current: dict) -> dict:
    """
    Render the S/G indicator input form and handle submission.
    Returns the updated disclosure_inputs dict (unchanged if no submission).
    This is UI logic only — no calculations are performed here.
    """
    with st.expander("✏️  Enter Social & Governance Indicators", expanded=not bool(di_current)):

        st.caption(
            "Enter available Social and Governance metrics. "
            "Each indicator disclosed improves score confidence. "
            "Leave fields at 0 if data is not available."
        )
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                        f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
                        f'color:{SOC_COLOR};margin-bottom:6px;">SOCIAL</div>',
                        unsafe_allow_html=True)
            turnover = st.number_input(
                "Employee Turnover Rate (%)", min_value=0.0, max_value=100.0, step=0.5,
                value=float(di_current.get("employee_turnover_pct", 0) or 0),
                key="esg_turnover",
            )
            training = st.number_input(
                "Training Hours / Employee / Year", min_value=0.0, max_value=500.0,
                step=1.0, value=float(di_current.get("training_hours_per_employee", 0) or 0),
                key="esg_training",
            )
            women_wf = st.number_input(
                "Women in Workforce (%)", min_value=0.0, max_value=100.0, step=0.5,
                value=float(di_current.get("women_workforce_pct", 0) or 0),
                key="esg_women_wf",
            )
            injury = st.number_input(
                "Injury Rate (per 100 workers)", min_value=0.0, max_value=100.0, step=0.1,
                value=float(di_current.get("injury_rate", 0) or 0),
                key="esg_injury",
            )

        with col2:
            st.markdown(f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                        f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
                        f'color:{GOV_COLOR};margin-bottom:6px;">GOVERNANCE</div>',
                        unsafe_allow_html=True)
            board_ind = st.number_input(
                "Board Independence (%)", min_value=0.0, max_value=100.0, step=0.5,
                value=float(di_current.get("board_independence_pct", 0) or 0),
                key="esg_board_ind",
            )
            women_bd = st.number_input(
                "Women on Board (%)", min_value=0.0, max_value=100.0, step=0.5,
                value=float(di_current.get("women_board_pct", 0) or 0),
                key="esg_women_bd",
            )
            water = st.number_input(
                "Water Recycling Rate (%)", min_value=0.0, max_value=100.0, step=0.5,
                value=float(di_current.get("water_recycled_pct", 0) or 0),
                key="esg_water",
            )
            has_coc = st.checkbox(
                "Code of Conduct / Ethics Policy in place",
                value=bool(di_current.get("has_code_of_conduct", False)),
                key="esg_coc",
            )

        submitted = st.button("Update ESG Score", type="primary", key="esg_submit")
        if submitted:
            new_di = {
                "employee_turnover_pct":    turnover,
                "training_hours_per_employee": training,
                "women_workforce_pct":      women_wf,
                "injury_rate":              injury,
                "board_independence_pct":   board_ind,
                "women_board_pct":          women_bd,
                "water_recycled_pct":       water,
                "has_code_of_conduct":      has_coc,
            }
            state_svc.save_disclosure_inputs(new_di)
            state_svc.invalidate(org.get("org_id", ""))
            st.rerun()

    return di_current


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_header(company: str, period: str, status: str, is_provisional: bool) -> None:
    badge      = "Provisional" if is_provisional else status
    badge_type = "yellow"     if is_provisional else (
        "green" if status == "Substantive" else "neutral"
    )
    page_header(
        title       = "ESG Analytics",
        subtitle    = f"{company}  ·  {period}" if period else company,
        badge       = badge,
        badge_type  = badge_type,
        destination = "esg_analytics",
    )


def _s2_overall_score(
    score: float, grade: str, label: str,
    env_s: float, social_s: float, gov_s: float,
    esg_conf: float, esg_prov: bool,
    n_disc: int, n_total: int,
) -> None:
    divider("Overall ESG Score")
    col_score, col_radar, col_pillars = st.columns([1, 2, 2])

    with col_score:
        gfg, gbg = grade_color(grade)
        st.markdown(
            f'<div style="background:{gbg};border-radius:16px;padding:24px 16px;'
            f'text-align:center;height:260px;display:flex;flex-direction:column;'
            f'justify-content:center;">'
            f'<div style="font-size:64px;font-weight:800;color:{gfg};">{grade}</div>'
            f'<div style="font-size:13px;font-weight:700;color:{gfg};">{label}</div>'
            f'<div style="font-size:36px;font-weight:700;color:{gfg};margin-top:4px;">'
            f'{score:.1f}</div>'
            f'<div style="font-size:10px;color:{gfg};opacity:0.7;">/ 100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        spacer(8)
        confidence_chip(esg_conf, esg_prov, compact=True, domain="esg", show_score=True)
        st.caption(f"{n_disc} of {n_total} S/G indicators disclosed")

    with col_radar:
        esg_radar_chart(env_s, social_s, gov_s, title="ESG Pillars")

    with col_pillars:
        spacer(24)
        for pillar, sc, color, bg in [
            ("Environmental", env_s,    ENV_COLOR, ENV_LIGHT),
            ("Social",        social_s, SOC_COLOR, SOC_LIGHT),
            ("Governance",    gov_s,    GOV_COLOR, GOV_LIGHT),
        ]:
            weight = "40%" if pillar == "Environmental" else "30%"
            st.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:10px 14px;'
                f'margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<span style="font-size:11px;font-weight:700;color:{color};">{pillar}</span>'
                f'<span style="font-size:9px;color:{color};opacity:0.7;">weight {weight}</span>'
                f'</div>'
                f'<div style="font-size:26px;font-weight:800;color:{color};">{sc:.1f}</div>'
                f'<div style="background:#FFFFFF40;border-radius:4px;height:4px;margin-top:4px;">'
                f'<div style="background:{color};width:{sc:.0f}%;height:4px;border-radius:4px;">'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
    spacer(8)


def _s3_environmental(
    env_s: float, e_bk: dict,
    intensity: float, benchmark: float, sector: str,
) -> None:
    divider("Environmental Pillar")
    col_chart, col_detail = st.columns([3, 2])

    with col_chart:
        sub_labels = ["Carbon", "Energy", "Waste", "Water"]
        sub_values = [
            float(e_bk.get("carbon", 0)),
            float(e_bk.get("energy", 0)),
            float(e_bk.get("waste",  0)),
            float(e_bk.get("water",  0)),
        ]
        scope_bar_chart(
            labels     = sub_labels,
            values     = sub_values,
            colors     = ["#059669","#10B981","#34D399","#6EE7B7"],
            title      = "Environmental Sub-indicators (0–100)",
            unit       = "Score",
        )

    with col_detail:
        spacer(16)
        weights = [("Carbon",  "45%"), ("Energy", "25%"),
                   ("Waste",   "15%"), ("Water",  "15%")]
        for (sub, wt), val in zip(weights, sub_values):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:4px 0;border-bottom:1px solid #F1F5F9;">'
                f'<span style="font-size:11px;color:#475569;">{sub} <span '
                f'style="font-size:9px;color:#94A3B8;">({wt})</span></span>'
                f'<span style="font-size:12px;font-weight:700;color:{ENV_COLOR};">'
                f'{val:.1f}</span></div>',
                unsafe_allow_html=True,
            )
        spacer(8)
        if intensity > 0:
            st.markdown(
                f'<div style="background:{ENV_LIGHT};border-radius:8px;padding:10px 12px;">'
                f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.8px;color:{ENV_COLOR};">Carbon intensity</div>'
                f'<div style="font-size:20px;font-weight:800;color:{ENV_COLOR};">'
                f'{intensity:.2f} kg/m²</div>'
                f'<div style="font-size:9px;color:{ENV_COLOR};opacity:0.7;">'
                f'{sector} benchmark: {benchmark:.0f} kg/m²</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    spacer(8)


def _s4_social(
    social_s: float, s_bk: dict,
    di: dict, n_disc: int,
) -> None:
    divider("Social Pillar")
    col_chart, col_inputs = st.columns([3, 2])

    sub_labels = ["Retention", "Training", "Diversity", "Safety"]
    sub_values = [
        float(s_bk.get("retention", 0)),
        float(s_bk.get("training",  0)),
        float(s_bk.get("diversity", 0)),
        float(s_bk.get("safety",    0)),
    ]

    with col_chart:
        scope_bar_chart(
            labels = sub_labels,
            values = sub_values,
            colors = ["#6366F1","#818CF8","#A5B4FC","#C7D2FE"],
            title  = "Social Sub-indicators (0–100)",
            unit   = "Score",
        )

    with col_inputs:
        spacer(16)
        disclosed_inputs = {
            "Turnover":   di.get("employee_turnover_pct"),
            "Training":   di.get("training_hours_per_employee"),
            "Diversity":  di.get("women_workforce_pct"),
            "Injury Rate":di.get("injury_rate"),
        }
        for name, val in disclosed_inputs.items():
            disclosed = val is not None and val != 0
            icon  = "✓" if disclosed else "○"
            color = "#059669" if disclosed else "#DC2626"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 0;border-bottom:1px solid #F1F5F9;">'
                f'<span style="font-size:11px;color:#475569;">{name}</span>'
                f'<span style="font-size:12px;font-weight:700;color:{color};">'
                f'{icon} {val if disclosed else "Not disclosed"}</span></div>',
                unsafe_allow_html=True,
            )
        spacer(4)
        st.caption(
            f"Social score: **{social_s:.1f}/100** · "
            f"Weight: 30% of composite · GRI 401, 403, 404, 405"
        )
    spacer(8)


def _s5_governance(
    gov_s: float, g_bk: dict,
    di: dict, certs: list,
) -> None:
    divider("Governance Pillar")
    col_chart, col_inputs = st.columns([3, 2])

    sub_labels = ["Board Ind.", "Disclosure", "Ethics", "Board Div.", "Certs"]
    sub_values = [
        float(g_bk.get("board_ind",  0)),
        float(g_bk.get("disclosure", 0)),
        float(g_bk.get("ethics",     0)),
        float(g_bk.get("board_div",  0)),
        float(g_bk.get("certs",      0)),
    ]

    with col_chart:
        scope_bar_chart(
            labels = sub_labels,
            values = sub_values,
            colors = ["#F97316","#FB923C","#FDBA74","#FED7AA","#FEF3C7"],
            title  = "Governance Sub-indicators (0–100)",
            unit   = "Score",
        )

    with col_inputs:
        spacer(16)
        g_items = {
            "Board Independence": di.get("board_independence_pct"),
            "Women on Board":     di.get("women_board_pct"),
            "Code of Conduct":    di.get("has_code_of_conduct"),
            "Certifications":     len(certs) if certs else None,
        }
        for name, val in g_items.items():
            disclosed = val is not None and val is not False and val != 0
            icon  = "✓" if disclosed else "○"
            color = "#059669" if disclosed else "#DC2626"
            disp  = (f"{val}" if not isinstance(val, bool) else ("Yes" if val else "No")) \
                    if disclosed else "Not disclosed"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 0;border-bottom:1px solid #F1F5F9;">'
                f'<span style="font-size:11px;color:#475569;">{name}</span>'
                f'<span style="font-size:12px;font-weight:700;color:{color};">'
                f'{icon} {disp}</span></div>',
                unsafe_allow_html=True,
            )
        spacer(4)
        st.caption(
            f"Governance score: **{gov_s:.1f}/100** · "
            f"Weight: 30% of composite · GRI 2-9, 2-10, 205"
        )
    spacer(8)


def _s6_confidence_methodology(
    esg_conf: float, esg_prov: bool,
    dq_conf:  float, dq_prov:  bool,
    prov_rows: list, meth_dis: str,
) -> None:
    divider("Confidence & Methodology")
    dual_confidence_row(esg_conf, esg_prov, dq_conf, dq_prov)
    spacer(8)
    if meth_dis:
        st.caption(meth_dis)
    provenance_panel(
        title            = "ESG Score",
        rows             = prov_rows,
        key              = "esg_prov",
        expanded         = False,
        methodology_note = "GRI 2021 aligned · E=40%, S=30%, G=30% · CarbonLens V8",
        show_download    = True,
    )
    spacer(8)


def _s7_benchmark(
    intensity:  float, benchmark: float,
    gap_pct:    float, above_bench: bool,
    sector:     str, esg_score: float,
) -> None:
    divider("Benchmark Interpretation")
    col_carbon, col_esg = st.columns(2)

    with col_carbon:
        color = "#DC2626" if above_bench else "#059669"
        direction = "above" if above_bench else "below"
        st.markdown(
            f'<div style="background:#F8FAFC;border:1.5px solid #E2E8F0;'
            f'border-radius:12px;padding:18px 16px;">'
            f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.8px;color:#94A3B8;">Carbon vs {sector} Benchmark</div>'
            f'<div style="font-size:32px;font-weight:800;color:{color};">'
            f'{gap_pct:+.1f}%</div>'
            f'<div style="font-size:11px;color:#64748B;">'
            f'{abs(gap_pct):.1f}% {direction} {benchmark:.0f} kg/m² sector benchmark</div>'
            f'<div style="font-size:9px;color:#94A3B8;margin-top:8px;">'
            f'Your intensity: {intensity:.2f} kg/m²/yr</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_esg:
        esg_color = "#059669" if esg_score >= 75 else "#D97706" if esg_score >= 50 else "#DC2626"
        esg_label = (
            "Strong — above industry average" if esg_score >= 75 else
            "Satisfactory — at industry level" if esg_score >= 50 else
            "Developing — below industry average"
        )
        st.markdown(
            f'<div style="background:#F8FAFC;border:1.5px solid #E2E8F0;'
            f'border-radius:12px;padding:18px 16px;">'
            f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.8px;color:#94A3B8;">ESG Score Interpretation</div>'
            f'<div style="font-size:32px;font-weight:800;color:{esg_color};">'
            f'{esg_score:.1f}</div>'
            f'<div style="font-size:11px;color:#64748B;">{esg_label}</div>'
            f'<div style="font-size:9px;color:#94A3B8;margin-top:8px;">'
            f'GRI 2021 aligned · E=40%, S=30%, G=30%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    spacer(8)


def _s8_recommendations(recs: list) -> None:
    divider("Recommendations")
    if not recs:
        st.markdown(
            '<div style="text-align:center;padding:20px;color:#94A3B8;">'
            '✓  No high-priority recommendations — good work!</div>',
            unsafe_allow_html=True,
        )
        return

    pillar_colors = {
        "E": ENV_COLOR, "S": SOC_COLOR,
        "G": GOV_COLOR, "DQ": "#0891B2", "All": "#6366F1",
    }
    pillar_labels = {
        "E": "Environmental", "S": "Social",
        "G": "Governance", "DQ": "Data Quality", "All": "All Pillars",
    }

    for i, rec in enumerate(recs):
        pillar = rec.get("pillar", "All")
        color  = pillar_colors.get(pillar, "#64748B")
        p_lbl  = pillar_labels.get(pillar, pillar)
        priority = rec.get("priority", i + 1)

        st.markdown(
            f'<div style="border-left:4px solid {color};border-radius:0 8px 8px 0;'
            f'background:#F8FAFC;padding:12px 16px;margin-bottom:8px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
            f'<span style="font-size:9px;font-weight:700;background:{color}20;'
            f'color:{color};padding:2px 8px;border-radius:10px;">'
            f'Priority {priority} · {p_lbl}</span></div>'
            f'<div style="font-size:13px;font-weight:700;color:#0F172A;">'
            f'{rec.get("title","")}</div>'
            f'<div style="font-size:11px;color:#64748B;margin-top:3px;">'
            f'{rec.get("description","")}</div>'
            f'<div style="font-size:11px;color:{color};font-weight:600;margin-top:5px;">'
            f'→ {rec.get("action","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◉ Executive Summary", use_container_width=True, key="esg_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col2:
        if st.button("◈ Carbon Accounting", use_container_width=True, key="esg_qa_carbon"):
            state_svc.navigate_to("carbon_accounting"); st.rerun()
    with col3:
        if st.button("◎ Generate Report", use_container_width=True, key="esg_qa_report"):
            state_svc.navigate_to("reporting_compliance"); st.rerun()
    spacer(16)


# ─────────────────────────────────────────────────────────────────────────────
# Provenance row builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_esg_provenance_rows(
    meth_ver: str, esg_conf: float, n_disc: int, n_total: int,
) -> list:
    """Build ProvenanceRow dicts for the ESG methodology panel. No arithmetic."""
    return [
        {
            "label":   "Environmental weight",
            "value":   "40%",
            "source":  "CarbonLens V8 Methodology Library",
            "formula": "E × 0.40",
            "note":    f"Phase 0 C2 · {meth_ver}",
        },
        {
            "label":   "Social weight",
            "value":   "30%",
            "source":  "CarbonLens V8 Methodology Library",
            "formula": "S × 0.30",
            "note":    "Phase 0 C2 · GRI 401, 403, 404, 405",
        },
        {
            "label":   "Governance weight",
            "value":   "30%",
            "source":  "CarbonLens V8 Methodology Library",
            "formula": "G × 0.30",
            "note":    "Phase 0 C2 · GRI 2-9, 2-10, 205",
        },
        {
            "label":   "Provisional floor",
            "value":   "50% disclosure",
            "source":  "CarbonLens V8 Methodology Library",
            "formula": "n_disclosed / n_total × 100",
            "note":    f"Phase 0 C3 · Current: {esg_conf:.0f}% ({n_disc}/{n_total})",
        },
        {
            "label":   "Carbon sub-indicator weight",
            "value":   "45% of E pillar",
            "source":  "CarbonLens V8 Methodology Library",
            "formula": "carbon_score × 0.45",
            "note":    "Intensity vs sector benchmark",
        },
    ]
