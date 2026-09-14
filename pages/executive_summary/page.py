"""
CarbonLens — Executive Summary page.

Reference implementation for all pages.

Architecture rules enforced here:
  - All data sourced from state_service.get_computed_state()
  - Charts receive pre-processed lists — never raw DataFrames
  - Components receive scalar/list parameters — never service objects
  - No calculations, no repository access, no session_state reads
  - Every service call is at the TOP of render() — never inside components

Service calls permitted:
  state_service · audit_service
"""
from __future__ import annotations
import html
import streamlit as st
from components.compat import width_stretch_kwargs

# ── Service imports ───────────────────────────────────────────────────────────
import services.state_service  as state_svc
import services.audit_service  as audit_svc

# ── Component imports ─────────────────────────────────────────────────────────
from components.ui import (
    page_header, kpi_card, info_banner, empty_state,
    divider, spacer,
)
from components.confidence_chip import (
    confidence_chip, quality_band, dual_confidence_row,
)
from components.provenance_panel import methodology_footnote
from components.charts.line_chart  import emission_trend_chart
from components.charts.radar_chart import esg_radar_chart, pillar_comparison_bar
from components.charts.benchmark_chart import benchmark_gauge
from components.charts.pie_chart import scope_donut_chart
from components.tables.audit_table import audit_table
from components.theme.colors import (
    grade_color, page_accent, ENV_COLOR, SOC_COLOR, GOV_COLOR,
    BRAND_ACCENT, BRAND_ACCENT_LT, BRAND_LIME, TEXT_MUTED, TEXT_PRIMARY, BORDER, BG_CARD,
)
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, FONT_BODY


# ─────────────────────────────────────────────────────────────────────────────
# Entry point (called by app.py router)
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """
    Render the Executive Summary page.
    All service calls are made here, at the top level, before any component
    rendering begins. Component functions receive plain Python values only.
    """

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        _render_no_org()
        return

    # ── 2. Fetch ComputedState (cache hit → instant; miss → full recompute) ──
    di          = state_svc.get_disclosure_inputs()
    scope_inp   = state_svc.get_scope_inputs()
    state       = state_svc.get_computed_state(
        org               = org,
        disclosure_inputs = di,
        scope_inputs      = scope_inp,
        force             = False,
    )

    # ── 3. Fetch trend data for charts ────────────────────────────────────────
    trend_data   = state_svc.get_trend_data()
    fcast_result = state_svc.get_forecast_validation()

    # ── 4. Fetch recent audit events ──────────────────────────────────────────
    recent_events = audit_svc.get_recent_events(n=8)

    # ── 5. Extract all scalars from ComputedState ─────────────────────────────
    carbon  = state.get("carbon",       {})
    esg     = state.get("esg",          {})
    dq      = state.get("data_quality", {})
    conf    = state.get("confidence",   {})
    status  = state.get("status",       "No data")
    version = state.get("version",      0)

    # Carbon scalars
    total_tco2e  = round(carbon.get("total_kg",  0) / 1000, 2)
    scope1_tco2e = round(carbon.get("scope1_kg", 0) / 1000, 2)
    scope2_tco2e = round(carbon.get("scope2_kg", 0) / 1000, 2)
    scope3_tco2e = round(carbon.get("scope3_kg", 0) / 1000, 2)
    intensity    = carbon.get("intens_m2",   0.0)
    benchmark    = carbon.get("benchmark",   0.0)
    gap          = carbon.get("gap",         {})
    gap_pct      = gap.get("gap_pct",        0.0)
    above_bench  = gap.get("above_benchmark", False)
    scope_src    = carbon.get("scope_source", "none")

    # ESG scalars
    esg_score    = esg.get("score",            0.0)
    esg_grade    = esg.get("grade",            "D")
    esg_label    = esg.get("label",            "--")
    esg_env      = esg.get("env",              0.0)
    esg_social   = esg.get("social",           0.0)
    esg_gov      = esg.get("gov",              0.0)
    esg_conf     = conf.get("esg_confidence",  0.0)
    esg_prov     = conf.get("esg_is_provisional", True)
    n_disc       = esg.get("n_disclosed",       0)
    n_total      = esg.get("n_total_indicators",8)

    # DQ scalars
    dq_conf      = conf.get("dq_confidence",   0.0)
    dq_prov      = conf.get("dq_is_provisional", True)
    dq_val       = dq.get("validation_status", "Fail")
    flags        = dq.get("flagged_fields",    [])

    # Trend scalars
    months        = trend_data.get("months",           [])
    emissions_t   = trend_data.get("emissions_tco2e",  [])
    trend_dir     = trend_data.get("trend", {}).get("direction", "insufficient_data")
    trend_desc    = trend_data.get("trend", {}).get("description", "")
    annual_tco2e  = trend_data.get("annual_tco2e",     0.0)
    has_data      = trend_data.get("has_data",         False)
    # Phase 5-B canonical forecast — never from trend_data["forecast"]
    fcast_valid   = fcast_result.get("valid", False)
    next_mo_t     = float(fcast_result.get("next_period_value") or 0)

    sector        = org.get("sector",           "Manufacturing")
    company       = org.get("company_name",     "")
    period        = org.get("reporting_period", "")

    # ── Render all 8 sections ────────────────────────────────────────────────
    _section_header(company, period, status, version)
    _section_kpis(
        total_tco2e, intensity, esg_score, esg_grade,
        dq_conf, dq_prov, annual_tco2e, scope_src,
        gap_pct, above_bench, has_data, trend_dir, trend_desc,
    )
    _section_confidence(esg_conf, esg_prov, dq_conf, dq_prov, n_disc, n_total)
    _section_carbon_performance(
        months, emissions_t, fcast_result, trend_dir,
        intensity, benchmark, sector, gap_pct, above_bench,
        scope1_tco2e, scope2_tco2e, scope3_tco2e, scope_src,
    )
    _section_esg_overview(esg_score, esg_grade, esg_label, esg_env, esg_social, esg_gov)
    _section_data_quality(dq, flags, dq_val)
    _section_top_sources(carbon)
    _section_reduction_initiatives(state)
    _section_recent_activity(recent_events)
    _section_quick_actions(has_data, scope_src)
    methodology_footnote()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_no_org() -> None:
    """Render the no-org-configured empty state."""
    page_header("Executive Summary", destination="executive_summary")
    empty_state(
        icon_name = "home",
        title   = "No organisation configured",
        message = (
            "Set up an organisation profile to begin your ESG and carbon "
            "accounting workflow."
        ),
        cta = "→ Complete organisation setup to continue",
    )


def _section_header(company: str, period: str, status: str, version: int) -> None:
    """Section 1 — Page header with org identity and status."""
    status_types = {
        "Substantive": ("Substantive", "green"),
        "Provisional": ("Provisional", "yellow"),
        "No data":     ("No data",     "neutral"),
    }
    badge, badge_type = status_types.get(status, ("No data", "neutral"))

    st.markdown(
        f'<div style="font-family:{FONT_BODY};font-size:10px;font-weight:700;'
        f'letter-spacing:0.6px;color:{TEXT_MUTED};text-transform:uppercase;">'
        f'Welcome back{", " + html.escape(company) if company else ""}</div>',
        unsafe_allow_html=True,
    )
    page_header(
        title       = "Here's your sustainability overview",
        subtitle    = "Track emissions, uncover insights, and take action for a cleaner tomorrow.",
        badge       = badge,
        badge_type  = badge_type,
        destination = "executive_summary",
    )
    if period:
        st.caption(f"Reporting period: {period}")
    if version > 1:
        st.caption(f"Computation version v{version}  ·  View history in Governance → Audit Trail")


def _section_kpis(
    total_tco2e:  float, intensity:    float,
    esg_score:    float, esg_grade:    str,
    dq_conf:      float, dq_prov:      bool,
    annual_tco2e: float, scope_src:    str,
    gap_pct:      float, above_bench:  bool,
    has_data:     bool = False, trend_dir: str = "insufficient_data",
    trend_desc:   str = "",
) -> None:
    """Section 2 — Five KPI cards. The first (Total GHG Emissions) uses the
    "hero" filled-dark treatment to match the reference's emphasis on the
    single most important number on the page; the rest stay on the
    standard light card. Deltas are only ever real, derived quantities —
    Carbon Intensity's badge is the existing vs-benchmark gap (calculations
    already produced this); Total GHG's delta is the real trend direction
    from calculations.forecasting.detect_trend() when a dataset exists, or
    an explicit "No comparable period" when it doesn't — never a fabricated
    percentage (Carbonlens has no month-over-month "previous period"
    concept for a single-snapshot inventory, so there is nothing to invent)."""
    divider("Key Performance Indicators")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        trend_delta = trend_desc if (has_data and trend_dir != "insufficient_data") else ""
        kpi_card(
            label       = "Total GHG Emissions",
            value       = f"{total_tco2e:.1f}",
            delta       = trend_delta,
            delta_label = "" if trend_delta else "No comparable period",
            badge       = "tCO2e \u00b7 Annual projected" if total_tco2e > 0 else "No data",
            badge_type  = "blue" if total_tco2e > 0 else "neutral",
            icon_name   = "activity",
            filled      = True,
        )
    with col2:
        kpi_card(
            label       = "Carbon Intensity",
            value       = f"{intensity:.2f}",
            delta_label = "kg CO₂e / m²",
            badge       = f"{gap_pct:+.1f}% vs benchmark",
            badge_type  = "red" if above_bench else "green",
            icon_name   = "gauge",
        )
    with col3:
        gfg, _gbg = grade_color(esg_grade)
        kpi_card(
            label      = "ESG Score",
            value      = f"{esg_score:.1f}",
            delta      = esg_grade,
            badge      = "Provisional" if esg_score == 0 else esg_grade,
            badge_type = "yellow" if esg_score == 0 else (
                "green" if esg_grade in ("A", "B+") else
                "blue"  if esg_grade == "B" else "red"
            ),
            icon_name  = "pie_chart",
        )
    with col4:
        kpi_card(
            label      = "Data Quality",
            value      = f"{dq_conf:.0f}%",
            badge      = "Insufficient Data" if dq_prov else "Acceptable",
            badge_type = "yellow" if dq_prov else "green",
            icon_name  = "governance",
        )
    with col5:
        src_labels = {
            "carbon_accounting": ("Form data",      "green"),
            "csv_scope_columns": ("CSV scopes",     "blue"),
            "csv_estimate":      ("CSV estimate",   "yellow"),
            "none":              ("No data",        "neutral"),
        }
        src_label, src_type = src_labels.get(scope_src, ("Unknown", "neutral"))
        kpi_card(
            label      = "Data Source",
            value      = src_label,
            badge      = "Ready" if scope_src != "none" else "Upload needed",
            badge_type = "green" if scope_src != "none" else "yellow",
            icon_name  = "database",
        )

    spacer(8)


def _section_confidence(
    esg_conf: float, esg_prov: bool,
    dq_conf:  float, dq_prov:  bool,
    n_disc:   int,   n_total:  int,
) -> None:
    """Section 3 — Dual confidence display."""
    divider("Score Confidence")
    dual_confidence_row(esg_conf, esg_prov, dq_conf, dq_prov)

    if esg_prov:
        st.caption(
            f"S/G disclosure: {n_disc} of {n_total} indicators provided. "
            "Complete disclosure in ESG Analytics → Scoring & Indicators."
        )
    spacer(4)


def _section_carbon_performance(
    months:       list,
    emissions_t:  list,
    fcast_result: dict,
    trend_dir:    str,
    intensity:    float,
    benchmark:    float,
    sector:       str,
    gap_pct:      float,
    above_bench:  bool,
    scope1_tco2e: float,
    scope2_tco2e: float,
    scope3_tco2e: float,
    scope_src:    str,
) -> None:
    """Section 4 — Carbon performance. Uses canonical Phase 5-B forecast.

    Redesign note: the scope breakdown moved from a bar (scope_bar) to the
    donut used elsewhere in the app (components/charts/pie_chart.py's
    scope_donut_chart — it already existed, just wasn't wired into this
    page) to match the reference's chart language, and a "trees planted"
    equivalency panel was added beside it. The trees figure is a real,
    cited calculation (EPA Greenhouse Gas Equivalencies Calculator: ~16.5
    urban tree seedlings grown for 10 years sequester 1 metric ton CO2 —
    https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator),
    not an invented number — and is explicitly labelled as an illustrative
    equivalency, consistent with how every other benchmark in this app is
    disclosed.
    """
    divider("Carbon Performance")

    if scope_src == "none" or not months:
        info_banner(
            "No emission data loaded. Upload a CSV in ESG Analytics to see carbon trends.",
            variant = "info",
        )
        return

    fcast_valid = fcast_result.get("valid", False)
    next_mo_t   = float(fcast_result.get("next_period_value") or 0)

    col_trend, col_scope = st.columns([3, 2])

    with col_trend:
        st.caption("Monthly Emissions Trend")
        emission_trend_chart(
            months         = months,
            values         = emissions_t,
            title          = "",
            unit           = "tCO2e",
            show_forecast  = fcast_valid and next_mo_t > 0,
            forecast_value = next_mo_t if fcast_valid else 0.0,
        )

    with col_scope:
        st.caption("Emissions Breakdown \u00b7 by scope (tCO2e)")
        total_tco2e = scope1_tco2e + scope2_tco2e + scope3_tco2e
        scope_donut_chart(
            labels = ["Scope 1", "Scope 2", "Scope 3"],
            values = [scope1_tco2e, scope2_tco2e, scope3_tco2e],
            colors = [ENV_COLOR, BRAND_ACCENT, BRAND_LIME],
            title  = "",
        )
        if total_tco2e > 0:
            trees = round(total_tco2e * 16.5)
            st.markdown(
                f'<div style="background:{BRAND_ACCENT_LT};border-radius:12px;'
                f'padding:10px 14px;margin-top:6px;font-size:{SIZE_XS};color:{TEXT_MUTED};">'
                f'Equivalent to <b style="color:{TEXT_PRIMARY};font-size:{SIZE_BASE};">'
                f'{trees:,}</b> tree seedlings grown for 10 years'
                f'<div style="font-size:9px;margin-top:2px;">Illustrative equivalency '
                f'\u2014 EPA Greenhouse Gas Equivalencies methodology</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    spacer(4)
    st.caption("vs Sector Benchmark")
    benchmark_gauge(
        intensity = intensity,
        benchmark = benchmark,
        sector    = sector,
    )
    spacer(8)


def _section_top_sources(carbon: dict) -> None:
    """
    New section — Top Emission Sources, ranked from real inventory data
    (Scope 1 total, Scope 2 total, and every non-zero Scope 3 category),
    not the reference's fictional Transport/Industries/Vehicles buckets,
    which don't exist in CarbonLens's GHG Protocol-based categorisation.
    """
    scope1_kg = carbon.get("scope1_kg", 0) or 0
    scope2_kg = carbon.get("scope2_kg", 0) or 0
    s3_breakdown = carbon.get("scope3_breakdown", {}) or {}

    sources = []
    if scope1_kg > 0:
        sources.append(("Stationary Combustion (Scope 1)", scope1_kg))
    if scope2_kg > 0:
        sources.append(("Purchased Electricity (Scope 2)", scope2_kg))
    for cat_key, kg_val in s3_breakdown.items():
        if kg_val and kg_val > 0:
            label = cat_key.split("_", 1)[-1].replace("_", " ").title() if "_" in cat_key else cat_key
            sources.append((f"{label} (Scope 3)", kg_val))

    if not sources:
        return

    sources.sort(key=lambda x: x[1], reverse=True)
    total_kg = sum(v for _, v in sources)
    top_n = sources[:5]

    divider("Top Emission Sources")
    st.caption("Share of total emissions \u00b7 ranked from actual inventory data")
    for label, kg_val in top_n:
        pct = (kg_val / total_kg * 100) if total_kg > 0 else 0
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 4px;border-bottom:1px solid {BORDER};font-size:{SIZE_SM};">'
            f'<span style="color:{TEXT_PRIMARY};">{html.escape(label)}</span>'
            f'<span style="color:{TEXT_MUTED};font-weight:{WEIGHT_BOLD};">{pct:.1f}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    spacer(8)


def _section_reduction_initiatives(state: dict) -> None:
    """
    New section — real recommendations from state_svc.get_recommendations(),
    shown with a priority badge rather than the reference's progress-bar
    percentages: CarbonLens has no tracked "% complete toward this target"
    concept for any recommendation, so a fabricated progress bar would be
    exactly the kind of invented metric the brief itself prohibits. A
    priority badge (High/Medium/Low) is real — it comes from the
    recommendation engine's own prioritisation logic.
    """
    recs = state_svc.get_recommendations(state)
    if not recs:
        return

    divider("Reduction Opportunities")
    st.caption("Prioritised by CarbonLens's recommendation engine \u00b7 not financial projections")
    badge_colors = {"high": ("#C65A5A", "#FBEAEA"), "medium": ("#D89A3D", "#FBF1DF"), "low": ("#66736B", "#F0F2EF")}
    for rec in recs[:4]:
        pr = str(rec.get("priority", "medium")).lower()
        fg, bg = badge_colors.get(pr, badge_colors["medium"])
        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;'
            f'padding:12px 14px;margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div style="font-weight:{WEIGHT_BOLD};font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">'
            f'{html.escape(str(rec.get("title","")))}</div>'
            f'<span style="background:{bg};color:{fg};font-size:9px;font-weight:700;'
            f'padding:2px 8px;border-radius:20px;text-transform:uppercase;">{html.escape(pr)}</span>'
            f'</div>'
            f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:4px;">'
            f'{html.escape(str(rec.get("description","")))}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    spacer(8)


def _section_esg_overview(
    esg_score: float, esg_grade: str, esg_label: str,
    esg_env:   float, esg_social: float, esg_gov: float,
) -> None:
    """Section 5 — ESG pillar overview."""
    divider("ESG Overview")

    if esg_score == 0:
        info_banner(
            "ESG score not yet computed. Enter Social & Governance indicators "
            "in ESG Analytics to generate a score.",
            variant = "info",
        )
        return

    col_radar, col_score, col_pillars = st.columns([2, 1, 2])

    with col_score:
        spacer(48)
        gfg, gbg = grade_color(esg_grade)
        st.markdown(
            f'<div style="background:{gbg};border-radius:16px;padding:20px;'
            f'text-align:center;">'
            f'<div style="font-size:52px;font-weight:800;color:{gfg};">'
            f'{esg_grade}</div>'
            f'<div style="font-size:12px;font-weight:700;color:{gfg};">'
            f'{esg_label}</div>'
            f'<div style="font-size:28px;font-weight:700;color:{gfg};'
            f'margin-top:4px;">{esg_score:.1f}</div>'
            f'<div style="font-size:10px;color:{gfg};opacity:0.7;">/ 100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Phase 6 — lazy-loaded charts: the ESG score/grade KPI above is always
    # visible; the radar + pillar-comparison charts are two different views
    # of the SAME three numbers (env/social/gov), so both are deferred
    # behind one toggle rather than mounting two Plotly components nobody
    # may look at on every page load.
    show_charts = st.checkbox("Show ESG Pillar Charts", value=False, key="es_show_esg_charts")

    if show_charts:
        with col_radar:
            esg_radar_chart(
                env    = esg_env,
                social = esg_social,
                gov    = esg_gov,
                title  = "ESG Pillars",
            )
        with col_pillars:
            spacer(16)
            pillar_comparison_bar(esg_env, esg_social, esg_gov)
    else:
        with col_radar:
            st.caption("Chart hidden — check the box below to render it.")

    spacer(8)


def _section_data_quality(dq: dict, flags: list, val_status: str) -> None:
    """Section 6 — Data Quality summary."""
    divider("Data Quality")
    quality_band(dq)

    if flags:
        spacer(8)
        n_high = sum(1 for f in flags if f.get("severity") == "high")
        if n_high:
            info_banner(
                f"{n_high} high-priority data quality issue(s) detected. "
                "See Data Quality page for details and fix-it actions.",
                variant = "warning",
            )

        with st.expander(f"Flagged fields ({len(flags)})", expanded=False):
            from components.tables.data_quality_table import data_quality_flags_table
            data_quality_flags_table(flags)

    spacer(8)


def _section_recent_activity(events: list) -> None:
    """Section 7 — Recent audit activity."""
    divider("Recent Activity")
    if not events:
        st.caption("No activity recorded yet. Uploads, calculations, and exports will appear here.")
        return
    audit_table(events, show_filters=False, max_rows=8)
    st.caption("Full audit history available in Governance → Audit Trail")
    spacer(8)


def _section_quick_actions(has_data: bool, scope_src: str) -> None:
    """Section 8 — Quick action navigation buttons."""
    divider("Quick Actions")

    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        label = "Upload Data" if not has_data else "Re-upload Data"
        if st.button(label, **width_stretch_kwargs(), key="qa_upload"):
            state_svc.navigate_to("esg_analytics"); st.rerun()

    with col2:
        if st.button("ESG Analytics", **width_stretch_kwargs(), key="qa_esg"):
            state_svc.navigate_to("esg_analytics"); st.rerun()

    with col3:
        if st.button("Carbon Accounting", **width_stretch_kwargs(), key="qa_carbon"):
            state_svc.navigate_to("carbon_accounting"); st.rerun()
            st.rerun()

    with col4:
        if st.button("Generate Report", **width_stretch_kwargs(), key="qa_report"):
            state_svc.navigate_to("reporting_compliance"); st.rerun()
            st.rerun()

    spacer(16)
