"""
CarbonLens V8 — Provenance panel component.
Renders "How this was calculated" expanders.
Pure presentation. No service calls. No session_state access.
"""
from __future__ import annotations
from typing import TypedDict
import streamlit as st
from components.theme.colors import BORDER, TEXT_MUTED, TEXT_PRIMARY, BRAND_ACCENT
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD
from components.theme.spacing import RADIUS_MD


class ProvenanceRow(TypedDict):
    label:   str
    value:   str
    source:  str
    formula: str
    note:    str


def provenance_panel(
    title:             str,
    rows:              list,
    key:               str,
    expanded:          bool = False,
    methodology_note:  str  = "",
    show_download:     bool = False,
) -> None:
    """
    Render a collapsible provenance expander with a four-column data table.

    Parameters
    ----------
    title            : Display title for the expander header.
    rows             : list[ProvenanceRow] — all values pre-computed by caller.
    key              : Unique widget key (required — enforced by caller).
    expanded         : Whether the expander starts open.
    methodology_note : Optional footer methodology reference.
    show_download    : If True, show a CSV download button for the rows.
    """
    if not rows:
        return

    with st.expander(f"How {title} was calculated", expanded=expanded):
        # Column header row
        st.markdown(
            f'<div style="display:grid;grid-template-columns:2fr 1.5fr 2fr 2fr;'
            f'gap:4px;padding:4px 0;border-bottom:1.5px solid {BORDER};'
            f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
            f'letter-spacing:0.8px;color:{TEXT_MUTED};">'
            f'<div>Input</div><div>Value</div><div>Source</div><div>Notes</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for i, row in enumerate(rows):
            bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
            notes = ""
            if row.get("formula"):
                notes += f'<span style="color:#64748B;">{row["formula"]}</span>'
            if row.get("note"):
                sep    = "<br>" if notes else ""
                notes += f'{sep}<span style="color:#D97706;font-style:italic;">{row["note"]}</span>'

            st.markdown(
                f'<div style="display:grid;grid-template-columns:2fr 1.5fr 2fr 2fr;'
                f'gap:4px;padding:6px 4px;background:{bg};'
                f'border-bottom:1px solid #F1F5F9;font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">'
                f'<div style="font-weight:{WEIGHT_BOLD};">{row.get("label","")}</div>'
                f'<div style="font-family:monospace;">{row.get("value","")}</div>'
                f'<div style="color:#64748B;">{row.get("source","")}</div>'
                f'<div>{notes}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if methodology_note:
            st.markdown(
                f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};'
                f'margin-top:8px;padding-top:6px;border-top:1px solid #F1F5F9;">'
                f'Methodology: {methodology_note}</div>',
                unsafe_allow_html=True,
            )

        if show_download and rows:
            import csv, io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=["label","value","source","formula","note"])
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in ["label","value","source","formula","note"]})
            st.download_button(
                "Download provenance as CSV",
                data      = buf.getvalue(),
                file_name = f"{title.replace(' ','_')}_provenance.csv",
                mime      = "text/csv",
                key       = f"{key}_dl",
            )


def methodology_footnote(version: str = "V8-Phase4", gri: str = "GRI 2021") -> None:
    """Render a compact methodology footer note."""
    st.markdown(
        f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};margin-top:12px;">'
        f'Methodology: CarbonLens {version} · {gri} aligned · '
        f'Not GRI-verified or ISO 14064 certified.</div>',
        unsafe_allow_html=True,
    )


def emission_factor_footnote(source: str = "IPCC 2006 + AR6 GWP100") -> None:
    """Render a compact emission factor source footnote."""
    st.markdown(
        f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};margin-top:4px;">'
        f'Emission factors: {source}</div>',
        unsafe_allow_html=True,
    )
