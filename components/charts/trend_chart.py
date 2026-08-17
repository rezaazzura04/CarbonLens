"""CarbonLens V8 — Trend and forecast chart component."""
from __future__ import annotations
import streamlit as st


def trend_forecast_chart(
    months:         list,
    actuals:        list,
    forecast_value: float = 0.0,
    trend:          str   = "stable",
    r2:             float = 0.0,
    title:          str   = "Emission Trend & Forecast",
) -> None:
    """
    Render combined actual + forecast trend chart.
    All data must be pre-computed by the caller.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    if not months or not actuals:
        st.caption("Insufficient data for trend analysis (minimum 3 months required).")
        return

    trend_colors = {"rising": "#DC2626", "falling": "#059669", "stable": "#0891B2"}
    color = trend_colors.get(trend, "#94A3B8")

    fig = go.Figure()

    # Actual line
    fig.add_trace(go.Scatter(
        x    = months,
        y    = actuals,
        mode = "lines+markers",
        name = "Actual",
        line = dict(color="#0EA5E9", width=2.5),
        marker = dict(size=6, color="#0EA5E9"),
    ))

    # Forecast point
    if forecast_value > 0 and months:
        fig.add_trace(go.Scatter(
            x    = [months[-1], "Next month"],
            y    = [actuals[-1], forecast_value],
            mode = "lines+markers",
            name = "Forecast",
            line = dict(color=color, width=1.5, dash="dot"),
            marker = dict(size=8, color=color, symbol="diamond"),
        ))

    # Trend direction annotation
    trend_labels = {
        "rising":             "↑ Rising trend",
        "falling":            "↓ Falling trend",
        "stable":             "→ Stable",
        "insufficient_data":  "~ Insufficient data",
    }
    annotation_text = trend_labels.get(trend, "")
    if annotation_text and r2 > 0:
        annotation_text += f"  (R² = {r2:.2f})"

    fig.update_layout(
        title        = dict(text=title, font=dict(size=14, color="#0F172A")),
        xaxis        = dict(showgrid=False, color="#94A3B8"),
        yaxis        = dict(title="tCO2e", gridcolor="#F1F5F9", color="#94A3B8"),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=50, b=0),
        legend       = dict(orientation="h", y=1.1),
        annotations  = [dict(
            text  = annotation_text,
            xref  = "paper", yref="paper",
            x=1.0, y=1.08, showarrow=False,
            font  = dict(size=11, color=color),
            xanchor="right",
        )] if annotation_text else [],
        height = 280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
