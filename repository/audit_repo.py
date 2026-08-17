"""
CarbonLens V8 — Audit log repository (append-only JSONL).

Enforces the write-once guarantee: once a line is written, it is never modified.
The log file grows indefinitely in Phase 4; rotation is implemented in Phase 6.
"""

from __future__ import annotations
import json
import logging
import pathlib
from typing import Optional

log = logging.getLogger("carbonlens.repository.audit")

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"
_LOG_FILE   = _CONFIG_DIR / "audit_log.jsonl"


def append(event: dict) -> bool:
    """
    Append one AuditEvent dict to the JSONL log file.

    WRITE-ONCE GUARANTEE: This function only appends. It never modifies
    existing lines. Any modification to this guarantee requires Architecture
    Review Board approval.

    Returns True on success; False on I/O failure (caller must handle fallback).
    """
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except (OSError, TypeError) as exc:
        log.warning(f"audit_repo append failed: {exc}")
        return False


def read(
    limit:        int           = 100,
    org_id:       Optional[str] = None,
    event_type:   Optional[str] = None,
    since:        Optional[str] = None,
    company_slot: Optional[int] = None,
) -> list[dict]:
    """
    Read audit events from JSONL in reverse-chronological order.

    Parameters
    ----------
    limit       : Maximum entries to return.
    org_id      : If provided, return only events from this organisation.
    event_type  : If provided, return only events of this type.
    since       : ISO date/timestamp lower bound (inclusive).
    company_slot: If provided, return only events from this slot index.

    Returns list of AuditEvent dicts, most recent first.
    Falls back to empty list on I/O failure.
    """
    entries: list[dict] = []
    try:
        if not _LOG_FILE.exists():
            return []
        lines = _LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Normalise legacy entries that used "action" instead of "event_type"
            if "event_type" not in entry and "action" in entry:
                entry["event_type"] = entry["action"]
                entry.setdefault("summary", str(entry.get("detail", "")))
                entry.setdefault("company_name", "")
                entry.setdefault("slot_index", 0)
                entry.setdefault("session_id", "")
                entry.setdefault("detail", {})
                entry.setdefault("state_version", None)
            # Apply filters
            if org_id and entry.get("org_id") != org_id:
                continue
            if event_type and entry.get("event_type") != event_type:
                continue
            if since and entry.get("ts", "") < since:
                continue
            if company_slot is not None and entry.get("slot_index") != company_slot:
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
    except OSError as exc:
        log.warning(f"audit_repo read failed: {exc}")
    return entries


def log_file_size_bytes() -> int:
    """Return current audit log file size in bytes. Used for rotation check."""
    try:
        return _LOG_FILE.stat().st_size if _LOG_FILE.exists() else 0
    except OSError:
        return 0
