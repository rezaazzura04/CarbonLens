"""CarbonLens V8 — Pie/donut chart component."""
from __future__ import annotations
import streamlit as st


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

    default_colors = ["#10B981", "#0EA5E9", "#6366F1"]
    pie_colors = colors or default_colors[:len(labels)]

    fig = go.Figure(go.Pie(
        labels    = labels,
        values    = values,
        hole      = 0.55,
        marker    = dict(colors=pie_colors, line=dict(color="#FFFFFF", width=2)),
        textinfo  = "percent",
        hovertemplate = "%{label}: %{value:.2f} tCO2e (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title        = dict(text=title, font=dict(size=14, color="#0F172A")),
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=40, b=0),
        legend       = dict(orientation="h", yanchor="bottom", y=-0.2),
        height       = 280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
