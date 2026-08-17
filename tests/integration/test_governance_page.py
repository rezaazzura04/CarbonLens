"""
Integration tests for pages/governance/page.py

Verifies:
  - Service calls (audit_service × 3, state_service × 3)
  - Methodology library schema and completeness
  - Emission factor library schema and coverage
  - Governance metrics schema
  - Architecture compliance (no calculations, no session_state)
  - Audit table integration
"""
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def org():
    return {
        "org_id": "test-gov-001", "company_name": "PT Governance Utama",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 20.0, "recycle_pct": 15.0, "certifications": [],
    }


@pytest.fixture
def audit_events():
    return [
        {"event_id": "ev-001", "ts": "2024-01-10T09:00:00",
         "user": "analyst", "event_type": "data_uploaded",
         "org_id": "test-gov-001", "company_name": "PT Governance Utama",
         "slot_index": 0, "session_id": "abc12345",
         "summary": "Data uploaded: test.csv",
         "detail": {"filename": "test.csv"}, "state_version": None},
        {"event_id": "ev-002", "ts": "2024-01-10T09:05:00",
         "user": "analyst", "event_type": "carbon_recalculated",
         "org_id": "test-gov-001", "company_name": "PT Governance Utama",
         "slot_index": 0, "session_id": "abc12345",
         "summary": "Carbon inventory recomputed: 175.0 tCO2e",
         "detail": {"total_tco2e": 175.0}, "state_version": 1},
    ]


@pytest.fixture
def gov_metrics():
    return {
        "total_audit_events": 24,
        "data_uploads": 3,
        "reports_generated": 2,
        "recomputations": 6,
        "last_event_ts": "2024-01-15 14:30",
        "methodology_version": "V8-Phase4",
        "approved_event_types": 13,
        "ef_scope1_count": 7,
        "ef_scope2_count": 7,
        "ef_scope3_count": 12,
        "methodology_entries": 29,
    }


# ── Service call tests ────────────────────────────────────────────────────────

def test_render_calls_audit_get_log(monkeypatch, org, audit_events, gov_metrics):
    calls = []
    _patch(monkeypatch, org, audit_events, gov_metrics,
           on_log=lambda: calls.append("log"))
    _stub_st(monkeypatch)
    from pages.governance.page import render
    render()
    assert "log" in calls


def test_render_calls_methodology_library(monkeypatch, org, audit_events, gov_metrics):
    calls = []
    _patch(monkeypatch, org, audit_events, gov_metrics,
           on_meth=lambda: calls.append("meth"))
    _stub_st(monkeypatch)
    from pages.governance.page import render
    render()
    assert "meth" in calls


def test_render_calls_emission_factor_library(monkeypatch, org, audit_events, gov_metrics):
    calls = []
    _patch(monkeypatch, org, audit_events, gov_metrics,
           on_ef=lambda: calls.append("ef"))
    _stub_st(monkeypatch)
    from pages.governance.page import render
    render()
    assert "ef" in calls


def test_render_calls_governance_metrics(monkeypatch, org, audit_events, gov_metrics):
    calls = []
    _patch(monkeypatch, org, audit_events, gov_metrics,
           on_metrics=lambda: calls.append("metrics"))
    _stub_st(monkeypatch)
    from pages.governance.page import render
    render()
    assert "metrics" in calls


# ── Architecture compliance ───────────────────────────────────────────────────

def test_no_calculation_imports():
    import ast
    src  = open("pages/governance/page.py").read()
    tree = ast.parse(src)
    bad  = [n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
            and n.module.startswith("calculations")]
    assert not bad, f"Page imports calculations: {bad}"


def test_no_direct_session_state():
    import ast
    src  = open("pages/governance/page.py").read()
    tree = ast.parse(src)
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not bad, f"Page uses st.session_state: {bad}"


def test_no_disallowed_repository():
    import ast
    src     = open("pages/governance/page.py").read()
    tree    = ast.parse(src)
    allowed = {"repository.session_repo"}
    bad     = [n.module for n in ast.walk(tree)
               if isinstance(n, ast.ImportFrom) and n.module
               and n.module.startswith("repository")
               and n.module not in allowed]
    assert not bad, f"Disallowed repository: {bad}"


# ── Methodology library tests ─────────────────────────────────────────────────

def test_get_methodology_library_returns_list():
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    assert isinstance(entries, list)
    assert len(entries) == 29


def test_methodology_library_schema():
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    for e in entries:
        for key in ("entry_id","category","name","value","formula",
                    "gri_reference","source","introduced_in","rationale"):
            assert key in e, f"Entry missing key: {key}"


def test_methodology_library_unique_ids():
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    ids = [e["entry_id"] for e in entries]
    assert len(ids) == len(set(ids)), "Duplicate entry_ids found"


def test_methodology_library_esg_weights_correct():
    """Phase 0 C2: E=40%, S=30%, G=30% must appear in library."""
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    weight_entries = {e["entry_id"]: e for e in entries}
    assert weight_entries["env-pillar-weight"]["value"]  == "40%"
    assert weight_entries["soc-pillar-weight"]["value"]  == "30%"
    assert weight_entries["gov-pillar-weight"]["value"]  == "30%"


def test_methodology_library_provisional_floor():
    """Phase 0 C3: provisional floor = 50% must appear in library."""
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    floor = next((e for e in entries if e["entry_id"] == "esg-provisional-floor"), None)
    assert floor is not None
    assert "50" in floor["value"]


def test_methodology_library_scope3_coverage():
    """Phase 0 H2: Scope 3 12/15 must appear in library."""
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    s3 = next((e for e in entries if e["entry_id"] == "scope3-coverage"), None)
    assert s3 is not None
    assert "12" in s3["value"]
    assert "15" in s3["value"]


def test_methodology_library_categories():
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    categories = {e["category"] for e in entries}
    assert "ESG Composite Weights"        in categories
    assert "Environmental Sub-indicators" in categories
    assert "Social Sub-indicators"        in categories
    assert "Governance Sub-indicators"    in categories
    assert "Data Quality Model"           in categories
    assert "GHG Inventory"               in categories


# ── Emission factor library tests ─────────────────────────────────────────────

def test_get_emission_factor_library_returns_list():
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    assert isinstance(entries, list)
    assert len(entries) > 0


def test_ef_library_schema():
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    for e in entries:
        for key in ("name","category","value","unit","source","gwp_basis"):
            assert key in e, f"EF entry missing key: {key}"


def test_ef_library_scope_categories():
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    categories = {e["category"] for e in entries}
    assert "Scope 1 — Combustion"      in categories
    assert "Scope 2 — Grid Electricity" in categories
    assert "Scope 3 — Value Chain"     in categories


def test_ef_library_diesel_phase0_h3():
    """Phase 0 H3: diesel EF must be 2.6967 and have co2_only_value."""
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    diesel = next((e for e in entries if e["name"] == "Diesel (automotive)"), None)
    assert diesel is not None
    assert diesel["value"] == 2.6967
    assert diesel["co2_only_value"] == 2.68


def test_ef_library_pln_national():
    """PLN national EF must be 0.716 per Kepmen ESDM No.18/2023."""
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    pln = next((e for e in entries if "National" in e.get("name","") and "PLN" in e.get("name","")), None)
    assert pln is not None
    assert pln["value"] == 0.716
    assert "Kepmen ESDM" in pln["regulation"]


def test_ef_library_scope3_count():
    """Scope 3 must have exactly 12 categories."""
    from services.state_service import get_emission_factor_library
    entries = get_emission_factor_library()
    s3 = [e for e in entries if e["category"] == "Scope 3 — Value Chain"]
    assert len(s3) == 12


# ── Governance metrics tests ──────────────────────────────────────────────────

def test_governance_metrics_schema(gov_metrics):
    required = ["total_audit_events","data_uploads","reports_generated",
                "recomputations","methodology_version","methodology_entries",
                "ef_scope1_count","ef_scope2_count","ef_scope3_count"]
    for key in required:
        assert key in gov_metrics, f"Missing: {key}"


def test_get_governance_metrics_returns_dict(monkeypatch):
    monkeypatch.setattr(
        "audit.reader.get_audit_log",
        lambda **kw: [], raising=False,
    )
    from services.state_service import get_governance_metrics
    result = get_governance_metrics()
    assert isinstance(result, dict)
    assert "methodology_version" in result
    from services.state_service import get_methodology_library
    assert result["methodology_entries"] == len(get_methodology_library())


def test_governance_metrics_ef_totals(gov_metrics):
    total_ef = (gov_metrics["ef_scope1_count"] +
                gov_metrics["ef_scope2_count"] +
                gov_metrics["ef_scope3_count"])
    assert total_ef > 0


# ── Audit event fixtures ──────────────────────────────────────────────────────

def test_audit_events_schema(audit_events):
    for ev in audit_events:
        for key in ("event_id","ts","user","event_type","summary"):
            assert key in ev, f"Event missing key: {key}"


def test_audit_events_approved_types(audit_events):
    from config.constants import APPROVED_EVENT_TYPES
    for ev in audit_events:
        assert ev["event_type"] in APPROVED_EVENT_TYPES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch(monkeypatch, org, events, metrics,
           on_log=None, on_meth=None, on_ef=None, on_metrics=None):
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: org)

    def _log(**kw):
        if on_log: on_log()
        return events
    monkeypatch.setattr("services.audit_service.get_log", _log, raising=False)
    monkeypatch.setattr("services.audit_service.get_report_events",
                        lambda **kw: [], raising=False)
    monkeypatch.setattr("services.audit_service.get_computation_events",
                        lambda **kw: [], raising=False)

    def _meth():
        if on_meth: on_meth()
        return []
    monkeypatch.setattr("services.state_service.get_methodology_library",
                        _meth, raising=False)

    def _ef():
        if on_ef: on_ef()
        return []
    monkeypatch.setattr("services.state_service.get_emission_factor_library",
                        _ef, raising=False)

    def _metrics():
        if on_metrics: on_metrics()
        return metrics
    monkeypatch.setattr("services.state_service.get_governance_metrics",
                        _metrics, raising=False)


def _stub_st(monkeypatch):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","text_input","selectbox",
               "info","warning","error","plotly_chart","download_button","write"]:
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
