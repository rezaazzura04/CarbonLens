"""CarbonLens V8 — Benchmark comparison chart component."""
from __future__ import annotations
import streamlit as st


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
    bar_color= "#DC2626" if above else "#059669"
    max_val  = max(intensity, benchmark) * 1.3 or 1.0

    fig = go.Figure()

    # Benchmark reference line (bar)
    fig.add_trace(go.Bar(
        x    = ["Organisation", "Benchmark"],
        y    = [intensity, benchmark],
        marker_color = [bar_color, "#94A3B8"],
        text = [f"{intensity:.1f}", f"{benchmark:.1f}"],
        textposition = "outside",
        width= 0.5,
    ))

    fig.update_layout(
        title        = dict(text=title, font=dict(size=14, color="#0F172A")),
        yaxis        = dict(range=[0, max_val], title="kg CO₂e/m²/yr",
                            gridcolor="#F1F5F9"),
        xaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=50, b=0),
        showlegend   = False,
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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
        connector = dict(line=dict(color="#E2E8F0")),
        increasing= dict(marker=dict(color="#0EA5E9")),
        totals    = dict(marker=dict(color="#0F172A")),
    ))
    fig.update_layout(
        title        = dict(text=f"Scope Build-up ({unit})", font=dict(size=14, color="#0F172A")),
        yaxis        = dict(title=unit, gridcolor="#F1F5F9"),
        xaxis        = dict(showgrid=False),
        plot_bgcolor = "#FFFFFF",
        paper_bgcolor= "#FFFFFF",
        margin       = dict(l=0, r=0, t=50, b=0),
        showlegend   = False,
        height       = 280,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
