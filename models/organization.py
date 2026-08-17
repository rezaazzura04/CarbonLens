"""
CarbonLens V8 — Organisation, User, Role, Session models.

Pure TypedDicts. No business logic. No imports from services or calculations.
"""

from __future__ import annotations
from typing import Optional
from typing import TypedDict


class Role(TypedDict):
    """Permission set for a user class."""
    role_id:      str          # "admin" | "analyst" | "viewer"
    display_name: str
    permissions:  list[str]   # subset of ALL_PERMISSIONS from constants


class User(TypedDict):
    """Authenticated identity with role assignment."""
    user_id:       str
    username:      str          # Unique per platform instance
    display_name:  str
    password_hash: str          # SHA-256 hex digest (64 chars)
    role:          str          # Role role_id string
    email:         str          # May be empty string
    must_change_pw: bool        # True for admin-created accounts
    created_at:    str          # ISO 8601
    last_login_at: str          # ISO 8601, may be empty string


class Organisation(TypedDict):
    """Single organisation profile and configuration."""
    org_id:           str
    company_name:     str
    sector:           str       # Must match INDUSTRY_BENCHMARKS key
    area_m2:          float     # > 0.0
    employees:        int       # >= 0
    province:         str       # PLN_GRID_SUBSYSTEM key or "Other / International"
    reporting_period: str       # "YYYY" | "Q[1-4] YYYY" | free text
    renew_pct:        float     # 0.0 – 100.0
    recycle_pct:      float     # 0.0 – 100.0
    certifications:   list[str] # e.g. ["ISO 14001", "ISO 50001"]
    created_at:       str       # ISO 8601
    updated_at:       str       # ISO 8601
    slot_index:       int       # 0–4


class Session(TypedDict):
    """Current active browser session."""
    session_id:    str               # UUID4 hex[:8]
    user:          Optional[User]    # None if unauthenticated
    active_slot:   int               # 0 – MAX_ORG_SLOTS-1
    active_page:   str               # V8 destination ID
    started_at:    str               # ISO 8601
    organisations: list[Optional[Organisation]]  # len == MAX_ORG_SLOTS


# ── Factory helpers (no validation — handled in services) ─────────────────────

def make_empty_organisation(slot_index: int) -> Organisation:
    """Return a blank Organisation for a given slot with safe defaults."""
    import datetime, uuid
    now = datetime.datetime.now().isoformat(timespec="seconds")
    return Organisation(
        org_id           = str(uuid.uuid4()),
        company_name     = "",
        sector           = "Manufacturing",
        area_m2          = 5000.0,
        employees        = 0,
        province         = "",
        reporting_period = "",
        renew_pct        = 0.0,
        recycle_pct      = 0.0,
        certifications   = [],
        created_at       = now,
        updated_at       = now,
        slot_index       = slot_index,
    )


def make_guest_session() -> Session:
    """Return an unauthenticated session with empty organisation slots."""
    import datetime, uuid
    from config.constants import MAX_ORG_SLOTS, DEFAULT_DESTINATION
    return Session(
        session_id    = uuid.uuid4().hex[:8],
        user          = None,
        active_slot   = 0,
        active_page   = DEFAULT_DESTINATION,
        started_at    = datetime.datetime.now().isoformat(timespec="seconds"),
        organisations = [None] * MAX_ORG_SLOTS,
    )
