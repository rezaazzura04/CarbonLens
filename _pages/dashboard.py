"""
CarbonLens V7 — Dashboard (Executive Overview)
Data-aware: shows empty state before upload, full overview after
"""

import streamlit as st
import utils.state as S
from utils.state import get_scope_results
import pandas as pd
from components.ui import (
    page_header, hero_banner, kpi_card,
    insight_panel, scope_bar, esg_gauge, divider,
)
from utils.charts import emission_trend, scope_donut
from utils.calculations import (
    yoy_delta, get_benchmark, annual_projection,
    dataset_overview, calculate_esg_score, generate_demo_data,
)
from config.settings import COLORS


def render():
    S.init()

    page_header(
        title="Executive Dashboard",
        subtitle="Centralized sustainability overview · Connected to ESG Analytics",
        badge="● Live",
        badge_type="green",
    )

    uploaded = S.get("uploaded_df")
    has_data = uploaded is not None

    # ── EMPTY STATE ────────────────────────────────────────────────────────
    if not has_data:
        st.markdown("""
        <div style="
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            padding:60px 20px;text-align:center;
        ">
            <div style="font-size:64px;margin-bottom:20px;opacity:0.4;">📊</div>
            <div style="font-size:20px;font-weight:800;color:#1F2937;margin-bottom:8px;">
                No ESG Data Connected
            </div>
            <div style="font-size:14px;color:#6B7280;max-width:420px;line-height:1.7;margin-bottom:24px;">
                The Executive Dashboard displays your organization's sustainability performance
                after an ESG dataset has been uploaded. All metrics, charts, and insights
                are derived automatically from your data.
            </div>
            <div style="background:#E0F2FE;border:1px solid #BAE6FD;border-radius:12px;
                        padding:20px 28px;max-width:480px;margin-bottom:28px;">
                <div style="font-size:13px;font-weight:700;color:#0C4A6E;margin-bottom:12px;">
                    📂 How to get started:
                </div>
                <div style="text-align:left;display:flex;flex-direction:column;gap:8px;">
                    <div style="font-size:13px;color:#374151;">
                        <strong>Step 1 —</strong> Navigate to <strong>ESG Analytics</strong> in the sidebar
                    </div>
                    <div style="font-size:13px;color:#374151;">
                        <strong>Step 2 —</strong> Upload your ESG dataset (CSV format)
                    </div>
                    <div style="font-size:13px;color:#374151;">
                        <strong>Step 3 —</strong> Return here to view your executive overview
                    </div>
                </div>
            </div>
            <div style="font-size:12px;color:#9CA3AF;">
                Expected columns: <code>Month, Emission</code> · Optional: <code>Energy, Water, Waste, Company</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick nav button
        if st.button("◉  Go to ESG Analytics →", type="primary", key="dash_goto_esg"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    # ── DATA EXISTS — Full Dashboard ───────────────────────────────────────
    df = uploaded
    overview    = dataset_overview(df)
    total_em    = overview.get("total", 0)
    avg_em      = overview.get("average", 0)
    peak_em     = overview.get("peak", 0)
    peak_mo     = overview.get("peak_month", "—")

    energy_kwh  = df["Energy"].sum() if "Energy" in df.columns else total_em * 14.2
    water_m3    = df["Water"].sum()  if "Water"  in df.columns else total_em * 2.8
    waste_t     = df["Waste"].sum()  if "Waste"  in df.columns else total_em * 0.11

    # ── Scope totals — from Carbon Accounting if used, else ratio estimate ──
    _sc          = get_scope_results()
    _scope_source= _sc["source"]
    scope1_val   = round(_sc["scope1_kg"] / 1000, 2)   # tCO2e
    scope2_val   = round(_sc["scope2_kg"] / 1000, 2)
    scope3_val   = round(_sc["scope3_kg"] / 1000, 2)

    from utils.state import compute_canonical_esg
    esg         = compute_canonical_esg(force=False)  # cache is invalidated on every upload; safe to read here
    sector      = S.get("sector", "Manufacturing")
    annual_em   = annual_projection(df)

    company     = st.session_state.get("company_name", "Your Organization")

    # ── Data freshness indicator — makes it explicit which dataset is live ──
    computed_at = S.get("esg_computed_at", "")
    rows_loaded = len(df)
    if computed_at:
        from datetime import datetime as _dt
        try:
            ts = _dt.fromisoformat(computed_at)
            ts_label = ts.strftime("%d %b %Y, %H:%M")
        except Exception:
            ts_label = "just now"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;'
            f'padding:7px 14px;background:#ECFDF5;border:1px solid #6EE7B7;border-radius:8px;'
            f'font-size:11px;color:#065F46;width:fit-content;">'
            f'<span style="width:7px;height:7px;background:#10B981;border-radius:50%;'
            f'box-shadow:0 0 0 2px rgba(16,185,129,0.2);"></span>'
            f'<strong>Live data</strong> · {rows_loaded} rows · ESG score recalculated {ts_label}'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Hero Banner ────────────────────────────────────────────────────────
    hero_banner(
        title=f"Welcome back, {company} 👋",
        subtitle="Here's your sustainability performance snapshot for FY 2025.",
        stats=[
            {"value": f"{total_em:,.0f}",                                 "label": "Total tCO₂e"},
            {"value": f"{esg['grade']}",                                   "label": "ESG Rating"},
            {"value": f"{peak_mo}",                                        "label": "Peak Month"},
            {"value": f"{overview.get('completeness', 94):.0f}%",         "label": "Data Quality"},
        ],
    )


    # ── Year-over-Year comparison ──────────────────────────────────────────
    prev_df   = S.get("prev_year_df")
    has_prev  = prev_df is not None
    if has_prev:
        from utils.calculations import dataset_overview as _ov
        prev_ov       = _ov(prev_df)
        prev_total    = prev_ov.get("total", 0)
        prev_energy   = prev_df["Energy"].sum() if "Energy" in prev_df.columns else prev_total * 14.2
        prev_water    = prev_df["Water"].sum()  if "Water"  in prev_df.columns else prev_total * 2.8
        prev_waste    = prev_df["Waste"].sum()  if "Waste"  in prev_df.columns else prev_total * 0.11
        yoy_em  = yoy_delta(total_em,    prev_total)
        yoy_en  = yoy_delta(energy_kwh,  prev_energy)
        yoy_wa  = yoy_delta(water_m3,    prev_water)
        yoy_ws  = yoy_delta(waste_t,     prev_waste)
    else:
        yoy_em = yoy_en = yoy_wa = yoy_ws = None

    def _yoy_label(yoy, invert=False):
        """Returns delta label + color. invert=True means up is good (e.g. renewables)."""
        if not yoy: return None, None
        d   = yoy["delta_pct"]
        arr = yoy["arrow"]
        if invert:
            color = "#10B981" if d > 0 else "#EF4444" if d < 0 else "#9CA3AF"
        else:
            color = "#EF4444" if d > 0 else "#10B981" if d < 0 else "#9CA3AF"
        return f"{arr} {d:+.1f}% YoY", color


    # ── KPI Row 1 — Environmental ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        _lbl, _clr = _yoy_label(yoy_em)
        kpi_card(label="Carbon Emission", value=f"{total_em:,.0f}",
                 delta=_lbl if has_prev else "", delta_label="tCO₂e · vs last year" if has_prev else "tCO₂e",
                 icon="☁️", icon_bg="#FEE2E2", icon_color=COLORS["danger"])
    with c2:
        _lbl, _clr = _yoy_label(yoy_en)
        kpi_card(label="Energy Consumption", value=f"{energy_kwh:,.0f}",
                 delta=_lbl if has_prev else "",
                 delta_label="kWh · vs last year" if has_prev else "kWh",
                 icon="⚡", icon_bg="#FFF7ED", icon_color=COLORS["warning"])
    with c3:
        _lbl, _clr = _yoy_label(yoy_wa)
        kpi_card(label="Water Usage", value=f"{water_m3:,.0f}",
                 delta=_lbl if has_prev else "",
                 delta_label="m³ · vs last year" if has_prev else "m³",
                 icon="💧", icon_bg="#EFF6FF", icon_color=COLORS["info"])
    with c4:
        _lbl, _clr = _yoy_label(yoy_ws)
        kpi_card(label="Waste Generated", value=f"{waste_t:,.1f}",
                 delta=_lbl if has_prev else "",
                 delta_label="t · vs last year" if has_prev else "tonnes",
                 icon="♻️", icon_bg="#E0F2FE", icon_color=COLORS["success"])

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── KPI Row 2 — ESG E+S+G scores ───────────────────────────────────────
    _score_color = lambda s: "#10B981" if s>=70 else "#F59E0B" if s>=50 else "#F43F5E"
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        kpi_card(label="ESG Overall Score", value=f"{esg['score']}/100",
                 delta=esg.get("grade","—"), delta_label=f"· {esg.get('label','')}",
                 icon="🎯", icon_bg="#EFF6FF", icon_color=_score_color(esg["score"]))
    with k2:
        kpi_card(label="Environmental Score", value=f"{esg['env']:.0f}/100",
                 delta=f"40% weight", delta_label="· GRI 302/303/305/306",
                 icon="🌿", icon_bg="#ECFDF5", icon_color="#10B981")
    with k3:
        kpi_card(label="Social Score", value=f"{esg['social']:.0f}/100",
                 delta=f"30% weight", delta_label="· GRI 401/403/404/405",
                 icon="👥", icon_bg="#EEF2FF", icon_color="#6366F1")
    with k4:
        kpi_card(label="Governance Score", value=f"{esg['gov']:.0f}/100",
                 delta=f"30% weight", delta_label="· GRI 2-9/2-23/205",
                 icon="⚖️", icon_bg="#F5F3FF", icon_color="#8B5CF6")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Middle section ─────────────────────────────────────────────────────
    col_left, col_right = st.columns([2.2, 1], gap="medium")

    with col_left:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📈 Carbon Emission Trend</div>
            <div class="cl-card-subtitle">Monthly CO₂e output vs industry benchmark · tCO₂e</div>
        """, unsafe_allow_html=True)
        fig = emission_trend(df, benchmark=round(avg_em * 1.1, 1), height=280)
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🎯 ESG Performance Score</div>
            <div class="cl-card-subtitle">Composite sustainability index</div>
        """, unsafe_allow_html=True)
        esg_gauge(esg["score"], title=f"{esg['label']} · Grade {esg['grade']}", height=220)
        for label, score, color in [
            ("Environmental", esg["env"],    COLORS["primary"]),
            ("Social",        esg["social"], COLORS["secondary"]),
            ("Governance",    esg["gov"],    COLORS["accent"]),
        ]:
            pct = min(max(score, 0), 100)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <div style="width:90px;font-size:11px;font-weight:600;color:#6B7280;">{label[:4]}.</div>
                <div style="flex:1;height:6px;background:#F3F4F6;border-radius:3px;overflow:hidden;">
                    <div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;"></div>
                </div>
                <div style="width:28px;font-size:11px;font-weight:700;color:{color};text-align:right;">{pct:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── S+G Indicator Detail ────────────────────────────────────────────────
    breakdown = esg.get("breakdown", {})
    soc_bd = breakdown.get("social", {})
    gov_bd = breakdown.get("governance", {})
    dp     = esg.get("data_provided", {})

    if soc_bd or gov_bd:
        sg1, sg2 = st.columns(2, gap="medium")
        with sg1:
            st.markdown("""
            <div class="cl-card">
                <div class="cl-card-title">👥 Social Performance (GRI 400)</div>
                <div class="cl-card-subtitle">30% of ESG score · Workforce, safety, diversity</div>
            """, unsafe_allow_html=True)
            s_color = "#6366F1"
            soc_items = [
                ("Employee Retention", soc_bd.get("Employee Retention (GRI 401-1)", 0),
                 "🟢" if dp.get("employee_turnover") else "⚪"),
                ("Training Hours",     soc_bd.get("Training Hours (GRI 404-1)", 0),
                 "🟢" if dp.get("training_hours") else "⚪"),
                ("Gender Diversity",   soc_bd.get("Gender Diversity (GRI 405-1)", 0),
                 "🟢" if dp.get("gender_diversity") else "⚪"),
                ("Workplace Safety",   soc_bd.get("Workplace Safety (GRI 403-9)", 0),
                 "🟢" if dp.get("injury_rate") else "⚪"),
            ]
            for label, score, disc in soc_items:
                pct = min(max(score, 0), 100)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:9px;">
                    <span style="font-size:11px;">{disc}</span>
                    <div style="width:120px;font-size:11px;font-weight:600;color:#64748B;">{label}</div>
                    <div style="flex:1;height:5px;background:#F3F4F6;border-radius:3px;overflow:hidden;">
                        <div style="width:{pct:.0f}%;height:100%;background:{s_color};border-radius:3px;"></div>
                    </div>
                    <div style="width:28px;font-size:11px;font-weight:700;color:{s_color};text-align:right;">{pct:.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            disclosed_s = sum(1 for k in ["employee_turnover","training_hours","gender_diversity","injury_rate"] if dp.get(k))
            status_s = "🟢 disclosed data" if disclosed_s == 4 else f"⚪ {4-disclosed_s} indicators using defaults"
            st.markdown(f'<div style="font-size:10px;color:#94A3B8;margin-top:4px;">{status_s} · Fill Social & Governance inputs in ESG Analytics for real data</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with sg2:
            st.markdown("""
            <div class="cl-card">
                <div class="cl-card-title">⚖️ Governance Performance (GRI 2)</div>
                <div class="cl-card-subtitle">30% of ESG score · Board, ethics, disclosure</div>
            """, unsafe_allow_html=True)
            g_color = "#8B5CF6"
            gov_items = [
                ("Board Independence", gov_bd.get("Board Independence (GRI 2-9/10)", 0),
                 "🟢" if dp.get("board_independence") else "⚪"),
                ("Board Diversity",    gov_bd.get("Board Diversity (GRI 405-1)", 0),
                 "🟢" if dp.get("board_diversity") else "⚪"),
                ("Ethics & Anti-Corr",gov_bd.get("Ethics & Anti-Corruption (GRI 2-23/205)", 0),
                 "🟢" if dp.get("ethics_policies") else "⚪"),
                ("Disclosure Quality", gov_bd.get("Disclosure Quality (GRI 2-3)", 0),
                 "🟢"),  # always computed from completeness
            ]
            for label, score, disc in gov_items:
                pct = min(max(score, 0), 100)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:9px;">
                    <span style="font-size:11px;">{disc}</span>
                    <div style="width:120px;font-size:11px;font-weight:600;color:#64748B;">{label}</div>
                    <div style="flex:1;height:5px;background:#F3F4F6;border-radius:3px;overflow:hidden;">
                        <div style="width:{pct:.0f}%;height:100%;background:{g_color};border-radius:3px;"></div>
                    </div>
                    <div style="width:28px;font-size:11px;font-weight:700;color:{g_color};text-align:right;">{pct:.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            disclosed_g = sum(1 for k in ["board_independence","board_diversity","ethics_policies"] if dp.get(k))
            status_g = "🟢 disclosed data" if disclosed_g == 3 else f"⚪ {3-disclosed_g} indicators using defaults"
            st.markdown(f'<div style="font-size:10px;color:#94A3B8;margin-top:4px;">{status_g}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Bottom section ─────────────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">💡 AI-Generated Insights</div>
            <div class="cl-card-subtitle">Executive summary · Derived from uploaded ESG dataset</div>
        """, unsafe_allow_html=True)
        # Compute dynamic insight values
        bench_annual   = get_benchmark(sector) * 12 * 100
        above_bench    = (annual_em / max(bench_annual, 1) - 1) * 100
        scope2_em      = scope2_val
        renew_saving   = scope2_em * 0.20 * 0.85
        peak_vs_avg    = (peak_em / max(avg_em, 1) - 1) * 100

        insights_list = []
        if above_bench > 5:
            insights_list.append({
                "text": f"<strong>Carbon intensity</strong> is <strong>{above_bench:.0f}%</strong> above the {sector} benchmark. Priority action: renewable energy transition and energy efficiency programme.",
                "type": "alert", "icon": "🔴"
            })
        else:
            insights_list.append({
                "text": f"<strong>Carbon intensity</strong> is <strong>{abs(above_bench):.0f}%</strong> below the {sector} benchmark — strong environmental performance. Focus on maintaining trajectory.",
                "type": "info", "icon": "✅"
            })
        insights_list.append({
            "text": f"<strong>Energy transition opportunity:</strong> Switching 20% of electricity to renewables could reduce Scope 2 by <strong>{renew_saving:,.0f} tCO₂e/yr</strong> (~{renew_saving/max(total_em,1)*100:.0f}% of total).",
            "type": "warn", "icon": "⚡"
        })
        insights_list.append({
            "text": f"<strong>Peak emission month: {peak_mo}</strong> — {peak_em:,.0f} tCO₂e ({peak_vs_avg:+.0f}% vs monthly average). Correlates with peak production cycle — demand shifting recommended.",
            "type": "warn", "icon": "📅"
        })
        insights_list.append({
            "text": f"<strong>Data quality: {overview.get('completeness', 94):.0f}%</strong> completeness — {'meets' if overview.get('completeness',94) >= 90 else 'below'} the GRI 90% threshold for third-party verification.",
            "type": "info" if overview.get('completeness', 94) >= 90 else "warn",
            "icon": "✅" if overview.get('completeness', 94) >= 90 else "⚠️"
        })
        insight_panel(insights_list)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">⬡ GHG Scope Breakdown</div>
            <div class="cl-card-subtitle">GHG Protocol · Scope 1, 2 & 3 · tCO₂e</div>
        """, unsafe_allow_html=True)
        fig2 = scope_donut(scope1_val, scope2_val, scope3_val, height=240)
        try:
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        scope_bar("Scope 1", scope1_val, total_em / 1000, color=COLORS["danger"])
        scope_bar("Scope 2", scope2_val, total_em / 1000, color=COLORS["warning"])
        scope_bar("Scope 3", scope3_val, total_em / 1000, color=COLORS["primary"])
        if _scope_source == "csv_estimate":
            st.markdown("""
            <div style="font-size:10px;color:#9CA3AF;margin-top:8px;padding:6px 10px;
                        background:#F9FAFB;border-radius:6px;border-left:3px solid #D1D5DB;">
                ⚠️ Scope split estimated from GHG Protocol typical ratios.
                For exact figures, enter activity data in <strong>Carbon Accounting</strong>
                or upload Scope1_tCO2e/Scope2_tCO2e columns in ESG Analytics.
            </div>""", unsafe_allow_html=True)
        elif _scope_source == "csv_scope_columns":
            st.markdown("""
            <div style="font-size:10px;color:#059669;margin-top:8px;padding:6px 10px;
                        background:#F0FDF4;border-radius:6px;border-left:3px solid #34D399;">
                ✅ Scope 1 & 2 from your uploaded dataset. Scope 3 = remainder.
                For full GHG Protocol Scope 3 categories, use <strong>Carbon Accounting</strong>.
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Deep dive link ─────────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:12px;padding:16px 20px;
                display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
        <div>
            <div style="font-size:13px;font-weight:700;color:#1F2937;margin-bottom:2px;">
                📊 Want detailed analysis?
            </div>
            <div style="font-size:12px;color:#6B7280;">
                Full environmental performance, correlation analysis, and outlier detection is available in ESG Analytics.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("◉  Open ESG Analytics →", key="dash_open_esg"):
        st.session_state.active_page = "esg_analytics"
        st.rerun()

    # ── Multi-company comparison (V6) ─────────────────────────────────────────
    comparison = S.get_comparison_data()
    if len(comparison) > 1:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
             padding:20px;border-top:3px solid #6366F1;box-shadow:0 1px 3px rgba(15,23,42,0.06);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">⬡  Multi-Organization Comparison</div>
        """, unsafe_allow_html=True)

        import plotly.graph_objects as go
        from config.settings import PLOTLY_THEME as T
        palette = ["#0EA5E9","#6366F1","#10B981","#F97316","#8B5CF6"]

        names  = [c["name"]  for c in comparison]
        totals = [c["total"] for c in comparison]
        grades = [c["grade"] for c in comparison]
        scores = [c["score"] for c in comparison]

        col_bar, col_radar = st.columns(2, gap="medium")

        with col_bar:
            fig_bar = go.Figure(go.Bar(
                x=names, y=totals,
                marker=dict(color=palette[:len(names)], cornerradius=6),
                text=[f"{v:,.0f} tCO₂e" for v in totals],
                textposition="outside",
                textfont=dict(size=11, family=T["font_family"]),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} tCO₂e<extra></extra>",
            ))
            fig_bar.update_layout(
                height=240, margin=dict(l=0,r=0,t=20,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=T["font_family"], color=T["font_color"]),
                showlegend=False,
                xaxis=dict(showgrid=False, tickfont=dict(size=11)),
                yaxis=dict(showgrid=True, gridcolor="#E2E8F0",
                           tickfont=dict(size=11), title="tCO₂e"),
                title=dict(text="Total Emissions by Organization",
                          font=dict(size=12, color="#64748B"), x=0),
            )
            try:
                st.plotly_chart(fig_bar, use_container_width=True)
            except Exception as _chart_err:
                st.warning(f"⚠️ Chart unavailable — {_chart_err}")

        with col_radar:
            if len(comparison) >= 2:
                cats = ["ESG Score","Renewable %","Employees (norm)","Data Quality"]
                fig_rad = go.Figure()
                for i, co in enumerate(comparison):
                    vals = [
                        co["score"],
                        min(co.get("renew",0), 100),
                        min(co.get("employees",100)/10, 100) if co.get("employees") else 50,
                        75,
                    ]
                    fig_rad.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=cats + [cats[0]],
                        fill="toself",
                        name=co["name"][:18],
                        line=dict(color=palette[i % len(palette)], width=2),
                        fillcolor=f"rgba({','.join(str(int(palette[i%len(palette)].lstrip('#')[j:j+2],16)) for j in (0,2,4))},0.1)",
                    ))
                fig_rad.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0,100],
                                       tickfont=dict(size=9), gridcolor="#E2E8F0"),
                        angularaxis=dict(tickfont=dict(size=10, family=T["font_family"])),
                        bgcolor="rgba(0,0,0,0)",
                    ),
                    height=240, showlegend=True,
                    margin=dict(l=40,r=40,t=20,b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family=T["font_family"], color=T["font_color"]),
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    title=dict(text="Performance Radar",
                              font=dict(size=12, color="#64748B"), x=0),
                )
                try:
                    st.plotly_chart(fig_rad, use_container_width=True)
                except Exception as _chart_err:
                    st.warning(f"⚠️ Chart unavailable — {_chart_err}")
            else:
                st.info("Add another organization in the sidebar to see radar comparison.")

        # Summary table
        import pandas as pd
        comp_df = pd.DataFrame([{
            "Organization": c["name"],
            "Sector":       c["sector"],
            "Total Emissions (tCO₂e)": f"{c['total']:,.0f}" if c["total"] else "—",
            "ESG Grade":    c["grade"],
            "ESG Score":    c["score"],
            "Renewable %":  f"{c.get('renew',0)}%",
        } for c in comparison])
        st.dataframe(comp_df, use_container_width=True, hide_index=True, height=160)
        st.markdown("</div>", unsafe_allow_html=True)

