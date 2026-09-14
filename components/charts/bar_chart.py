"""CarbonLens — Bar chart component."""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs
from components.theme.colors import CHART_SERIES


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

    bar_colors = colors or CHART_SERIES[:len(labels)]

    if horizontal:
        fig = go.Figure(go.Bar(
            y=labels, x=values, orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:.2f} " + unit + "<extra></extra>",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:.2f} " + unit + "<extra></extra>",
        ))

    fig.update_layout(
        title        = dict(text=title, font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        font         = dict(family="Inter, sans-serif", color="#66736B"),
        yaxis        = dict(title=unit if not horizontal else "", gridcolor="#E0EFE7"),
        xaxis        = dict(title=unit if horizontal else "", showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=40, b=0),
        showlegend   = False,
        bargap       = 0.35,
        transition   = dict(duration=400, easing="cubic-in-out"),
        height       = 280,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})
