"""
CarbonLens V8 — Navigation sidebar.
Renders logo, org switcher, 7-destination nav, user profile, and version indicator.
Reads active page from session_repo — the only permitted session read in components.
"""
from __future__ import annotations
import streamlit as st
from components.theme.colors import BRAND_ACCENT, BORDER, TEXT_MUTED, BG_CARD
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, SIZE_LG, WEIGHT_BOLD, WEIGHT_BLACK
from config.navigation import ROUTES


def render_sidebar() -> None:
    """Render the complete V8 navigation sidebar."""
    from repository.session_repo import (
        get_active_page, set_active_page,
        get_active_slot, set_active_slot,
    )
    from state.session import get_company_summary
    from services.auth_service import get_current_user, logout
    from components.theme.colors import page_accent

    with st.sidebar:
        _render_logo()
        # Demo Mode banner (shown only when is_demo_mode() is True)
        try:
            from services.auth_service import is_demo_mode
            if is_demo_mode():
                _render_demo_banner()
        except Exception:
            pass
        st.markdown(
            f'<div style="height:1px;background:{BORDER};margin:8px 0 12px;"></div>',
            unsafe_allow_html=True,
        )
        _render_org_switcher(get_active_slot, set_active_slot, get_company_summary)
        st.markdown(
            f'<div style="height:8px;"></div>', unsafe_allow_html=True,
        )
        _render_nav(get_active_page, set_active_page, page_accent)
        st.markdown(
            f'<div style="height:1px;background:{BORDER};margin:12px 0 8px;"></div>',
            unsafe_allow_html=True,
        )
        _render_user_footer(get_current_user, logout)
        _render_version()


def _render_logo() -> None:
    """Render CarbonLens wordmark and tagline."""
    st.markdown(
        f'<div style="padding:12px 0 4px;">'
        f'<div style="font-size:{SIZE_LG};font-weight:{WEIGHT_BLACK};'
        f'color:#0F172A;letter-spacing:-0.5px;">'
        f'◉ CarbonLens</div>'
        f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};margin-top:2px;">'
        f'ESG & Carbon Intelligence · V8</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_org_switcher(get_slot_fn, set_slot_fn, get_summary_fn) -> None:
    """Render the organisation slot selector."""
    companies   = get_summary_fn()
    active_slot = get_slot_fn()

    st.markdown(
        f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
        f'text-transform:uppercase;letter-spacing:0.8px;'
        f'color:{TEXT_MUTED};margin-bottom:4px;">Organisation</div>',
        unsafe_allow_html=True,
    )

    options = list(range(len(companies)))
    def _fmt(i: int) -> str:
        c = companies[i]
        prefix = "✓ " if c["setup"] else "○ "
        return f"{prefix}{c['name']}"

    selected = st.selectbox(
        "org",
        options       = options,
        format_func   = _fmt,
        index         = active_slot,
        key           = "sidebar_org_select",
        label_visibility = "collapsed",
    )
    if selected != active_slot:
        set_slot_fn(selected)
        st.rerun()


def _render_nav(get_page_fn, set_page_fn, accent_fn) -> None:
    """Render the 7-destination navigation list."""
    active_page = get_page_fn()

    for route in ROUTES:
        rid    = route["id"]
        label  = route["label"]
        icon   = route["icon"]
        accent, light = accent_fn(rid)
        is_active = rid == active_page

        if is_active:
            st.markdown(
                f'<div style="background:{light};border-left:3px solid {accent};'
                f'border-radius:6px;padding:8px 12px;margin:2px 0;'
                f'font-size:{SIZE_BASE};font-weight:{WEIGHT_BOLD};color:{accent};">'
                f'{icon}  {label}</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button(
                f"{icon}  {label}",
                key               = f"nav_{rid}",
                use_container_width = True,
            ):
                set_page_fn(rid)
                st.rerun()


def _render_user_footer(get_user_fn, logout_fn) -> None:
    """Render the signed-in user card and sign-out button."""
    user = get_user_fn()
    if not user:
        return

    role_colors = {
        "admin":   ("#059669", "#D1FAE5"),
        "analyst": ("#0891B2", "#CFFAFE"),
        "viewer":  ("#64748B", "#F1F5F9"),
    }
    role = user.get("role", "viewer")
    r_fg, r_bg = role_colors.get(role, role_colors["viewer"])

    st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid {BORDER};'
        f'border-radius:8px;padding:10px 12px;margin-bottom:6px;">'
        f'<div style="font-size:{SIZE_SM};font-weight:{WEIGHT_BOLD};'
        f'color:#0F172A;">{user.get("display_name", user.get("username",""))}</div>'
        f'<div style="margin-top:4px;">'
        f'<span style="background:{r_bg};color:{r_fg};font-size:{SIZE_XS};'
        f'font-weight:{WEIGHT_BOLD};padding:1px 7px;border-radius:10px;">'
        f'{role.title()}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign out", key="sidebar_signout", use_container_width=True):
        logout_fn()
        st.rerun()


def _render_version() -> None:
    """Render platform version and build label at the bottom of sidebar."""
    st.markdown(
        f'<div style="font-size:{SIZE_XS};color:{TEXT_MUTED};'
        f'text-align:center;padding:8px 0 4px;">'
        f'CarbonLens V8 · Phase 5-B · Universitas Brawijaya'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_demo_banner() -> None:
    """Render a clearly visible DEMO MODE banner in the sidebar."""
    st.markdown(
        f'<div style="background:#FEF3C7;border:1.5px solid #D97706;'
        f'border-radius:8px;padding:8px 12px;margin-bottom:4px;">'
        f'<div style="font-size:10px;font-weight:800;color:#92400E;'
        f'text-transform:uppercase;letter-spacing:1px;">⚠ DEMO MODE</div>'
        f'<div style="font-size:9px;color:#78350F;margin-top:2px;">'
        f'Demo Data — Not real organisational data</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("🏢  Set Up My Organisation", use_container_width=True,
                 key="sidebar_setup_real_org"):
        from services.demo_service import exit_demo_mode
        from repository.session_repo import set_active_page
        exit_demo_mode(slot=0)
        set_active_page("executive_summary")
        st.rerun()
