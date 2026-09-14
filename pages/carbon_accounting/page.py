"""
CarbonLens — Carbon Accounting page.

Second reference implementation. Follows the Executive Summary pattern:
  - All service calls at the TOP of render() before any rendering
  - Scalars extracted from ComputedState before section functions are called
  - Section functions receive plain Python values only
  - Charts receive lists/floats — never DataFrames or service objects
  - No calculations, no repository access, no st.session_state

Permitted service calls:
  state_service · audit_service · gis_service (Phase 5-C, Spatial Context tab only)
"""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs

import services.state_service as state_svc
import services.audit_service as audit_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer, scope_bar, status_badge, loading_state,
)
from components.confidence_chip import confidence_chip
from components.provenance_panel import (
    provenance_panel, emission_factor_footnote, methodology_footnote,
)
from components.charts.pie_chart       import scope_donut_chart
from components.charts.line_chart      import emission_trend_chart
from components.charts.benchmark_chart import benchmark_gauge, scope_waterfall_chart
from components.charts.bar_chart       import scope_bar_chart
from components.theme.colors           import ENV_COLOR, page_accent


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching happens here before any rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        page_header("Carbon Accounting", destination="carbon_accounting")
        empty_state("carbon", "No organisation configured",
                    "Set up an organisation to begin your GHG inventory.")
        return

    # ── 2. Fetch ComputedState ────────────────────────────────────────────────
    scope_inp = state_svc.get_scope_inputs()
    state     = state_svc.get_computed_state(
        org          = org,
        scope_inputs = scope_inp,
        force        = False,
    )

    # ── 3. Fetch trend data for charts ────────────────────────────────────────
    trend_data = state_svc.get_trend_data()

    # ── 3b. Hardened Phase 5-B forecast (lazy — called only in this section) ──
    # get_forecast_validation is called here and passed to _s5_carbon_trends.
    # It is NOT called during Executive Summary or any other page render.
    # NOTE: actual forecast rendering is controlled by the data gate inside the function.
    fcast_result = state_svc.get_forecast_validation()

    # ── 4. Extract all scalars from ComputedState ─────────────────────────────
    carbon = state.get("carbon", {})
    conf   = state.get("confidence", {})
    status = state.get("status", "No data")

    total_kg     = float(carbon.get("total_kg",  0))
    scope1_kg    = float(carbon.get("scope1_kg", 0))
    scope2_kg    = float(carbon.get("scope2_kg", 0))
    scope3_kg    = float(carbon.get("scope3_kg", 0))
    total_tco2e  = round(total_kg  / 1000, 2)
    scope1_tco2e = round(scope1_kg / 1000, 2)
    scope2_tco2e = round(scope2_kg / 1000, 2)
    scope3_tco2e = round(scope3_kg / 1000, 2)

    intensity   = float(carbon.get("intens_m2",   0))
    pln_ef      = float(carbon.get("pln_ef_used", 0.716))
    province    = str(carbon.get("province",      ""))
    scope_src   = str(carbon.get("scope_source",  "none"))
    scope3_bk   = dict(carbon.get("scope3_breakdown",  {}))
    screened    = list(carbon.get("screened_excluded",  []))
    benchmark   = float(carbon.get("benchmark",   0))
    gap         = dict(carbon.get("gap",          {}))
    gap_pct     = float(gap.get("gap_pct",         0))
    above_bench = bool(gap.get("above_benchmark", False))
    red_needed  = float(gap.get("reduction_needed_pct", 0))

    sector      = str(org.get("sector", "Manufacturing"))
    company     = str(org.get("company_name", ""))
    period      = str(org.get("reporting_period", ""))
    area_m2     = float(org.get("area_m2", 0) or 0)

    dq_conf     = float(conf.get("dq_confidence",   0))
    dq_prov     = bool(conf.get("dq_is_provisional", True))

    # Trend scalars
    months       = trend_data.get("months",           [])
    emissions_t  = trend_data.get("emissions_tco2e",  [])
    forecast     = trend_data.get("forecast",         {})
    trend_dir    = trend_data.get("trend", {}).get("direction", "insufficient_data")
    trend_desc   = trend_data.get("trend", {}).get("description", "")
    annual_tco2e = float(trend_data.get("annual_tco2e", 0))
    has_data     = bool(trend_data.get("has_data", False))
    # Phase 5-B: no longer read r2 from trend_data["forecast"]
    next_mo_t    = float(fcast_result.get("next_period_value") or 0)

    # Build provenance rows — presentation logic only, no formulas
    prov_rows = _build_provenance_rows(scope_src, pln_ef, province, scope_inp)

    # ── 5. Spatial Context (Phase 5-C, Experimental) — lazy, opt-in only ──────
    # NEVER fetched here. Only the panel-open flag and any ALREADY-persisted
    # result are read — running a NEW query only happens inside
    # _s8_spatial_context() itself, triggered by an explicit button click.
    spatial_panel_open = state_svc.is_spatial_panel_open()
    spatial_context     = state_svc.get_spatial_context() if spatial_panel_open else None

    # ── Render all 9 sections ─────────────────────────────────────────────────
    _s1_header(company, period, status, scope_src)
    _s2_inventory_kpis(total_tco2e, scope1_tco2e, scope2_tco2e,
                       scope3_tco2e, intensity, scope_src, area_m2)
    _s3_scope_breakdown(scope1_tco2e, scope2_tco2e, scope3_tco2e, scope_src)
    _s4_emission_sources(scope_inp, scope3_bk, screened, pln_ef, scope_src)
    _s5_carbon_trends(months, emissions_t, fcast_result, trend_dir,
                      trend_desc, annual_tco2e, has_data)
    _s6_benchmark(intensity, benchmark, sector, gap_pct, above_bench,
                  red_needed, scope_src)
    _s7_provenance(prov_rows, scope_src, dq_conf, dq_prov)
    _s8_spatial_context(province, spatial_panel_open, spatial_context)
    _s9_quick_actions(scope_src)
    methodology_footnote()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_header(company: str, period: str, status: str, scope_src: str) -> None:
    src_labels = {
        "carbon_accounting": "Form — Activity Data",
        "csv_scope_columns": "CSV — Scope Columns",
        "csv_estimate":      "CSV — Estimated",
        "none":              "No inventory data",
    }
    badge_types = {
        "carbon_accounting": "green", "csv_scope_columns": "blue",
        "csv_estimate": "yellow", "none": "neutral",
    }
    page_header(
        title       = "Carbon Accounting",
        subtitle    = f"{company}  ·  {period}" if period else company,
        badge       = src_labels.get(scope_src, "Unknown"),
        badge_type  = badge_types.get(scope_src, "neutral"),
        destination = "carbon_accounting",
    )


def _s2_inventory_kpis(
    total_tco2e:  float, scope1_tco2e: float,
    scope2_tco2e: float, scope3_tco2e: float,
    intensity:    float, scope_src:    str,
    area_m2:      float,
) -> None:
    divider("GHG Inventory Summary")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        kpi_card("Total Emissions", f"{total_tco2e:.1f}",
                 delta_label="tCO2e",
                 badge="Computed" if total_tco2e > 0 else "No data",
                 badge_type="green" if total_tco2e > 0 else "neutral",
                 accent=ENV_COLOR, icon_name="activity")
    with c2:
        kpi_card("Scope 1", f"{scope1_tco2e:.2f}",
                 delta_label="tCO2e · Direct combustion",
                 badge_type="blue", icon_name="carbon")
    with c3:
        kpi_card("Scope 2", f"{scope2_tco2e:.2f}",
                 delta_label="tCO2e · Grid electricity",
                 badge_type="blue", icon_name="database")
    with c4:
        kpi_card("Scope 3", f"{scope3_tco2e:.2f}",
                 delta_label="tCO2e · Value chain",
                 badge_type="blue", icon_name="layers")
    with c5:
        kpi_card("Carbon Intensity", f"{intensity:.2f}",
                 delta_label="kg CO₂e / m²",
                 badge=f"Floor area: {area_m2:,.0f} m²",
                 badge_type="neutral", icon_name="gauge")

    spacer(8)
    if total_tco2e > 0:
        scope_bar(scope1_tco2e, scope2_tco2e, scope3_tco2e)
    spacer(4)


def _s3_scope_breakdown(
    s1: float, s2: float, s3: float, scope_src: str,
) -> None:
    divider("Scope Breakdown")
    if scope_src == "none" or (s1 + s2 + s3) == 0:
        info_banner("No emission data available. Enter activity data or upload a CSV.", "info")
        return

    col_donut, col_waterfall = st.columns(2)
    with col_donut:
        scope_donut_chart(
            labels = ["Scope 1", "Scope 2", "Scope 3"],
            values = [s1, s2, s3],
            colors = ["#037C38", "#3E7C8C", "#3E7C8C"],
            title  = "Scope Distribution",
        )
    with col_waterfall:
        scope_waterfall_chart(s1, s2, s3, round(s1+s2+s3, 2))

    col_s1, col_s2, col_s3 = st.columns(3)
    total = s1 + s2 + s3 or 1
    for col, label, val, color in [
        (col_s1, "Scope 1 — Direct Combustion", s1, "#037C38"),
        (col_s2, "Scope 2 — Grid Electricity",  s2, "#3E7C8C"),
        (col_s3, "Scope 3 — Value Chain",        s3, "#3E7C8C"),
    ]:
        with col:
            pct = val / total * 100
            metric_card(label, f"{val:.2f}", f"tCO2e  ({pct:.1f}%)", color)
    spacer(8)


def _s4_emission_sources(
    scope_inp:  dict,
    scope3_bk:  dict,
    screened:   list,
    pln_ef:     float,
    scope_src:  str,
) -> None:
    divider("Emission Sources")

    if scope_src == "none":
        info_banner("Enter fuel and electricity activity data in the form below to see "
                    "emission source details.", "info")
        return

    # Scope 1 breakdown
    fuel_labels = {
        "diesel":      "Diesel",
        "petrol":      "Petrol",
        "lpg":         "LPG",
        "natural_gas": "Natural Gas",
        "cng":         "CNG",
        "coal":        "Coal",
    }
    scope_inp = scope_inp or {}
    s1_entries = []
    for key, label in fuel_labels.items():
        li_key  = key + "_liters" if key in ("diesel","petrol") else (
                  key + "_kg" if key in ("lpg","coal") else key + "_m3")
        kg_key  = key   # matches carbon.scope1_breakdown keys if available
        qty     = float(scope_inp.get(li_key, 0) or 0)
        if qty > 0:
            s1_entries.append({"metric": label, "value": f"{qty:,.0f}",
                                "unit": "L/kg/m³", "status": "neutral"})

    if scope_src == "carbon_accounting" and s1_entries:
        st.caption("**Scope 1 — Fuel Activity**")
        from components.tables.kpi_table import kpi_table
        kpi_table(s1_entries)
    else:
        st.caption("**Scope 1** — sourced from uploaded CSV or estimated from total")

    st.caption(
        f"**Scope 2** — PLN grid electricity  ·  "
        f"EF used: **{pln_ef:.4f} kg CO₂e/kWh** "
        f"(Kepmen ESDM No.18/2023)"
    )

    # Scope 3 breakdown
    if scope3_bk:
        st.caption("**Scope 3 — Category Breakdown**")
        cat_labels = {
            "cat1_purchased_goods": "Cat 1 — Purchased Goods",
            "cat2_capital_goods":   "Cat 2 — Capital Goods",
            "cat3_energy_upstream": "Cat 3 — Energy Upstream",
            "cat4_transport_upstream": "Cat 4 — Upstream Transport",
            "cat5_waste":           "Cat 5 — Waste",
            "cat6_business_travel": "Cat 6 — Business Travel",
            "cat7_employee_commute":"Cat 7 — Employee Commute",
            "cat8_upstream_leased": "Cat 8 — Upstream Leased",
            "cat9_downstream_transport": "Cat 9 — Downstream Transport",
            "cat10_processing":     "Cat 10 — Processing",
            "cat12_end_of_life":    "Cat 12 — End of Life",
            "cat13_downstream_leased": "Cat 13 — Downstream Leased",
        }
        bk_rows = [
            {"metric": cat_labels.get(k, k), "value": f"{v:.2f}",
             "unit": "kg CO₂e", "status": "neutral"}
            for k, v in scope3_bk.items() if v > 0
        ]
        if bk_rows:
            from components.tables.kpi_table import kpi_table
            kpi_table(bk_rows)

    if screened:
        with st.expander("Screened & excluded categories (3 of 15 GHG Protocol categories)", expanded=False):
            for s in screened:
                st.caption(f"• {s}")
    spacer(8)


def _s5_carbon_trends(
    months:       list,
    emissions_t:  list,
    fcast_result: dict,
    trend_dir:    str,
    trend_desc:   str,
    annual_tco2e: float,
    has_data:     bool,
) -> None:
    """Trend chart + Phase 5-B validated forecast panel. R2 never labelled as confidence."""
    divider("Carbon Trends")
    if not has_data or not months:
        info_banner("Upload a CSV with monthly emission data to see trend analysis.", "info")
        return
    trend_icons  = {"rising": "\u2191", "falling": "\u2193", "stable": "\u2192"}
    trend_colors = {"rising": "#C65A5A", "falling": "#037C38", "stable": "#3E7C8C"}
    col_chart, col_stats = st.columns([3, 1])
    with col_stats:
        direction_icon  = trend_icons.get(trend_dir, "~")
        direction_color = trend_colors.get(trend_dir, "#8A968D")
        st.markdown(
            f'<div style="background:#F5F7F2;border:1.5px solid #DDE5DE;'
            f'border-radius:10px;padding:10px 14px;">'
            f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.8px;color:#8A968D;">Trend Direction</div>'
            f'<div style="font-size:28px;color:{direction_color};font-weight:800;">'
            f'{direction_icon}</div>'
            f'<div style="font-size:11px;color:#64748B;">{trend_desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        spacer(6)
        metric_card("Annual Projection", f"{annual_tco2e:.1f}", "tCO2e")
    with col_chart:
        # Phase 6 — lazy-loaded chart: KPI numbers above (trend direction,
        # annual projection) are always visible; only the Plotly chart
        # mount itself is deferred until explicitly requested, avoiding an
        # unnecessary component render + JS payload on every page load.
        show_chart = st.checkbox("Show Emissions Trend Chart",
                                  value=False, key="ca_show_trend_chart")
        if show_chart:
            fcast_valid = fcast_result.get("valid", False)
            next_mo_t   = float(fcast_result.get("next_period_value") or 0)
            emission_trend_chart(
                months         = months,
                values         = emissions_t,
                title          = "Monthly Emissions",
                unit           = "tCO2e",
                show_forecast  = fcast_valid and next_mo_t > 0,
                forecast_value = next_mo_t if fcast_valid else 0.0,
            )
        else:
            st.caption("Chart hidden — check the box above to render it.")
    spacer(8)
    _render_forecast_panel(fcast_result)
    spacer(8)


def _render_forecast_panel(fcast: dict) -> None:
    """Phase 5-B validated forecast. Training R2 is never presented as validation accuracy."""
    gate  = fcast.get("gate",       {})
    val   = fcast.get("validation", {})
    naive = fcast.get("naive",      {})
    if not fcast.get("valid", False):
        reason = gate.get("reason", "Forecast not available.")
        n_have = gate.get("n_unique_periods", 0)
        n_need = gate.get("n_required",       6)
        st.markdown(
            f'<div style="background:#FBF1DF;border:1.5px solid #D89A3D;'
            f'border-radius:10px;padding:14px 16px;">'
            f'<div style="font-size:11px;font-weight:700;color:#92400E;margin-bottom:4px;">'
            f'Emission Forecast \u2014 Unavailable</div>'
            f'<div style="font-size:11px;color:#78350F;">{reason}</div>'
            + (f'<div style="font-size:10px;color:#92400E;margin-top:4px;">'
               f'Coverage: {n_have}/{n_need} periods</div>' if n_have < n_need else "")
            + f'</div>',
            unsafe_allow_html=True,
        )
        return
    next_val    = fcast.get("next_period_value")
    n_train     = val.get("n_train",  0)
    n_test      = val.get("n_test",   0)
    mae         = val.get("mae")
    rmse        = val.get("rmse")
    naive_mae   = naive.get("mae")
    outperforms = fcast.get("outperforms_baseline")
    n_periods   = gate.get("n_unique_periods", 0)
    missing     = gate.get("missing_periods",  [])
    rows = [
        ("Historical Coverage", f"{n_periods} period(s)", ""),
        ("Training / Holdout",  f"{n_train} / {n_test}", "Chronological — no shuffle"),
        ("Holdout MAE",  f"{mae:.1f} kg CO2e"  if mae      else "\u2014", "Unseen data error"),
        ("Holdout RMSE", f"{rmse:.1f} kg CO2e" if rmse     else "\u2014", ""),
        ("Naive MAE",    f"{naive_mae:.1f} kg CO2e" if naive_mae else "\u2014", "Lag-1 baseline"),
        ("vs Baseline",  ("\u2713 Outperforms" if outperforms else
                          "\u2715 Does not outperform" if outperforms is False else "\u2014"), ""),
        ("Forecast",     f"{next_val:.1f} kg CO2e" if next_val else "\u2014",
         "Next period — modelled estimate"),
    ]
    with st.expander("Emission Forecast (Phase 5-B Validated)", expanded=True):
        for label, value, note in rows:
            ca, cb, cc = st.columns([2, 1.5, 2])
            with ca: st.markdown(f"**{label}**")
            with cb: st.markdown(f"`{value}`")
            with cc:
                if note: st.caption(note)
        if missing:
            st.caption(f"\u26a0 Gap(s): {', '.join(missing[:4])}")
        lim = fcast.get("limitation", "Modelled estimate — not a guaranteed future outcome.")
        st.markdown(
            f'<div style="background:#FBF1DF;border-radius:6px;padding:8px 12px;'
            f'margin-top:6px;font-size:10px;color:#78350F;">\u26a0  {lim}</div>',
            unsafe_allow_html=True,
        )


def _s6_benchmark(
    intensity: float, benchmark: float, sector: str,
    gap_pct: float, above_bench: bool,
    red_needed: float, scope_src: str,
) -> None:
    divider("Benchmark Comparison")

    if scope_src == "none" or intensity == 0:
        info_banner("Carbon intensity not yet computed — no benchmark comparison available.", "info")
        return

    col_gauge, col_detail = st.columns([3, 2])

    with col_gauge:
        benchmark_gauge(intensity=intensity, benchmark=benchmark, sector=sector)

    with col_detail:
        spacer(24)
        color  = "#C65A5A" if above_bench else "#037C38"
        label  = f"{gap_pct:+.1f}%  {'above' if above_bench else 'below'} benchmark"

        st.markdown(
            f'<div style="background:#F5F7F2;border:1.5px solid #DDE5DE;'
            f'border-radius:12px;padding:18px 16px;">'
            f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.8px;color:#8A968D;margin-bottom:4px;">'
            f'Gap to {sector} benchmark</div>'
            f'<div style="font-size:32px;font-weight:800;color:{color};">'
            f'{gap_pct:+.1f}%</div>'
            f'<div style="font-size:11px;color:#64748B;margin-top:2px;">{label}</div>'
            + (
                f'<div style="font-size:11px;color:#D89A3D;margin-top:8px;">'
                f'Reduction needed to reach benchmark: {red_needed:.1f}%</div>'
                if above_bench and red_needed > 0 else ""
            )
            + f'<div style="font-size:9px;color:#8A968D;margin-top:12px;">'
              f'Benchmark: {benchmark:.0f} kg CO₂e/m²/yr · {sector}</div>'
            + f'</div>',
            unsafe_allow_html=True,
        )

    st.caption(
        "Note: Benchmarks are illustrative sector intensity estimates. "
        "Validation required before formal POJK 51 or GRI submission. "
        "See Methodology Library in Governance for provenance."
    )
    spacer(8)


def _s7_provenance(prov_rows: list, scope_src: str, dq_conf: float, dq_prov: bool) -> None:
    divider("Methodology & Provenance")

    col_panel, col_conf = st.columns([3, 1])

    with col_panel:
        provenance_panel(
            title            = "Carbon Inventory",
            rows             = prov_rows,
            key              = "ca_prov",
            expanded         = False,
            methodology_note = "GHG Protocol Corporate Standard · IPCC 2006 + AR6 GWP100",
            show_download    = True,
        )
        with st.expander("Scope 3 coverage declaration", expanded=False):
            st.markdown(
                "CarbonLens covers **12 of 15 GHG Protocol Scope 3 categories**.  \n"
                "The following 3 categories are screened and excluded with documented rationale:\n\n"
                "- **Category 11 — Use of sold products:** screened as not relevant "
                "(platform / service provider business model)\n"
                "- **Category 14 — Franchises:** screened as not relevant "
                "(non-franchise business model)\n"
                "- **Category 15 — Investments:** screened as not relevant "
                "(non-financial entity)\n\n"
                "Source: GHG Protocol Corporate Value Chain (Scope 3) Standard, Chapter 7."
            )

    with col_conf:
        spacer(8)
        st.caption("Dataset Confidence")
        confidence_chip(dq_conf, dq_prov, domain="dq", show_score=True)

    emission_factor_footnote("IPCC 2006 Vol.2 + AR6 GWP100 · Kepmen ESDM No.18/2023")
    spacer(8)


def _s8_spatial_context(
    province: str, panel_open: bool, spatial_context: dict | None,
) -> None:
    """
    Spatial / Land-Use Context — Phase 5-C, EXPERIMENTAL.
    Never queries on page load: the section always renders its header,
    badge, and description immediately (cheap), but calling
    state_svc.run_spatial_query() only ever happens inside the button
    click handler below.
    """
    divider("Spatial / Land-Use Context")

    st.markdown(
        status_badge("EXPERIMENTAL — Modelled Estimate", variant="warning"),
        unsafe_allow_html=True,
    )
    spacer(6)
    st.caption(
        "Illustrative forest-biomass and land-cover context for this "
        "organisation's province, using a province-centroid buffer as an "
        "approximate site location — not a precise facility boundary. "
        "This is exploratory spatial analysis, not a certified land-use "
        "disclosure. See the methodology note below before citing any "
        "figure from this section."
    )

    from config.constants import PROVINCE_CENTROIDS
    centroid = PROVINCE_CENTROIDS.get(province)
    if not centroid:
        info_banner(f"No approximate coordinates available for '{province}'.", "info")
        spacer(8)
        return

    if not panel_open:
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            if st.button("Load Spatial Analysis", **width_stretch_kwargs(),
                         key="ca_gis_load"):
                with st.spinner("Querying spatial data…"):
                    state_svc.run_spatial_query(
                        lat=centroid[0], lon=centroid[1],
                        radius_km=5.0, province=province,
                    )
                st.rerun()
        spacer(8)
        return

    if not spatial_context:
        # Panel marked open but no result persisted yet (first click this render)
        loading_state("Loading spatial data…")
        spacer(8)
        return

    _render_spatial_result(spatial_context)


def _render_spatial_result(ctx: dict) -> None:
    data_source = ctx.get("data_source", "unknown")
    source_label = {
        "earth_engine_live": "Live Google Earth Engine query",
        "synthetic_fallback": "Synthetic fallback data (Earth Engine unavailable/unauthenticated)",
    }.get(data_source, data_source)

    if data_source == "synthetic_fallback":
        info_banner(
            f"{source_label}. Figures below are illustrative, not derived "
            "from real satellite imagery for this session.",
            "warning",
        )
    else:
        info_banner(f"{source_label}.", "success")

    land_cover = ctx.get("land_cover", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Forest Cover", f"{ctx.get('forest_pct', 0):.0f}%",
                    f"of {ctx.get('aoi_area_ha', 0):,.0f} ha buffer")
    with col2:
        metric_card("Est. Biomass Carbon Stock", f"{ctx.get('carbon_stock_tc', 0):,.0f} tC",
                    f"≈ {ctx.get('co2e_stock_t', 0):,.0f} tCO2e")
    with col3:
        trend = ctx.get("loss_trend", {})
        metric_card("Forest-Loss Trend", str(trend.get("direction", "—")).replace("_", " ").title(),
                    f"{trend.get('change_pct')}% Δ" if trend.get("change_pct") is not None else "")

    if ctx.get("saturated"):
        info_banner(
            "NDVI is at/above its known saturation threshold for dense "
            "biomass — the biomass figure above is a conservative floor "
            "estimate, not a precise measurement.",
            "warning",
        )

    with st.expander("Land cover breakdown", expanded=False):
        for cls, pct in land_cover.items():
            st.write(f"**{cls.replace('_', ' ').title()}:** {pct:.1f}%")

    with st.expander("Methodology & limitations", expanded=False):
        st.markdown(f"**Biomass formula:** `{ctx.get('agb_formula', '')}`")
        st.markdown(f"**Carbon conversion:** `{ctx.get('carbon_formula', '')}`")
        st.caption(ctx.get("citation", ""))
        st.caption(ctx.get("masking_note", ""))
        st.caption(
            "Graduation status: this tab remains Experimental. It graduates "
            "to Advanced only once (a) the biomass citation is independently "
            "verified against a real calibration dataset, (b) forest-pixel "
            "masking is validated against ground truth, and (c) a live "
            "Earth Engine query has been demonstrably run in a deployed "
            "instance with real credentials — not just structurally coded."
        )

    if st.button("Reload Spatial Analysis", key="ca_gis_reload"):
        from config.constants import PROVINCE_CENTROIDS
        centroid = PROVINCE_CENTROIDS.get(ctx.get("province", ""))
        if centroid:
            with st.spinner("Querying spatial data…"):
                state_svc.run_spatial_query(
                    lat=centroid[0], lon=centroid[1],
                    radius_km=ctx.get("radius_km", 5.0), province=ctx.get("province", ""),
                )
            st.rerun()
    spacer(8)


def _s9_quick_actions(scope_src: str) -> None:
    divider("Quick Actions")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Executive Summary", **width_stretch_kwargs(), key="ca_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col2:
        if st.button("ESG Analytics", **width_stretch_kwargs(), key="ca_qa_esg"):
            state_svc.navigate_to("esg_analytics"); st.rerun()
    with col3:
        if st.button("Data Quality", **width_stretch_kwargs(), key="ca_qa_dq"):
            state_svc.navigate_to("data_quality"); st.rerun()
    with col4:
        if st.button("Generate Report", **width_stretch_kwargs(), key="ca_qa_report"):
            state_svc.navigate_to("reporting_compliance"); st.rerun()
    spacer(16)


# ─────────────────────────────────────────────────────────────────────────────
# Provenance row builder — presentation logic only, no formulas
# ─────────────────────────────────────────────────────────────────────────────

def _build_provenance_rows(
    scope_src: str,
    pln_ef:    float,
    province:  str,
    scope_inp: dict,
) -> list:
    """
    Build ProvenanceRow dicts for the methodology panel.
    All values are read from pre-computed ComputedState fields.
    No arithmetic is performed here.
    """
    from config.settings import EMISSION_FACTORS as EF, EMISSION_FACTORS_CO2_ONLY as EF_CO2

    rows = []

    # Scope 1 combustion factors
    scope1_factors = [
        ("diesel_kgco2_per_liter",    "Diesel",       "kg CO₂e/L",   "2.6967"),
        ("petrol_kgco2_per_liter",    "Petrol",       "kg CO₂e/L",   "2.3254"),
        ("lpg_kgco2_per_kg",          "LPG",          "kg CO₂e/kg",  "3.1172"),
        ("natural_gas_kgco2_per_m3",  "Natural Gas",  "kg CO₂e/m³",  "2.1692"),
        ("coal_kgco2_per_kg",         "Coal",         "kg CO₂e/kg",  "2.7264"),
    ]
    for ef_key, label, unit, val in scope1_factors:
        co2_only = EF_CO2.get(ef_key, 0)
        rows.append({
            "label":   f"Scope 1 — {label}",
            "value":   f"{EF.get(ef_key, val)} {unit}",
            "source":  "IPCC 2006 Vol.2 + AR6 GWP100",
            "formula": f"Fuel qty × EF",
            "note":    f"Phase 0 H3: was {co2_only} (CO₂-only)" if co2_only else "",
        })

    # Scope 2 PLN factor
    pln_source = (
        f"Kepmen ESDM No.18/2023 — {province} subsystem"
        if province else "Kepmen ESDM No.18/2023 — National average"
    )
    rows.append({
        "label":   "Scope 2 — PLN Grid",
        "value":   f"{pln_ef:.4f} kg CO₂e/kWh",
        "source":  pln_source,
        "formula": "Electricity kWh × PLN EF",
        "note":    "Regional subsystem factor applied where available",
    })

    # Scope 3 average factor note
    rows.append({
        "label":   "Scope 3 — 12 categories",
        "value":   "Multiple EFs",
        "source":  "DEFRA 2023 · USEEIO v2.0 · GLEC v3",
        "formula": "Activity × category EF",
        "note":    "Cats 11, 14, 15 screened & excluded",
    })

    # Carbon intensity formula
    rows.append({
        "label":   "Carbon Intensity",
        "value":   "kg CO₂e / m²",
        "source":  "GHG Protocol Corporate Standard",
        "formula": "Total kg CO₂e ÷ Floor area (m²)",
        "note":    "Normalised by rentable floor area",
    })

    return rows
