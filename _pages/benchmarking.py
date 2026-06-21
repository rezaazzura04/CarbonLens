"""
CarbonLens V7 — Industry Benchmarking Hub
Full-page benchmark analysis: rank vs peers, gap heatmap, improvement path.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel
from utils.calculations import (
    dataset_overview, calculate_esg_score, get_benchmark,
    benchmark_gap, generate_demo_data,
)
from config.settings import INDUSTRY_BENCHMARKS, PLOTLY_THEME as T, COLORS


PEER_DATA = {
    "Manufacturing": [
        {"name": "Industry Leader",   "intensity": 65,  "esg": 88, "renew": 72},
        {"name": "Sector Average",    "intensity": 120, "esg": 62, "renew": 18},
        {"name": "Sector Median",     "intensity": 108, "esg": 65, "renew": 22},
        {"name": "Laggard",           "intensity": 195, "esg": 38, "renew": 4},
    ],
    "Office": [
        {"name": "Industry Leader",   "intensity": 22,  "esg": 91, "renew": 88},
        {"name": "Sector Average",    "intensity": 50,  "esg": 68, "renew": 31},
        {"name": "Sector Median",     "intensity": 44,  "esg": 71, "renew": 28},
        {"name": "Laggard",           "intensity": 98,  "esg": 41, "renew": 5},
    ],
    "University": [
        {"name": "Industry Leader",   "intensity": 30,  "esg": 87, "renew": 65},
        {"name": "Sector Average",    "intensity": 70,  "esg": 64, "renew": 24},
        {"name": "Sector Median",     "intensity": 62,  "esg": 67, "renew": 26},
        {"name": "Laggard",           "intensity": 140, "esg": 39, "renew": 3},
    ],
    "Hospital": [
        {"name": "Industry Leader",   "intensity": 72,  "esg": 84, "renew": 55},
        {"name": "Sector Average",    "intensity": 150, "esg": 58, "renew": 14},
        {"name": "Sector Median",     "intensity": 138, "esg": 61, "renew": 16},
        {"name": "Laggard",           "intensity": 248, "esg": 32, "renew": 2},
    ],
    "Retail": [
        {"name": "Industry Leader",   "intensity": 28,  "esg": 89, "renew": 81},
        {"name": "Sector Average",    "intensity": 80,  "esg": 63, "renew": 22},
        {"name": "Sector Median",     "intensity": 72,  "esg": 66, "renew": 25},
        {"name": "Laggard",           "intensity": 155, "esg": 35, "renew": 3},
    ],
    "Data Center": [
        {"name": "Industry Leader",   "intensity": 88,  "esg": 83, "renew": 92},
        {"name": "Sector Average",    "intensity": 200, "esg": 56, "renew": 28},
        {"name": "Sector Median",     "intensity": 182, "esg": 59, "renew": 31},
        {"name": "Laggard",           "intensity": 380, "esg": 29, "renew": 4},
    ],
    "Hotel": [
        {"name": "Industry Leader",   "intensity": 38,  "esg": 86, "renew": 68},
        {"name": "Sector Average",    "intensity": 90,  "esg": 61, "renew": 18},
        {"name": "Sector Median",     "intensity": 80,  "esg": 64, "renew": 21},
        {"name": "Laggard",           "intensity": 175, "esg": 36, "renew": 3},
    ],
}


def _bubble_chart(peers, your_intensity, your_esg, company, sector) -> go.Figure:
    fig = go.Figure()

    colors_p = {"Industry Leader": "#10B981", "Sector Average": "#9CA3AF",
                "Sector Median": "#D1D5DB", "Laggard": "#EF4444"}

    for p in peers:
        fig.add_trace(go.Scatter(
            x=[p["intensity"]], y=[p["esg"]],
            mode="markers+text",
            name=p["name"],
            marker=dict(
                size=max(p["renew"] * 0.5 + 12, 14),
                color=colors_p.get(p["name"], "#6B7280"),
                opacity=0.75,
                line=dict(width=2, color="white"),
            ),
            text=[p["name"]],
            textposition="top center",
            textfont=dict(size=10, family="Montserrat"),
            hovertemplate=(
                f"<b>{p['name']}</b><br>"
                f"Intensity: {p['intensity']} kg/m²<br>"
                f"ESG Score: {p['esg']}/100<br>"
                f"Renewable: {p['renew']}%<extra></extra>"
            ),
        ))

    # Your organization
    fig.add_trace(go.Scatter(
        x=[your_intensity], y=[your_esg],
        mode="markers+text",
        name=company,
        marker=dict(size=22, color="#FFB703", symbol="star",
                    line=dict(width=2, color="#0EA5E9")),
        text=[f"⭐ {company}"],
        textposition="top center",
        textfont=dict(size=11, family="Montserrat", color="#0EA5E9"),
        hovertemplate=(
            f"<b>{company}</b><br>"
            f"Intensity: {your_intensity:.1f} kg/m²<br>"
            f"ESG Score: {your_esg}/100<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=340, margin=dict(l=0,r=0,t=24,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Carbon Intensity (kg CO₂e/m²)", gridcolor="#F0F2F5",
                   showline=False, zeroline=False),
        yaxis=dict(title="ESG Score (/100)", gridcolor="#F0F2F5",
                   showline=False, zeroline=False),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        legend=dict(orientation="h", y=-0.18, font=dict(size=10)),
        showlegend=True,
    )
    return fig



def _hex_to_rgba(color: str, alpha: float = 0.1) -> str:
    """Convert hex or rgb color to rgba string for Plotly fillcolor."""
    if color.startswith("#"):
        h = color.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return f"rgba({r},{g},{b},{alpha})"
        elif len(h) == 3:
            r,g,b = int(h[0]*2,16), int(h[1]*2,16), int(h[2]*2,16)
            return f"rgba({r},{g},{b},{alpha})"
    if "rgb(" in color:
        inner = color.replace("rgb(","").replace(")","")
        r,g,b = inner.split(",")
        return f"rgba({r},{g},{b},{alpha})"
    return color  # fallback unchanged


def _radar_chart(your_scores, leader_scores, avg_scores) -> go.Figure:
    categories = ["Environmental", "Social", "Governance",
                  "Data Quality", "Renewable %", "Efficiency"]
    fig = go.Figure()
    for scores, name, color in [
        (leader_scores, "Industry Leader", "#10B981"),
        (avg_scores,    "Sector Average",  "#9CA3AF"),
        (your_scores,   "Your Org",        "#FFB703"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=name,
            line=dict(color=color, width=2),
            fillcolor=_hex_to_rgba(color, 0.10),
            hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
        ))
    fig.update_layout(
        height=300, margin=dict(l=20,r=20,t=30,b=20),
        polar=dict(
            radialaxis=dict(visible=True, range=[0,100],
                            tickfont=dict(size=9), gridcolor="#F0F2F5"),
            angularaxis=dict(tickfont=dict(size=10, family="Montserrat")),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.12, font=dict(size=10, family="Montserrat")),
        font=dict(family=T["font_family"]),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TIER 4 · Indonesia Sector Benchmark — KLHK PROPER / IESR-calibrated reference
# ─────────────────────────────────────────────────────────────────────────────
# Indicative reference ranges calibrated against publicly disclosed KLHK PROPER
# environmental-compliance patterns and IESR Indonesia energy-transition sector
# analysis. Each sector keeps its own most representative unit (building-area
# intensity isn't meaningful for a plantation or an open-pit mine) — for
# statutory/compliance reporting, validate against your facility's latest
# PROPER assessment and the current KLHK/IESR published statistics.
INDONESIA_SECTOR_BENCHMARKS = {
    "Manufaktur": {
        "icon": "🏭", "unit": "kg CO₂e/m²/yr",
        "leader": 68, "average": 142, "laggard": 255,
        "renew_avg_pct": 9,
        "proper_note": ("Largest PROPER cohort nationally — predominantly Biru, with Hijau/Emas "
                         "concentrated among export-oriented (EU CBAM-exposed) producers."),
        "regulation": "PROPER (KLHK) · AMDAL/UKL-UPL · ISO 50001 (increasingly required by export buyers)",
        "context": ("Cement, steel and pulp &amp; paper are the most energy-intensive sub-sectors, and sit "
                    "among Perpres 110/2025's six carbon-pricing priority sectors."),
    },
    "Perkebunan": {
        "icon": "🌴", "unit": "tCO₂e/ha/yr",
        "leader": 1.8, "average": 5.6, "laggard": 12.4,
        "renew_avg_pct": 13,
        "proper_note": ("Widest Biru–Merah spread of the four sectors — peatland conversion and open "
                         "burning are the recurring non-compliance drivers."),
        "regulation": "ISPO (mandatory) · RSPO (export premium) · Permen LHK 21/2021 (peatland protection)",
        "context": ("Palm oil dominates the category. Deforestation-free / no-burn sourcing is now a "
                    "binding EU/UK market-access requirement, not just a voluntary ESG signal."),
    },
    "Pertambangan": {
        "icon": "⛏️", "unit": "tCO₂e/ton ore",
        "leader": 0.15, "average": 0.41, "laggard": 0.92,
        "renew_avg_pct": 6,
        "proper_note": ("Highest national share of Merah/Hitam ratings — land rehabilitation and acid "
                         "mine water management are the recurring failure points."),
        "regulation": "PROPER · RKAB land-rehabilitation obligation · Jaminan Reklamasi (UU Minerba)",
        "context": ("Coal (≥100MW-linked operations) is the first-priority sector under Perpres 110/2025; "
                    "nickel's footprint faces growing EV battery supply-chain scrutiny (EU Battery Regulation)."),
    },
    "Properti": {
        "icon": "🏢", "unit": "kWh/m²/yr",
        "leader": 98, "average": 168, "laggard": 285,
        "renew_avg_pct": 11,
        "proper_note": ("Mostly voluntary / self-assessment participation — far lower mandatory PROPER "
                         "coverage than heavy industry."),
        "regulation": "Greenship (GBCI) · EDGE Certification · Permen PUPR Bangunan Gedung Hijau",
        "context": ("Jakarta/Surabaya Grade-A office and mixed-use assets lead adoption; the leader-to-"
                    "laggard gap is driven mainly by HVAC/lighting system age, not by grid access."),
    },
}

# Most recently published full-cycle national PROPER results (KLHK).
PROPER_NATIONAL = {
    "cycle": "2023–2024", "total": 4495,
    "emas": 85, "hijau": 227, "biru": 2649, "merah": 1313, "hitam": 16,
}


def _indonesia_tier_bar(data: dict) -> go.Figure:
    tiers  = ["Leader", "Sector Average", "Laggard"]
    values = [data["leader"], data["average"], data["laggard"]]
    colors = ["#10B981", "#0EA5E9", "#F43F5E"]
    fmt    = (lambda v: f"{v:,.2f}") if max(values) < 10 else (lambda v: f"{v:,.0f}")
    fig = go.Figure(go.Bar(
        x=tiers, y=values, marker=dict(color=colors),
        text=[fmt(v) for v in values], textposition="outside",
        hovertemplate=f"<b>%{{x}}</b><br>%{{y}} {data['unit']}<extra></extra>",
    ))
    fig.update_layout(
        height=260, margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F3F4F6", title=data["unit"]),
        xaxis=dict(showgrid=False),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        showlegend=False,
    )
    return fig


def render():
    S.init()

    page_header(
        title="Industry Benchmarking Hub",
        subtitle="Compare performance against sector peers · Identify gaps · Understand ranking",
        badge="Peer Analysis",
        badge_type="green",
    )

    has_data = S.get("uploaded_df") is not None
    df       = S.get("uploaded_df") if has_data else generate_demo_data()
    ov       = dataset_overview(df)
    company  = S.get("company_name", "Your Organization")
    sector   = S.get("sector", "Manufacturing")
    area_m2  = float(S.get("area_m2", 5000))
    total    = ov.get("total", 0)
    from utils.state import compute_canonical_esg, get_scope_results
    esg       = compute_canonical_esg()
    intensity = get_scope_results()["intens_m2"]
    bench    = get_benchmark(sector)
    gap      = benchmark_gap(intensity, bench)
    peers    = PEER_DATA.get(sector, PEER_DATA["Manufacturing"])

    if not has_data:
        st.info("📌 Using demo data. Upload your dataset in ESG Analytics for real benchmarking.")

    # ── Sector selector ──────────────────────────────────────────────────────
    sel_col, _ = st.columns([1, 3])
    with sel_col:
        sector_sel = st.selectbox("Compare against sector", list(INDUSTRY_BENCHMARKS.keys()),
                                   index=list(INDUSTRY_BENCHMARKS.keys()).index(sector)
                                         if sector in INDUSTRY_BENCHMARKS else 0,
                                   key="bench_sector")
    peers = PEER_DATA.get(sector_sel, PEER_DATA["Manufacturing"])
    bench = get_benchmark(sector_sel)
    gap   = benchmark_gap(intensity, bench)

    # ── Ranking KPIs ─────────────────────────────────────────────────────────
    leader_intensity = peers[0]["intensity"]
    avg_intensity    = peers[1]["intensity"]
    # Percentile: lower intensity = better rank
    all_intensities  = sorted([p["intensity"] for p in peers] + [intensity])
    rank_pos         = all_intensities.index(min(all_intensities, key=lambda x: abs(x - intensity))) + 1
    percentile       = round((1 - rank_pos / (len(all_intensities))) * 100)

    k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
    with k1:
        kpi_card("Your Intensity", f"{intensity:.0f}",
                 badge="kg CO₂e/m²", badge_type="gray",
                 icon="📊", icon_bg="#E0F2FE")
    with k2:
        kpi_card("Sector Benchmark", str(bench),
                 badge="kg CO₂e/m²", badge_type="gray",
                 icon="📏", icon_bg="#F9FAFB")
    with k3:
        kpi_card("Gap vs Average",
                 f"{gap['gap_pct']:+.0f}%",
                 badge="vs sector avg",
                 badge_type="red" if gap["above_benchmark"] else "green",
                 icon="📉" if not gap["above_benchmark"] else "📈",
                 icon_bg="#DCFCE7" if not gap["above_benchmark"] else "#FEE2E2")
    with k4:
        gap_to_leader = ((intensity - leader_intensity) / max(leader_intensity, 1)) * 100
        kpi_card("Gap to Leader",
                 f"{gap_to_leader:+.0f}%",
                 badge=f"Leader: {leader_intensity} kg/m²", badge_type="green",
                 icon="🏆", icon_bg="#FFF9C4" if gap_to_leader > 0 else "#E0F2FE")
    with k5:
        kpi_card("ESG Score", f"{esg['score']}/100",
                 badge=f"Grade {esg['grade']}", badge_type="green" if esg["score"]>=75 else "yellow",
                 icon="🎯", icon_bg="#E0F2FE")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Bubble chart + Radar ──────────────────────────────────────────────────
    bub_col, rad_col = st.columns([1.4, 1], gap="medium")

    with bub_col:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🔵 Peer Positioning Map</div>
            <div class="cl-card-subtitle">Carbon intensity vs ESG score · Bubble size = renewable energy % · ⭐ = your organization</div>
        """, unsafe_allow_html=True)
        fig_bub = _bubble_chart(peers, intensity, esg["score"], company, sector_sel)
        try:
            st.plotly_chart(fig_bub, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    with rad_col:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🕸️ Multi-Dimension Radar</div>
            <div class="cl-card-subtitle">Your org vs Leader vs Sector Average</div>
        """, unsafe_allow_html=True)
        renew_norm = float(S.get("renew_pct", 5))
        recycle    = float(S.get("recycle_pct", 20))
        your_scores   = [esg["env"], esg["social"], esg["gov"],
                         ov.get("completeness",94), renew_norm, max(100-intensity/bench*100,0)]
        leader_scores = [88, 75, 82, 96, peers[0]["renew"], 88]
        avg_scores    = [62, 58, 60, 80, peers[1]["renew"], 48]
        fig_rad = _radar_chart(your_scores, leader_scores, avg_scores)
        try:
            st.plotly_chart(fig_rad, use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── ESG Composition vs Sector Average ─────────────────────────────────────
    comp_col, gap_col = st.columns(2, gap="medium")
    with comp_col:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🎯 ESG Score Composition</div>
            <div class="cl-card-subtitle">Your E/S/G breakdown vs sector average · GRI 2021 weighting</div>
        """, unsafe_allow_html=True)
        _colors = {"Environmental":"#0EA5E9","Social":"#6366F1","Governance":"#8B5CF6"}
        _sector_avg = {"Environmental": avg_scores[0], "Social": avg_scores[1], "Governance": avg_scores[2]}
        for dim, your_sc, dim_wt in [
            ("Environmental", esg["env"],    "40%"),
            ("Social",        esg["social"], "30%"),
            ("Governance",    esg["gov"],    "30%"),
        ]:
            col = _colors[dim]
            avg = _sector_avg[dim]
            your_pct = min(max(your_sc,0),100)
            avg_pct  = min(max(avg,0),100)
            diff     = your_sc - avg
            diff_str = f"{'▲' if diff>0 else '▼'} {abs(diff):.0f} vs sector avg"
            diff_col = "#10B981" if diff>0 else "#F43F5E"
            st.markdown(f"""
            <div style="margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <div style="font-size:11px;font-weight:700;color:#0F172A;">{dim} <span style="color:#94A3B8;font-weight:400;">({dim_wt})</span></div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:11px;font-weight:700;color:{col};">{your_sc:.0f}</span>
                        <span style="font-size:10px;color:{diff_col};font-weight:600;">{diff_str}</span>
                    </div>
                </div>
                <div style="position:relative;height:10px;background:#F3F4F6;border-radius:5px;overflow:visible;">
                    <div style="position:absolute;width:{your_pct:.0f}%;height:100%;background:{col};border-radius:5px;opacity:0.9;"></div>
                    <div style="position:absolute;left:{avg_pct:.0f}%;top:-3px;width:2px;height:16px;background:#94A3B8;border-radius:1px;" title="Sector avg"></div>
                </div>
                <div style="font-size:9px;color:#94A3B8;margin-top:2px;">Sector avg: {avg:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with gap_col:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📊 Priority Gap Analysis</div>
            <div class="cl-card-subtitle">Dimensions with largest improvement potential</div>
        """, unsafe_allow_html=True)
        gaps = [
            ("Environmental", esg["env"],    avg_scores[0], "0EA5E9", "Reduce carbon intensity, increase renewables, improve water recycling"),
            ("Social",        esg["social"], avg_scores[1], "6366F1", "Improve training hours, safety record, gender diversity"),
            ("Governance",    esg["gov"],    avg_scores[2], "8B5CF6", "Strengthen board independence, disclose ethics policies"),
        ]
        gaps_sorted = sorted(gaps, key=lambda x: x[1]-x[2])
        for dim, your_sc, avg_sc, hex_c, tip in gaps_sorted:
            diff = your_sc - avg_sc
            urgent = diff < -10
            st.markdown(f"""
            <div style="border-left:3px solid #{'F43F5E' if urgent else '0EA5E9'};
                 padding:10px 12px;margin-bottom:10px;background:#{'FFF1F2' if urgent else 'F0F9FF'};
                 border-radius:0 8px 8px 0;">
                <div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:3px;">
                    {dim} {'⚠️' if urgent else '✓'}
                    <span style="font-size:10px;color:{'#F43F5E' if diff<0 else '#10B981'};margin-left:4px;">
                        {'+' if diff>=0 else ''}{diff:.0f} vs avg
                    </span>
                </div>
                <div style="font-size:11px;color:#64748B;">{tip}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Detailed peer table ───────────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">📋 Sector Peer Comparison Table</div>
        <div class="cl-card-subtitle">Full breakdown — carbon intensity · ESG score · renewable % · vs your organization</div>
    """, unsafe_allow_html=True)

    rows = []
    for p in peers:
        rows.append({
            "Organization":        p["name"],
            "Intensity (kg/m²)":   p["intensity"],
            "ESG Score":           f"{p['esg']}/100",
            "Renewable %":         f"{p['renew']}%",
            "vs Your Intensity":   f"{((p['intensity']-intensity)/max(intensity,1)*100):+.0f}%",
        })
    rows.append({
        "Organization":        f"⭐ {company} (You)",
        "Intensity (kg/m²)":   round(intensity, 1),
        "ESG Score":           f"{esg['score']}/100",
        "Renewable %":         f"{int(renew_norm)}%",
        "vs Your Intensity":   "—",
    })

    df_peers = pd.DataFrame(rows)
    st.dataframe(df_peers, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Path to leadership ────────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    reduction_to_leader = max(intensity - leader_intensity, 0)
    reduction_pct       = (reduction_to_leader / max(intensity, 1)) * 100

    insight_panel([
        {
            "text": (f"<strong>Path to Industry Leadership:</strong> Reduce carbon intensity from "
                     f"{intensity:.0f} to {leader_intensity} kg/m² — a "
                     f"<strong>{reduction_pct:.0f}% reduction</strong> required. "
                     f"Primary lever: renewable energy transition (current {int(renew_norm)}% → target {peers[0]['renew']}%)."),
            "type": "info", "icon": "🏆"
        },
        {
            "text": (f"<strong>Quick win vs Sector Average:</strong> Reducing intensity by "
                     f"{max(intensity - avg_intensity, 0):.0f} kg/m² would move you from "
                     f"{'above' if gap['above_benchmark'] else 'below'} to at-or-below the sector average, "
                     f"unlocking better ESG ratings from major rating agencies (MSCI, Sustainalytics)."),
            "type": "warn" if gap["above_benchmark"] else "info",
            "icon": "⚡"
        },
    ])

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 4 · INDONESIA SECTOR BENCHMARK (KLHK PROPER / IESR)
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:4px;">🇮🇩 Indonesia Sector Benchmark</div>
    <div style="font-size:11px;color:#94A3B8;margin-bottom:14px;">
        Sector-specific reference ranges calibrated against KLHK PROPER compliance patterns &amp; IESR energy-transition analysis</div>
    """, unsafe_allow_html=True)

    _pn = PROPER_NATIONAL
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#F0F9FF,#ECFEFF);border:1.5px solid #BAE6FD;
                border-radius:12px;padding:14px 18px;margin-bottom:14px;">
        <div style="font-size:11px;font-weight:700;color:#0C4A6E;margin-bottom:6px;">
            📊 PROPER {_pn['cycle']} — National Compliance Ratings (KLHK)</div>
        <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:11px;color:#374151;">
            <span>🟡 Emas: <strong>{_pn['emas']}</strong></span>
            <span>🟢 Hijau: <strong>{_pn['hijau']}</strong></span>
            <span>🔵 Biru: <strong>{_pn['biru']:,}</strong></span>
            <span>🔴 Merah: <strong>{_pn['merah']:,}</strong></span>
            <span>⚫ Hitam: <strong>{_pn['hitam']}</strong></span>
            <span style="color:#64748B;">of {_pn['total']:,} companies assessed nationally</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _id_default_map = {"Manufacturing": "Manufaktur", "Mining": "Pertambangan"}
    _id_default      = _id_default_map.get(sector, "Manufaktur")

    id_sectors = list(INDONESIA_SECTOR_BENCHMARKS.keys())
    id_sel_col, _ = st.columns([1, 3])
    with id_sel_col:
        id_sector_sel = st.selectbox("Indonesia sector reference", id_sectors,
                                      index=id_sectors.index(_id_default),
                                      key="id_bench_sector")

    id_data = INDONESIA_SECTOR_BENCHMARKS[id_sector_sel]

    id_l, id_r = st.columns([1, 1.3], gap="medium")
    with id_l:
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">{id_data['icon']} {id_sector_sel} — Sector Profile</div>
            <div class="cl-card-subtitle">Indicative reference, KLHK/IESR-calibrated</div>
            <div style="margin-top:10px;font-size:11px;color:#374151;line-height:1.8;">
                <strong>Avg. renewable adoption:</strong> {id_data['renew_avg_pct']}%<br>
                <strong>Regulatory / certification:</strong> {id_data['regulation']}<br><br>
                <strong>PROPER tendency:</strong> {id_data['proper_note']}<br><br>
                <strong>Context:</strong> {id_data['context']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with id_r:
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">📶 {id_data['unit']} — Leader / Average / Laggard</div>
        """, unsafe_allow_html=True)
        try:
            st.plotly_chart(_indonesia_tier_bar(id_data), use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown(f"""<div style="font-size:10px;color:#9CA3AF;">Your organization's general
                    building-area intensity: <strong>{intensity:.0f} kg CO₂e/m²/yr</strong> — shown for
                    reference only; this sector's primary metric uses a different basis
                    ({id_data['unit']}).</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">📋 Cross-Sector Comparison — Indonesia</div>
        <div class="cl-card-subtitle">Each sector uses its own most representative unit — figures are not directly comparable across rows</div>
    """, unsafe_allow_html=True)
    id_rows = []
    for _sname, _sdata in INDONESIA_SECTOR_BENCHMARKS.items():
        id_rows.append({
            "Sector":            f"{_sdata['icon']} {_sname}",
            "Unit":               _sdata["unit"],
            "Leader":             _sdata["leader"],
            "Sector Average":     _sdata["average"],
            "Laggard":            _sdata["laggard"],
            "Avg. Renewable %":  f"{_sdata['renew_avg_pct']}%",
            "Key Regulation":     _sdata["regulation"],
        })
    st.dataframe(pd.DataFrame(id_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:9.5px;color:#B0BEC9;margin-top:8px;line-height:1.6;">
        Methodology: indicative sector reference ranges calibrated against publicly disclosed KLHK PROPER
        environmental-compliance patterns and IESR Indonesia energy-transition sector analysis. National
        PROPER figures above reflect the most recently published full-cycle results. For statutory or
        regulatory reporting, validate against your facility's current PROPER assessment and the latest
        KLHK/IESR published statistics.
    </div>
    """, unsafe_allow_html=True)
