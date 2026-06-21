"""
CarbonLens V7 — Authentication & Role-Based Access
Uses streamlit-authenticator. Falls back gracefully if not installed.
Roles: admin (full access), analyst (no export/reporting edit), viewer (read-only).
"""

from __future__ import annotations
import streamlit as st
import hashlib, json, os, datetime
from pathlib import Path

_AUTH_FILE = Path(__file__).parent.parent / "config" / "users.json"

# ── Password hashing ─────────────────────────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Default users (change passwords in production) ────────────────────────────
DEFAULT_USERS = {
    "admin": {
        "name":     "Administrator",
        "password": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
        "role":     "admin",
        "email":    "admin@carbonlens.io",
    },
    "analyst": {
        "name":     "ESG Analyst",
        "password": "20249749412d73a3f5799f6f1dcf910e7b4aa3ce4de133b1f8a63c044792a4e9",
        "role":     "analyst",
        "email":    "analyst@carbonlens.io",
    },
    "viewer": {
        "name":     "Viewer",
        "password": "65375049b9e4d7cad6c9ba286fdeb9394b28135a3e84136404cfccfdcc438894",
        "role":     "viewer",
        "email":    "viewer@carbonlens.io",
    },
}

ROLE_PERMISSIONS = {
    "admin":   {"can_upload", "can_export", "can_report", "can_manage_users",
                "can_edit_profile", "can_view_all"},
    "analyst": {"can_upload", "can_export", "can_view_all"},
    "viewer":  {"can_view_all"},
}

ROLE_COLORS  = {"admin": "#0EA5E9", "analyst": "#6366F1", "viewer": "#64748B"}
ROLE_LABELS  = {"admin": "Administrator", "analyst": "ESG Analyst", "viewer": "Viewer"}




def _load_users() -> dict:
    import streamlit as _st
    if "_cl_users_override" in _st.session_state:
        return _st.session_state["_cl_users_override"]
    if _AUTH_FILE.exists():
        try:
            return json.loads(_AUTH_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_USERS.copy()


def _save_users(users: dict):
    try:
        _AUTH_FILE.parent.mkdir(exist_ok=True)
        _AUTH_FILE.write_text(json.dumps(users, indent=2))
    except (OSError, PermissionError):
        import streamlit as _st
        _st.session_state["_cl_users_override"] = users


def is_authenticated() -> bool:
    if st.session_state.get("cl_auth_user"):
        return True
    # Session memory was cleared (e.g. mobile tab backgrounded / websocket
    # reconnect) — try to silently restore from the URL token so the user
    # isn't bounced back to the login screen on every reconnect.
    return _try_restore_session_from_query()


def current_user() -> dict | None:
    if not st.session_state.get("cl_auth_user"):
        _try_restore_session_from_query()
    return st.session_state.get("cl_auth_user")


def _try_restore_session_from_query() -> bool:
    """Restore login from a ?session=username:token URL param, set right
    after a successful login. Tokens are first 16 chars of the user's
    password hash — enough to validate without re-exposing the full hash."""
    try:
        token = st.query_params.get("session", "")
    except Exception:
        return False
    if not token or ":" not in token:
        return False
    username, short_token = token.split(":", 1)
    users = _load_users()
    if username not in users:
        return False
    expected = users[username]["password"][:16]
    if short_token != expected:
        return False
    user_data = dict(users[username])
    user_data["username"] = username
    st.session_state["cl_auth_user"] = user_data
    return True


def current_role() -> str:
    u = current_user()
    return u["role"] if u else "viewer"


def can(permission: str) -> bool:
    role = current_role()
    return permission in ROLE_PERMISSIONS.get(role, set())


def login_page():
    """Render login form. Returns True if just logged in."""
    st.markdown("""
    <div style="max-width:400px;margin:60px auto 0;">
        <div style="text-align:center;margin-bottom:32px;">
            <div style="font-size:40px;margin-bottom:8px;">🌊</div>
            <div style="font-size:26px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">CarbonLens</div>
            <div style="font-size:13px;color:#64748B;margin-top:4px;">Climate Intelligence Platform · V7</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_c, col_m, col_c2 = st.columns([1, 2, 1])
    with col_m:
        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:16px;
             padding:28px 24px;box-shadow:0 4px 24px rgba(14,165,233,0.1);">
            <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">Sign In</div>
            <div style="font-size:12px;color:#94A3B8;margin-bottom:20px;">
                Enter your credentials to access the platform</div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pw")
            submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

        if submitted:
            users = _load_users()
            if username in users and users[username]["password"] == _hash(password):
                user_data = dict(users[username])
                user_data["username"] = username
                st.session_state["cl_auth_user"] = user_data
                # Persist a short, non-sensitive session token in the URL so
                # mobile browsers (which frequently drop the websocket on
                # backgrounding) can silently restore login without forcing
                # the user to re-enter credentials from scratch.
                short_token = users[username]["password"][:16]
                st.query_params["session"] = f"{username}:{short_token}"
                _audit_log("login", username, "User logged in")
                st.success(f"Welcome, {user_data['name']}!")
                st.rerun()
                return True
            else:
                st.error("Invalid username or password.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center;margin-top:14px;font-size:11px;color:#94A3B8;">
            Demo credentials: analyst/analyst123 · viewer/viewer123
        </div>
        """, unsafe_allow_html=True)

    return False


def logout():
    user = current_user()
    if user:
        _audit_log("logout", user.get("username","?"), "User logged out")
    st.session_state.pop("cl_auth_user", None)
    try:
        if "session" in st.query_params:
            del st.query_params["session"]
    except Exception:
        pass
    st.rerun()


def user_badge_html() -> str:
    u = current_user()
    if not u:
        return ""
    role   = u.get("role","viewer")
    color  = ROLE_COLORS.get(role, "#64748B")
    label  = ROLE_LABELS.get(role, role.title())
    name   = u.get("name","User")[:18]
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:11px;'
            f'font-weight:600;padding:3px 10px;border-radius:20px;'
            f'background:{color}20;color:{color};border:1px solid {color}40;">'
            f'<span style="width:6px;height:6px;background:{color};border-radius:50%;'
            f'display:inline-block;"></span>{name} · {label}</span>')


# ── Audit Log ─────────────────────────────────────────────────────────────────
_LOG_FILE = Path(__file__).parent.parent / "config" / "audit_log.jsonl"

def _audit_log(action: str, user: str, detail: str = ""):
    try:
        _LOG_FILE.parent.mkdir(exist_ok=True)
        entry = {
            "ts":     datetime.datetime.now().isoformat(),
            "user":   user,
            "action": action,
            "detail": detail,
        }
        try:
            with open(_LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except (OSError, PermissionError):
            import streamlit as _st
            log = _st.session_state.get("_cl_audit_log", [])
            log.append(entry)
            _st.session_state["_cl_audit_log"] = log[-500:]
        # Keep in session state too
        if "audit_log" not in st.session_state:
            st.session_state["audit_log"] = []
        st.session_state["audit_log"].insert(0, entry)
        st.session_state["audit_log"] = st.session_state["audit_log"][:200]
    except Exception:
        pass


def log(action: str, detail: str = ""):
    u = current_user()
    _audit_log(action, u.get("username","?") if u else "anonymous", detail)


def get_audit_log(limit: int = 50) -> list:
    entries = list(st.session_state.get("audit_log", []))
    if not entries and _LOG_FILE.exists():
        try:
            lines = _LOG_FILE.read_text().strip().split("\n")
            entries = [json.loads(l) for l in reversed(lines) if l]
        except Exception:
            pass
    return entries[:limit]
