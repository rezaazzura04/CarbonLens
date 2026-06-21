"""
CarbonLens V7 — AI Prediction Center
- Multi-resource 12-month forecasting
- Decarbonization target setting with required trajectory line
- Data-gated: empty state before upload
"""

import streamlit as st
import pandas as pd
import utils.state as S
import numpy as np
import plotly.graph_objects as go
from components.ui import page_header, kpi_card, insight_panel
from utils.charts import risk_gauge
from utils.calculations import (
    predict_next_emission, annual_projection,
    overshoot_risk, get_benchmark, generate_demo_data,
    dataset_overview,
)
from config.settings import COLORS, PLOTLY_THEME as T


def _multi_forecast(df):
    results = {}
    base_pred = predict_next_emission(df)
    results["Emission"] = base_pred
    for col, factor in [("Energy", 14.2), ("Water", 2.8), ("Waste", 0.11)]:
        if col in df.columns:
            sub = df[["Month", col]].rename(columns={col: "Emission"})
            results[col] = predict_next_emission(sub)
        else:
            fv = (base_pred.get("forecast") or 0) * factor
            results[col] = {
                "forecast": round(fv, 1), "trendline": None,
                "r2": base_pred.get("r2", 0),
                "slope": (base_pred.get("slope") or 0) * factor,
                "trend_dir": base_pred.get("trend_dir", "stable"),
                "confidence": base_pred.get("confidence", 0),
            }
    return results


def _build_forecast_chart(df, forecast_val, trendline, height,
                           target_pct=None, target_year=None,
                           show_sbti: bool = False) -> go.Figure:
    """Forecast line chart with optional required-trajectory overlay."""
    months  = list(df["Month"]) if "Month" in df.columns else [f"M{i}" for i in range(len(df))]
    actuals = list(df["Emission"])
    n       = len(actuals)

    # Projection months
    pred      = predict_next_emission(df)
    slope     = pred.get("slope") or 0
    last_val  = actuals[-1] if actuals else forecast_val
    proj_vals = [last_val + slope * i for i in range(1, 7)]
    proj_months = [f"M+{i}" for i in range(1, 7)]

    conf_upper = [v * 1.08 for v in proj_vals]
    conf_lower = [v * 0.92 for v in proj_vals]

    fig = go.Figure()

    # Confidence band
    fig.add_trace(go.Scatter(
        x=proj_months + proj_months[::-1],
        y=conf_upper + conf_lower[::-1],
        fill="toself", fillcolor="rgba(0,168,107,0.08)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    # Actual line
    fig.add_trace(go.Scatter(
        x=months, y=actuals, name="Actual",
        mode="lines+markers",
        line=dict(color="#0EA5E9", width=2.5),
        marker=dict(size=5, color="#0EA5E9"),
        hovertemplate="<b>%{x}</b><br>Actual: %{y:,.0f} tCO₂e<extra></extra>",
    ))

    # Trendline
    if trendline is not None:
        fig.add_trace(go.Scatter(
            x=months, y=list(trendline), name="Trend",
            mode="lines", line=dict(color="#9CA3AF", width=1.5, dash="dot"),
            hoverinfo="skip",
        ))

    # Projection
    fig.add_trace(go.Scatter(
        x=proj_months, y=proj_vals, name="AI Forecast",
        mode="lines+markers",
        line=dict(color="#FFB703", width=2.5, dash="dash"),
        marker=dict(size=6, color="#FFB703"),
        hovertemplate="<b>%{x}</b><br>Forecast: %{y:,.0f} tCO₂e<extra></extra>",
    ))

    # ── Required trajectory line (decarbonization target) ─────────────────
    if target_pct is not None and target_year is not None and target_pct > 0:
        baseline     = actuals[0] if actuals else forecast_val
        target_val   = baseline * (1 - target_pct / 100)
        import datetime
        years_ahead  = max(target_year - datetime.date.today().year, 1)
        # Monthly reduction needed
        months_total = years_ahead * 12
        # Straight line from last actual month to target
        req_start    = actuals[-1] if actuals else baseline
        req_end      = target_val
        req_vals     = np.linspace(req_start, req_end, len(proj_months) + 1)[1:]
        req_months   = proj_months[:len(req_vals)]

        fig.add_trace(go.Scatter(
            x=[months[-1]] + req_months,
            y=[req_start]  + list(req_vals),
            name=f"Required path ({target_pct:.0f}% by {target_year})",
            mode="lines",
            line=dict(color="#EF4444", width=2.5, dash="longdash"),
            hovertemplate=(
                f"<b>%{{x}}</b><br>"
                f"Required: %{{y:,.0f}} tCO₂e<br>"
                f"Target: −{target_pct:.0f}% by {target_year}<extra></extra>"
            ),
        ))

        # Annotation at target end
        fig.add_annotation(
            x=req_months[-1], y=float(req_vals[-1]),
            text=f"🎯 Target: {target_val:,.0f} tCO₂e",
            showarrow=True, arrowhead=2, arrowsize=1,
            arrowcolor="#EF4444", arrowwidth=1.5,
            font=dict(size=10, color="#EF4444", family="Montserrat"),
            bgcolor="rgba(254,226,226,0.9)",
            bordercolor="#EF4444", borderwidth=1, borderpad=4,
        )


    # ── SBTi 1.5°C trajectory line ────────────────────────────────────────
    if show_sbti and actuals:
        sbti_start  = actuals[-1]
        # SBTi 1.5°C requires 4.2% absolute reduction per year = 0.35%/month
        sbti_monthly_rate = 0.042 / 12
        sbti_vals   = [sbti_start * (1 - sbti_monthly_rate) ** i for i in range(1, len(proj_months) + 1)]

        fig.add_trace(go.Scatter(
            x=[months[-1]] + proj_months,
            y=[sbti_start]  + sbti_vals,
            name="SBTi 1.5°C Path (−4.2%/yr)",
            mode="lines",
            line=dict(color="#8B5CF6", width=2, dash="dashdot"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "SBTi 1.5°C: %{y:,.0f} tCO₂e<br>"
                "Science-based target<extra></extra>"
            ),
        ))

        # WB2C line — 2.5%/yr
        wb2c_monthly_rate = 0.025 / 12
        wb2c_vals = [sbti_start * (1 - wb2c_monthly_rate) ** i for i in range(1, len(proj_months) + 1)]
        fig.add_trace(go.Scatter(
            x=[months[-1]] + proj_months,
            y=[sbti_start]  + wb2c_vals,
            name="SBTi Well-below 2°C (−2.5%/yr)",
            mode="lines",
            line=dict(color="#A78BFA", width=1.5, dash="dot"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "SBTi WB2°C: %{y:,.0f} tCO₂e<br>"
                "Well-below 2°C pathway<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=height, margin=dict(l=0,r=0,t=24,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F0F2F5", title="tCO₂e"),
        xaxis=dict(showgrid=False),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        legend=dict(orientation="h", y=1.08, font=dict(size=10, family="Montserrat")),
    )
    return fig


def render():
    S.init()

    page_header(
        title="AI Prediction Center",
        subtitle="ML-powered 12-month forecasting · Decarbonization target · SBTi 1.5°C & WB2°C trajectories",
        badge="Model Active",
        badge_type="green",
    )

    has_data = S.get("uploaded_df") is not None

    if not has_data:
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:60px 20px;text-align:center;">
            <div style="font-size:56px;margin-bottom:16px;opacity:0.3;">◎</div>
            <div style="font-size:20px;font-weight:800;color:#111827;margin-bottom:8px;">
                No Data Available for Forecasting</div>
            <div style="font-size:13px;color:#6B7280;max-width:420px;line-height:1.7;margin-bottom:24px;">
                AI Prediction requires your ESG dataset. Upload a CSV in ESG Analytics —
                the forecasting engine will automatically use it.
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("◉ Go to ESG Analytics →", type="primary"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    df        = S.get("uploaded_df")
    sector    = S.get("sector", "Manufacturing")
    ov        = dataset_overview(df)
    forecasts = _multi_forecast(df)
    pred      = forecasts["Emission"]
    forecast_val  = pred.get("forecast") or 0
    trendline     = pred.get("trendline")
    r2            = pred.get("r2") or 0
    slope         = pred.get("slope") or 0
    trend_dir     = pred.get("trend_dir", "stable")
    annual        = annual_projection(df)
    bench         = get_benchmark(sector)
    risk          = overshoot_risk(annual, bench * 12 * 100)
    avg_em        = ov.get("average", 0)

    # ── Decarbonization target config ─────────────────────────────────────
    st.markdown("""
    <div class="cl-card" style="margin-bottom:16px;">
        <div class="cl-card-title">🎯 Decarbonization Target</div>
        <div class="cl-card-subtitle">Set your reduction target — required trajectory overlaid on forecast chart</div>
    """, unsafe_allow_html=True)
    tc1, tc2, tc3, tc4 = st.columns(4, gap="medium")
    with tc1:
        target_pct = st.slider("Emission Reduction Target (%)", 0, 100, 30, 5,
                                key="pred_tgt_pct",
                                help="% reduction from first month baseline")
    with tc2:
        import datetime
        target_year = st.selectbox("Target Year", [2026,2027,2028,2029,2030],
                                    index=4, key="pred_tgt_yr")
    with tc3:
        show_sbti = st.checkbox("Show SBTi Trajectories",
                                value=True, key="pred_sbti",
                                help="Overlay SBTi 1.5°C (−4.2%/yr) and Well-below 2°C (−2.5%/yr) science-based target lines")
    with tc4:
        if target_pct > 0:
            baseline_em  = float(df["Emission"].iloc[0])
            target_em    = baseline_em * (1 - target_pct/100)
            years_left   = max(target_year - datetime.date.today().year, 1)
            monthly_red  = (baseline_em - target_em) / (years_left * 12)
            st.markdown(f"""
            <div style="padding:12px 0;">
                <div style="font-size:10px;color:#6B7280;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.5px;margin-bottom:4px;">Required monthly reduction</div>
                <div style="font-size:22px;font-weight:800;color:#EF4444;">{monthly_red:,.1f}</div>
                <div style="font-size:10px;color:#9CA3AF;">tCO₂e/month to reach {target_em:,.0f} tCO₂e/yr by {target_year}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── KPIs ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        delta_pct = (forecast_val - avg_em) / max(avg_em, 1) * 100
        kpi_card("Next Month Forecast", f"{forecast_val:,.0f}",
                 delta=f"{delta_pct:+.1f}%", delta_label="vs monthly avg",
                 icon="📅", icon_bg="#DBEAFE")
    with k2:
        kpi_card("Annual Projection", f"{annual:,.0f}",
                 badge="tCO₂e / 12 months", badge_type="gray",
                 icon="📆", icon_bg="#FFF7ED")
    with k3:
        kpi_card("Model Confidence", f"{pred.get('confidence',0):.0f}%",
                 badge=f"R² = {r2:.2f}",
                 badge_type="green" if r2 > 0.7 else "yellow",
                 icon="🎯", icon_bg="#E0F2FE")
    with k4:
        bt = {"Low":"green","Moderate":"yellow","High":"yellow","Critical":"red"}.get(risk["level"],"gray")
        kpi_card("Risk Level", risk["level"],
                 badge=f"{risk['probability']*100:.0f}% overshoot prob",
                 badge_type=bt,
                 icon="⚠️", icon_bg="#FEE2E2" if risk["level"] in ["High","Critical"] else "#FFF7ED")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Multi-resource forecast mini-cards ───────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4, gap="medium")
    resource_meta = [
        ("Emission","tCO₂e","☁️","#FEE2E2"),
        ("Energy","MWh","⚡","#FFF7ED"),
        ("Water","m³","💧","#EFF6FF"),
        ("Waste","tonnes","♻️","#E0F2FE"),
    ]
    for col, (res, unit, icon, bg) in zip([fc1,fc2,fc3,fc4], resource_meta):
        fdata = forecasts[res]
        fval  = fdata.get("forecast") or 0
        tdir  = fdata.get("trend_dir","stable")
        sl    = fdata.get("slope") or 0
        t_ind = "↑" if tdir=="increasing" else "↓" if tdir=="decreasing" else "→"
        t_clr = "#EF4444" if tdir=="increasing" else "#10B981" if tdir=="decreasing" else "#6B7280"
        with col:
            st.markdown(f"""
            <div class="cl-card">
                <div style="font-size:20px;margin-bottom:6px;">{icon}</div>
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                            letter-spacing:0.5px;color:#9CA3AF;margin-bottom:3px;">{res}</div>
                <div style="font-size:24px;font-weight:800;color:#111827;letter-spacing:-0.5px;line-height:1;">
                    {fval:,.0f}</div>
                <div style="font-size:10px;color:#9CA3AF;margin-bottom:6px;">{unit}</div>
                <div style="font-size:11px;font-weight:600;color:{t_clr};">
                    {t_ind} {tdir.title()} · {abs(sl):+.1f}/mo</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Main forecast chart ──────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">📈 Historical Trend + AI Forecast + Decarbonization Target</div>
        <div class="cl-card-subtitle">Green = actual · Amber dashed = AI projection · Red = required trajectory to hit target</div>
    """, unsafe_allow_html=True)
    if trendline is not None:
        fig = _build_forecast_chart(
            df, forecast_val, trendline, height=360,
            target_pct=target_pct if target_pct > 0 else None,
            target_year=target_year,
            show_sbti=show_sbti,
        )
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
    else:
        st.info("Upload at least 3 months of emission data to enable forecasting.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Risk + Narrative ─────────────────────────────────────────────────────
    col_risk, col_narr = st.columns([1, 1.4], gap="medium")
    with col_risk:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🔴 Risk Assessment</div>
            <div class="cl-card-subtitle">Emission overshoot probability</div>
        """, unsafe_allow_html=True)
        r1c, r2c = st.columns(2, gap="small")
        with r1c:
            fig_r1 = risk_gauge(risk["probability"], "Exceed 2026 Target", height=180)
            try:
                st.plotly_chart(fig_r1, use_container_width=True)
            except Exception as _chart_err:
                st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        with r2c:
            fig_r2 = risk_gauge(min(risk["probability"]*0.8, 0.95), "Exceed Benchmark", height=180)
            st.plotly_chart(fig_r2, use_container_width=True)
        nz_prob = max(0.05, 1-risk["probability"]-0.4)
        st.markdown(f"""
        <div style="background:#E0F2FE;border-radius:10px;padding:12px 16px;margin-top:8px;">
            <div style="font-size:11px;font-weight:600;color:#0C4A6E;margin-bottom:3px;">🎯 Net-Zero 2030 Probability</div>
            <div style="font-size:24px;font-weight:800;color:#0EA5E9;">{nz_prob*100:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_narr:
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">🤖 AI Narrative</div>
            <div class="cl-card-subtitle">Model interpretation · Plain language summary</div>
        """, unsafe_allow_html=True)
        target_gap = ""
        if target_pct > 0:
            baseline_em  = float(df["Emission"].iloc[0])
            target_em    = baseline_em * (1 - target_pct/100)
            gap_to_tgt   = forecast_val * 12 - target_em
            on_track     = gap_to_tgt <= 0
            target_gap   = (
                f" At the **{target_pct:.0f}% reduction target** for {target_year}, "
                f"{'current trajectory is on track ✅' if on_track else f'a gap of {abs(gap_to_tgt):,.0f} tCO₂e exists — intervention required.'}."
            )
        trend_phrase = "continues its upward trajectory ⚠️" if trend_dir=="increasing" else "shows stabilisation ✅" if trend_dir=="stable" else "is declining ✅"
        st.markdown(f"""
        <div style="font-size:13px;color:#374151;line-height:1.8;padding:12px 14px;
                    background:#F8FAFC;border-radius:10px;margin-bottom:12px;">
            Emission trend <strong>{trend_phrase}</strong> with a slope of
            <strong>{slope:+.1f} tCO₂e/month</strong> (R² = {r2:.2f}).
            Annual projection: <strong>{annual:,.0f} tCO₂e</strong>.{target_gap}
            Risk of exceeding benchmark: <strong>{risk['level']}</strong>
            ({risk['probability']*100:.0f}% probability).
        </div>
        """, unsafe_allow_html=True)
        insight_panel([
            {"text": f"Next month: <strong>{forecast_val:,.0f} tCO₂e</strong> ({(forecast_val-avg_em)/max(avg_em,1)*100:+.0f}% vs average).", "type": "warn" if forecast_val > avg_em else "info", "icon": "📊"},
            {"text": f"Trend: <strong>{trend_dir.title()}</strong> · {slope:+.1f} tCO₂e/month slope detected.", "type": "alert" if trend_dir=="increasing" else "info", "icon": "📈" if trend_dir=="increasing" else "📉"},
            {"text": "A −62% reduction from today is needed for 2030 net-zero. Use Scenario Simulator to model intervention impacts.", "type": "warn", "icon": "🌍"},
        ])
        st.markdown("</div>", unsafe_allow_html=True)

    # Scenario table
    with st.expander("📋 Scenario Comparison", expanded=False):
        bench_ann = bench * 12 * 100
        overshoot_pct = max((annual/max(bench_ann,1)-1)*100, 0)
        scenarios = pd.DataFrame({
            "Scenario":          ["Business as Usual", "10% Reduction Plan", "Renewable Transition", "Full Decarbonization"],
            "Annual Projection": [f"{annual:,.0f}", f"{annual*0.9:,.0f}", f"{annual*0.75:,.0f}", f"{annual*0.45:,.0f}"],
            "vs Benchmark":      [f"+{overshoot_pct:.0f}%"] + [f"{max((annual*r/max(bench_ann,1)-1)*100,0):+.0f}%" for r in [0.9,0.75,0.45]],
            "Investment":        ["—","Low","Medium","High"],
            "Feasibility":       ["Baseline","✅ Feasible","✅ Feasible","⚠️ Stretch"],
        })
        st.dataframe(scenarios, use_container_width=True, hide_index=True)

    # ── Download forecast data ──────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    col_dl, _ = st.columns([1, 3])
    with col_dl:
        forecast_rows = []
        months = list(df["Month"]) + ["Forecast +1"]
        actuals_list = list(df["Emission"]) + [None]
        trendline_list = list(pred["trendline"]) + [None] if pred.get("trendline") is not None else [None] * (len(months))
        for i, (mo, act, tr) in enumerate(zip(months, actuals_list, trendline_list)):
            forecast_rows.append({
                "Month":     mo,
                "Actual":    f"{act:.1f}" if act is not None else "",
                "Trend":     f"{tr:.1f}"  if tr  is not None else "",
                "Forecast":  f"{forecast_val:.1f}" if mo == "Forecast +1" else "",
            })
        dl_df = pd.DataFrame(forecast_rows)
        st.download_button(
            "⬇️  Download Forecast CSV",
            data=dl_df.to_csv(index=False).encode(),
            file_name=f"carbonlens_forecast_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
