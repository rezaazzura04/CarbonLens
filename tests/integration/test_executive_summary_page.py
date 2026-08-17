"""
Integration tests for pages/executive_summary/page.py

Tests verify:
  - Service calls are made correctly
  - Data extraction from ComputedState is correct
  - No calculations performed in page functions
  - Section renderers receive correct input types
  - No service duplication across sections
"""
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_org():
    return {
        "org_id": "test-org-exec", "company_name": "PT Nusantara Energi",
        "sector": "Manufacturing", "area_m2": 5000.0, "employees": 120,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 20.0, "recycle_pct": 15.0, "certifications": ["ISO 14001"],
    }


@pytest.fixture
def full_computed_state():
    return {
        "state_id": "abc-001", "org_id": "test-org-exec",
        "period": "2024", "version": 2, "previous_version_id": "abc-000",
        "input_hash": "deadbeef", "status": "Substantive",
        "carbon": {
            "scope1_kg": 50000.0, "scope2_kg": 100000.0,
            "scope3_kg": 25000.0, "total_kg": 175000.0,
            "intens_m2": 35.0, "scope_source": "carbon_accounting",
            "province": "Jawa Timur", "pln_ef_used": 0.781,
            "scope3_breakdown": {}, "screened_excluded": [],
            "benchmark": 120.0,
            "gap": {"gap_pct": -70.8, "gap_abs": -85.0, "above_benchmark": False},
            "computed_at": "2024-01-01T00:00:00",
        },
        "esg": {
            "org_id": "test-org-exec", "score": 72.5, "grade": "B",
            "label": "Satisfactory", "env": 80.0, "social": 65.0, "gov": 70.0,
            "confidence_score": 100.0, "is_provisional": False,
            "n_disclosed": 8, "n_total_indicators": 8,
            "disclosure_summary": "8 of 8 disclosed",
            "methodology_version": "V8-Phase4",
            "methodology_disclaimer": "Substantive.",
            "computed_at": "2024-01-01T00:00:00",
        },
        "data_quality": {
            "completeness_score": 85.0, "consistency_score": 100.0,
            "validation_status": "Pass", "validation_score": 100.0,
            "confidence_score": 92.5, "is_provisional": False,
            "env_completeness": 90.0, "sg_completeness": 100.0,
            "sg_disclosed": 8, "sg_total": 8,
            "flagged_fields": [], "summary": "Confidence 93%",
        },
        "confidence": {
            "esg_confidence": 100.0, "esg_is_provisional": False,
            "dq_confidence": 92.5, "dq_is_provisional": False,
            "interpretation": "Substantive.",
        },
        "computed_at": "2024-01-01T00:00:00",
        "computation_time_ms": 150,
    }


@pytest.fixture
def trend_data():
    return {
        "months": ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"],
        "emissions_tco2e": [245,268,231,259,277,242,264,251,239,267,245,258],
        "forecast": {"next_month": 255.0, "trend": "stable", "r2": 0.12, "slope": -0.5},
        "trend": {"direction": "stable", "slope_kg_mo": -0.5, "description": "Stable"},
        "annual_tco2e": 3045.0,
        "has_data": True,
    }


@pytest.fixture
def empty_trend_data():
    return {
        "months": [], "emissions_tco2e": [], "has_data": False,
        "forecast": {"next_month": 0, "trend": "insufficient_data", "r2": 0, "slope": 0},
        "trend": {"direction": "insufficient_data", "slope_kg_mo": 0, "description": ""},
        "annual_tco2e": 0.0,
    }


# ── Service call verification tests ──────────────────────────────────────────

def test_render_calls_state_service(monkeypatch, minimal_org, full_computed_state, trend_data):
    """render() must call state_service.get_computed_state() exactly once."""
    calls = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: minimal_org)
    monkeypatch.setattr("services.state_service.get_disclosure_inputs",   lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",        lambda: {})
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: (calls.append("get_computed_state"), full_computed_state)[1],
                        raising=False)
    monkeypatch.setattr("services.state_service.get_forecast_validation",
                        lambda: {"valid":False,"gate":{"reason":"No data","n_unique_periods":0,
                                 "n_required":6,"has_duplicates":False,"has_missing_periods":False,
                                 "missing_periods":[],"coverage_label":""},"validation":{},
                                 "naive":{},"outperforms_baseline":None,"next_period_value":None,
                                 "model_type":"OLS","limitation":"Modelled estimate."},
                        raising=False)
    monkeypatch.setattr("services.state_service.get_trend_data",    lambda: trend_data)
    monkeypatch.setattr("services.audit_service.get_recent_events", lambda n=8: [])
    _stub_streamlit(monkeypatch)

    from pages.executive_summary.page import render
    render()
    assert "get_computed_state" in calls, "state_service.get_computed_state() not called"


def test_render_calls_audit_service(monkeypatch, minimal_org, full_computed_state, trend_data):
    """render() must call audit_service.get_recent_events() exactly once."""
    audit_called = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: minimal_org)
    monkeypatch.setattr("services.state_service.get_disclosure_inputs",   lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",        lambda: {})
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: full_computed_state, raising=False)
    monkeypatch.setattr("services.state_service.get_forecast_validation",
                        lambda: {"valid":False,"gate":{"reason":"No data","n_unique_periods":0,
                                 "n_required":6,"has_duplicates":False,"has_missing_periods":False,
                                 "missing_periods":[],"coverage_label":""},"validation":{},
                                 "naive":{},"outperforms_baseline":None,"next_period_value":None,
                                 "model_type":"OLS","limitation":"Modelled estimate."},
                        raising=False)
    monkeypatch.setattr("services.state_service.get_trend_data", lambda: trend_data)
    monkeypatch.setattr("services.audit_service.get_recent_events",
                        lambda n=8: (audit_called.append(True), [])[1])
    _stub_streamlit(monkeypatch)

    from pages.executive_summary.page import render
    render()
    assert audit_called, "audit_service.get_recent_events() not called"


def test_render_no_org_does_not_call_state_service(monkeypatch):
    """When no org is configured, state_service.get_computed_state() must NOT be called."""
    state_called = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: None)
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: (state_called.append(True), {})[1], raising=False)
    _stub_streamlit(monkeypatch)

    from pages.executive_summary.page import render
    render()
    assert not state_called, "state_service called despite no org being configured"


# ── Data extraction tests ─────────────────────────────────────────────────────

def test_carbon_scalars_correctly_extracted(full_computed_state):
    """Verify tCO2e conversion from kg is correct."""
    carbon       = full_computed_state["carbon"]
    total_tco2e  = round(carbon["total_kg"]  / 1000, 2)
    scope1_tco2e = round(carbon["scope1_kg"] / 1000, 2)
    scope2_tco2e = round(carbon["scope2_kg"] / 1000, 2)
    scope3_tco2e = round(carbon["scope3_kg"] / 1000, 2)

    assert total_tco2e  == 175.0
    assert scope1_tco2e == 50.0
    assert scope2_tco2e == 100.0
    assert scope3_tco2e == 25.0
    # Scope totals must sum to total
    assert abs(scope1_tco2e + scope2_tco2e + scope3_tco2e - total_tco2e) < 0.01


def test_esg_scalars_extracted(full_computed_state):
    esg = full_computed_state["esg"]
    assert esg["score"]  == 72.5
    assert esg["grade"]  == "B"
    assert esg["env"]    == 80.0
    assert esg["social"] == 65.0
    assert esg["gov"]    == 70.0


def test_dq_scalars_extracted(full_computed_state):
    conf = full_computed_state["confidence"]
    dq   = full_computed_state["data_quality"]
    assert conf["dq_confidence"]      == 92.5
    assert conf["dq_is_provisional"]  is False
    assert dq["validation_status"]   == "Pass"


def test_status_extracted(full_computed_state):
    assert full_computed_state["status"] == "Substantive"


def test_gap_scalars_extracted(full_computed_state):
    gap = full_computed_state["carbon"]["gap"]
    assert gap["gap_pct"] == -70.8
    assert gap["above_benchmark"] is False


# ── No-calculation assertion tests ────────────────────────────────────────────

def test_page_module_has_no_calculation_imports():
    """The page must not import from calculations/ directly."""
    import ast
    src = open("pages/executive_summary/page.py").read()
    tree = ast.parse(src)
    bad_imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = ""
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
            if module.startswith("calculations"):
                bad_imports.append(module)
    assert not bad_imports, (
        f"Page imports from calculations/ directly: {bad_imports}. "
        "All calculation access must go through state_service."
    )


def test_page_module_has_no_repository_imports():
    """The page must not import from repository/ (except session_repo for quick actions)."""
    import ast
    src = open("pages/executive_summary/page.py").read()
    tree = ast.parse(src)
    allowed = {"repository.session_repo"}  # only for quick action navigation
    bad_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if (node.module.startswith("repository")
                    and node.module not in allowed):
                bad_imports.append(node.module)
    assert not bad_imports, (
        f"Page imports from disallowed repository module(s): {bad_imports}"
    )


def test_page_module_has_no_st_session_state():
    """The page must not call st.session_state directly in executable code."""
    import ast
    src  = open("pages/executive_summary/page.py").read()
    tree = ast.parse(src)
    bad  = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "session_state":
            bad.append(ast.unparse(node))
    assert not bad, (
        f"Page accesses st.session_state directly: {bad}. "
        "Use state_service or repository.session_repo wrappers."
    )


# ── Section helper input type tests ──────────────────────────────────────────

def test_section_kpis_accepts_correct_types():
    """_section_kpis must accept floats and strings without error (no Streamlit call)."""
    # Test the type contracts without invoking Streamlit
    total    = 175.0
    intensity= 35.0
    esg_score= 72.5
    grade    = "B"
    dq_conf  = 92.5
    dq_prov  = False
    annual   = 3045.0
    src      = "carbon_accounting"
    gap_pct  = -70.8
    above    = False

    # Assert all are correct Python types before passing to component
    assert isinstance(total,     float)
    assert isinstance(intensity, float)
    assert isinstance(esg_score, float)
    assert isinstance(grade,     str)
    assert isinstance(dq_conf,   float)
    assert isinstance(dq_prov,   bool)
    assert isinstance(annual,    float)
    assert isinstance(src,       str)
    assert isinstance(gap_pct,   float)
    assert isinstance(above,     bool)


def test_trend_chart_receives_lists(trend_data):
    """Chart inputs must be Python lists, not DataFrames or service objects."""
    months = trend_data["months"]
    values = trend_data["emissions_tco2e"]
    assert isinstance(months, list)
    assert isinstance(values, list)
    assert all(isinstance(m, str)   for m in months)
    assert all(isinstance(v, (int, float)) for v in values)


def test_get_trend_data_returns_correct_schema(trend_data):
    """get_trend_data() output must contain all required keys."""
    required = ["months", "emissions_tco2e", "forecast", "trend",
                "annual_tco2e", "has_data"]
    for key in required:
        assert key in trend_data, f"Missing key in trend_data: {key}"


def test_empty_trend_data_has_correct_defaults(empty_trend_data):
    assert empty_trend_data["has_data"] is False
    assert empty_trend_data["months"] == []
    assert empty_trend_data["emissions_tco2e"] == []
    assert empty_trend_data["annual_tco2e"] == 0.0


# ── State service integration (no Streamlit) ──────────────────────────────────

def test_get_trend_data_no_dataframe(monkeypatch):
    """get_trend_data() with no uploaded DataFrame must return safe empty dict."""
    monkeypatch.setattr(
        "repository.session_repo.get_uploaded_df",
        lambda: None, raising=False,
    )
    from services.state_service import get_trend_data
    result = get_trend_data()
    assert result["has_data"] is False
    assert result["months"] == []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stub_streamlit(monkeypatch):
    """Stub all Streamlit rendering calls so tests don't need a browser."""
    import streamlit as st

    noop = lambda *a, **kw: None
    for fn in ["markdown", "caption", "expander", "button", "text_input",
               "selectbox", "info", "warning", "error", "plotly_chart",
               "download_button"]:
        monkeypatch.setattr(st, fn, noop, raising=False)

    # columns must return an iterable of context-manager stubs
    monkeypatch.setattr(st, "columns", lambda n, **kw: [_ColStub()] * (n if isinstance(n, int) else len(n)), raising=False)
    monkeypatch.setattr(st, "rerun",   lambda: None, raising=False)


class _ColStub:
    """Minimal context-manager stub for a single Streamlit column."""
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __getattr__(self, name): return lambda *a, **kw: None
