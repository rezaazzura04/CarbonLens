"""CarbonLens V8 — ESG radar chart component."""
from __future__ import annotations
import streamlit as st


def esg_radar_chart(
    env:    float,
    social: float,
    gov:    float,
    title:  str = "ESG Pillar Scores",
) -> None:
    """
    Render an ESG pillar radar chart.
    All values must be 0–100. No calculations performed here.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    categories = ["Environmental", "Social", "Governance", "Environmental"]
    values_    = [env, social, gov, env]   # close the polygon

    fig = go.Figure(go.Scatterpolar(
        r     = values_,
        theta = categories,
        fill  = "toself",
        fillcolor = "rgba(99,102,241,0.15)",
        line  = dict(color="#6366F1", width=2),
        name  = "ESG Score",
    ))
    fig.update_layout(
        polar = dict(
            bgcolor   = "#FFFFFF",
            radialaxis= dict(visible=True, range=[0,100], gridcolor="#E2E8F0",
                             tickfont=dict(size=9, color="#94A3B8")),
            angularaxis=dict(tickfont=dict(size=11, color="#0F172A")),
        ),
        title        = dict(text=title, font=dict(size=14, color="#0F172A")),
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=40, r=40, t=60, b=40),
        showlegend   = False,
        height       = 320,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def pillar_comparison_bar(env: float, social: float, gov: float) -> None:
    """Render a simple horizontal bar comparison of the three ESG pillars."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    pillars = ["Environmental", "Social", "Governance"]
    scores  = [env, social, gov]
    colors  = ["#10B981", "#6366F1", "#F97316"]

    fig = go.Figure(go.Bar(
        x           = scores,
        y           = pillars,
        orientation = "h",
        marker_color= colors,
        text        = [f"{s:.1f}" for s in scores],
        textposition= "outside",
    ))
    fig.update_layout(
        xaxis        = dict(range=[0,110], showgrid=False, title="Score (0–100)"),
        yaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=40, t=10, b=0),
        showlegend   = False,
        height       = 180,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
