"""
CarbonLens V8 — Shared UI primitives.
Pure presentation layer. All components receive data as parameters.
Never calls services, calculations, or repository.
"""
from __future__ import annotations
import streamlit as st
from components.theme.colors import (
    BRAND_DARK, BRAND_ACCENT, BRAND_ACCENT_LT,
    BG_CARD, BORDER, TEXT_MUTED, TEXT_PRIMARY, TEXT_INVERSE,
    grade_color, semantic_color, page_accent,
)
from components.theme.spacing import (
    CARD_PADDING, RADIUS_MD, RADIUS_LG, RADIUS_PILL, SM, MD,
)
from components.theme.typography import (
    SIZE_XS, SIZE_SM, SIZE_BASE, SIZE_LG, SIZE_XL, SIZE_2XL,
    WEIGHT_BOLD, WEIGHT_BLACK, TRACKING_WIDE,
)


# ── Page header ───────────────────────────────────────────────────────────────

def page_header(
    title:       str,
    subtitle:    str = "",
    badge:       str = "",
    badge_type:  str = "blue",
    destination: str = "",
) -> None:
    """
    Render the standard V8 page header with accent border.

    Parameters
    ----------
    title       : Page title text.
    subtitle    : Optional descriptive subtitle.
    badge       : Optional badge label (e.g. "Phase 3").
    badge_type  : "blue"|"green"|"yellow"|"red"|"purple" — badge colour preset.
    destination : V8 destination ID for accent colour lookup.
    """
    accent, _lt = page_accent(destination) if destination else (BRAND_ACCENT, BRAND_ACCENT_LT)
    fg, bg = semantic_color({
        "green": "success", "yellow": "warning",
        "red": "error", "purple": "info",
    }.get(badge_type, "info"))

    badge_html = (
        f'<span style="background:{bg};color:{fg};font-size:{SIZE_XS};'
        f'font-weight:{WEIGHT_BOLD};padding:2px 9px;border-radius:{RADIUS_PILL};'
        f'margin-left:8px;vertical-align:middle;">{badge}</span>'
    ) if badge else ""
    subtitle_html = (
        f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:3px;">'
        f'{subtitle}</div>'
    ) if subtitle else ""

    st.markdown(
        f'<div style="border-left:4px solid {accent};padding:8px 0 8px 16px;'
        f'margin-bottom:20px;">'
        f'<div style="font-size:{SIZE_XL};font-weight:{WEIGHT_BLACK};'
        f'color:{BRAND_DARK};letter-spacing:-0.5px;">{title}{badge_html}</div>'
        f'{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


# ── KPI card ──────────────────────────────────────────────────────────────────

def kpi_card(
    label:        str,
    value:        str,
    delta:        str  = "",
    delta_label:  str  = "",
    badge:        str  = "",
    badge_type:   str  = "blue",
    help_text:    str  = "",
    accent:       str  = "",
    compact:      bool = False,
) -> None:
    """Render a KPI metric card with optional delta and badge."""
    ac = accent or BRAND_ACCENT
    fg, bg = semantic_color({
        "green": "success", "yellow": "warning",
        "red": "error", "blue": "info",
    }.get(badge_type, "info"))

    badge_html = (
        f'<span style="background:{bg};color:{fg};font-size:{SIZE_XS};'
        f'font-weight:{WEIGHT_BOLD};padding:2px 8px;border-radius:{RADIUS_PILL};'
        f'margin-top:4px;display:inline-block;">{badge}</span>'
    ) if badge else ""
    delta_html = (
        f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:2px;">'
        f'{delta}{" · " + delta_label if delta_label else ""}</div>'
    ) if delta else ""
    val_size = SIZE_XL if compact else SIZE_2XL

    title_attr = f'title="{help_text}"' if help_text else ""
    st.markdown(
        f'<div {title_attr} style="background:{BG_CARD};border:1.5px solid {BORDER};'
        f'border-radius:{RADIUS_LG};padding:{CARD_PADDING};">'
        f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:{TRACKING_WIDE};color:{TEXT_MUTED};margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:{val_size};font-weight:{WEIGHT_BLACK};'
        f'color:{TEXT_PRIMARY};">{value}</div>'
        f'{delta_html}{badge_html}</div>',
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    unit:  str = "",
    color: str = "",
) -> None:
    """Compact metric display without delta/badge."""
    col = color or BRAND_ACCENT
    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-radius:{RADIUS_MD};padding:12px 14px;">'
        f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};'
        f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};">{label}</div>'
        f'<div style="font-size:{SIZE_XL};font-weight:{WEIGHT_BLACK};color:{col};">'
        f'{value}</div>'
        + (f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};">{unit}</div>' if unit else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# ── Status badge ──────────────────────────────────────────────────────────────

def status_badge(
    label:   str,
    variant: str = "info",
    size:    str = "md",
) -> str:
    """Return an inline HTML status badge string."""
    fg, bg = semantic_color(variant)
    fs = SIZE_XS if size == "sm" else SIZE_SM
    return (
        f'<span style="background:{bg};color:{fg};font-size:{fs};'
        f'font-weight:{WEIGHT_BOLD};padding:2px 9px;'
        f'border-radius:{RADIUS_PILL};display:inline-block;">{label}</span>'
    )


def render_grade_badge(grade: str) -> None:
    """Render an ESG grade badge inline."""
    fg, bg = grade_color(grade)
    st.markdown(
        f'<span style="background:{bg};color:{fg};font-size:{SIZE_LG};'
        f'font-weight:{WEIGHT_BLACK};padding:4px 14px;border-radius:{RADIUS_PILL};">'
        f'{grade}</span>',
        unsafe_allow_html=True,
    )


# ── Section container ─────────────────────────────────────────────────────────

def section_container(title: str = "", accent: str = "") -> None:
    """Render a styled section header label."""
    ac = accent or BRAND_ACCENT
    if title:
        st.markdown(
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
            f'color:{ac};margin:20px 0 8px;">{title}</div>',
            unsafe_allow_html=True,
        )


# ── Information banners ───────────────────────────────────────────────────────

def info_banner(message: str, variant: str = "info", dismissible: bool = False) -> None:
    """Render an inline information banner (info/warning/error/success)."""
    fg, bg = semantic_color(variant)
    icons = {"info": "ℹ", "warning": "⚠", "error": "✕", "success": "✓"}
    icon = icons.get(variant, "ℹ")
    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {fg};border-radius:{RADIUS_MD};'
        f'padding:10px 14px;margin:8px 0;display:flex;align-items:flex-start;gap:8px;">'
        f'<span style="color:{fg};font-weight:{WEIGHT_BOLD};">{icon}</span>'
        f'<span style="font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">{message}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Empty, loading, error states ─────────────────────────────────────────────

def empty_state(
    icon:    str,
    title:   str,
    message: str,
    cta:     str = "",
) -> None:
    """Render a centred empty-state placeholder."""
    st.markdown(
        f'<div style="text-align:center;padding:48px 24px;color:{TEXT_MUTED};">'
        f'<div style="font-size:36px;margin-bottom:12px;">{icon}</div>'
        f'<div style="font-size:{SIZE_LG};font-weight:{WEIGHT_BOLD};'
        f'color:#475569;margin-bottom:6px;">{title}</div>'
        f'<div style="font-size:{SIZE_BASE};max-width:360px;margin:0 auto;">{message}</div>'
        + (f'<div style="font-size:{SIZE_SM};font-weight:{WEIGHT_BOLD};'
           f'color:{BRAND_ACCENT};margin-top:10px;">{cta}</div>' if cta else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def loading_state(message: str = "Computing…") -> None:
    """Render a loading placeholder."""
    st.markdown(
        f'<div style="text-align:center;padding:32px 24px;color:{TEXT_MUTED};">'
        f'<div style="font-size:24px;margin-bottom:8px;">⟳</div>'
        f'<div style="font-size:{SIZE_BASE};">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def error_state(title: str, message: str, technical: str = "") -> None:
    """Render an error state with optional technical detail."""
    fg, bg = semantic_color("error")
    tech = (
        f'<div style="font-size:{SIZE_SM};font-family:monospace;'
        f'background:#FEE2E2;padding:8px;border-radius:{RADIUS_MD};'
        f'margin-top:8px;color:#991B1B;">{technical}</div>'
    ) if technical else ""
    st.markdown(
        f'<div style="background:{bg};border:1.5px solid {fg};'
        f'border-radius:{RADIUS_LG};padding:20px 24px;">'
        f'<div style="font-size:{SIZE_LG};font-weight:{WEIGHT_BOLD};'
        f'color:{fg};margin-bottom:4px;">✕  {title}</div>'
        f'<div style="font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">{message}</div>'
        f'{tech}</div>',
        unsafe_allow_html=True,
    )


# ── Divider ───────────────────────────────────────────────────────────────────

def divider(label: str = "") -> None:
    """Render a horizontal divider with optional centred label."""
    if label:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin:16px 0;">'
            f'<div style="flex:1;height:1px;background:{BORDER};"></div>'
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:{TRACKING_WIDE};">'
            f'{label}</div>'
            f'<div style="flex:1;height:1px;background:{BORDER};"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="height:1px;background:{BORDER};margin:16px 0;"></div>',
            unsafe_allow_html=True,
        )


# ── Card grid ─────────────────────────────────────────────────────────────────

def card_grid(n: int = 4):
    """Return st.columns for a responsive KPI grid."""
    return st.columns(n)


def responsive_cols(ratios: list):
    """Return st.columns from a list of integer ratios."""
    return st.columns(ratios)


# ── Scope breakdown bar ───────────────────────────────────────────────────────

def scope_bar(scope1: float, scope2: float, scope3: float) -> None:
    """Render a proportional Scope 1/2/3 stacked bar."""
    total = scope1 + scope2 + scope3
    if total == 0:
        st.markdown(
            f'<div style="height:8px;background:{BORDER};border-radius:4px;"></div>',
            unsafe_allow_html=True,
        )
        return
    p1 = scope1 / total * 100
    p2 = scope2 / total * 100
    p3 = scope3 / total * 100
    st.markdown(
        f'<div style="height:8px;border-radius:4px;overflow:hidden;display:flex;gap:1px;">'
        f'<div style="width:{p1:.1f}%;background:#10B981;" title="Scope 1: {p1:.1f}%"></div>'
        f'<div style="width:{p2:.1f}%;background:#0EA5E9;" title="Scope 2: {p2:.1f}%"></div>'
        f'<div style="width:{p3:.1f}%;background:#6366F1;" title="Scope 3: {p3:.1f}%"></div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;margin-top:4px;font-size:{SIZE_XS};color:{TEXT_MUTED};">'
        f'<span>■ Scope 1 {p1:.0f}%</span>'
        f'<span style="color:#0EA5E9;">■ Scope 2 {p2:.0f}%</span>'
        f'<span style="color:#6366F1;">■ Scope 3 {p3:.0f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Spacer ────────────────────────────────────────────────────────────────────

def spacer(px: int = 16) -> None:
    """Insert a vertical spacer of given pixel height."""
    st.markdown(
        f'<div style="height:{px}px;"></div>', unsafe_allow_html=True,
    )
