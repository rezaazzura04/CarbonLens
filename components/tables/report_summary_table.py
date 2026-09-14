"""CarbonLens — Report summary table component."""
from __future__ import annotations
import streamlit as st
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, FONT_BODY
from components.theme.colors import BORDER, TEXT_MUTED, TEXT_PRIMARY, SUCCESS, ERROR, PILLAR_COLORS
from components.theme.icons import icon


def gri_coverage_table(gap_analysis: list) -> None:
    """
    Render the GRI disclosure gap analysis table.

    Parameters
    ----------
    gap_analysis : list of gap analysis dicts from gri_framework.run_gap_analysis().
                   Pre-computed by caller — never computed here.
    """
    if not gap_analysis:
        st.info("GRI gap analysis not available. Upload data to run disclosure check.")
        return

    pillar_filter = st.selectbox(
        "Filter by pillar", ["All", "E — Environmental", "S — Social", "G — Governance"],
        key="gri_pillar_filter",
    )
    sel_pillar = pillar_filter[0] if pillar_filter != "All" else None

    filtered = gap_analysis
    if sel_pillar:
        filtered = [r for r in gap_analysis if r.get("pillar") == sel_pillar]

    st.markdown(
        f'<div style="display:grid;grid-template-columns:100px 80px 1fr 80px;'
        f'gap:4px;padding:6px 4px;border-bottom:2px solid {BORDER};'
        f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:0.8px;color:{TEXT_MUTED};">'
        f'<div>GRI Code</div><div>Pillar</div><div>Indicator</div><div>Status</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for i, row in enumerate(filtered):
        bg      = "#FAFBF9" if i % 2 == 0 else "#FFFFFF"
        covered = row.get("covered", False)
        p       = row.get("pillar", "")
        p_color = PILLAR_COLORS.get(p, (TEXT_MUTED, ""))[0]
        status_html = (
            f'<span style="display:flex;align-items:center;gap:4px;color:{SUCCESS};font-weight:700;">'
            f'{icon("check", size=12, color=SUCCESS)}<span>Covered</span></span>'
            if covered else
            f'<span style="display:flex;align-items:center;gap:4px;color:{ERROR};">'
            f'{icon("x_circle", size=12, color=ERROR)}<span>Gap</span></span>'
        )

        st.markdown(
            f'<div style="display:grid;grid-template-columns:100px 80px 1fr 80px;'
            f'gap:4px;padding:7px 4px;background:{bg};align-items:center;'
            f'border-bottom:1px solid {BORDER};font-size:{SIZE_SM};color:{TEXT_PRIMARY};'
            f'font-family:{FONT_BODY};">'
            f'<div style="font-family:monospace;font-weight:{WEIGHT_BOLD};">'
            f'{row.get("standard","")}</div>'
            f'<div style="color:{p_color};font-weight:{WEIGHT_BOLD};">{p}</div>'
            f'<div>{row.get("title","")}</div>'
            f'<div>{status_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    n_covered = sum(1 for r in gap_analysis if r.get("covered"))
    st.caption(f"{n_covered} of {len(gap_analysis)} GRI indicators covered.")
