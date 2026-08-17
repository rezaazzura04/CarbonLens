"""CarbonLens V8 — KPI summary table component."""
from __future__ import annotations
import streamlit as st
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD
from components.theme.colors import BORDER, TEXT_MUTED, TEXT_PRIMARY


def kpi_table(rows: list, title: str = "") -> None:
    """
    Render a styled metric/KPI summary table.

    Parameters
    ----------
    rows  : list of dicts with keys: metric, value, unit (opt), status (opt), note (opt)
    title : Optional section title above the table.
    """
    if not rows:
        st.caption("No metrics available.")
        return

    if title:
        st.markdown(
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'text-transform:uppercase;letter-spacing:0.8px;'
            f'color:{TEXT_MUTED};margin-bottom:6px;">{title}</div>',
            unsafe_allow_html=True,
        )

    # Header
    st.markdown(
        f'<div style="display:grid;grid-template-columns:2fr 1.5fr 1fr 2fr;'
        f'gap:4px;padding:6px 4px;border-bottom:2px solid {BORDER};'
        f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:0.8px;color:{TEXT_MUTED};">'
        f'<div>Metric</div><div>Value</div><div>Unit</div><div>Note</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    status_colors = {
        "good":    "#059669", "warning": "#D97706",
        "bad":     "#DC2626", "neutral": "#64748B",
    }

    for i, row in enumerate(rows):
        bg     = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        status = row.get("status", "neutral")
        val_color = status_colors.get(status, status_colors["neutral"])
        note   = row.get("note", "")
        unit   = row.get("unit", "")
        metric = row.get("metric", "")
        value  = row.get("value", "--")

        st.markdown(
            f'<div style="display:grid;grid-template-columns:2fr 1.5fr 1fr 2fr;'
            f'gap:4px;padding:7px 4px;background:{bg};'
            f'border-bottom:1px solid #F1F5F9;font-size:{SIZE_BASE};'
            f'color:{TEXT_PRIMARY};">'
            f'<div style="font-weight:{WEIGHT_BOLD};">{metric}</div>'
            f'<div style="color:{val_color};font-weight:{WEIGHT_BOLD};">{value}</div>'
            f'<div style="color:{TEXT_MUTED};">{unit}</div>'
            f'<div style="color:{TEXT_MUTED};font-size:{SIZE_SM};">{note}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
