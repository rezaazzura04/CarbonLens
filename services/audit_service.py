"""
CarbonLens V8 — Audit service.
Thin orchestration layer over audit/writer.py and audit/reader.py.
Pages and components call this service — never the writer/reader directly.
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.services.audit")


def emit(
    event_type:    str,
    summary:       str,
    detail:        Optional[dict] = None,
    user:          Optional[str]  = None,
    org_id:        Optional[str]  = None,
    company_name:  Optional[str]  = None,
    slot_index:    Optional[int]  = None,
    state_version: Optional[int]  = None,
) -> Optional[dict]:
    """
    Emit one audit event.

    Delegates to audit.writer.write_audit_event().
    Context (user, org, slot, session_id) is auto-resolved from session
    if not explicitly provided.

    Parameters
    ----------
    event_type    : Must be one of APPROVED_EVENT_TYPES (13 defined types).
    summary       : One human-readable sentence.
    detail        : Event-specific structured payload.
    user          : Username — auto-resolved from session if None.
    org_id        : Organisation ID — auto-resolved if None.
    company_name  : Org name — auto-resolved if None.
    slot_index    : Slot index — auto-resolved if None.
    state_version : ComputedState.version at event time.

    Returns
    -------
    AuditEvent dict on success, None on failure.
    """
    from audit.writer import write_audit_event
    return write_audit_event(
        event_type    = event_type,
        summary       = summary,
        detail        = detail,
        user          = user,
        org_id        = org_id,
        company_name  = company_name,
        slot_index    = slot_index,
        state_version = state_version,
    )


def get_log(
    org_id:       Optional[str] = None,
    event_type:   Optional[str] = None,
    since:        Optional[str] = None,
    limit:        int           = 100,
    company_slot: Optional[int] = None,
) -> list:
    """
    Retrieve audit events with optional filters.

    Parameters
    ----------
    org_id       : Filter to one organisation.
    event_type   : Filter to one event type.
    since        : ISO date lower bound (inclusive).
    limit        : Maximum entries to return.
    company_slot : Filter to one slot index.

    Returns
    -------
    list[AuditEvent dicts] in reverse-chronological order.
    """
    from audit.reader import get_audit_log
    return get_audit_log(
        limit        = limit,
        event_type   = event_type,
        org_id       = org_id,
        since        = since,
        company_slot = company_slot,
    )


def get_recent_events(n: int = 10) -> list:
    """Return the n most recent audit events across all organisations."""
    return get_log(limit=n)


def get_events_for_org(org_id: str, limit: int = 50) -> list:
    """Return all audit events for a specific organisation."""
    return get_log(org_id=org_id, limit=limit)


def get_events_by_type(event_type: str, limit: int = 50) -> list:
    """Return all audit events of a specific type."""
    return get_log(event_type=event_type, limit=limit)


def get_report_events(limit: int = 20) -> list:
    """Return all report-related events (exports, PDFs)."""
    results = []
    for etype in ("report_exported", "pdf_generated"):
        results.extend(get_log(event_type=etype, limit=limit))
    results.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return results[:limit]


def get_computation_events(limit: int = 20) -> list:
    """Return all computation events (recalculations)."""
    results = []
    for etype in ("carbon_recalculated", "esg_score_recalculated", "dq_score_recalculated"):
        results.extend(get_log(event_type=etype, limit=limit))
    results.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return results[:limit]
