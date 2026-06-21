"""
CarbonLens V7 — ESG Target Tracker
Set emission reduction targets, track progress, get deadline alerts.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel
from utils.calculations import (
    dataset_overview, predict_next_emission, annual_projection,
    generate_demo_data,
)
from config.settings import PLOTLY_THEME as T, COLORS


def _progress_ring(current: float, target: float, label: str,
                   color: str = "#06B6D4", height: int = 180) -> go.Figure:
    pct = min(current / max(target, 1) * 100, 100)
    remaining = 100 - pct

    fig = go.Figure(go.Pie(
        values=[pct, remaining],
        hole=0.72,
        marker_colors=[color, "#F3F4F6"],
        showlegend=False,
        hoverinfo="skip",
        textinfo="none",
        sort=False,
    ))
    fig.add_annotation(
        x=0.5, y=0.55,
        text=f"<b>{pct:.0f}%</b>",
        font=dict(size=22, color="#111827", family="Montserrat"),
        showarrow=False,
    )
    fig.add_annotation(
        x=0.5, y=0.35,
        text=label,
        font=dict(size=10, color="#6B7280", family="Montserrat"),
        showarrow=False,
    )
    fig.update_layout(
        height=height, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _trajectory_chart(df, targets: dict, annual: float) -> go.Figure:
    months = list(df["Month"]) if "Month" in df.columns else [f"M{i}" for i in range(len(df))]
    actuals= df["Emission"].tolist() if "Emission" in df.columns else []

    fig = go.Figure()

    # Actual emissions
    if actuals:
        fig.add_trace(go.Scatter(
            x=months, y=actuals, name="Actual",
            mode="lines+markers",
            line=dict(color="#0EA5E9", width=2.5),
            marker=dict(size=5),
            hovertemplate="<b>%{x}</b><br>Actual: %{y:,.0f} tCO₂e<extra></extra>",
        ))

    # Projection line
    last_val = actuals[-1] if actuals else annual / 12
    pred     = predict_next_emission(df)
    slope    = pred.get("slope", 0) or 0
    proj_months = [f"Proj+{i}" for i in range(1, 7)]
    proj_vals   = [last_val + slope * i for i in range(1, 7)]
    fig.add_trace(go.Scatter(
        x=proj_months, y=proj_vals, name="Projection",
        mode="lines", line=dict(color="#F59E0B", width=2, dash="dot"),
        hovertemplate="<b>%{x}</b><br>Projected: %{y:,.0f} tCO₂e<extra></extra>",
    ))

    # Target line
    if actuals:
        t2026_monthly = targets.get("2026", annual * 0.75) / 12
        t2030_monthly = targets.get("2030", annual * 0.38) / 12
        avg_monthly   = sum(actuals) / len(actuals)
        fig.add_hline(y=t2026_monthly, line_dash="dash", line_color="#10B981", line_width=1.5,
                      annotation_text=f"2026 target ({t2026_monthly:,.0f}/mo)",
                      annotation_font=dict(size=10, color="#10B981"))
        fig.add_hline(y=t2030_monthly, line_dash="dash", line_color="#3B82F6", line_width=1.5,
                      annotation_text=f"2030 target ({t2030_monthly:,.0f}/mo)",
                      annotation_font=dict(size=10, color="#3B82F6"))

    fig.update_layout(
        height=280, margin=dict(l=0,r=0,t=24,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F0F2F5", title="tCO₂e"),
        xaxis=dict(showgrid=False),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        legend=dict(orientation="h", y=1.08, font=dict(size=11)),
    )
    return fig


def render():
    S.init()

    page_header(
        title="ESG Target Tracker",
        subtitle="Set emission reduction targets · Monitor progress · Get deadline alerts",
        badge="Live Tracking",
        badge_type="green",
    )

    has_data = S.get("uploaded_df") is not None
    df       = S.get("uploaded_df") if has_data else generate_demo_data()
    ov       = dataset_overview(df)
    total    = ov.get("total", 0)
    annual   = annual_projection(df)
    company  = S.get("company_name", "My Organization")

    if not has_data:
        st.info("📌 Using demo data. Upload your dataset in ESG Analytics for real tracking.")

    # ── Target configuration ─────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card" style="margin-bottom:18px;">
        <div class="cl-card-title">🎯 Set Reduction Targets</div>
        <div class="cl-card-subtitle">Define your science-based or organizational emission targets per year</div>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4 = st.columns(4, gap="medium")
    with t1:
        t2025 = st.number_input("2025 Target (tCO₂e/yr)",
                                 min_value=0.0, value=round(annual * 0.95, 0),
                                 step=10.0, key="trk_2025")
    with t2:
        t2026 = st.number_input("2026 Target (tCO₂e/yr)",
                                 min_value=0.0, value=round(annual * 0.80, 0),
                                 step=10.0, key="trk_2026")
    with t3:
        t2028 = st.number_input("2028 Target (tCO₂e/yr)",
                                 min_value=0.0, value=round(annual * 0.55, 0),
                                 step=10.0, key="trk_2028")
    with t4:
        t2030 = st.number_input("2030 Net-Zero Target (tCO₂e/yr)",
                                 min_value=0.0, value=round(annual * 0.38, 0),
                                 step=10.0, key="trk_2030")

    # Target type
    ta, tb = st.columns(2, gap="medium")
    with ta:
        target_type = st.selectbox("Target Framework",
                                    ["Organizational Target", "SBTi 1.5°C Aligned",
                                     "SBTi Well-below 2°C", "NDC Aligned", "Net Zero 2030 (Custom)"],
                                    key="trk_type")
    with tb:
        baseline_year = st.selectbox("Baseline Year", [2023, 2024, 2025], index=2, key="trk_base")
    st.markdown("</div>", unsafe_allow_html=True)

    targets = {"2025": t2025, "2026": t2026, "2028": t2028, "2030": t2030}

    # ── Progress rings ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:14px;">📊 Target Progress</div>
    """, unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4, gap="medium")
    ring_data = [
        (r1, "2025 Progress", annual, t2025, "#06B6D4"),
        (r2, "2026 Progress", annual, t2026, "#0EA5E9"),
        (r3, "2028 Progress", annual, t2028, "#F59E0B"),
        (r4, "2030 Progress", annual, t2030, "#3B82F6"),
    ]
    for col, label, current, target, color in ring_data:
        with col:
            st.markdown(f"""
            <div class="cl-card" style="text-align:center;padding:14px 10px;">
                <div style="font-size:11px;font-weight:600;color:#6B7280;margin-bottom:8px;">{label}</div>
            """, unsafe_allow_html=True)
            pct = min(current / max(target, 1) * 100, 100)
            fig_ring = _progress_ring(current, target, label, color)
            try:
                st.plotly_chart(fig_ring, use_container_width=True)
            except Exception as _chart_err:
                st.warning(f"⚠️ Chart unavailable — {_chart_err}")
            gap_val = current - target
            status  = "✅ On Track" if gap_val <= 0 else f"⚠️ Over by {gap_val:,.0f}"
            st.markdown(f"""
                <div style="font-size:10px;font-weight:700;
                    color:{'#10B981' if gap_val<=0 else '#F59E0B'};margin-top:4px;">
                    {status}</div>
                <div style="font-size:10px;color:#9CA3AF;">Current: {current:,.0f} · Target: {target:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Trajectory chart ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">📈 Emission Trajectory vs Targets</div>
        <div class="cl-card-subtitle">Actual emissions · AI projection · 2026 & 2030 target lines</div>
    """, unsafe_allow_html=True)
    try:
        st.plotly_chart(_trajectory_chart(df, targets, annual), use_container_width=True)
    except Exception as _chart_err:
        st.warning(f"⚠️ Chart unavailable — {_chart_err}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Gap analysis & alerts ─────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">⚠️ Deadline Alerts & Gap Analysis</div>
        <div class="cl-card-subtitle">Required annual reduction to meet each target</div>
    """, unsafe_allow_html=True)

    import datetime
    current_year = datetime.date.today().year
    alerts = []
    for yr, target in [(2026, t2026), (2028, t2028), (2030, t2030)]:
        years_left = max(yr - current_year, 1)
        needed_reduction = annual - target
        annual_reduction_needed = needed_reduction / years_left
        pct_needed = (needed_reduction / max(annual, 1)) * 100
        on_track   = annual <= target

        alert_type = "info" if on_track else ("warn" if pct_needed < 40 else "alert")
        status_icon = "✅" if on_track else ("⚠️" if pct_needed < 40 else "🔴")

        alerts.append({
            "text": (
                f"<strong>{yr} Target ({target:,.0f} tCO₂e):</strong> "
                + (f"Currently on track — projected at {annual:,.0f} vs target {target:,.0f} tCO₂e."
                   if on_track else
                   f"Gap of <strong>{needed_reduction:,.0f} tCO₂e</strong> ({pct_needed:.0f}% reduction needed). "
                   f"Requires <strong>{annual_reduction_needed:,.0f} tCO₂e/yr</strong> reduction over "
                   f"{years_left} year{'s' if years_left > 1 else ''}.")
            ),
            "type": alert_type, "icon": status_icon,
        })
    insight_panel(alerts)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Reduction requirements table ──────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    with st.expander("📋 Full Reduction Requirements Table", expanded=False):
        rows = []
        for yr, target in [(2025,t2025),(2026,t2026),(2028,t2028),(2030,t2030)]:
            needed   = max(annual - target, 0)
            yrs_left = max(yr - datetime.date.today().year, 1)
            rows.append({
                "Target Year":           yr,
                "Target (tCO₂e)":        f"{target:,.0f}",
                "Current Projection":    f"{annual:,.0f}",
                "Required Reduction":    f"{needed:,.0f}",
                "% Reduction Needed":    f"{needed/max(annual,1)*100:.0f}%",
                "Years Remaining":       yrs_left,
                "Annual Rate Needed":    f"{needed/yrs_left:,.0f} tCO₂e/yr",
                "Framework":             target_type,
                "Status":                "✅ On Track" if annual <= target else "⚠️ Intervention Required",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download Target Plan CSV",
            data=pd.DataFrame(rows).to_csv(index=False),
            file_name=f"CarbonLens_{company.replace(' ','_')}_Targets.csv",
            mime="text/csv",
        )
