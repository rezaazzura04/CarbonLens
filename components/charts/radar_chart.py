"""CarbonLens — ESG radar chart component."""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs
from components.theme.colors import ENV_COLOR, SOC_COLOR, GOV_COLOR


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
        fillcolor = "rgba(47,107,79,0.12)",
        # Straight edges only — NOT shape="spline". A radar/spider chart's
        # three axes (Environmental/Social/Governance) are categorical, not
        # continuous; curving the polygon edges would visually imply a
        # measured value existing "between" two pillars, which does not
        # exist. Standard radar-chart convention is always straight
        # vertex-to-vertex segments — this is an analytical-honesty
        # requirement, not a style preference.
        line  = dict(color="#037C38", width=2.5),
        marker = dict(size=6, color="#037C38"),
        name  = "ESG Score",
        hovertemplate = "<b>%{theta}</b><br>%{r:.1f} / 100<extra></extra>",
    ))
    fig.update_layout(
        polar = dict(
            bgcolor   = "#FFFFFF",
            radialaxis= dict(visible=True, range=[0,100], gridcolor="#DDE5DE",
                             tickfont=dict(family="Inter, sans-serif", size=9, color="#8A968D")),
            angularaxis=dict(tickfont=dict(family="Inter, sans-serif", size=11, color="#17221C")),
        ),
        title        = dict(text=title, font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=40, r=40, t=60, b=40),
        showlegend   = False,
        transition   = dict(duration=400, easing="cubic-in-out"),
        height       = 320,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})


def pillar_comparison_bar(env: float, social: float, gov: float) -> None:
    """Render a simple horizontal bar comparison of the three ESG pillars."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    pillars = ["Environmental", "Social", "Governance"]
    scores  = [env, social, gov]
    colors  = [ENV_COLOR, SOC_COLOR, GOV_COLOR]

    fig = go.Figure(go.Bar(
        x           = scores,
        y           = pillars,
        orientation = "h",
        marker_color= colors,
        text        = [f"{s:.1f}" for s in scores],
        textposition= "outside",
        hovertemplate = "<b>%{y}</b><br>%{x:.1f} / 100<extra></extra>",
    ))
    fig.update_layout(
        font         = dict(family="Inter, sans-serif", color="#66736B"),
        xaxis        = dict(range=[0,110], showgrid=False, title="Score (0–100)"),
        yaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        transition   = dict(duration=400, easing="cubic-in-out"),
        margin       = dict(l=0, r=40, t=10, b=0),
        showlegend   = False,
        height       = 180,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})
