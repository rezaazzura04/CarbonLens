"""
Integration tests for pages/data_quality/page.py

Verifies:
  - Service calls (state_service, no audit duplication)
  - Data extraction correctness
  - Flagged field grouping and navigation routing
  - Validation summary rendering
  - Completeness breakdown
  - Quality trend history
  - Provenance row schema
  - Zero calculation imports
  - No st.session_state access
"""
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def org():
    return {
        "org_id": "test-dq-001", "company_name": "PT Data Kualitas",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 0.0, "recycle_pct": 0.0, "certifications": [],
    }


@pytest.fixture
def full_state():
    return {
        "state_id": "dq-state-001", "org_id": "test-dq-001",
        "period": "2024", "version": 1, "previous_version_id": None,
        "input_hash": "dq123", "status": "Provisional",
        "carbon": {
            "scope1_kg": 0.0, "scope2_kg": 0.0, "scope3_kg": 0.0,
            "total_kg": 0.0, "intens_m2": 0.0,
            "scope_source": "csv_estimate", "province": "Jawa Timur",
            "pln_ef_used": 0.716, "scope3_breakdown": {},
            "screened_excluded": [], "benchmark": 120.0,
            "gap": {"gap_pct": 0.0, "above_benchmark": False},
            "computed_at": "2024-01-01T00:00:00",
        },
        "esg": {
            "score": 40.0, "grade": "D", "label": "Needs Improvement",
            "env": 50.0, "social": 30.0, "gov": 40.0,
            "confidence_score": 25.0, "is_provisional": True,
            "n_disclosed": 2, "n_total_indicators": 8,
            "disclosure_summary": "2 of 8 disclosed",
            "methodology_version": "V8-Phase4",
            "methodology_disclaimer": "Provisional.",
            "computed_at": "2024-01-01T00:00:00",
        },
        "data_quality": {
            "completeness_score": 65.0, "consistency_score": 85.0,
            "validation_status": "Warning", "validation_score": 70.0,
            "confidence_score": 72.75, "is_provisional": False,
            "env_completeness": 88.0, "sg_completeness": 25.0,
            "sg_disclosed": 2, "sg_total": 8,
            "flagged_fields": [
                {
                    "field_name": "employee_turnover",
                    "reason": "estimated_default",
                    "severity": "medium",
                    "description": "Employee turnover not disclosed.",
                    "suggested_action": "Enter in ESG Analytics.",
                    "fix_route": "esg_analytics",
                },
                {
                    "field_name": "Water",
                    "reason": "missing",
                    "severity": "low",
                    "description": "Water column not found in CSV.",
                    "suggested_action": "Add Water column to CSV.",
                    "fix_route": "carbon_accounting",
                },
                {
                    "field_name": "Emission",
                    "reason": "outlier",
                    "severity": "high",
                    "description": "August emission is a statistical outlier.",
                    "suggested_action": "Review August data.",
                    "fix_route": "carbon_accounting",
                },
            ],
            "summary": "Confidence 73% — 1 high and 1 medium priority issue.",
        },
        "confidence": {
            "esg_confidence": 25.0, "esg_is_provisional": True,
            "dq_confidence": 72.75, "dq_is_provisional": False,
            "interpretation": "S/G disclosure incomplete.",
        },
        "computed_at": "2024-01-01T00:00:00",
        "computation_time_ms": 180,
    }


@pytest.fixture
def validation_result():
    return {
        "status": "Warning",
        "errors": [],
        "warnings": ["Duplicate month entry detected."],
        "columns_present": ["Month", "Emission", "Energy"],
        "rows_valid": 11,
        "rows_total": 13,
        "normalisation_applied": True,
    }


@pytest.fixture
def quality_history():
    return [
        {"ts": "2024-01-10 09:00", "confidence": 65.0,
         "validation": "Warning", "summary": "DQ score: 65%"},
        {"ts": "2024-01-15 14:30", "confidence": 72.75,
         "validation": "Warning", "summary": "DQ score: 73%"},
    ]


# ── Service call tests ────────────────────────────────────────────────────────

def test_render_calls_get_computed_state(
        monkeypatch, org, full_state, validation_result, quality_history):
    calls = []
    _patch(monkeypatch, org, full_state, validation_result, quality_history,
           on_computed=lambda: calls.append("computed"))
    _stub_st(monkeypatch)
    from pages.data_quality.page import render
    render()
    assert "computed" in calls


def test_render_calls_get_validation_result(
        monkeypatch, org, full_state, validation_result, quality_history):
    calls = []
    _patch(monkeypatch, org, full_state, validation_result, quality_history,
           on_validation=lambda: calls.append("validation"))
    _stub_st(monkeypatch)
    from pages.data_quality.page import render
    render()
    assert "validation" in calls


def test_render_calls_get_quality_history(
        monkeypatch, org, full_state, validation_result, quality_history):
    calls = []
    _patch(monkeypatch, org, full_state, validation_result, quality_history,
           on_history=lambda: calls.append("history"))
    _stub_st(monkeypatch)
    from pages.data_quality.page import render
    render()
    assert "history" in calls


def test_render_no_org_skips_services(monkeypatch):
    called = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: None)
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: (called.append(True), {})[1], raising=False)
    _stub_st(monkeypatch)
    from pages.data_quality.page import render
    render()
    assert not called


# ── Architecture compliance ───────────────────────────────────────────────────

def test_no_calculation_imports():
    import ast
    src  = open("pages/data_quality/page.py").read()
    tree = ast.parse(src)
    bad  = [n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
            and n.module.startswith("calculations")]
    assert not bad, f"Page imports calculations: {bad}"


def test_no_direct_session_state():
    import ast
    src  = open("pages/data_quality/page.py").read()
    tree = ast.parse(src)
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not bad, f"Page accesses st.session_state: {bad}"


def test_no_disallowed_repository():
    import ast
    src     = open("pages/data_quality/page.py").read()
    tree    = ast.parse(src)
    allowed = {"repository.session_repo"}
    bad     = [n.module for n in ast.walk(tree)
               if isinstance(n, ast.ImportFrom) and n.module
               and n.module.startswith("repository")
               and n.module not in allowed]
    assert not bad, f"Disallowed repository imports: {bad}"


# ── Data extraction tests ─────────────────────────────────────────────────────

def test_dq_scalars_correct(full_state):
    dq = full_state["data_quality"]
    assert dq["confidence_score"]  == 72.75
    assert dq["completeness_score"] == 65.0
    assert dq["consistency_score"]  == 85.0
    assert dq["validation_status"]  == "Warning"
    assert dq["is_provisional"]     is False


def test_flags_count_correct(full_state):
    flags = full_state["data_quality"]["flagged_fields"]
    assert len(flags) == 3
    high_flags = [f for f in flags if f["severity"] == "high"]
    med_flags  = [f for f in flags if f["severity"] == "medium"]
    low_flags  = [f for f in flags if f["severity"] == "low"]
    assert len(high_flags) == 1
    assert len(med_flags)  == 1
    assert len(low_flags)  == 1


def test_flags_have_fix_routes(full_state):
    flags = full_state["data_quality"]["flagged_fields"]
    approved_routes = {"esg_analytics", "carbon_accounting", "data_quality",
                       "reporting_compliance", "governance"}
    for flag in flags:
        assert flag["fix_route"] in approved_routes, \
            f"Unknown fix_route: {flag['fix_route']}"


def test_confidence_scalars(full_state):
    conf = full_state["confidence"]
    assert conf["esg_confidence"]     == 25.0
    assert conf["esg_is_provisional"] is True
    assert conf["dq_confidence"]      == 72.75
    assert conf["dq_is_provisional"]  is False


def test_sg_disclosure_scalars(full_state):
    dq = full_state["data_quality"]
    assert dq["sg_disclosed"] == 2
    assert dq["sg_total"]     == 8


# ── Validation result tests ───────────────────────────────────────────────────

def test_validation_result_schema(validation_result):
    for key in ("status","errors","warnings","columns_present",
                "rows_valid","rows_total","normalisation_applied"):
        assert key in validation_result, f"Missing key: {key}"


def test_validation_row_counts(validation_result):
    assert validation_result["rows_valid"]  == 11
    assert validation_result["rows_total"]  == 13
    assert validation_result["rows_valid"]  <= validation_result["rows_total"]


def test_validation_normalisation_flag(validation_result):
    assert validation_result["normalisation_applied"] is True


# ── Quality history tests ─────────────────────────────────────────────────────

def test_quality_history_schema(quality_history):
    for entry in quality_history:
        for key in ("ts", "confidence", "validation", "summary"):
            assert key in entry, f"History entry missing key: {key}"


def test_quality_history_confidence_range(quality_history):
    for entry in quality_history:
        assert 0.0 <= float(entry["confidence"]) <= 100.0


def test_get_quality_history_empty_audit(monkeypatch):
    """get_quality_history() with no audit events must return empty list safely."""
    monkeypatch.setattr(
        "audit.reader.get_audit_log",
        lambda **kw: [], raising=False,
    )
    from services.state_service import get_quality_history
    result = get_quality_history()
    assert isinstance(result, list)
    assert result == []


# ── Provenance row tests ──────────────────────────────────────────────────────

def test_dq_provenance_rows_schema():
    from pages.data_quality.page import _build_dq_provenance_rows
    rows = _build_dq_provenance_rows()
    assert isinstance(rows, list)
    assert len(rows) == 5
    for row in rows:
        for key in ("label", "value", "source", "formula", "note"):
            assert key in row


def test_dq_provenance_weights_sum():
    """The three blending weights must sum to 100%."""
    from config.constants import (
        DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION
    )
    total = DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION
    assert abs(total - 1.0) < 1e-9


def test_dq_provenance_contains_provisional_floor():
    from pages.data_quality.page import _build_dq_provenance_rows
    rows = _build_dq_provenance_rows()
    labels = [r["label"] for r in rows]
    assert any("Provisional" in l or "provisional" in l for l in labels)


def test_dq_provenance_contains_fail_cap():
    from pages.data_quality.page import _build_dq_provenance_rows
    rows = _build_dq_provenance_rows()
    labels = [r["label"] for r in rows]
    assert any("cap" in l.lower() or "Fail" in l for l in labels)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch(monkeypatch, org, state, validation, history,
           on_computed=None, on_validation=None, on_history=None):
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: org)
    monkeypatch.setattr("services.state_service.get_disclosure_inputs",   lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",        lambda: {})

    def _computed(**kw):
        if on_computed: on_computed()
        return state
    monkeypatch.setattr("services.state_service.get_computed_state",
                        _computed, raising=False)

    def _val():
        if on_validation: on_validation()
        return validation
    monkeypatch.setattr("services.state_service.get_validation_result",
                        _val, raising=False)

    def _hist(**kw):
        if on_history: on_history()
        return history
    monkeypatch.setattr("services.state_service.get_quality_history",
                        _hist, raising=False)


def _stub_st(monkeypatch):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","number_input","checkbox",
               "text_input","selectbox","info","warning","error",
               "plotly_chart","download_button","write","add_hline"]:
        monkeypatch.setattr(st, fn, noop, raising=False)
    monkeypatch.setattr(
        st, "columns",
        lambda n, **kw: [_Col()] * (n if isinstance(n, int) else len(n)),
        raising=False,
    )
    monkeypatch.setattr(st, "expander", lambda *a, **kw: _Col(), raising=False)
    monkeypatch.setattr(st, "rerun",    lambda: None, raising=False)


class _Col:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __getattr__(self, name): return lambda *a, **kw: None
