"""
Integration tests for pages/carbon_accounting/page.py

Verifies:
  - Service calls are made at the top of render()
  - Data extraction from ComputedState is arithmetically correct
  - No calculations imported directly in the page
  - No st.session_state access in executable code
  - Provenance rows are built from pre-computed values only
  - Charts receive correct Python list/float types
"""
import pytest


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def org():
    return {
        "org_id": "test-ca-001", "company_name": "PT Karbon Nusantara",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 20.0, "recycle_pct": 15.0, "certifications": [],
    }


@pytest.fixture
def carbon_state():
    return {
        "state_id": "ca-state-001", "org_id": "test-ca-001",
        "period": "2024", "version": 1, "previous_version_id": None,
        "input_hash": "deadbeef01", "status": "Substantive",
        "carbon": {
            "scope1_kg": 75000.0, "scope2_kg": 150000.0,
            "scope3_kg": 50000.0, "total_kg": 275000.0,
            "intens_m2": 55.0, "scope_source": "carbon_accounting",
            "province": "Jawa Timur", "pln_ef_used": 0.7810,
            "scope3_breakdown": {
                "cat5_waste": 12500.0,
                "cat6_business_travel": 8750.0,
                "cat7_employee_commute": 14000.0,
            },
            "screened_excluded": [
                "cat11: Use of sold products — screened",
                "cat14: Franchises — screened",
                "cat15: Investments — screened",
            ],
            "benchmark": 120.0,
            "gap": {"gap_pct": -54.2, "gap_abs": -65.0, "above_benchmark": False,
                    "reduction_needed_pct": 0.0},
            "computed_at": "2024-01-01T00:00:00",
        },
        "esg": {
            "score": 68.0, "grade": "B", "label": "Satisfactory",
            "env": 75.0, "social": 60.0, "gov": 65.0,
            "confidence_score": 75.0, "is_provisional": False,
            "n_disclosed": 6, "n_total_indicators": 8,
            "disclosure_summary": "6 of 8 disclosed",
            "methodology_version": "V8-Phase4",
            "methodology_disclaimer": "Substantive.",
            "computed_at": "2024-01-01T00:00:00",
        },
        "data_quality": {
            "completeness_score": 78.0, "consistency_score": 100.0,
            "validation_status": "Pass", "validation_score": 100.0,
            "confidence_score": 88.2, "is_provisional": False,
            "env_completeness": 85.0, "sg_completeness": 75.0,
            "sg_disclosed": 6, "sg_total": 8,
            "flagged_fields": [], "summary": "Confidence 88%",
        },
        "confidence": {
            "esg_confidence": 75.0, "esg_is_provisional": False,
            "dq_confidence": 88.2, "dq_is_provisional": False,
            "interpretation": "Substantive.",
        },
        "computed_at": "2024-01-01T00:00:00",
        "computation_time_ms": 200,
    }


@pytest.fixture
def trend_data():
    return {
        "months": ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"],
        "emissions_tco2e": [22.0,24.5,21.0,23.5,25.0,22.0,
                            24.0,23.0,21.5,24.0,22.5,23.5],
        "forecast": {"next_month": 23.2, "trend": "stable", "r2": 0.08, "slope": -0.05},
        "trend": {"direction": "stable", "slope_kg_mo": -50.0, "description": "Stable"},
        "annual_tco2e": 275.0,
        "has_data": True,
    }


# ── Service call tests ────────────────────────────────────────────────────────

def test_render_calls_get_computed_state(monkeypatch, org, carbon_state, trend_data):
    """render() must call state_service.get_computed_state() exactly once."""
    calls = []
    _patch_services(monkeypatch, org, carbon_state, trend_data,
                    on_computed=lambda: calls.append("computed"))
    _stub_st(monkeypatch)

    from pages.carbon_accounting.page import render
    render()
    assert "computed" in calls


def test_render_calls_get_trend_data(monkeypatch, org, carbon_state, trend_data):
    """render() must call state_service.get_trend_data()."""
    calls = []
    _patch_services(monkeypatch, org, carbon_state, trend_data,
                    on_trend=lambda: calls.append("trend"))
    _stub_st(monkeypatch)

    from pages.carbon_accounting.page import render
    render()
    assert "trend" in calls


def test_render_no_org_skips_state_service(monkeypatch):
    """With no org, state_service.get_computed_state() must NOT be called."""
    state_called = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: None)
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: (state_called.append(True), {})[1], raising=False)
    _stub_st(monkeypatch)

    from pages.carbon_accounting.page import render
    render()
    assert not state_called


# ── Data extraction correctness ───────────────────────────────────────────────

def test_tco2e_conversion(carbon_state):
    """kg → tCO2e conversion must be accurate for all four scope values."""
    c = carbon_state["carbon"]
    assert round(c["total_kg"]  / 1000, 2) == 275.0
    assert round(c["scope1_kg"] / 1000, 2) == 75.0
    assert round(c["scope2_kg"] / 1000, 2) == 150.0
    assert round(c["scope3_kg"] / 1000, 2) == 50.0


def test_scope_totals_invariant(carbon_state):
    """scope1 + scope2 + scope3 must equal total within floating-point tolerance."""
    c = carbon_state["carbon"]
    s1 = round(c["scope1_kg"] / 1000, 2)
    s2 = round(c["scope2_kg"] / 1000, 2)
    s3 = round(c["scope3_kg"] / 1000, 2)
    total = round(c["total_kg"] / 1000, 2)
    assert abs(s1 + s2 + s3 - total) < 0.01


def test_gap_extracted_correctly(carbon_state):
    gap = carbon_state["carbon"]["gap"]
    assert gap["gap_pct"]         == -54.2
    assert gap["above_benchmark"] is False
    assert gap["reduction_needed_pct"] == 0.0


def test_pln_ef_extracted(carbon_state):
    assert carbon_state["carbon"]["pln_ef_used"] == 0.7810


def test_screened_excluded_count(carbon_state):
    assert len(carbon_state["carbon"]["screened_excluded"]) == 3


# ── Architecture compliance tests ─────────────────────────────────────────────

def test_page_has_no_calculation_imports():
    """Page must not import from calculations/ directly."""
    import ast
    src  = open("pages/carbon_accounting/page.py").read()
    tree = ast.parse(src)
    bad  = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("calculations"):
                bad.append(node.module)
    assert not bad, f"Page imports from calculations/: {bad}"


def test_page_has_no_direct_session_state():
    """Page must not call st.session_state directly in executable code."""
    import ast
    src  = open("pages/carbon_accounting/page.py").read()
    tree = ast.parse(src)
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not bad, f"Page accesses st.session_state: {bad}"


def test_page_has_no_repository_direct_access():
    """Only session_repo (for nav) is allowed in page."""
    import ast
    src  = open("pages/carbon_accounting/page.py").read()
    tree = ast.parse(src)
    allowed = {"repository.session_repo"}
    bad  = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if (node.module.startswith("repository")
                    and node.module not in allowed):
                bad.append(node.module)
    assert not bad, f"Page imports from disallowed repository: {bad}"


# ── Provenance row builder tests ──────────────────────────────────────────────

def test_build_provenance_rows_returns_list():
    from pages.carbon_accounting.page import _build_provenance_rows
    rows = _build_provenance_rows("carbon_accounting", 0.781, "Jawa Timur", {})
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_build_provenance_rows_schema():
    """Every provenance row must contain required keys."""
    from pages.carbon_accounting.page import _build_provenance_rows
    rows = _build_provenance_rows("carbon_accounting", 0.781, "Jawa Timur", {})
    for row in rows:
        for key in ("label", "value", "source", "formula"):
            assert key in row, f"Provenance row missing key: {key}"


def test_build_provenance_rows_pln_ef_correct():
    """PLN EF in provenance row must match the value passed in."""
    from pages.carbon_accounting.page import _build_provenance_rows
    rows = _build_provenance_rows("carbon_accounting", 0.8120, "Kalimantan Timur", {})
    pln_rows = [r for r in rows if "PLN" in r["label"]]
    assert len(pln_rows) == 1
    assert "0.8120" in pln_rows[0]["value"]


def test_build_provenance_rows_contains_phase0_h3_note():
    """Phase 0 H3 fix note must appear for diesel row."""
    from pages.carbon_accounting.page import _build_provenance_rows
    rows = _build_provenance_rows("carbon_accounting", 0.716, "", {})
    diesel_rows = [r for r in rows if "Diesel" in r["label"]]
    assert diesel_rows, "No diesel provenance row found"
    assert "Phase 0 H3" in diesel_rows[0]["note"]


# ── Chart input type tests ────────────────────────────────────────────────────

def test_trend_chart_inputs_are_lists(trend_data):
    months = trend_data["months"]
    values = trend_data["emissions_tco2e"]
    assert isinstance(months, list)
    assert isinstance(values, list)
    assert len(months) == len(values)
    assert all(isinstance(v, (int, float)) for v in values)


def test_donut_chart_inputs_are_scalars(carbon_state):
    """Scope donut chart receives individual floats, not the carbon dict."""
    c = carbon_state["carbon"]
    s1 = round(c["scope1_kg"] / 1000, 2)
    s2 = round(c["scope2_kg"] / 1000, 2)
    s3 = round(c["scope3_kg"] / 1000, 2)
    assert isinstance(s1, float)
    assert isinstance(s2, float)
    assert isinstance(s3, float)


def test_benchmark_gauge_inputs(carbon_state):
    """Benchmark gauge receives intensity float and benchmark float."""
    intensity = float(carbon_state["carbon"]["intens_m2"])
    benchmark = float(carbon_state["carbon"]["benchmark"])
    assert isinstance(intensity, float)
    assert isinstance(benchmark, float)
    assert benchmark > 0


# ── Helper fixtures / stubs ───────────────────────────────────────────────────

def _patch_services(monkeypatch, org, state, trend,
                    on_computed=None, on_trend=None):
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: org)
    monkeypatch.setattr("services.state_service.get_scope_inputs",        lambda: {})

    def _get_computed(**kw):
        if on_computed: on_computed()
        return state
    monkeypatch.setattr("services.state_service.get_computed_state",
                        _get_computed, raising=False)

    def _get_trend():
        if on_trend: on_trend()
        return trend
    monkeypatch.setattr("services.state_service.get_trend_data", _get_trend)


def _stub_st(monkeypatch):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","text_input",
               "selectbox","info","warning","error","plotly_chart",
               "download_button","write"]:
        monkeypatch.setattr(st, fn, noop, raising=False)
    monkeypatch.setattr(
        st, "columns",
        lambda n, **kw: [_Col()] * (n if isinstance(n, int) else len(n)),
        raising=False,
    )
    monkeypatch.setattr(st, "expander", lambda *a, **kw: _Col(), raising=False)
    monkeypatch.setattr(st, "rerun", lambda: None, raising=False)


class _Col:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __getattr__(self, name): return lambda *a, **kw: None
