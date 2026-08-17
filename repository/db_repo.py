"""
CarbonLens V8 — Database repository stub (Phase 6).

Provides the same interface as disk_repo.py but backed by SQLite (Phase 6)
or PostgreSQL (production SaaS). Switching from JSON persistence to a
database requires only replacing disk_repo with db_repo in services —
no service code changes are required.

Status: Interface stub only. All methods raise NotImplementedError.
        Implement in Phase 6 alongside session persistence and log rotation.
"""

from __future__ import annotations
from typing import Optional


def save_organisation(org: dict, slot: int) -> bool:
    raise NotImplementedError("db_repo.save_organisation — Phase 6 not yet implemented")


def load_organisation(slot: int) -> Optional[dict]:
    raise NotImplementedError("db_repo.load_organisation — Phase 6 not yet implemented")


def delete_organisation(slot: int) -> bool:
    raise NotImplementedError("db_repo.delete_organisation — Phase 6 not yet implemented")


def save_computed_state(state: dict, org_id: str) -> bool:
    raise NotImplementedError("db_repo.save_computed_state — Phase 6 not yet implemented")


def load_computed_state(org_id: str) -> Optional[dict]:
    raise NotImplementedError("db_repo.load_computed_state — Phase 6 not yet implemented")


def save_users(users: dict) -> bool:
    raise NotImplementedError("db_repo.save_users — Phase 6 not yet implemented")


def load_users() -> dict:
    raise NotImplementedError("db_repo.load_users — Phase 6 not yet implemented")


# ── Future schema (SQLite/PostgreSQL) ─────────────────────────────────────────
#
# organisations:
#   org_id TEXT PK, slot_index INT, company_name TEXT, sector TEXT,
#   area_m2 REAL, employees INT, province TEXT, reporting_period TEXT,
#   renew_pct REAL, recycle_pct REAL, certifications JSON,
#   created_at TEXT, updated_at TEXT
#
# computed_states:
#   state_id TEXT PK, org_id TEXT FK, version INT,
#   previous_version_id TEXT, input_hash TEXT, status TEXT,
#   carbon_json JSON, esg_json JSON, dq_json JSON, confidence_json JSON,
#   computed_at TEXT, computation_time_ms INT
#
# audit_events:
#   event_id TEXT PK, ts TEXT, user TEXT, event_type TEXT,
#   org_id TEXT, company_name TEXT, slot_index INT, session_id TEXT,
#   summary TEXT, detail JSON, state_version INT
#
# users:
#   user_id TEXT PK, username TEXT UNIQUE, display_name TEXT,
#   password_hash TEXT, role TEXT, email TEXT,
#   must_change_pw INT, created_at TEXT, last_login_at TEXT
