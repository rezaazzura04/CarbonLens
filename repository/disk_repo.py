"""
CarbonLens V8 — Disk (JSON file) repository.

Persists organisation profiles and computed state across browser sessions.
Implements the same interface that db_repo.py will implement for
SQLite/PostgreSQL — switching storage backends requires only replacing this module.
"""

from __future__ import annotations
import json
import logging
import pathlib
from typing import Any, Optional

log = logging.getLogger("carbonlens.repository.disk")

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"
_USERS_FILE = _CONFIG_DIR / "users.json"


def _org_file(slot: int) -> pathlib.Path:
    return _CONFIG_DIR / f"org_slot_{slot}.json"


def _state_file(org_id: str) -> pathlib.Path:
    return _CONFIG_DIR / f"state_{org_id[:8]}.json"


def _write(path: pathlib.Path, data: Any) -> bool:
    """Write JSON to path. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except (OSError, TypeError) as exc:
        log.warning(f"disk_repo write failed for {path}: {exc}")
        return False


def _read(path: pathlib.Path) -> Optional[Any]:
    """Read JSON from path. Returns None on failure or missing file."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"disk_repo read failed for {path}: {exc}")
    return None


# ── Organisation persistence ──────────────────────────────────────────────────

def save_organisation(org: dict, slot: int) -> bool:
    """
    Persist an Organisation dict for a slot index.
    Returns True on success, False on I/O failure.
    """
    return _write(_org_file(slot), org)


def load_organisation(slot: int) -> Optional[dict]:
    """Load a saved Organisation dict for a slot, or None if not found."""
    return _read(_org_file(slot))


def delete_organisation(slot: int) -> bool:
    """Remove the organisation file for a slot."""
    try:
        path = _org_file(slot)
        if path.exists():
            path.unlink()
        return True
    except OSError as exc:
        log.warning(f"disk_repo delete failed for slot {slot}: {exc}")
        return False


# ── ComputedState persistence ─────────────────────────────────────────────────

def save_computed_state(state: dict, org_id: str) -> bool:
    """
    Persist the latest ComputedState for an organisation.
    Only the most recent state is persisted to disk (full history is in audit log).
    """
    return _write(_state_file(org_id), state)


def load_computed_state(org_id: str) -> Optional[dict]:
    """Load the saved ComputedState for an organisation, or None."""
    return _read(_state_file(org_id))


# ── User registry ─────────────────────────────────────────────────────────────

def save_users(users: dict) -> bool:
    """Persist the full user registry."""
    return _write(_USERS_FILE, users)


def load_users() -> dict:
    """Load the user registry. Falls back to DEFAULT_USERS if file not found."""
    data = _read(_USERS_FILE)
    if data is None:
        from config.settings import DEFAULT_USERS
        log.info("users.json not found — using DEFAULT_USERS from settings")
        return DEFAULT_USERS
    return data
