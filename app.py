"""
CarbonLens — Application entry point.

PORTFOLIO / PRE-COMMERCIAL MODE — no login gate.
This build is a research/portfolio artefact, not a commercial multi-tenant
deployment, so the app always opens directly to the Home (Executive Summary)
screen — no authentication step stands between opening the app and using it.

TWO-MODE ARCHITECTURE (the third, login-gated mode has been removed — see
services/auth_service.py's module docstring for how to reintroduce it later
if/when this becomes a real multi-user commercial deployment):

  MODE 1 — DEMO (demo_mode_enabled=True)
    → Demo User (analyst) + Demo Organisation + Demo Dataset

  MODE 2 — LOCAL REAL ORG (demo_mode_enabled=False)
    → Local analyst permissions + Real org setup + Real CSV upload

Architecture: app.py → state_service → repository (never directly)
"""
from __future__ import annotations
import importlib
import logging
import streamlit as st

logging.basicConfig(
    level  = logging.INFO,
    format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt= "%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("carbonlens.app")

import pathlib
_ASSETS_DIR = pathlib.Path(__file__).parent / "assets"

st.set_page_config(
    page_title          = "CarbonLens",
    page_icon           = str(_ASSETS_DIR / "favicon.png"),
    layout              = "wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Application root — called every Streamlit render cycle."""
    _init_session()

    from components.theme.layout import inject_global_css
    inject_global_css()

    # No login gate: always resolve a local identity and go straight to Home.
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
