"""
CarbonLens — Chart factory (Plotly)
All charts follow the CarbonLens design system.
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from config.settings import PLOTLY_THEME, COLORS

T = PLOTLY_THEME


def _base_layout(**kwargs) -> dict:
    # Default legend — caller can override by passing legend=dict(...)
    default_legend = dict(
        font=dict(size=11, family=T["font_family"]),
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
    )
    # Merge caller's legend on top of defaults to avoid duplicate key error
    if "legend" in kwargs:
        caller_legend = kwargs.pop("legend")
        merged_legend = {**default_legend, **caller_legend}
    else:
        merged_legend = default_legend

    return dict(
        font=dict(family=T["font_family"], color=T["font_color"], size=T["font_size"]),
        paper_bgcolor=T["paper_color"],
        plot_bgcolor=T["bg_color"],
        margin=dict(l=0, r=0, t=28, b=0),
        legend=merged_legend,
        **kwargs,
    )


def _base_axes(fig, xgrid=False, ygrid=True):
    fig.update_xaxes(
        showgrid=xgrid, gridcolor=T["gridcolor"],
        showline=False, zeroline=False,
        tickfont=dict(size=11, family=T["font_family"]),
    )
    fig.update_yaxes(
        showgrid=ygrid, gridcolor=T["gridcolor"],
        showline=False, zeroline=False,
        tickfont=dict(size=11, family=T["font_family"]),
    )
    return fig


# ── 1. Emission trend line ──────────────────────────────────────────────────
def emission_trend(df: pd.DataFrame, benchmark: float = None, height: int = 300) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Month"], y=df["Emission"],
        name="Emissions",
        mode="lines+markers",
        line=dict(color=T["primary_color"], width=2.5, shape="spline", smoothing=0.8),
        marker=dict(size=5, color=T["primary_color"]),
        fill="tozeroy",
        fillcolor="rgba(45,122,79,0.08)",
        hovertemplate="<b>%{x}</b><br>%{y:,.1f} tCO₂e<extra></extra>",
    ))

    if benchmark is not None:
        fig.add_hline(
            y=benchmark,
            line_dash="dot",
            line_color=COLORS["accent"],
            line_width=1.5,
            annotation_text=f" Benchmark ({benchmark})",
            annotation_position="top right",
            annotation_font=dict(size=11, color=COLORS["accent"], family=T["font_family"]),
        )

    fig.update_layout(**_base_layout(height=height, showlegend=False))
    fig = _base_axes(fig)
    return fig


# ── 2. Emission bar (monthly) ───────────────────────────────────────────────
def emission_bar(df: pd.DataFrame, height: int = 280) -> go.Figure:
    mean_val = df["Emission"].mean()
    colors = [COLORS["danger"] if v > mean_val * 1.15 else T["primary_color"] for v in df["Emission"]]

    fig = go.Figure(go.Bar(
        x=df["Month"], y=df["Emission"],
        marker=dict(color=colors, cornerradius=4),
        hovertemplate="<b>%{x}</b><br>%{y:,.1f} tCO₂e<extra></extra>",
    ))

    fig.add_hline(
        y=mean_val,
        line_dash="dash", line_color="#9CA3AF", line_width=1.2,
        annotation_text=f" Avg {mean_val:,.0f}",
        annotation_font=dict(size=10, color="#9CA3AF", family=T["font_family"]),
    )

    fig.update_layout(**_base_layout(height=height, showlegend=False))
    fig = _base_axes(fig, xgrid=False)
    return fig


# ── 3. Scope donut ──────────────────────────────────────────────────────────
def scope_donut(scope1: float, scope2: float, scope3: float = 0, height: int = 280) -> go.Figure:
    labels = ["Scope 1 (Direct)", "Scope 2 (Indirect)", "Scope 3 (Value Chain)"]
    values = [scope1, scope2, scope3]
    palette = [COLORS["danger"], COLORS["warning"], T["primary_color"]]

    if scope3 == 0:
        labels = labels[:2]; values = values[:2]; palette = palette[:2]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.62,
        marker=dict(colors=palette, line=dict(color="white", width=2)),
        textinfo="percent",
        textfont=dict(size=11, family=T["font_family"]),
        hovertemplate="<b>%{label}</b><br>%{value:,.1f} tCO₂e (%{percent})<extra></extra>",
    ))

    total = sum(values)
    fig.add_annotation(
        text=f"<b>{total:,.0f}</b><br><span style='font-size:11px'>tCO₂e</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#1F2937", family=T["font_family"]),
        align="center",
    )

    fig.update_layout(**_base_layout(height=height,
                                     legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.08,
                                                 font=dict(size=11, family=T["font_family"]))))
    return fig


# ── 4. Category donut ───────────────────────────────────────────────────────
def category_donut(categories: dict, height: int = 260) -> go.Figure:
    labels = list(categories.keys())
    values = list(categories.values())

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=T["palette"], line=dict(color="white", width=2)),
        textinfo="percent+label",
        textfont=dict(size=10, family=T["font_family"]),
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(height=height, showlegend=False))
    return fig


# ── 5. Benchmark bar ────────────────────────────────────────────────────────
def benchmark_bar(intensity: float, benchmarks, sector: str = "", height: int = 300) -> go.Figure:
    """benchmarks can be a dict {sector: value} or a single float benchmark value."""
    from config.settings import INDUSTRY_BENCHMARKS as _IB
    if isinstance(benchmarks, dict):
        sectors = list(benchmarks.keys())
        values  = list(benchmarks.values())
    elif isinstance(benchmarks, (int, float)):
        # Called as (intensity, bench_float, sector_name)
        # Show all sectors, highlight the selected one
        sectors = list(_IB.keys())
        values  = list(_IB.values())
    else:
        sectors = list(_IB.keys())
        values  = list(_IB.values())
    bar_colors = [COLORS["danger"] if v < intensity else T["primary_color"] for v in values]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=sectors, y=values,
        name="Industry Benchmark",
        marker=dict(color=bar_colors, cornerradius=4, opacity=0.65),
        hovertemplate="<b>%{x}</b><br>Benchmark: %{y} kg CO₂e/m²<extra></extra>",
    ))

    fig.add_hline(
        y=intensity,
        line_color=COLORS["accent"],
        line_width=2,
        line_dash="solid",
        annotation_text=f" Your intensity: {intensity:.1f} kg/m²",
        annotation_font=dict(size=11, color=COLORS["accent"], family=T["font_family"]),
        annotation_position="top left",
    )

    fig.update_layout(**_base_layout(height=height, showlegend=False))
    fig = _base_axes(fig, xgrid=False)
    return fig


# ── 6. Forecast line ────────────────────────────────────────────────────────
def forecast_line(df: pd.DataFrame, forecast_val: float,
                  trendline: np.ndarray, height: int = 320) -> go.Figure:
    n = len(df)
    months = list(df["Month"]) + [f"Forecast"]
    actuals = list(df["Emission"]) + [None]
    preds   = list(trendline) + [forecast_val]

    fig = go.Figure()

    # Actual
    fig.add_trace(go.Scatter(
        x=df["Month"], y=df["Emission"],
        name="Actual",
        mode="lines+markers",
        line=dict(color=T["primary_color"], width=2.5, shape="spline", smoothing=0.7),
        marker=dict(size=5, color=T["primary_color"]),
        hovertemplate="<b>%{x}</b><br>Actual: %{y:,.1f}<extra></extra>",
    ))

    # Trendline
    fig.add_trace(go.Scatter(
        x=df["Month"], y=trendline,
        name="Trend",
        mode="lines",
        line=dict(color="#9CA3AF", width=1.5, dash="dot"),
        hoverinfo="skip",
    ))

    # Forecast point
    last_month = df["Month"].iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last_month, "Forecast +1"],
        y=[df["Emission"].iloc[-1], forecast_val],
        name="Forecast",
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=2.5, dash="dash"),
        marker=dict(size=8, color=COLORS["accent"], symbol="diamond"),
        hovertemplate="<b>%{x}</b><br>Forecast: %{y:,.1f}<extra></extra>",
    ))

    fig.update_layout(**_base_layout(height=height))
    fig = _base_axes(fig)
    return fig


# ── 7. Correlation scatter ──────────────────────────────────────────────────
def correlation_scatter(df: pd.DataFrame,
                        x_col: str, y_col: str,
                        x_label: str = "", y_label: str = "",
                        height: int = 280) -> go.Figure:
    fig = go.Figure()

    x = df[x_col].dropna()
    y = df[y_col].dropna()
    # Align index
    common = x.index.intersection(y.index)
    x, y = x[common], y[common]

    # Scatter points
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="markers",
        marker=dict(color=T["primary_color"], size=8, opacity=0.7),
        showlegend=False,
        hovertemplate=f"<b>{x_label or x_col}</b>: %{{x}}<br><b>{y_label or y_col}</b>: %{{y}}<extra></extra>",
    ))

    # Numpy OLS trendline (no statsmodels needed)
    if len(x) >= 2:
        coeffs = np.polyfit(x, y, 1)
        x_sorted = np.linspace(x.min(), x.max(), 100)
        y_trend  = np.polyval(coeffs, x_sorted)
        fig.add_trace(go.Scatter(
            x=x_sorted, y=y_trend,
            mode="lines",
            line=dict(color=COLORS["accent"], width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        **_base_layout(height=height, showlegend=False),
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or y_col,
    )
    fig = _base_axes(fig)
    return fig


# ── 8. Carbon stock area ────────────────────────────────────────────────────
def carbon_stock_area(years: list, values: list, height: int = 280) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=years, y=values,
        mode="lines+markers",
        line=dict(color=T["primary_color"], width=3, shape="spline", smoothing=0.8),
        marker=dict(size=7, color=T["primary_color"],
                    line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor="rgba(45,122,79,0.10)",
        hovertemplate="<b>%{x}</b><br>%{y:.1f} Mg C/ha<extra></extra>",
    ))
    fig.update_layout(**_base_layout(height=height, showlegend=False))
    fig = _base_axes(fig)
    return fig


# ── 9. Risk gauge ───────────────────────────────────────────────────────────
def risk_gauge(probability: float, label: str, height: int = 200) -> go.Figure:
    color = (COLORS["success"] if probability < 0.35
             else COLORS["warning"] if probability < 0.65
             else COLORS["danger"])

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=probability * 100,
        number={"suffix": "%", "font": {"size": 26, "color": "#1F2937", "family": T["font_family"]}},
        title={"text": label, "font": {"size": 12, "color": "#6B7280", "family": T["font_family"]}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#D1D5DB",
                     "tickfont": {"size": 10}},
            "bar":  {"color": color, "thickness": 0.2},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  35], "color": "#D1FAE5"},
                {"range": [35, 65], "color": "#FEF3C7"},
                {"range": [65, 100], "color": "#FEE2E2"},
            ],
        },
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=T["font_family"]),
    )
    return fig
