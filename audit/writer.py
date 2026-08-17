"""
CarbonLens V8 — Audit event writer.

write_audit_event() is the SINGLE write point for all audit events.
It is called exclusively from services/ — never from pages/ or components/.

Architecture rule: pages and components that trigger auditable actions must
call the relevant service, which then calls write_audit_event(). Direct calls
from pages are a violation of the audit architecture.
"""

from __future__ import annotations
import datetime
import logging
import uuid
from typing import Optional

log = logging.getLogger("carbonlens.audit.writer")


def write_audit_event(
    event_type: str,
    summary:    str,
    detail:     Optional[dict] = None,
    user:       Optional[str]  = None,
    org_id:     Optional[str]  = None,
    company_name: Optional[str] = None,
    slot_index: Optional[int]  = None,
    state_version: Optional[int] = None,
) -> Optional[dict]:
    """
    Write one audit event to the JSONL log and session cache.

    Parameters
    ----------
    event_type    : Must be one of APPROVED_EVENT_TYPES (13 defined types).
    summary       : One human-readable sentence describing what happened.
    detail        : Event-specific structured payload dict (optional).
    user          : Username. Auto-resolved from session if not provided.
    org_id        : Organisation ID. Auto-resolved from active session if not provided.
    company_name  : Org name at event time. Auto-resolved if not provided.
    slot_index    : Active slot index. Auto-resolved if not provided.
    state_version : ComputedState.version at time of event (if applicable).

    Returns the AuditEvent dict on success, None on failure.

    This function NEVER raises exceptions — audit failures must not break
    the calling workflow.
    """
    from config.constants import APPROVED_EVENT_TYPES, MAX_AUDIT_SESSION_ENTRIES

    try:
        # Validate event type
        if event_type not in APPROVED_EVENT_TYPES:
            log.warning(
                f"write_audit_event called with unapproved event_type: {event_type!r}. "
                f"Approved types: {sorted(APPROVED_EVENT_TYPES)}"
            )
            # Write anyway — better to have an unapproved event than to miss it
            # Enforcement is via code review, not runtime rejection

        # Auto-resolve context from session if not provided
        resolved_user         = user         or _resolve_user()
        resolved_org_id       = org_id       or _resolve_org_id()
        resolved_company_name = company_name or _resolve_company_name()
        resolved_slot         = slot_index   if slot_index is not None else _resolve_slot()
        session_id            = _resolve_session_id()

        event: dict = {
            "event_id":      str(uuid.uuid4()),
            "ts":            datetime.datetime.now().isoformat(timespec="seconds"),
            "user":          resolved_user,
            "event_type":    event_type,
            "org_id":        resolved_org_id,
            "company_name":  resolved_company_name,
            "slot_index":    resolved_slot,
            "session_id":    session_id,
            "summary":       summary,
            "detail":        detail or {},
            "state_version": state_version,
        }

        # Write to JSONL file (primary)
        from repository.audit_repo import append
        written = append(event)
        if not written:
            log.warning(f"audit_repo.append failed for event_type={event_type!r}")

        # Write to session cache (secondary — for in-session display)
        try:
            from repository.session_repo import prepend_audit_event
            prepend_audit_event(event, max_entries=MAX_AUDIT_SESSION_ENTRIES)
        except Exception as exc:
            log.debug(f"Session audit cache update failed: {exc}")

        return event

    except Exception as exc:
        log.error(f"write_audit_event raised unexpectedly: {exc}", exc_info=True)
        return None


# ── Context auto-resolution helpers ──────────────────────────────────────────

def _resolve_user() -> str:
    try:
        from repository.session_repo import get_current_user
        user = get_current_user()
        return user.get("username", "system") if user else "system"
    except Exception:
        return "system"


def _resolve_org_id() -> str:
    try:
        from state.session import get_active_org
        org = get_active_org()
        return org.get("org_id", "") if org else ""
    except Exception:
        return ""


def _resolve_company_name() -> str:
    try:
        from state.session import get_active_org
        org = get_active_org()
        return org.get("company_name", "") if org else ""
    except Exception:
        return ""


def _resolve_slot() -> int:
    try:
        from repository.session_repo import get_active_slot
        return get_active_slot()
    except Exception:
        return 0


def _resolve_session_id() -> str:
    try:
        from repository.session_repo import get_session_id
        return get_session_id()
    except Exception:
        return "unknown"
