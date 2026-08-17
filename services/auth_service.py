"""
CarbonLens V8 — Authentication service.
Handles login, logout, session management, and RBAC enforcement.
"""
from __future__ import annotations
import hashlib
import logging
from typing import Optional
log = logging.getLogger("carbonlens.services.auth")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user credentials. Returns User dict on success, None on failure.
    Emits user_login audit event on success.
    """
    from repository.disk_repo import load_users
    from audit.writer import write_audit_event

    users = load_users()
    if username not in users:
        log.info(f"Login failed: unknown user {username!r}")
        return None

    user_data = users[username]
    if user_data.get("password_hash") != _hash_password(password):
        log.info(f"Login failed: wrong password for {username!r}")
        return None

    user = dict(user_data)
    user["username"] = username

    from repository.session_repo import set_current_user
    set_current_user(user)

    write_audit_event(
        event_type = "user_login",
        summary    = f"User {username} logged in",
        detail     = {"username": username, "role": user.get("role", "viewer")},
    )
    log.info(f"Login successful: {username!r} ({user.get('role')})")
    return user


def logout() -> None:
    """Clear the authenticated user from session. Emits user_logout event."""
    from repository.session_repo import get_current_user, set_current_user
    from audit.writer import write_audit_event

    user = get_current_user()
    username = user.get("username", "?") if user else "?"

    set_current_user(None)
    write_audit_event(
        event_type = "user_logout",
        summary    = f"User {username} logged out",
        detail     = {"username": username},
    )


def get_current_user() -> Optional[dict]:
    """Return the authenticated user dict or None."""
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
