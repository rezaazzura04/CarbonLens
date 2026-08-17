"""
CarbonLens V8 — Report section builders.
Reusable Streamlit display blocks for every major report section.
These render the same content that will feed the PDF in Sprint 6.
Pure presentation. Never calls services. Never computes values.
All data received via parameters from the report context dict.
"""
from __future__ import annotations
import streamlit as st
from components.theme.colors import (
    BORDER, TEXT_MUTED, BRAND_ACCENT, grade_color
)
from components.theme.typography import (
    SIZE_XS, SIZE_SM, SIZE_BASE, SIZE_LG, WEIGHT_BOLD, WEIGHT_BLACK, TRACKING_WIDE
)
from components.theme.spacing import RADIUS_MD, RADIUS_LG, CARD_PADDING


# ── Section header helper ─────────────────────────────────────────────────────

def _section_title(title: str, subtitle: str = "") -> None:
    sub = (
        f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="margin:20px 0 10px;">'
        f'<div style="font-size:{SIZE_LG};font-weight:{WEIGHT_BLACK};'
        f'color:#0F172A;border-left:3px solid {BRAND_ACCENT};padding-left:10px;">'
        f'{title}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


# ── Executive summary section ─────────────────────────────────────────────────

def render_executive_summary_section(ctx: dict) -> None:
    """
    Render the executive summary report block.
    ctx : report context dict from report_service.build_report_context().
    """
    _section_title(
        "Executive Summary",
        subtitle=f"{ctx.get('company','')} · {ctx.get('reporting_period','')}",
    )

    from components.ui import kpi_card, scope_bar
    from components.confidence_chip import confidence_chip

    col1, col2, col3, col4 = st.columns(4)
    grade = ctx.get("esg_grade", "--")
    gfg, gbg = grade_color(grade)

    with col1:
        kpi_card(
            "ESG Score",
            f"{ctx.get('esg_score', 0):.1f} / 100",
            badge = grade,
            badge_type = "green" if grade in ("A","B+") else "yellow" if grade == "B" else "red",
        )
    with col2:
        total = ctx.get("total_tco2e", 0)
        kpi_card("Total Emissions", f"{total:.1f}", delta_label="tCO2e")
    with col3:
        gap_pct = ctx.get("gap_pct", 0)
        kpi_card(
            "vs Sector Benchmark",
            f"{gap_pct:+.1f}%",
            badge = "Above" if gap_pct > 0 else "Below",
            badge_type = "red" if gap_pct > 0 else "green",
        )
    with col4:
        kpi_card("DQ Confidence", f"{ctx.get('dq_confidence',0):.0f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    scope_bar(ctx.get("scope1_tco2e",0), ctx.get("scope2_tco2e",0), ctx.get("scope3_tco2e",0))

    is_prov = ctx.get("is_provisional", True)
    conf    = ctx.get("esg_confidence", 0)
    confidence_chip(conf, is_prov, compact=True, domain="esg", show_score=True)
    st.caption(ctx.get("methodology_disclaimer",""))


# ── Carbon accounting section ─────────────────────────────────────────────────

def render_carbon_section(ctx: dict) -> None:
    """Render the carbon accounting report block."""
    _section_title("Carbon Accounting", subtitle="GHG Protocol — Scope 1/2/3")

    from components.ui import metric_card, kpi_card
    from components.charts.pie_chart import scope_donut_chart

    col_chart, col_metrics = st.columns([1, 1])

    with col_chart:
        scope_donut_chart(
            labels = ["Scope 1", "Scope 2", "Scope 3"],
            values = [
                ctx.get("scope1_tco2e", 0),
                ctx.get("scope2_tco2e", 0),
                ctx.get("scope3_tco2e", 0),
            ],
            colors = ["#10B981", "#0EA5E9", "#6366F1"],
            title  = "Scope Distribution",
        )

    with col_metrics:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        for label, val, color in [
            ("Scope 1 — Direct Combustion", ctx.get("scope1_tco2e",0), "#10B981"),
            ("Scope 2 — Grid Electricity",  ctx.get("scope2_tco2e",0), "#0EA5E9"),
            ("Scope 3 — Value Chain",        ctx.get("scope3_tco2e",0), "#6366F1"),
        ]:
            metric_card(label, f"{val:.2f}", "tCO2e", color)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:#F8FAFC;border:1.5px solid {BORDER};'
            f'border-radius:{RADIUS_MD};padding:10px 14px;margin-top:8px;">'
            f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};text-transform:uppercase;'
            f'letter-spacing:{TRACKING_WIDE};">Carbon Intensity</div>'
            f'<div style="font-size:22px;font-weight:{WEIGHT_BLACK};color:#0F172A;">'
            f'{ctx.get("intensity_kg_m2",0):.2f}</div>'
            f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};">kg CO₂e / m² · yr</div>'
            f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:4px;">'
            f'PLN factor: {ctx.get("pln_ef_used",0):.4f} kg CO₂e/kWh</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── ESG section ───────────────────────────────────────────────────────────────

def render_esg_section(ctx: dict) -> None:
    """Render the ESG analytics report block."""
    _section_title("ESG Analytics", subtitle="GRI 2021 aligned · E=40% S=30% G=30%")

    from components.charts.radar_chart import esg_radar_chart, pillar_comparison_bar
    from components.confidence_chip import dual_confidence_row

    col_radar, col_detail = st.columns([1, 1])

    with col_radar:
        esg_radar_chart(
            env    = ctx.get("esg_env",    0),
            social = ctx.get("esg_social", 0),
            gov    = ctx.get("esg_gov",    0),
        )

    with col_detail:
        grade  = ctx.get("esg_grade", "--")
        label  = ctx.get("esg_label", "--")
        gfg, gbg = grade_color(grade)
        st.markdown(
            f'<div style="background:{gbg};border-radius:{RADIUS_LG};'
            f'padding:20px;text-align:center;">'
            f'<div style="font-size:48px;font-weight:{WEIGHT_BLACK};'
            f'color:{gfg};">{grade}</div>'
            f'<div style="font-size:{SIZE_BASE};color:{gfg};'
            f'font-weight:{WEIGHT_BOLD};">{label}</div>'
            f'<div style="font-size:32px;color:{gfg};margin-top:4px;">'
            f'{ctx.get("esg_score",0):.1f}</div>'
            f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};">out of 100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        conf = ctx.get("confidence", {})
        dual_confidence_row(
            esg_conf = conf.get("esg_confidence", 0),
            esg_prov = conf.get("esg_is_provisional", True),
            dq_conf  = conf.get("dq_confidence", 0),
            dq_prov  = conf.get("dq_is_provisional", True),
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    pillar_comparison_bar(
        ctx.get("esg_env",    0),
        ctx.get("esg_social", 0),
        ctx.get("esg_gov",    0),
    )


# ── Benchmark section ─────────────────────────────────────────────────────────

def render_benchmark_section(ctx: dict) -> None:
    """Render the benchmark comparison block."""
    _section_title("Benchmark Comparison", subtitle=f"Sector: {ctx.get('sector','')}")

    from components.charts.benchmark_chart import benchmark_gauge

    col_gauge, col_info = st.columns([2, 1])
    with col_gauge:
        benchmark_gauge(
            intensity = ctx.get("intensity_kg_m2", 0),
            benchmark = ctx.get("benchmark", 0),
            sector    = ctx.get("sector", ""),
        )
    with col_info:
        gap = ctx.get("gap", {})
        gap_pct   = gap.get("gap_pct", 0)
        above     = gap.get("above_benchmark", False)
        color     = "#DC2626" if above else "#059669"
        label     = "above benchmark" if above else "below benchmark"
        reduction = gap.get("reduction_needed_pct", 0)

        st.markdown(
            f'<div style="padding:16px;">'
            f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};text-transform:uppercase;'
            f'letter-spacing:{TRACKING_WIDE};">Gap to benchmark</div>'
            f'<div style="font-size:28px;font-weight:{WEIGHT_BLACK};color:{color};">'
            f'{gap_pct:+.1f}%</div>'
            f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};">{label}</div>'
            + (
                f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:8px;">'
                f'Reduction needed: {reduction:.1f}%</div>'
                if above else ""
            )
            + f'</div>',
            unsafe_allow_html=True,
        )


# ── Methodology appendix section ─────────────────────────────────────────────

def render_methodology_appendix(entries: list) -> None:
    """
    Render the Methodology Appendix as a Streamlit section.
    entries : list of MethodologyEntry dicts — pre-fetched by caller.
    """
    _section_title("Appendix A — Methodology", subtitle="CarbonLens V8 scoring weights and thresholds")

    if not entries:
        st.info("Methodology library not available.")
        return

    categories = {}
    for e in entries:
        cat = e.get("category", "General")
        categories.setdefault(cat, []).append(e)

    for cat, cat_entries in categories.items():
        with st.expander(cat, expanded=False):
            for entry in cat_entries:
                col_name, col_val, col_ref = st.columns([2, 1, 2])
                with col_name:
                    st.markdown(
                        f'**{entry.get("name","")}**  \n'
                        f'<span style="font-size:{SIZE_XS};color:{TEXT_MUTED};">'
                        f'{entry.get("rationale","")}</span>',
                        unsafe_allow_html=True,
                    )
                with col_val:
                    st.markdown(
                        f'`{entry.get("value","")}`  \n'
                        f'<span style="font-size:{SIZE_XS};color:{TEXT_MUTED};">'
                        f'{entry.get("formula","")}</span>',
                        unsafe_allow_html=True,
                    )
                with col_ref:
                    st.markdown(
                        f'<span style="font-size:{SIZE_SM};color:{TEXT_MUTED};">'
                        f'{entry.get("source","")} · {entry.get("gri_reference","")}</span>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div style="height:1px;background:{BORDER};margin:4px 0;"></div>',
                    unsafe_allow_html=True,
                )


# ── Emission factor appendix section ─────────────────────────────────────────

def render_ef_appendix(entries: list) -> None:
    """
    Render the Emission Factor Appendix as a Streamlit section.
    entries : list of EmissionFactorEntry dicts — pre-fetched by caller.
    """
    _section_title("Appendix B — Emission Factors",
                   subtitle="Source: IPCC 2006 Vol.2 + AR6 GWP100 · Kepmen ESDM No.18/2023")

    if not entries:
        st.info("Emission factor library not available.")
        return

    categories = {}
    for e in entries:
        cat = e.get("category", "Other")
        categories.setdefault(cat, []).append(e)

    for cat, cat_entries in categories.items():
        with st.expander(cat, expanded=False):
            for ef in cat_entries:
                col_name, col_val, col_src = st.columns([2, 1, 2])
                with col_name:
                    st.markdown(f"**{ef.get('name','')}**")
                with col_val:
                    pre_h3 = ef.get("co2_only_value", 0)
                    current = ef.get("value", 0)
                    note = (
                        f'<span style="font-size:{SIZE_XS};color:#D97706;">'
                        f'Updated from {pre_h3} (Phase 0 H3)</span>'
                    ) if pre_h3 and pre_h3 != current else ""
                    st.markdown(
                        f'`{current}` {ef.get("unit","")}{note}',
                        unsafe_allow_html=True,
                    )
                with col_src:
                    st.markdown(
                        f'<span style="font-size:{SIZE_SM};color:{TEXT_MUTED};">'
                        f'{ef.get("source","")} · {ef.get("gwp_basis","")}</span>',
                        unsafe_allow_html=True,
                    )
