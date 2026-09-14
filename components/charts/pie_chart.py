"""CarbonLens — Pie/donut chart component."""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs
from components.theme.colors import CHART_PRIMARY, CHART_SECONDARY, CHART_ACCENT


def scope_donut_chart(
    labels: list,
    values: list,
    colors: list = None,
    title:  str  = "Scope Distribution",
) -> None:
    """Render a donut chart for scope or category distribution."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    if not labels or not values or sum(values) == 0:
        st.caption("No emissions data to display.")
        return

    default_colors = [CHART_PRIMARY, CHART_SECONDARY, CHART_ACCENT]
    pie_colors = colors or default_colors[:len(labels)]

    fig = go.Figure(go.Pie(
        labels    = labels,
        values    = values,
        hole      = 0.55,
        marker    = dict(colors=pie_colors, line=dict(color="#FFFFFF", width=2)),
        textinfo  = "percent",
        pull      = [0.02] * len(labels),
        hovertemplate = "<b>%{label}</b><br>%{value:.2f} tCO2e (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title        = dict(text=title, font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        font         = dict(family="Inter, sans-serif", color="#66736B"),
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=40, b=0),
        legend       = dict(orientation="h", yanchor="bottom", y=-0.2),
        transition   = dict(duration=400, easing="cubic-in-out"),
        height       = 280,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})
