"""
CarbonLens V8 — Audit event reader.

get_audit_log() is the single read point for audit events.
Delegates to audit_repo for JSONL reads, with session cache fallback.
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.audit.reader")


def get_audit_log(
    limit:        int           = 100,
    event_type:   Optional[str] = None,
    org_id:       Optional[str] = None,
    since:        Optional[str] = None,
    company_slot: Optional[int] = None,
) -> list[dict]:
    """
    Read audit events in reverse-chronological order with optional filters.

    Reads from JSONL file (authoritative). Falls back to session cache on failure.
    Returns empty list if neither source is available.
    """
    from repository import audit_repo

    try:
        entries = audit_repo.read(
            limit        = limit,
            org_id       = org_id,
            event_type   = event_type,
            since        = since,
            company_slot = company_slot,
        )
        if entries:
            return entries
    except Exception as exc:
        log.warning(f"audit_repo.read failed, falling back to session cache: {exc}")

    # Session cache fallback
    try:
        from repository.session_repo import get_audit_cache
        all_events = get_audit_cache()
        filtered = _apply_filters(all_events, event_type, org_id, since, company_slot)
        return filtered[:limit]
    except Exception as exc:
        log.warning(f"Session audit cache fallback also failed: {exc}")
        return []


def _apply_filters(
    events:       list[dict],
    event_type:   Optional[str],
    org_id:       Optional[str],
    since:        Optional[str],
    company_slot: Optional[int],
) -> list[dict]:
    result = []
    for e in events:
        if event_type and e.get("event_type") != event_type:
            continue
        if org_id and e.get("org_id") != org_id:
            continue
        if since and e.get("ts", "") < since:
            continue
        if company_slot is not None and e.get("slot_index") != company_slot:
            continue
        result.append(e)
    return result
