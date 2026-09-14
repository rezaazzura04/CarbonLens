"""
CarbonLens — Authentication service.

No login/password system exists in this build (portfolio / pre-commercial
deployment — see app.py's module docstring). This module handles session
identity (a single local identity, always analyst-level — see DEMO_USER /
init_demo_mode()) and RBAC permission checks against that identity.

get_current_user() / is_authenticated() / has_permission() /
require_permission() are the reusable RBAC boundary every page gates
mutating actions behind. There is no username/password verification
anywhere in this codebase.
"""
from __future__ import annotations
import logging
from typing import Optional
log = logging.getLogger("carbonlens.services.auth")


def get_current_user() -> Optional[dict]:
    """Return the current local identity dict, or None."""
    from repository.session_repo import get_current_user as _get
    return _get()


def is_authenticated() -> bool:
    """Return True if a user is currently authenticated."""
    return get_current_user() is not None


def has_permission(permission: str) -> bool:
    """Return True if the current user has the given permission."""
    from config.constants import ROLE_PERMISSIONS
    user = get_current_user()
    if not user:
        return False
    role = user.get("role", "viewer")
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str) -> None:
    """Raise PermissionError if the current user lacks the given permission."""
    if not has_permission(permission):
        user = get_current_user()
        role = user.get("role", "viewer") if user else "anonymous"
        raise PermissionError(
            f"Role {role!r} does not have permission: {permission!r}"
        )


# ── Demo / Local Mode entry ────────────────────────────────────────────────────

DEMO_USER: dict = {
    "username":     "demo_user",
    "display_name": "Demo Mode",
    "role":         "analyst",    # analyst: can view, upload, calculate, export
    "email":        "",
    "is_demo":      True,
}


def init_demo_mode() -> dict:
    """
    Initialise an explicit demo-mode session so the application can render
    without requiring user login.

    The demo identity is labelled 'Demo Mode' and is never confused with a
    real corporate user. RBAC remains active — the demo user has analyst
    permissions (view + upload + export, no user management).

    Returns the demo user dict that was placed in session.
    """
    try:
        from repository.session_repo import set_current_user
        set_current_user(DEMO_USER)
        log.info("Demo Mode initialised — analyst-level access, no login required")
    except Exception as exc:
        log.warning(f"init_demo_mode: could not persist demo user: {exc}")
    return DEMO_USER


def is_demo_mode() -> bool:
    """Return True if the current session is running as the demo identity."""
    user = get_current_user()
    return bool(user and user.get("is_demo", False))
