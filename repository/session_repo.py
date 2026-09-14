"""
CarbonLens — Session repository.

The ONLY module permitted to call st.session_state directly.
Every session state access in the platform goes through this module.
No other module may import streamlit and read/write session_state.
"""

from __future__ import annotations
import logging
from typing import Any, Optional

log = logging.getLogger("carbonlens.repository.session")

_SLOT_PREFIX = "cl_slot"         # Namespace prefix: cl_slot_0_key
_GLOBAL_PREFIX = "cl_global"     # Non-slot keys: cl_global_session_id


def _slot_key(slot: int, key: str) -> str:
    return f"{_SLOT_PREFIX}_{slot}_{key}"


def _global_key(key: str) -> str:
    return f"{_GLOBAL_PREFIX}_{key}"


# ── Global (non-slot) session operations ─────────────────────────────────────

def get_global(key: str, default: Any = None) -> Any:
    """Read a global (non-org-specific) session value."""
    import streamlit as st
    return st.session_state.get(_global_key(key), default)


def set_global(key: str, value: Any) -> None:
    """Write a global session value."""
    import streamlit as st
    st.session_state[_global_key(key)] = value


def get_active_slot() -> int:
    return int(get_global("active_slot", 0))


def set_active_slot(slot: int) -> None:
    set_global("active_slot", slot)


def get_active_page() -> str:
    from config.navigation import DEFAULT_DESTINATION
    return str(get_global("active_page", DEFAULT_DESTINATION))


def set_active_page(page: str) -> None:
    set_global("active_page", page)


# ── Onboarding wizard scratch state ────────────────────────────────────────────
# Global (non-slot) scratch space for the in-progress onboarding wizard.
# This is the sole owner of onboarding wizard state — pages/onboarding/page.py
# must go through these functions (via services.state_service) rather than
# touching st.session_state directly. Cleared once setup completes.

_ONBOARDING_KEY_PREFIX = "onboarding_field_"


def get_onboarding_field(field: str, default: Any = None) -> Any:
    """Read a single onboarding-wizard scratch field."""
    return get_global(f"{_ONBOARDING_KEY_PREFIX}{field}", default)


def set_onboarding_field(field: str, value: Any) -> None:
    """Write a single onboarding-wizard scratch field."""
    set_global(f"{_ONBOARDING_KEY_PREFIX}{field}", value)


def pop_onboarding_field(field: str, default: Any = None) -> Any:
    """Read-and-remove a single onboarding-wizard scratch field."""
    import streamlit as st
    return st.session_state.pop(_global_key(f"{_ONBOARDING_KEY_PREFIX}{field}"), default)


def clear_onboarding_fields() -> None:
    """Remove all onboarding-wizard scratch fields (profile + upload + step)."""
    import streamlit as st
    fields = ("company", "sector", "period", "province", "area", "employees",
              "df", "val_result", "step")
    for field in fields:
        st.session_state.pop(_global_key(f"{_ONBOARDING_KEY_PREFIX}{field}"), None)


def get_onboarding_step() -> int:
    """Return the current onboarding wizard step (1-3), default 1."""
    return int(get_global(f"{_ONBOARDING_KEY_PREFIX}step", 1))


def set_onboarding_step(step: int) -> None:
    """Set the current onboarding wizard step (1-3)."""
    set_global(f"{_ONBOARDING_KEY_PREFIX}step", step)


def get_session_id() -> str:
    import uuid
    sid = get_global("session_id")
    if not sid:
        sid = uuid.uuid4().hex[:8]
        set_global("session_id", sid)
    return sid


# ── Slot-namespaced operations ────────────────────────────────────────────────

def get(key: str, slot: Optional[int] = None, default: Any = None) -> Any:
    """Read a slot-namespaced value. Uses active slot if slot is None."""
    import streamlit as st
    if slot is None:
        slot = get_active_slot()
    return st.session_state.get(_slot_key(slot, key), default)


def set(key: str, value: Any, slot: Optional[int] = None) -> None:
    """Write a slot-namespaced value. Uses active slot if slot is None."""
    import streamlit as st
    if slot is None:
        slot = get_active_slot()
    st.session_state[_slot_key(slot, key)] = value


def clear_slot(slot: int) -> None:
    """Remove all keys for a given organisation slot."""
    import streamlit as st
    prefix = f"{_SLOT_PREFIX}_{slot}_"
    keys_to_remove = [k for k in st.session_state if k.startswith(prefix)]
    for k in keys_to_remove:
        del st.session_state[k]
    log.info(f"Cleared {len(keys_to_remove)} keys for slot {slot}")


# ── ComputedState storage ─────────────────────────────────────────────────────

def get_computed_state(slot: Optional[int] = None) -> Optional[dict]:
    """Return the serialised ComputedState dict for a slot, or None."""
    return get("computed_state", slot=slot)


def set_computed_state(state: dict, slot: Optional[int] = None) -> None:
    """Persist a ComputedState dict to the session for a slot."""
    set("computed_state", state, slot=slot)


def invalidate_computed_state(slot: Optional[int] = None) -> None:
    """Mark the ComputedState as stale so the next render triggers recomputation."""
    set("computed_state", None, slot=slot)


# ── Organisation storage ──────────────────────────────────────────────────────

def get_organisation(slot: int) -> Optional[dict]:
    """Return the Organisation dict for a slot, or None if not configured."""
    return get("organisation", slot=slot)


def set_organisation(org: dict, slot: int) -> None:
    """Persist an Organisation dict for a slot."""
    set("organisation", org, slot=slot)


# ── Upload / DataFrame ────────────────────────────────────────────────────────

def get_uploaded_df(slot: Optional[int] = None):
    """Return the active pandas DataFrame or None."""
    return get("uploaded_df", slot=slot)


def set_uploaded_df(df, slot: Optional[int] = None) -> None:
    set("uploaded_df", df, slot=slot)


def get_validation_result(slot: Optional[int] = None) -> Optional[dict]:
    return get("validation_result", slot=slot)


def set_validation_result(result: dict, slot: Optional[int] = None) -> None:
    set("validation_result", result, slot=slot)


# ── Spatial / Land-Use Context (Phase 5-C, Experimental) ──────────────────────
# Slot-scoped like uploaded_df/validation_result — spatial context is
# location-specific per organisation, so switching org slots correctly
# resets the panel to unopened/unloaded rather than showing the previous
# org's location data.

def get_spatial_context(slot: Optional[int] = None) -> Optional[dict]:
    """Return the last spatial query result for a slot, or None if never run."""
    return get("spatial_context", slot=slot)


def set_spatial_context(data: dict, slot: Optional[int] = None) -> None:
    """Persist a spatial query result for a slot."""
    set("spatial_context", data, slot=slot)


def is_spatial_panel_open(slot: Optional[int] = None) -> bool:
    """
    Return True if the user has explicitly opted into loading the Spatial
    Context tab for this slot. False by default and on every fresh slot —
    this is the lazy-load gate: the tab's expensive query must never fire
    just because the page rendered.
    """
    return bool(get("spatial_panel_open", slot=slot, default=False))


def set_spatial_panel_open(open_: bool, slot: Optional[int] = None) -> None:
    set("spatial_panel_open", bool(open_), slot=slot)


# ── Session audit log cache ───────────────────────────────────────────────────

def get_audit_cache() -> list:
    import streamlit as st
    return st.session_state.get("cl_audit_log", [])


def prepend_audit_event(event: dict, max_entries: int = 500) -> None:
    import streamlit as st
    log_list = st.session_state.get("cl_audit_log", [])
    log_list.insert(0, event)
    st.session_state["cl_audit_log"] = log_list[:max_entries]


# ── Authenticated user ────────────────────────────────────────────────────────

def get_current_user() -> Optional[dict]:
    import streamlit as st
    return st.session_state.get("cl_auth_user")


def set_current_user(user: Optional[dict]) -> None:
    import streamlit as st
    if user is None:
        st.session_state.pop("cl_auth_user", None)
    else:
        st.session_state["cl_auth_user"] = user


# ── Onboarding completion flags ───────────────────────────────────────────────

def is_onboarding_complete(slot: Optional[int] = None) -> bool:
    complete = get("onboarding_complete", slot=slot, default=False)
    done     = get("onboarding_done",     slot=slot, default=False)
    return bool(complete or done)


def mark_onboarding_complete(slot: Optional[int] = None) -> None:
    set("onboarding_complete", True, slot=slot)
    set("onboarding_done",     True, slot=slot)


# ── Phase 5-B Demo Mode flag ──────────────────────────────────────────────────
# Separate from authentication identity and from organisation setup state.
# Controls whether init_demo_organisation() runs.

_DEMO_MODE_KEY = "__carbonlens_demo_mode_enabled__"


def is_demo_mode_enabled() -> bool:
    """Return True if Demo Mode is explicitly enabled for this session."""
    try:
        import streamlit as st
        return bool(st.session_state.get(_DEMO_MODE_KEY, False))
    except Exception:
        return False


def set_demo_mode_enabled(enabled: bool) -> None:
    """Set or clear the Demo Mode flag for this session."""
    try:
        import streamlit as st
        st.session_state[_DEMO_MODE_KEY] = bool(enabled)
    except Exception as exc:
        # This is a state-machine transition, not cosmetic UI — losing it
        # silently would leave the app with no single source of truth for
        # which of the three modes is active (Phase 5-B Fix 9C).
        log.warning(f"set_demo_mode_enabled({enabled}) failed: {exc}")
