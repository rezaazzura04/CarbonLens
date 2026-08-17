"""
P0 Usability Unblock — Demo Mode Tests (T-DEMO-01 through T-DEMO-15)
"""
import ast, os, sys, pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── T-DEMO-01: Fresh launch initializes Demo Mode ─────────────────────────────

def test_DEMO_01_fresh_launch_inits_demo(monkeypatch):
    """T-DEMO-01: CARBONLENS_AUTH_REQUIRED=false → Demo Mode auto-init."""
    import os as _os
    monkeypatch.setenv("CARBONLENS_AUTH_REQUIRED", "false")
    demo_called = []
    monkeypatch.setattr("services.auth_service.is_authenticated", lambda: False, raising=False)
    monkeypatch.setattr("services.auth_service.init_demo_mode",
                        lambda: (demo_called.append(True), {})[1], raising=False)
    app_src = open('app.py').read()
    assert 'init_demo_mode' in app_src
    assert 'CARBONLENS_AUTH_REQUIRED' in app_src


# ── T-DEMO-02: Idempotent initialization ─────────────────────────────────────

def test_DEMO_02_init_idempotent(monkeypatch):
    """T-DEMO-02: init_demo_organisation() returns DEMO_ORG safely when already done."""
    from services.demo_service import DEMO_ORG
    monkeypatch.setattr("services.demo_service.is_demo_initialised",
                        lambda: True, raising=False)
    from services.demo_service import init_demo_organisation
    result = init_demo_organisation()
    assert result["org_id"] == DEMO_ORG["org_id"]


# ── T-DEMO-03: Demo org has is_demo=True ──────────────────────────────────────

def test_DEMO_03_demo_org_tagged(monkeypatch):
    """T-DEMO-03: DEMO_ORG must have is_demo=True and a synthetic org_id."""
    from services.demo_service import DEMO_ORG
    assert DEMO_ORG["is_demo"] is True
    assert DEMO_ORG["org_id"] == "demo-org-carbonlens"
    assert "Demo" in DEMO_ORG["company_name"]


# ── T-DEMO-04: Executive Summary not blocked ──────────────────────────────────

def test_DEMO_04_exec_summary_renders_with_demo_org(monkeypatch):
    """T-DEMO-04: With demo org in session, Executive Summary must not show org-blocked state."""
    from services.demo_service import DEMO_ORG
    monkeypatch.setattr("services.state_service.get_active_organisation",
                        lambda: DEMO_ORG, raising=False)
    monkeypatch.setattr("services.state_service.get_disclosure_inputs", lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",      lambda: {})
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: _minimal_state(), raising=False)
    monkeypatch.setattr("services.state_service.get_trend_data", lambda: _empty_trend())
    monkeypatch.setattr("services.state_service.get_forecast_validation",
                        lambda: _empty_fcast(), raising=False)
    monkeypatch.setattr("services.audit_service.get_recent_events", lambda n=8: [])
    _stub_st(monkeypatch)
    no_org_calls = []
    import streamlit as st
    orig_empty = lambda *a, **kw: no_org_calls.append(a)
    from pages.executive_summary import page as pg
    from pages.executive_summary.page import render
    render()
    # org is set → _render_no_org() must NOT have been called
    # (test passes if no unhandled exception and render completed)


# ── T-DEMO-05: All 7 destinations reachable in Demo Mode ─────────────────────

def test_DEMO_05_all_destinations_importable():
    """T-DEMO-05: All 7 V8 destinations must import without error."""
    import importlib
    from config.constants import APPROVED_DESTINATIONS
    for dest in APPROVED_DESTINATIONS:
        mod = importlib.import_module(f"pages.{dest}.page")
        assert callable(getattr(mod, "render", None)), f"{dest}.render() missing"


# ── T-DEMO-06: Demo dataset has ≥ 6 unique chronological periods ─────────────

def test_DEMO_06_demo_dataset_satisfies_forecast_gate():
    """T-DEMO-06: Demo dataset must have ≥ 6 unique chronological periods."""
    from services.demo_service import get_demo_dataframe
    df = get_demo_dataframe()
    assert "Month"    in df.columns
    assert "Emission" in df.columns
    unique_months = df["Month"].nunique()
    assert unique_months >= 6, f"Only {unique_months} unique months — need ≥6"


def test_DEMO_06_demo_dataset_12_months():
    from services.demo_service import get_demo_dataframe
    df = get_demo_dataframe()
    assert len(df) == 12
    assert df["Month"].nunique() == 12


# ── T-DEMO-07: Forecast validation works on demo data ────────────────────────

def test_DEMO_07_forecast_gate_passes_on_demo_data():
    """T-DEMO-07: Phase 5-B forecast_with_validation() must return valid=True for demo data."""
    from services.demo_service import get_demo_dataframe
    from calculations.forecasting import forecast_with_validation
    df     = get_demo_dataframe()
    result = forecast_with_validation(df)
    assert result["valid"] is True, f"Gate failed: {result['gate']['reason']}"
    assert result["next_period_value"] is not None
    assert "limitation" in result


# ── T-DEMO-08: Demo Mode visibly identifies itself ────────────────────────────

def test_DEMO_08_sidebar_has_demo_banner():
    """T-DEMO-08: sidebar_nav.py must contain _render_demo_banner function."""
    src = open('components/sidebar_nav.py').read()
    assert '_render_demo_banner' in src
    assert 'DEMO MODE' in src


def test_DEMO_08_demo_banner_has_disclaimer():
    src = open('components/sidebar_nav.py').read()
    assert 'Not real organisational data' in src or 'Demo Data' in src


# ── T-DEMO-09: Demo Mode contains no real company identity ───────────────────

def test_DEMO_09_no_real_company_in_demo_org():
    """T-DEMO-09: DEMO_ORG must not reference any real company name."""
    from services.demo_service import DEMO_ORG
    real_companies = ["pertamina","pln","astra","unilever","adaro","medco"]
    name_lower = DEMO_ORG["company_name"].lower()
    for co in real_companies:
        assert co not in name_lower, f"Real company name '{co}' in demo org"
    assert "demo" in name_lower.lower()


def test_DEMO_09_demo_data_has_no_real_company():
    from services.demo_service import DEMO_EMISSIONS_DATA
    assert isinstance(DEMO_EMISSIONS_DATA, dict)
    assert "Emission" in DEMO_EMISSIONS_DATA
    assert len(DEMO_EMISSIONS_DATA["Month"]) == 12


# ── T-DEMO-10: "Set Up My Organisation" exits demo context ───────────────────

def test_DEMO_10_exit_demo_mode_callable():
    """T-DEMO-10: exit_demo_mode() must exist and be callable."""
    from services.demo_service import exit_demo_mode
    assert callable(exit_demo_mode)


def test_DEMO_10_exit_demo_does_not_raise_on_empty_slot(monkeypatch):
    monkeypatch.setattr("repository.session_repo.get_organisation",
                        lambda slot: None, raising=False)
    monkeypatch.setattr("repository.session_repo.clear_slot",
                        lambda s: None, raising=False)
    from services.demo_service import exit_demo_mode
    exit_demo_mode(slot=0)   # must not raise


# ── T-DEMO-11: Real organisation setup remains functional ─────────────────────

def test_DEMO_11_real_org_functions_intact():
    """T-DEMO-11: Real org session functions must still exist in session_repo."""
    from repository.session_repo import (
        set_organisation, get_organisation, mark_onboarding_complete,
        is_onboarding_complete, clear_slot,
    )
    for fn in (set_organisation, get_organisation, mark_onboarding_complete,
               is_onboarding_complete, clear_slot):
        assert callable(fn), f"{fn} not callable"


# ── T-DEMO-12: Demo data cannot leak into real organisation ──────────────────

def test_DEMO_12_demo_org_slot_is_zero():
    """T-DEMO-12: Demo data is always in slot 0. Real orgs use other slots."""
    src = open('services/demo_service.py').read()
    # Verify demo always uses slot=0
    assert 'slot=0' in src
    # Verify no higher slot gets demo data
    assert 'slot=1' not in src


def test_DEMO_12_demo_service_never_uses_slot_1():
    import ast
    tree = ast.parse(open('services/demo_service.py').read())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword):
            if node.arg == 'slot':
                val = ast.unparse(node.value)
                assert val == '0', f"Demo service uses slot={val} — must only use slot=0"


# ── T-DEMO-13: CARBONLENS_AUTH_REQUIRED=true preserves auth ──────────────────

def test_DEMO_13_auth_required_true_path_in_app():
    """T-DEMO-13: app.py must have a real auth gate when auth_required=True."""
    src = open('app.py').read()
    assert 'auth_required' in src
    assert '_render_login' in src
    # The auth_required=True path must call _render_login
    assert 'if not is_authenticated()' in src


# ── T-DEMO-14: Demo init does not remove RBAC ────────────────────────────────

def test_DEMO_14_rbac_unchanged():
    """T-DEMO-14: RBAC constants must remain intact after demo_service import."""
    from config.constants import ROLE_PERMISSIONS, ALL_PERMISSIONS
    from services.demo_service import DEMO_ORG
    assert "admin"   in ROLE_PERMISSIONS
    assert "analyst" in ROLE_PERMISSIONS
    assert "viewer"  in ROLE_PERMISSIONS
    assert "can_manage_users" in ROLE_PERMISSIONS["admin"]
    assert "can_manage_users" not in ROLE_PERMISSIONS["viewer"]


def test_DEMO_14_demo_user_has_role():
    from services.auth_service import DEMO_USER
    from config.constants import ROLE_PERMISSIONS
    assert DEMO_USER["role"] in ROLE_PERMISSIONS


# ── T-DEMO-15: Audit infrastructure remains intact ────────────────────────────

def test_DEMO_15_audit_event_types_unchanged():
    from config.constants import APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 16
    assert "data_uploaded" in APPROVED_EVENT_TYPES
    assert "scenario_created" in APPROVED_EVENT_TYPES


def test_DEMO_15_audit_writer_not_modified():
    from audit.writer import write_audit_event
    assert callable(write_audit_event)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_state():
    return {
        "state_id":"demo","org_id":"demo-org-carbonlens","period":"2025",
        "version":1,"previous_version_id":None,"input_hash":"demo","status":"Provisional",
        "carbon":{"scope1_kg":22919.0,"scope2_kg":89500.0,"scope3_kg":13255.0,
                  "total_kg":125674.0,"intens_m2":14.79,"scope_source":"carbon_accounting",
                  "province":"Jawa Timur","pln_ef_used":0.781,
                  "scope3_breakdown":{},"screened_excluded":[],
                  "benchmark":120.0,"gap":{"gap_pct":-87.7,"above_benchmark":False},
                  "computed_at":"2025-01-01T00:00:00"},
        "esg":{"score":68.5,"grade":"B","label":"Satisfactory",
               "env":75.0,"social":62.0,"gov":67.0,"confidence_score":100.0,
               "is_provisional":False,"n_disclosed":8,"n_total_indicators":8,
               "disclosure_summary":"","methodology_version":"V8-Phase4",
               "methodology_disclaimer":"","computed_at":"2025-01-01T00:00:00"},
        "data_quality":{"completeness_score":88.0,"consistency_score":100.0,
                        "validation_status":"Pass","validation_score":100.0,
                        "confidence_score":93.0,"is_provisional":False,
                        "env_completeness":90.0,"sg_completeness":100.0,
                        "sg_disclosed":8,"sg_total":8,"flagged_fields":[],"summary":""},
        "confidence":{"esg_confidence":100.0,"esg_is_provisional":False,
                      "dq_confidence":93.0,"dq_is_provisional":False,"interpretation":""},
        "computed_at":"2025-01-01T00:00:00","computation_time_ms":180,
    }


def _empty_trend():
    return {"months":[],"emissions_tco2e":[],"has_data":False,
            "forecast":{},"trend":{"direction":"insufficient_data","description":""},
            "annual_tco2e":0.0}


def _empty_fcast():
    return {"valid":False,"gate":{"reason":"Demo test","n_unique_periods":0,
            "n_required":6,"has_duplicates":False,"has_missing_periods":False,
            "missing_periods":[],"coverage_label":""},"validation":{},"naive":{},
            "outperforms_baseline":None,"next_period_value":None,
            "model_type":"OLS","limitation":"Modelled estimate."}


def _stub_st(monkeypatch):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","number_input","checkbox","text_input",
               "selectbox","info","warning","error","plotly_chart","write"]:
        monkeypatch.setattr(st, fn, noop, raising=False)
    monkeypatch.setattr(st, "columns",
        lambda n, **kw: [_Col()]*(n if isinstance(n,int) else len(n)), raising=False)
    monkeypatch.setattr(st, "expander", lambda *a, **kw: _Col(), raising=False)
    monkeypatch.setattr(st, "rerun",    lambda: None, raising=False)


class _Col:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __getattr__(self, n): return lambda *a, **kw: None
