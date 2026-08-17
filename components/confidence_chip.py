"""
CarbonLens V8 — Confidence chip component.
Renders ESG and Data Quality confidence indicators.
Pure presentation. Never calls services or performs calculations.

The two confidence domains MUST remain visually distinct:
  - domain="esg" : S/G disclosure ratio → Provisional / Substantive vocabulary
  - domain="dq"  : Dataset integrity    → High Quality / Moderate / Low vocabulary
"""
from __future__ import annotations
import streamlit as st
from components.theme.colors import confidence_color, semantic_color
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD
from components.theme.spacing import RADIUS_PILL, RADIUS_MD


def confidence_chip(
    confidence:     float,
    is_provisional: bool  = False,
    compact:        bool  = False,
    show_score:     bool  = True,
    domain:         str   = "dq",
    label_override: str   = "",
    tooltip:        str   = "",
) -> None:
    """
    Render an inline confidence chip.

    Parameters
    ----------
    confidence     : 0–100 blended confidence score.
    is_provisional : Amber override regardless of numeric value.
    compact        : Pill-only (no explanation text).
    show_score     : Whether to show the numeric percentage.
    domain         : "esg" | "dq" — controls vocabulary.
    label_override : Override the auto-generated label.
    tooltip        : Optional hover tooltip text.
    """
    txt, bg, border = confidence_color(confidence, is_provisional)
    label   = label_override or _label(confidence, is_provisional, domain)
    score_s = f"{confidence:.0f}%" if show_score else ""
    tip     = f'title="{tooltip}"' if tooltip else ""

    if compact:
        st.markdown(
            f'<span {tip} style="display:inline-block;background:{bg};color:{txt};'
            f'border:1px solid {border};border-radius:{RADIUS_PILL};'
            f'padding:2px 9px;font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};">'
            f'{label}{(" — " + score_s) if score_s else ""}</span>',
            unsafe_allow_html=True,
        )
    else:
        explanation = _explanation(confidence, is_provisional, domain)
        st.markdown(
            f'<div {tip} style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
            f'<span style="background:{bg};color:{txt};border:1px solid {border};'
            f'border-radius:{RADIUS_PILL};padding:3px 10px;'
            f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};">'
            f'{label}{(" — " + score_s) if score_s else ""}</span>'
            f'<span style="font-size:{SIZE_SM};color:#94A3B8;">{explanation}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def provisional_badge(label: str = "Provisional") -> None:
    """Render an amber Provisional badge (standalone)."""
    st.markdown(
        f'<span style="background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;'
        f'border-radius:{RADIUS_PILL};padding:2px 10px;font-size:{SIZE_XS};'
        f'font-weight:{WEIGHT_BOLD};">{label}</span>',
        unsafe_allow_html=True,
    )


def quality_band(dq: dict) -> None:
    """
    Render the four-part Data Quality confidence band (4-column layout).
    Accepts a DataQualityScore dict. Never computes values.
    """
    completeness = float(dq.get("completeness_score", 0))
    consistency  = float(dq.get("consistency_score",  100))
    val_status   = str(dq.get("validation_status",    "Fail"))
    confidence   = float(dq.get("confidence_score",   0))
    is_prov      = bool(dq.get("is_provisional",      True))

    def _sc(v: float) -> str:
        if v >= 80: return "#059669"
        if v >= 60: return "#D97706"
        return "#DC2626"

    val_col = {"Pass": "#059669", "Warning": "#D97706", "Fail": "#DC2626"}.get(
        val_status, "#DC2626"
    )
    txt, bg, brd = confidence_color(confidence, is_prov)
    conf_label   = _label(confidence, is_prov, "dq")

    cards = [
        ("Completeness",  f"{completeness:.0f}%", _sc(completeness), "Env + S/G coverage",     "#FFFFFF", "#E2E8F0"),
        ("Consistency",   f"{consistency:.0f}%",  _sc(consistency),  "Rows passing checks",    "#FFFFFF", "#E2E8F0"),
        ("Validation",    val_status,              val_col,           "Upload validation",       "#FFFFFF", "#E2E8F0"),
        ("Confidence",    f"{confidence:.0f}%",   txt,               conf_label,                bg,        brd),
    ]
    cols = st.columns(4)
    for col, (title, value, color, subtitle, card_bg, card_brd) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div style="background:{card_bg};border:1.5px solid {card_brd};'
                f'border-radius:12px;padding:14px 16px;">'
                f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                f'text-transform:uppercase;letter-spacing:0.8px;'
                f'color:#94A3B8;margin-bottom:4px;">{title}</div>'
                f'<div style="font-size:24px;font-weight:700;color:{color};">{value}</div>'
                f'<div style="font-size:{SIZE_SM};color:#64748B;margin-top:3px;">{subtitle}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def dual_confidence_row(esg_conf: float, esg_prov: bool, dq_conf: float, dq_prov: bool) -> None:
    """
    Render both confidence dimensions side-by-side in a two-column layout.
    Makes the dual-confidence architecture visible to the user.
    """
    col_esg, col_dq = st.columns(2)
    with col_esg:
        st.caption("Score Confidence (S/G Disclosure)")
        confidence_chip(esg_conf, esg_prov, domain="esg", show_score=True)
    with col_dq:
        st.caption("Data Quality Confidence")
        confidence_chip(dq_conf, dq_prov, domain="dq", show_score=True)


# ── Private helpers ───────────────────────────────────────────────────────────

def _label(score: float, provisional: bool, domain: str) -> str:
    if domain == "esg":
        if provisional: return "Provisional"
        if score >= 70: return "Substantive"
        return "Partial"
    else:
        if provisional: return "Insufficient Data"
        if score >= 80: return "High Quality"
        if score >= 60: return "Moderate Quality"
        return "Low Quality"


def _explanation(score: float, provisional: bool, domain: str) -> str:
    if domain == "esg":
        if provisional: return "Fewer than 50% of S/G indicators disclosed."
        if score >= 70: return "All key S/G indicators disclosed."
        return "Some S/G indicators missing — score partially estimated."
    else:
        if provisional: return "Dataset integrity requires improvement."
        if score >= 80: return "Dataset passes all quality checks."
        if score >= 60: return "Some quality improvements available."
        return "Material data quality issues — see Data Quality page."
