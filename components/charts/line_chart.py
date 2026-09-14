"""CarbonLens — Line chart component. Receives processed data. Never calculates."""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs


def emission_trend_chart(
    months:  list,
    values:  list,
    title:   str  = "Monthly Emissions",
    unit:    str  = "tCO2e",
    color:   str  = "#037C38",
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

    # Line rendering is deliberately shape="linear" (straight segments
    # between actual monthly totals), NOT a spline — for discrete
    # accounting data, a spline can overshoot between points and visually
    # suggest values that were never recorded. Straight segments are the
    # analytically honest way to connect known, discrete measurements.
    #
    # The area fill and a non-zero y-axis range are still used (below) —
    # a filled/zoomed LINE chart with clearly labelled tick values and
    # exact-value hover tooltips is standard, accepted practice (unlike a
    # truncated BAR chart, where axis position directly encodes visual
    # area/magnitude). The padding here is intentionally moderate, not
    # aggressive, so the visible fluctuation reflects the data rather than
    # exaggerating it.
    all_vals = y_vals + ([forecast_value] if show_forecast and forecast_value > 0 else [])
    y_min, y_max = min(all_vals), max(all_vals)
    pad = max((y_max - y_min) * 0.35, y_max * 0.08, 1)
    axis_range = [max(0, y_min - pad), y_max + pad]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x    = x_vals,
        y    = y_vals,
        mode = "lines+markers",
        name = unit,
        line = dict(color=color, width=3, shape="linear"),
        marker = dict(size=7, color=color, line=dict(color="#FFFFFF", width=1.5)),
        fill = "tozeroy",
        fillcolor = "rgba(47,107,79,0.08)",
        hovertemplate = "%{x}<br><b>%{y:.1f}</b> " + unit + "<extra></extra>",
    ))

    if show_forecast and forecast_value > 0:
        fig.add_trace(go.Scatter(
            x    = [x_vals[-1], "Forecast"],
            y    = [y_vals[-1], forecast_value],
            mode = "lines+markers",
            name = "Forecast",
            line = dict(color="#AAB5AE", width=2, dash="dot", shape="linear"),
            marker = dict(size=8, color="#AAB5AE", symbol="diamond"),
            hovertemplate = "%{x}<br><b>%{y:.1f}</b> " + unit + " (forecast)<extra></extra>",
        ))

    fig.update_layout(
        title      = dict(text=title, font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        font       = dict(family="Inter, sans-serif", color="#66736B"),
        xaxis      = dict(showgrid=False, color="#66736B"),
        yaxis      = dict(title=unit, gridcolor="#E0EFE7", color="#66736B", range=axis_range),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin     = dict(l=0, r=0, t=40, b=0),
        showlegend = show_forecast,
        hovermode  = "x unified",
        transition = dict(duration=400, easing="cubic-in-out"),
        height     = 280,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})
