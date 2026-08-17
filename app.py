"""
CarbonLens V8 — Application entry point.

THREE-MODE ARCHITECTURE:

  MODE 1 — DEMO (CARBONLENS_AUTH_REQUIRED=false, demo_mode_enabled=True)
    → Demo User (analyst) + Demo Organisation + Demo Dataset

  MODE 2 — LOCAL REAL ORG (CARBONLENS_AUTH_REQUIRED=false, demo_mode_enabled=False)
    → Local analyst permissions + Real org setup + Real CSV upload

  MODE 3 — AUTHENTICATED PRODUCTION (CARBONLENS_AUTH_REQUIRED=true)
    → Login required + Real user + RBAC enforced

These three states are kept SEPARATE.
Architecture: app.py → state_service → repository (never directly)
"""
from __future__ import annotations
import importlib
import logging
import os
import streamlit as st

logging.basicConfig(
    level  = logging.INFO,
    format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt= "%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("carbonlens.app")

st.set_page_config(
    page_title          = "CarbonLens V8",
    page_icon           = "◉",
    layout              = "wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Application root — called every Streamlit render cycle."""
    _init_session()

    from components.theme.layout import inject_global_css
    inject_global_css()

    auth_required = os.environ.get("CARBONLENS_AUTH_REQUIRED", "false").lower() == "true"

    # ── MODE 3: Authenticated Production ─────────────────────────────────────
    if auth_required:
        from services.auth_service import is_authenticated
        if not is_authenticated():
            _render_login()
            return
        # Real authenticated user — demo mode must never run
        import services.state_service as svc
        _render_main(svc)
        return

    # ── MODE 1 or 2: Login-free (demo or local-real-org) ─────────────────────
    from services.auth_service import is_authenticated, init_demo_mode
    from services.demo_service  import (
        init_demo_organisation, is_demo_mode_active, enable_demo_mode, flag_was_set,
    )

    # Initialise a local user identity if none exists yet
    if not is_authenticated():
        init_demo_mode()
        # On first launch with no existing flag, default to Demo Mode
        if not flag_was_set():
            enable_demo_mode()

    # Demo Mode: only when the explicit flag is True
    if is_demo_mode_active():
        init_demo_organisation()   # idempotent — safe every render

    import services.state_service as svc
    _render_main(svc)


def _render_main(svc) -> None:
    """Render sidebar, resolve routing, dispatch to destination."""
    from components.sidebar_nav import render_sidebar
    render_sidebar()

    from services.demo_service import is_demo_mode_active
    demo_active = is_demo_mode_active()

    org = svc.get_active_organisation()
    org_ready = svc.is_onboarding_complete() and svc.is_org_setup(org)

    if not org_ready and not demo_active:
        # MODE 2: local-real-org mode — show onboarding wizard
        _route_to("onboarding")
        return

    _route_to(svc.get_active_page())


# ─────────────────────────────────────────────────────────────────────────────

def _init_session() -> None:
    from state.session import init
    init()


def _render_login() -> None:
    """Full login UI for MODE 3 (CARBONLENS_AUTH_REQUIRED=true)."""
    st.markdown(
        '<div style="max-width:420px;margin:80px auto 0;text-align:center;">'
        '<div style="font-size:28px;font-weight:800;color:#0F172A;letter-spacing:-1px;">'
        '◉ CarbonLens</div>'
        '<div style="font-size:12px;color:#64748B;margin-top:4px;">'
        'ESG & Carbon Intelligence Platform · V8</div>'
        '<div style="font-size:11px;color:#D97706;margin-top:6px;'
        'background:#FEF3C7;border-radius:6px;padding:4px 10px;">'
        'Authentication required — CARBONLENS_AUTH_REQUIRED=true</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login_form", clear_on_submit=False):
            username  = st.text_input("Username", placeholder="Enter username", key="login_u")
            password  = st.text_input("Password", type="password",
                                      placeholder="Enter password", key="login_p")
            submitted = st.form_submit_button("Sign In", type="primary",
                                              use_container_width=True)
        if submitted:
            from services.auth_service import login
            user = login(username, password)
            if user:
                log.info(f"Login: {username!r}")
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.caption("Contact your administrator for credentials.")


def _route_to(destination: str) -> None:
    """Lazy-import and call render() for a destination."""
    import services.state_service as svc
    from config.constants import APPROVED_DESTINATIONS, DEFAULT_DESTINATION

    if destination == "onboarding":
        try:
            from pages.onboarding.page import render as onboard_render
            onboard_render()
        except Exception as exc:
            log.error(f"Onboarding render failed: {exc}", exc_info=True)
            from components.ui import error_state
            error_state("Onboarding Error", str(exc))
        return

    if destination not in APPROVED_DESTINATIONS:
        log.warning(f"Unknown destination {destination!r} → executive_summary")
        destination = DEFAULT_DESTINATION
        svc.navigate_to(destination)

    try:
        mod = importlib.import_module(f"pages.{destination}.page")
        mod.render()
    except NotImplementedError:
        from components.ui import page_header, empty_state
        page_header(destination.replace("_", " ").title(), badge="Scheduled", badge_type="yellow")
        empty_state("◐", "Coming in a future sprint", "This destination is scheduled.")
    except Exception as exc:
        log.error(f"Page render failed [{destination}]: {exc}", exc_info=True)
        from components.ui import error_state
        error_state("Page Error",
                    f"Could not render {destination.replace('_',' ').title()}.",
                    str(exc))


if __name__ == "__main__":
    main()
else:
    main()
