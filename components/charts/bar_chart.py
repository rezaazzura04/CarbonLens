"""CarbonLens V8 — Bar chart component."""
from __future__ import annotations
import streamlit as st


def scope_bar_chart(
    labels:  list,
    values:  list,
    colors:  list = None,
    title:   str  = "Scope Breakdown",
    unit:    str  = "tCO2e",
    horizontal: bool = False,
) -> None:
    """Render a bar chart for Scope 1/2/3 or any category breakdown."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    if not labels or not values:
        st.caption("No data available.")
        return

    default_colors = ["#10B981", "#0EA5E9", "#6366F1", "#F97316", "#EC4899"]
    bar_colors = colors or default_colors[:len(labels)]

    if horizontal:
        fig = go.Figure(go.Bar(
            y=labels, x=values, orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
        ))

    fig.update_layout(
        title        = dict(text=title, font=dict(size=14, color="#0F172A")),
        yaxis        = dict(title=unit if not horizontal else "", gridcolor="#F1F5F9"),
        xaxis        = dict(title=unit if horizontal else "", showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=40, b=0),
        showlegend   = False,
        height       = 280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
