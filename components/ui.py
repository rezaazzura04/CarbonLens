"""
CarbonLens — Shared UI primitives.
Pure presentation layer. All components receive data as parameters.
Never calls services, calculations, or repository.
"""
from __future__ import annotations
import html
import streamlit as st
from components.theme.colors import (
    BRAND_DARK, BRAND_ACCENT, BRAND_ACCENT_LT, BRAND_PRIMARY_DARK, BRAND_LIME,
    BG_CARD, BORDER, TEXT_MUTED, TEXT_PRIMARY, TEXT_INVERSE,
    grade_color, semantic_color, page_accent,
)
from components.theme.spacing import (
    CARD_PADDING, RADIUS_MD, RADIUS_LG, RADIUS_PILL, SM, MD,
)
from components.theme.typography import (
    SIZE_XS, SIZE_SM, SIZE_BASE, SIZE_LG, SIZE_XL, SIZE_2XL,
    WEIGHT_BOLD, WEIGHT_BLACK, TRACKING_WIDE, FONT_BRAND, FONT_BODY,
)
from components.theme.icons import icon, STATUS_ICONS


# ── Page header ───────────────────────────────────────────────────────────────

def page_header(
    title:       str,
    subtitle:    str = "",
    badge:       str = "",
    badge_type:  str = "blue",
    destination: str = "",
) -> None:
    """
    Render the standard page header with accent border.

    Parameters
    ----------
    title       : Page title text.
    subtitle    : Optional descriptive subtitle.
    badge       : Optional badge label (e.g. "Phase 3").
    badge_type  : "blue"|"green"|"yellow"|"red"|"purple" — badge colour preset.
    destination : destination ID for accent colour lookup.

    A compact "Demo Mode" badge is appended automatically (never passed in
    by callers) whenever demo mode is active — this is the single place
    that decides Demo Mode visibility, so it never needs a large sidebar
    card and stays consistent across all 8 pages with zero per-page changes.
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

    demo_badge_html = ""
    try:
        from services.auth_service import is_demo_mode
        if is_demo_mode():
            dfg, dbg = semantic_color("warning")
            demo_badge_html = (
                f'<span style="background:{dbg};color:{dfg};font-size:{SIZE_XS};'
                f'font-weight:{WEIGHT_BOLD};padding:2px 9px;border-radius:{RADIUS_PILL};'
                f'margin-left:6px;vertical-align:middle;letter-spacing:0.4px;">'
                f'DEMO MODE</span>'
            )
    except Exception:
        pass

    # subtitle commonly carries the user-entered organisation name
    # (e.g. page_header(subtitle=f"{company} · {period}")) — escape it
    # here, at the point it enters unsafe_allow_html, rather than trusting
    # every caller to do so.
    subtitle_html = (
        f'<div style="font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:3px;">'
        f'{html.escape(subtitle)}</div>'
    ) if subtitle else ""

    st.markdown(
        f'<div style="border-left:4px solid {accent};padding:8px 0 8px 16px;'
        f'margin-bottom:20px;">'
        f'<div style="font-family:{FONT_BRAND};font-size:{SIZE_XL};font-weight:{WEIGHT_BLACK};'
        f'color:{BRAND_DARK};letter-spacing:-0.5px;">{title}{badge_html}{demo_badge_html}</div>'
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
    icon_name:    str  = "",
    filled:       bool = False,
) -> None:
    """Render a KPI metric card with optional delta, badge, and a small
    semantic Lucide icon in the top-right corner (matching the reference
    design's per-card icon treatment — muted, non-decorative, one per card).

    `filled=True` renders the "hero" dark-green variant (reserved for the
    single most prominent KPI on a page, e.g. Total GHG Emissions on
    Executive Summary) — light-on-dark instead of the default light card.
    Every other existing call site is unaffected: default is `filled=False`.
    """
    ac = accent or BRAND_ACCENT
    fg, bg = semantic_color({
        "green": "success", "yellow": "warning",
        "red": "error", "blue": "info",
    }.get(badge_type, "info"))

    if filled:
        # Light-on-dark badge tint: a semi-transparent white pill reads
        # clearly on the dark fill regardless of semantic colour, whereas
        # the light-mode fg/bg pair above (e.g. dark-green-on-pale-green)
        # would have poor contrast against BRAND_PRIMARY_DARK.
        badge_html = (
            f'<span style="background:rgba(255,255,255,0.18);color:#FFFFFF;font-size:{SIZE_XS};'
            f'font-weight:{WEIGHT_BOLD};padding:2px 8px;border-radius:{RADIUS_PILL};'
            f'margin-top:4px;display:inline-block;">{badge}</span>'
        ) if badge else ""
        delta_html = (
            f'<div style="font-size:{SIZE_SM};color:{BRAND_LIME};margin-top:2px;">'
            f'{delta}{" · " + delta_label if delta_label else ""}</div>'
        ) if delta else ""
        val_size = SIZE_XL if compact else SIZE_2XL
        icon_html = (
            f'<div style="position:absolute;top:14px;right:14px;">'
            f'{icon(icon_name, size=17, color="rgba(255,255,255,0.7)", stroke_width=1.75)}</div>'
        ) if icon_name else ""
        title_attr = f'title="{help_text}"' if help_text else ""
        st.markdown(
            f'<div {title_attr} style="background:{BRAND_PRIMARY_DARK};border:none;'
            f'border-radius:{RADIUS_LG};padding:{CARD_PADDING};position:relative;'
            f'box-shadow:0 1px 2px rgba(23,34,28,0.04);">'
            f'{icon_html}'
            f'<div style="font-family:{FONT_BODY};font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
            f'letter-spacing:{TRACKING_WIDE};color:{BRAND_LIME};margin-bottom:4px;'
            f'{"padding-right:22px;" if icon_name else ""}">{label}</div>'
            f'<div style="font-family:{FONT_BODY};font-size:{val_size};font-weight:{WEIGHT_BLACK};'
            f'color:#FFFFFF;">{value}</div>'
            f'{delta_html}{badge_html}</div>',
            unsafe_allow_html=True,
        )
        return

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
    icon_html = (
        f'<div style="position:absolute;top:14px;right:14px;">'
        f'{icon(icon_name, size=17, color=TEXT_MUTED, stroke_width=1.75)}</div>'
    ) if icon_name else ""

    title_attr = f'title="{help_text}"' if help_text else ""
    st.markdown(
        f'<div {title_attr} style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-radius:{RADIUS_LG};padding:{CARD_PADDING};position:relative;'
        f'box-shadow:0 1px 2px rgba(23,34,28,0.04);">'
        f'{icon_html}'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:{TRACKING_WIDE};color:{TEXT_MUTED};margin-bottom:4px;'
        f'{"padding-right:22px;" if icon_name else ""}">{label}</div>'
        f'<div style="font-family:{FONT_BODY};font-size:{val_size};font-weight:{WEIGHT_BLACK};'
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
    """
    Compact metric display without delta/badge.

    Uses the same card shell (radius, padding, shadow) as kpi_card() —
    previously this used a different radius (RADIUS_MD vs RADIUS_LG) and a
    hardcoded "12px 14px" padding instead of the shared CARD_PADDING token,
    so a metric_card sitting next to a kpi_card (e.g. Carbon Accounting,
    Data Quality) had visibly mismatched corners and padding despite both
    being "label + big value" cards. Aligned here so every card in the app
    shares one consistent shell regardless of which helper renders it.
    """
    col = color or BRAND_ACCENT
    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-radius:{RADIUS_LG};padding:{CARD_PADDING};'
        f'box-shadow:0 1px 2px rgba(23,34,28,0.04);">'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_XS};color:{TEXT_MUTED};'
        f'font-weight:{WEIGHT_BOLD};text-transform:uppercase;letter-spacing:{TRACKING_WIDE};">{label}</div>'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_XL};font-weight:{WEIGHT_BLACK};color:{col};'
        f'margin-top:4px;">{value}</div>'
        + (f'<div style="font-family:{FONT_BODY};font-size:{SIZE_SM};color:{TEXT_MUTED};margin-top:2px;">{unit}</div>' if unit else "")
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
    icon_name = STATUS_ICONS.get(variant, "info")
    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {fg};border-radius:{RADIUS_MD};'
        f'padding:10px 14px;margin:8px 0;display:flex;align-items:flex-start;gap:8px;">'
        f'<span style="flex-shrink:0;margin-top:1px;">{icon(icon_name, size=16, color=fg)}</span>'
        f'<span style="font-family:{FONT_BODY};font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">{message}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Empty, loading, error states ─────────────────────────────────────────────

def empty_state(
    icon_name: str,
    title:     str,
    message:   str,
    cta:       str = "",
) -> None:
    """
    Render a centred empty-state placeholder.
    `icon_name` is a components.theme.icons name (e.g. "lock", "upload",
    "database") — not an emoji.
    """
    st.markdown(
        f'<div style="text-align:center;padding:48px 24px;color:{TEXT_MUTED};">'
        f'<div style="margin-bottom:12px;display:flex;justify-content:center;">'
        f'{icon(icon_name, size=36, color=TEXT_MUTED, stroke_width=1.5)}</div>'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_LG};font-weight:{WEIGHT_BOLD};'
        f'color:{TEXT_PRIMARY};margin-bottom:6px;">{title}</div>'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_BASE};max-width:360px;margin:0 auto;">{message}</div>'
        + (f'<div style="font-family:{FONT_BODY};font-size:{SIZE_SM};font-weight:{WEIGHT_BOLD};'
           f'color:{BRAND_ACCENT};margin-top:10px;">{cta}</div>' if cta else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def loading_state(message: str = "Computing…") -> None:
    """Render a loading placeholder."""
    st.markdown(
        f'<div style="text-align:center;padding:32px 24px;color:{TEXT_MUTED};">'
        f'<div style="margin-bottom:8px;display:flex;justify-content:center;">'
        f'{icon("refresh", size=22, color=TEXT_MUTED)}</div>'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_BASE};">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def error_state(title: str, message: str, technical: str = "") -> None:
    """Render an error state with optional technical detail."""
    fg, bg = semantic_color("error")
    tech = (
        f'<div style="font-size:{SIZE_SM};font-family:monospace;'
        f'background:{BG_CARD};border:1px solid {fg};padding:8px;border-radius:{RADIUS_MD};'
        f'margin-top:8px;color:{fg};">{technical}</div>'
    ) if technical else ""
    st.markdown(
        f'<div style="background:{bg};border:1px solid {fg};'
        f'border-radius:{RADIUS_LG};padding:20px 24px;">'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_LG};font-weight:{WEIGHT_BOLD};'
        f'color:{fg};margin-bottom:4px;display:flex;align-items:center;gap:8px;">'
        f'{icon("x_circle", size=18, color=fg)}<span>{title}</span></div>'
        f'<div style="font-family:{FONT_BODY};font-size:{SIZE_BASE};color:{TEXT_PRIMARY};">{message}</div>'
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
        f'<div style="width:{p1:.1f}%;background:#037C38;" title="Scope 1: {p1:.1f}%"></div>'
        f'<div style="width:{p2:.1f}%;background:#6E9B7F;" title="Scope 2: {p2:.1f}%"></div>'
        f'<div style="width:{p3:.1f}%;background:#B7D77A;" title="Scope 3: {p3:.1f}%"></div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;margin-top:4px;font-size:{SIZE_XS};color:{TEXT_MUTED};">'
        f'<span style="color:#037C38;">\u25a0 Scope 1 {p1:.0f}%</span>'
        f'<span style="color:#6E9B7F;">\u25a0 Scope 2 {p2:.0f}%</span>'
        f'<span style="color:#B7D77A;">\u25a0 Scope 3 {p3:.0f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Spacer ────────────────────────────────────────────────────────────────────

def spacer(px: int = 16) -> None:
    """Insert a vertical spacer of given pixel height."""
    st.markdown(
        f'<div style="height:{px}px;"></div>', unsafe_allow_html=True,
    )
