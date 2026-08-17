"""CarbonLens V8 — Line chart component. Receives processed data. Never calculates."""
from __future__ import annotations
import streamlit as st


def emission_trend_chart(
    months:  list,
    values:  list,
    title:   str  = "Monthly Emissions",
    unit:    str  = "tCO2e",
    color:   str  = "#0EA5E9",
    show_forecast: bool = False,
    forecast_value: float = 0.0,
) -> None:
    """
    Render a line chart for monthly emission data.

    Parameters — all pre-computed by caller:
    months         : List of month label strings.
    values         : List of numeric emission values (same length as months).
    show_forecast  : If True, append a forecast point.
    forecast_value : Pre-computed next-month forecast value.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed — install with: pip install plotly")
        return

    if not months or not values:
        st.caption("No data available for chart.")
        return

    x_vals = list(months)
    y_vals = list(values)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x    = x_vals,
        y    = y_vals,
        mode = "lines+markers",
        name = unit,
        line = dict(color=color, width=2.5),
        marker = dict(size=6, color=color),
    ))

    if show_forecast and forecast_value > 0:
        fig.add_trace(go.Scatter(
            x    = [x_vals[-1], "Forecast"],
            y    = [y_vals[-1], forecast_value],
            mode = "lines+markers",
            name = "Forecast",
            line = dict(color="#94A3B8", width=1.5, dash="dot"),
            marker = dict(size=7, color="#94A3B8", symbol="diamond"),
        ))

    fig.update_layout(
        title      = dict(text=title, font=dict(size=14, color="#0F172A")),
        xaxis      = dict(showgrid=False, color="#94A3B8"),
        yaxis      = dict(title=unit, gridcolor="#F1F5F9", color="#94A3B8"),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin     = dict(l=0, r=0, t=40, b=0),
        showlegend = show_forecast,
        height     = 280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
