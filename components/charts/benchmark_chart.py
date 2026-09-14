"""CarbonLens — Benchmark comparison chart component."""
from __future__ import annotations
import streamlit as st
from components.compat import width_stretch_kwargs
from components.theme.colors import CHART_CRITICAL, CHART_PRIMARY, CHART_NEUTRAL, CHART_PRIMARY as _DARK


def benchmark_gauge(
    intensity:  float,
    benchmark:  float,
    sector:     str   = "Manufacturing",
    title:      str   = "Carbon Intensity vs Benchmark",
) -> None:
    """
    Render a bullet/gauge chart showing intensity vs sector benchmark.
    All values pre-computed by caller.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    above    = intensity > benchmark
    bar_color= CHART_CRITICAL if above else CHART_PRIMARY
    max_val  = max(intensity, benchmark) * 1.3 or 1.0

    fig = go.Figure()

    # Benchmark reference line (bar)
    fig.add_trace(go.Bar(
        x    = ["Organisation", "Benchmark"],
        y    = [intensity, benchmark],
        marker_color = [bar_color, CHART_NEUTRAL],
        text = [f"{intensity:.1f}", f"{benchmark:.1f}"],
        textposition = "outside",
        width= 0.5,
        hovertemplate = "<b>%{x}</b><br>%{y:.2f} kg CO2e/m²<extra></extra>",
    ))

    fig.update_layout(
        title        = dict(text=title, font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        font         = dict(family="Inter, sans-serif", color="#66736B"),
        yaxis        = dict(range=[0, max_val], title="kg CO₂e/m²/yr",
                            gridcolor="#DDE5DE"),
        xaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=50, b=0),
        showlegend   = False,
        transition   = dict(duration=400, easing="cubic-in-out"),
        height       = 260,
        annotations  = [dict(
            text      = f"{'↑ {:.1f}% above' if above else '↓ {:.1f}% below'} {sector} benchmark".format(
                abs((intensity-benchmark)/benchmark*100) if benchmark else 0
            ),
            xref="paper", yref="paper",
            x=0.5, y=1.08, showarrow=False,
            font=dict(size=12, color=bar_color), xanchor="center",
        )],
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})


def scope_waterfall_chart(
    scope1: float,
    scope2: float,
    scope3: float,
    total:  float,
    unit:   str = "tCO2e",
) -> None:
    """
    Render a waterfall chart showing Scope 1→2→3→Total build-up.
    All values pre-computed by caller.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("plotly not installed")
        return

    fig = go.Figure(go.Waterfall(
        name      = "Scope",
        orientation="v",
        measure   = ["relative", "relative", "relative", "total"],
        x         = ["Scope 1", "Scope 2", "Scope 3", "Total"],
        y         = [scope1, scope2, scope3, 0],
        text      = [f"{scope1:.1f}", f"{scope2:.1f}", f"{scope3:.1f}", f"{total:.1f}"],
        textposition = "outside",
        connector = dict(line=dict(color="#DDE5DE")),
        increasing= dict(marker=dict(color="#6E9B7F")),
        totals    = dict(marker=dict(color="#0F3D2E")),
        hovertemplate = "<b>%{x}</b><br>%{y:.2f} " + unit + "<extra></extra>",
    ))
    fig.update_layout(
        title        = dict(text=f"Scope Build-up ({unit})", font=dict(family="Inter, sans-serif", size=14, color="#17221C")),
        font         = dict(family="Inter, sans-serif", color="#66736B"),
        yaxis        = dict(title=unit, gridcolor="#E0EFE7"),
        xaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=50, b=0),
        showlegend   = False,
        transition   = dict(duration=400, easing="cubic-in-out"),
        height       = 280,
    )
    st.plotly_chart(fig, **width_stretch_kwargs(), config={"displayModeBar": False})
