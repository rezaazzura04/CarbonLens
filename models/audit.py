"""
CarbonLens V8 — AuditEvent model.
"""
from __future__ import annotations
from typing import Optional
from typing import TypedDict


class AuditEvent(TypedDict):
    """
    Immutable record of one significant platform event.
    Write-once. The audit log is append-only.
    """
    event_id:      str              # UUID4
    ts:            str              # ISO 8601 timestamp
    user:          str              # Username or "system"
    event_type:    str              # One of APPROVED_EVENT_TYPES (13 types)
    org_id:        str
    company_name:  str              # Denormalised — snapshot at event time
    slot_index:    int
    session_id:    str              # hex[:8] of session UUID
    summary:       str              # One human-readable sentence
    detail:        dict             # Event-specific structured payload
    state_version: Optional[int]   # ComputedState.version at event time
