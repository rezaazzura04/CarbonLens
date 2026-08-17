"""CarbonLens V8 — Data Quality flagged fields table component."""
from __future__ import annotations
import streamlit as st
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD
from components.theme.colors import BORDER, TEXT_MUTED, TEXT_PRIMARY


SEV_STYLES = {
    "high":   ("#DC2626", "#FEE2E2"),
    "medium": ("#D97706", "#FEF3C7"),
    "low":    ("#0891B2", "#CFFAFE"),
}


def data_quality_flags_table(flags: list) -> None:
    """
    Render the flagged fields table for the Data Quality page.

    Parameters
    ----------
    flags : list of FlaggedField dicts — pre-fetched from DataQualityScore.
    """
    if not flags:
        st.markdown(
            '<div style="text-align:center;padding:20px;color:#94A3B8;">'
            '✓  No data quality issues detected.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="display:grid;grid-template-columns:70px 120px 1fr 1fr;'
        f'gap:4px;padding:6px 4px;border-bottom:2px solid {BORDER};'
        f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:0.8px;color:{TEXT_MUTED};">'
        f'<div>Severity</div><div>Field</div><div>Issue</div><div>Suggested Action</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for i, flag in enumerate(flags):
        bg  = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        sev = flag.get("severity", "low")
        sfg, sbg = SEV_STYLES.get(sev, SEV_STYLES["low"])

        st.markdown(
            f'<div style="display:grid;grid-template-columns:70px 120px 1fr 1fr;'
            f'gap:4px;padding:7px 4px;background:{bg};'
            f'border-bottom:1px solid #F1F5F9;font-size:{SIZE_SM};color:{TEXT_PRIMARY};">'
            f'<div><span style="background:{sbg};color:{sfg};font-size:{SIZE_XS};'
            f'font-weight:{WEIGHT_BOLD};padding:1px 6px;border-radius:10px;">'
            f'{sev.upper()}</span></div>'
            f'<div style="font-weight:{WEIGHT_BOLD};font-family:monospace;">'
            f'{flag.get("field_name","")}</div>'
            f'<div style="color:{TEXT_MUTED};">{flag.get("description","")}</div>'
            f'<div style="color:#0891B2;">{flag.get("suggested_action","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
