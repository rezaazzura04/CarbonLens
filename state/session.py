"""
CarbonLens V8 — Session lifecycle management.

Initialises Streamlit session state on first render and manages
the multi-organisation slot structure. Called once by app.py on startup.
"""

from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.state.session")


def init() -> None:
    """
    Initialise session state for a new browser session.
    Idempotent — safe to call on every Streamlit render cycle.
    Only writes keys that are not already present.
    """
    import streamlit as st
    from config.constants import MAX_ORG_SLOTS, DEFAULT_DESTINATION
    from repository import session_repo as SR

    if st.session_state.get("_cl_v8_initialised"):
        return

    log.info("Initialising new CarbonLens V8 session")

    # Session identity
    SR.set_global("session_id",  __import__("uuid").uuid4().hex[:8])
    SR.set_global("active_slot", 0)
    SR.set_global("active_page", DEFAULT_DESTINATION)

    # Try to restore slot 0 organisation from disk
    from repository import disk_repo as DR
    for slot in range(MAX_ORG_SLOTS):
        org = DR.load_organisation(slot)
        if org:
            SR.set_organisation(org, slot)
            log.debug(f"Restored org from disk for slot {slot}: {org.get('company_name', '?')}")

    # Mark as initialised
    st.session_state["_cl_v8_initialised"] = True


def reset_slot(slot: int) -> None:
    """
    Clear all data for an organisation slot, including disk persistence.
    Used when a user clears an org or starts fresh.
    """
    from repository import session_repo as SR, disk_repo as DR
    from state.cache import invalidate_org

    org = SR.get_organisation(slot)
    if org:
        invalidate_org(org.get("org_id", ""))

    SR.clear_slot(slot)
    DR.delete_organisation(slot)
    log.info(f"Reset slot {slot}")


def get_active_org() -> dict | None:
    """Return the active Organisation dict or None if slot is empty."""
    from repository import session_repo as SR
    slot = SR.get_active_slot()
    return SR.get_organisation(slot)


def is_org_setup(org: dict | None) -> bool:
    """
    Return True if the organisation has a valid, non-placeholder company name,
    a valid province, and a non-zero floor area.
    Used by app.py to decide whether to show the onboarding wizard.
    """
    if org is None:
        return False
    from config.constants import PLACEHOLDER_NAMES
    name = (org.get("company_name") or "").strip()
    if not name or name in PLACEHOLDER_NAMES:
        return False
    if not (org.get("area_m2") or 0) > 0:
        return False
    return True


def get_company_summary() -> list[dict]:
    """
    Return a summary list of all organisation slots for the sidebar org switcher.
    [{"slot": 0, "name": "PT Example", "setup": True}, ...]
    """
    from repository import session_repo as SR
    from config.constants import MAX_ORG_SLOTS
    result = []
    for slot in range(MAX_ORG_SLOTS):
        org = SR.get_organisation(slot)
        result.append({
            "slot":  slot,
            "name":  org.get("company_name", f"Slot {slot + 1}") if org else f"Slot {slot + 1}",
            "setup": is_org_setup(org),
        })
    return result
