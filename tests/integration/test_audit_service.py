"""Integration tests for services/audit_service.py"""
import pytest


def test_emit_returns_event_dict(tmp_path, monkeypatch):
    """emit() should return an AuditEvent dict on success."""
    # Redirect audit log to a temp file
    import audit.writer as writer_mod
    import pathlib
    monkeypatch.setattr(
        "repository.audit_repo._LOG_FILE",
        tmp_path / "audit_log.jsonl",
    )
    monkeypatch.setattr(
        "repository.session_repo.get_current_user",
        lambda: {"username": "test_user"}, raising=False,
    )
    monkeypatch.setattr(
        "state.session.get_active_org",
        lambda: {"org_id": "org-001", "company_name": "PT Test"}, raising=False,
    )
    monkeypatch.setattr(
        "repository.session_repo.get_active_slot", lambda: 0, raising=False,
    )
    monkeypatch.setattr(
        "repository.session_repo.get_session_id", lambda: "abc12345", raising=False,
    )
    monkeypatch.setattr(
        "repository.session_repo.prepend_audit_event",
        lambda e, **kw: None, raising=False,
    )

    from services.audit_service import emit
    event = emit("data_uploaded", "Test upload", {"file": "test.csv"})
    assert event is not None
    assert event["event_type"] == "data_uploaded"
    assert event["summary"] == "Test upload"
    assert "ts" in event
    assert "event_id" in event


def test_get_log_empty(tmp_path, monkeypatch):
    """get_log() should return empty list when no events exist."""
    monkeypatch.setattr(
        "repository.audit_repo._LOG_FILE",
        tmp_path / "audit_log.jsonl",
    )
    monkeypatch.setattr(
        "repository.session_repo.get_audit_cache",
        lambda: [], raising=False,
    )
    from services.audit_service import get_log
    result = get_log()
    assert result == []


def test_get_recent_events_returns_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "repository.audit_repo._LOG_FILE",
        tmp_path / "audit_log.jsonl",
    )
    monkeypatch.setattr(
        "repository.session_repo.get_audit_cache",
        lambda: [], raising=False,
    )
    from services.audit_service import get_recent_events
    result = get_recent_events(5)
    assert isinstance(result, list)


def test_emit_unapproved_type_still_writes(tmp_path, monkeypatch):
    """Unapproved event types should be written with a warning, not rejected."""
    monkeypatch.setattr(
        "repository.audit_repo._LOG_FILE",
        tmp_path / "audit_log.jsonl",
    )
    monkeypatch.setattr(
        "repository.session_repo.prepend_audit_event",
        lambda e, **kw: None, raising=False,
    )
    for fn in ("get_current_user","get_active_slot","get_session_id"):
        monkeypatch.setattr(
            f"repository.session_repo.{fn}",
            (lambda: {"username":"u"}) if fn == "get_current_user" else (lambda: 0 if fn == "get_active_slot" else "sess"),
            raising=False,
        )
    monkeypatch.setattr(
        "state.session.get_active_org",
        lambda: {"org_id": "o", "company_name": "C"}, raising=False,
    )
    from services.audit_service import emit
    event = emit("custom_unknown_type", "test")
    assert event is not None    # Should still return the event
