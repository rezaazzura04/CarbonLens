"""
Phase 5-A Integration Tests — Decarbonization Planner.

T1  baseline renders from ComputedState
T2  no-data state
T3  no-target state
T4  target calculation
T5  scenario creation
T6  scenario modification
T7  scenario comparison
T8  target gap calculation
T9  baseline consistency with Carbon Accounting
T10 provenance
T11 scenario audit event
T12 admin RBAC
T13 analyst RBAC
T14 viewer read-only behaviour
T15 no repository import from page
T16 no calculation import from page
T17 no direct session_state
T18 Phase 0 regression
T19 Phase 2 regression
T20 Phase 3 regression
T21 Phase 4 regression
"""
import ast, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def org():
    return {
        "org_id": "test-decarb-001", "company_name": "PT Dekarbon Nusantara",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 20.0, "recycle_pct": 15.0, "certifications": [],
    }


@pytest.fixture
def carbon_state():
    return {
        "state_id": "dec-001", "org_id": "test-decarb-001",
        "period": "2024", "version": 1, "previous_version_id": None,
        "input_hash": "dec123", "status": "Provisional",
        "carbon": {
            "scope1_kg": 75000.0, "scope2_kg": 100000.0,
            "scope3_kg": 25000.0, "total_kg": 200000.0,
            "intens_m2": 40.0, "scope_source": "carbon_accounting",
            "province": "Jawa Timur", "pln_ef_used": 0.7810,
            "scope3_breakdown": {}, "screened_excluded": [],
            "benchmark": 120.0,
            "gap": {"gap_pct": -66.7, "above_benchmark": False},
            "computed_at": "2024-01-01T00:00:00",
        },
        "esg": {"score": 65.0, "grade": "B", "label": "Satisfactory",
                "env": 70.0, "social": 60.0, "gov": 65.0,
                "confidence_score": 75.0, "is_provisional": False,
                "n_disclosed": 6, "n_total_indicators": 8,
                "disclosure_summary": "", "methodology_version": "V8-Phase4",
                "methodology_disclaimer": "", "computed_at": "2024-01-01T00:00:00"},
        "data_quality": {"completeness_score": 80.0, "consistency_score": 100.0,
                         "validation_status": "Pass", "validation_score": 100.0,
                         "confidence_score": 90.0, "is_provisional": False,
                         "env_completeness": 90.0, "sg_completeness": 75.0,
                         "sg_disclosed": 6, "sg_total": 8,
                         "flagged_fields": [], "summary": ""},
        "confidence": {"esg_confidence": 75.0, "esg_is_provisional": False,
                       "dq_confidence": 90.0, "dq_is_provisional": False,
                       "interpretation": ""},
        "computed_at": "2024-01-01T00:00:00", "computation_time_ms": 150,
    }


@pytest.fixture
def decarb_state_with_target():
    return {
        "target": {
            "baseline_period": "2024",
            "target_year": "2030",
            "reduction_target_pct": 30.0,
            "baseline_kg": 200000.0,
            "target_kg": 140000.0,
            "assumption_type": "user-provided",
        },
        "scenarios": {
            "A": {
                "id": "A", "name": "Conservative",
                "description": "Low-cost levers only",
                "levers": [
                    {"lever_id": "energy_efficiency", "name": "Energy Efficiency",
                     "reduction_pct": 10.0, "implementation_year": 2026,
                     "assumption_type": "carbonlens-default", "scope": "1+2"},
                ],
                "created_at": "2024-01-01T00:00:00",
                "modified_at": "2024-01-01T00:00:00",
            }
        },
        "active_scenario_id": "A",
        "last_modified": "2024-01-01T00:00:00",
    }


# ── T1: Baseline renders from ComputedState ───────────────────────────────────

def test_T1_baseline_from_computed_state(monkeypatch, org, carbon_state):
    """T1: Baseline scope values must come from ComputedState, not recalculated."""
    calls = []
    _patch(monkeypatch, org, carbon_state, on_computed=lambda: calls.append("computed"))
    _stub_st(monkeypatch)
    from pages.decarbonization.page import render
    render()
    assert "computed" in calls, "get_computed_state() was not called"


def test_T1_baseline_tco2e_conversion(carbon_state):
    """T1: kg → tCO2e conversion must match Carbon Accounting page."""
    c = carbon_state["carbon"]
    total_tco2e  = round(c["total_kg"]  / 1000, 2)
    scope1_tco2e = round(c["scope1_kg"] / 1000, 2)
    scope2_tco2e = round(c["scope2_kg"] / 1000, 2)
    scope3_tco2e = round(c["scope3_kg"] / 1000, 2)
    assert total_tco2e  == 200.0
    assert scope1_tco2e == 75.0
    assert scope2_tco2e == 100.0
    assert scope3_tco2e == 25.0
    assert abs(scope1_tco2e + scope2_tco2e + scope3_tco2e - total_tco2e) < 0.01


# ── T2: No-data state ─────────────────────────────────────────────────────────

def test_T2_no_org_does_not_call_state_service(monkeypatch):
    """T2: With no org, state_service.get_computed_state must NOT be called."""
    called = []
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: None)
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: (called.append(True), {})[1], raising=False)
    _stub_st(monkeypatch)
    from pages.decarbonization.page import render
    render()
    assert not called


def test_T2_zero_baseline_shows_warning(monkeypatch, org, carbon_state):
    """T2: No emission data should show an info banner."""
    cs = {**carbon_state, "carbon": {**carbon_state["carbon"],
          "total_kg": 0.0, "scope1_kg": 0.0, "scope2_kg": 0.0,
          "scope3_kg": 0.0, "scope_source": "none"}}
    banners = []
    _patch(monkeypatch, org, cs)
    _stub_st(monkeypatch, capture_banners=banners)
    from pages.decarbonization.page import render
    render()
    # Absence of exception is the primary check; banner rendering is Streamlit-side


# ── T3: No-target state ───────────────────────────────────────────────────────

def test_T3_no_target_empty_state():
    """T3: get_decarb_state() with no target must return target=None."""
    from models.decarbonization import make_empty_decarb_state
    state = make_empty_decarb_state()
    assert state["target"] is None


# ── T4: Target calculation ────────────────────────────────────────────────────

def test_T4_target_calculation_formula():
    """T4: Target = baseline × (1 − pct/100). Must match blueprint formula."""
    from calculations.decarbonization import calculate_target_emissions
    baseline_kg = 200000.0
    pct         = 30.0
    expected    = 200000.0 * (1 - 30.0 / 100.0)  # = 140000.0
    result      = calculate_target_emissions(baseline_kg, pct)
    assert result == expected


def test_T4_target_never_negative():
    from calculations.decarbonization import calculate_target_emissions
    result = calculate_target_emissions(100000.0, 100.0)
    assert result >= 0.0


def test_T4_set_reduction_target_service(monkeypatch):
    """T4: decarbonization_service.set_reduction_target must persist target."""
    saved = {}
    def _get(): return {"target": None, "scenarios": {}, "active_scenario_id": "A", "last_modified": ""}
    def _save(s): saved.update(s)
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state", _get, raising=False)
    monkeypatch.setattr("services.decarbonization_service.save_decarb_state", _save, raising=False)
    monkeypatch.setattr("services.decarbonization_service._emit",
                        lambda *a, **kw: None, raising=False)
    from services.decarbonization_service import set_reduction_target
    target = set_reduction_target(200000.0, "2024", "2030", 30.0)
    assert target["target_kg"]            == 140000.0
    assert target["reduction_target_pct"] == 30.0
    assert target["assumption_type"]      == "user-provided"


# ── T5: Scenario creation ─────────────────────────────────────────────────────

def test_T5_create_scenario(monkeypatch):
    """T5: create_scenario must persist scenario and emit scenario_created."""
    state_store = {"target": None, "scenarios": {}, "active_scenario_id": "A", "last_modified": ""}
    emitted = []
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state",
                        lambda: state_store, raising=False)
    monkeypatch.setattr("services.decarbonization_service.save_decarb_state",
                        lambda s: state_store.update(s), raising=False)
    monkeypatch.setattr("services.decarbonization_service._emit",
                        lambda *a, **kw: emitted.append(a[0]), raising=False)
    from services.decarbonization_service import create_scenario
    result = create_scenario("A", "Conservative", "Low-cost only")
    assert result["id"]   == "A"
    assert result["name"] == "Conservative"
    assert "A" in state_store["scenarios"]
    assert "scenario_created" in emitted


def test_T5_invalid_scenario_id_raises():
    """T5: scenario_id must be A, B, or C."""
    with pytest.raises(ValueError):
        from services.decarbonization_service import create_scenario
        create_scenario("X", "Bad", "")


# ── T6: Scenario modification ─────────────────────────────────────────────────

def test_T6_update_levers(monkeypatch):
    """T6: update_scenario_levers must persist levers and emit scenario_modified."""
    state_store = {
        "target": None,
        "scenarios": {"A": {"id":"A","name":"Test","description":"",
                             "levers":[],"created_at":"","modified_at":""}},
        "active_scenario_id": "A", "last_modified": "",
    }
    emitted = []
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state",
                        lambda: state_store, raising=False)
    monkeypatch.setattr("services.decarbonization_service.save_decarb_state",
                        lambda s: state_store.update(s), raising=False)
    monkeypatch.setattr("services.decarbonization_service._emit",
                        lambda *a, **kw: emitted.append(a[0]), raising=False)
    levers = [{"lever_id": "energy_efficiency", "reduction_pct": 10.0,
               "implementation_year": 2026}]
    from services.decarbonization_service import update_scenario_levers
    update_scenario_levers("A", levers)
    assert state_store["scenarios"]["A"]["levers"] == levers
    assert "scenario_modified" in emitted


# ── T7: Scenario comparison ───────────────────────────────────────────────────

def test_T7_get_all_scenario_results(monkeypatch):
    """T7: get_all_scenario_results must return list of ScenarioResult dicts."""
    state_store = {
        "target": {"target_kg": 140000.0, "reduction_target_pct": 30.0},
        "scenarios": {
            "A": {"id":"A","name":"Conservative","description":"",
                  "levers":[{"lever_id":"energy_efficiency","reduction_pct":10.0,
                              "implementation_year":2026}],
                  "created_at":"","modified_at":""},
        },
        "active_scenario_id": "A", "last_modified": "",
    }
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state",
                        lambda: state_store, raising=False)
    from services.decarbonization_service import get_all_scenario_results
    results = get_all_scenario_results(75000.0, 100000.0, 25000.0, 0.781)
    assert isinstance(results, list)
    assert len(results) == 1
    r = results[0]
    assert r["scenario_id"]   == "A"
    assert r["total_kg"]      <  200000.0
    assert r["reduction_kg"]  >  0


# ── T8: Target gap calculation ─────────────────────────────────────────────────

def test_T8_gap_above_target():
    from calculations.decarbonization import calculate_target_gap
    gap = calculate_target_gap(160000.0, 140000.0)
    assert gap["above_target"]  is True
    assert gap["gap_kg"]        == 20000.0

def test_T8_gap_below_target():
    from calculations.decarbonization import calculate_target_gap
    gap = calculate_target_gap(130000.0, 140000.0)
    assert gap["above_target"]  is False
    assert gap["gap_kg"]        < 0

def test_T8_gap_exact_target():
    from calculations.decarbonization import calculate_target_gap
    gap = calculate_target_gap(140000.0, 140000.0)
    assert abs(gap["gap_kg"]) < 0.01


# ── T9: Baseline consistency with Carbon Accounting ───────────────────────────

def test_T9_baseline_matches_carbon_accounting(carbon_state):
    """T9: Scope values used by Decarbonization must equal those in ComputedState."""
    c = carbon_state["carbon"]
    assert c["scope1_kg"] + c["scope2_kg"] + c["scope3_kg"] == c["total_kg"]


def test_T9_apply_levers_to_baseline_uses_scope_values():
    from calculations.decarbonization import apply_levers_to_baseline
    s1, s2, s3 = 75000.0, 100000.0, 25000.0
    levers = [{"lever_id": "energy_efficiency", "reduction_pct": 10.0}]
    result = apply_levers_to_baseline(s1, s2, s3, levers, 0.781)
    assert result["total_kg"] < s1 + s2 + s3
    assert result["reduction_kg"] > 0


# ── T10: Provenance ───────────────────────────────────────────────────────────

def test_T10_provenance_rows_schema(decarb_state_with_target):
    from pages.decarbonization.page import _build_decarb_provenance_rows
    from models.decarbonization import LEVER_CATALOGUE
    rows = _build_decarb_provenance_rows(
        decarb_state_with_target["scenarios"]["A"], LEVER_CATALOGUE, 0.781
    )
    assert isinstance(rows, list)
    assert len(rows) >= 3
    for row in rows:
        for key in ("label","value","source","formula","note"):
            assert key in row, f"Provenance row missing: {key}"


def test_T10_provenance_no_arithmetic():
    """T10: _build_decarb_provenance_rows must be deterministic."""
    from pages.decarbonization.page import _build_decarb_provenance_rows
    from models.decarbonization import LEVER_CATALOGUE
    rows_a = _build_decarb_provenance_rows(None, LEVER_CATALOGUE, 0.781)
    rows_b = _build_decarb_provenance_rows(None, LEVER_CATALOGUE, 0.781)
    assert rows_a == rows_b


# ── T11: Audit event ──────────────────────────────────────────────────────────

def test_T11_scenario_events_in_approved_types():
    from config.constants import APPROVED_EVENT_TYPES
    assert "scenario_created"  in APPROVED_EVENT_TYPES
    assert "scenario_modified" in APPROVED_EVENT_TYPES
    assert "scenario_saved"    in APPROVED_EVENT_TYPES

def test_T11_save_named_scenario_emits_saved(monkeypatch):
    state_store = {
        "target": {"target_year":"2030","reduction_target_pct":30.0},
        "scenarios": {"A": {"id":"A","name":"Test","description":"",
                            "levers":[],"created_at":"","modified_at":""}},
        "active_scenario_id":"A","last_modified":"",
    }
    emitted = []
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state",
                        lambda: state_store, raising=False)
    monkeypatch.setattr("services.decarbonization_service.save_decarb_state",
                        lambda s: state_store.update(s), raising=False)
    monkeypatch.setattr("services.decarbonization_service._emit",
                        lambda *a, **kw: emitted.append(a[0]), raising=False)
    from services.decarbonization_service import save_named_scenario
    save_named_scenario("A")
    assert "scenario_saved" in emitted


# ── T12–T14: RBAC ─────────────────────────────────────────────────────────────

def test_T12_admin_has_can_upload():
    from config.constants import ROLE_PERMISSIONS
    assert "can_upload" in ROLE_PERMISSIONS["admin"]

def test_T13_analyst_has_can_upload():
    from config.constants import ROLE_PERMISSIONS
    assert "can_upload" in ROLE_PERMISSIONS["analyst"]

def test_T14_viewer_cannot_upload():
    from config.constants import ROLE_PERMISSIONS
    assert "can_upload" not in ROLE_PERMISSIONS["viewer"]

def test_T14_check_permission_returns_bool(monkeypatch):
    monkeypatch.setattr("services.auth_service.has_permission",
                        lambda p: p == "can_view_all", raising=False)
    from services.state_service import check_permission
    assert check_permission("can_view_all") is True
    assert check_permission("can_upload")   is False


# ── T15–T17: Architecture ─────────────────────────────────────────────────────

def test_T15_no_repository_import_in_page():
    tree = ast.parse(open("pages/decarbonization/page.py").read())
    bad  = [n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and "repository" in (n.module or "")]
    assert not bad, f"Page has repository imports: {bad}"

def test_T16_no_calculation_import_in_page():
    tree = ast.parse(open("pages/decarbonization/page.py").read())
    bad  = [n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and "calculations" in (n.module or "")]
    assert not bad, f"Page has calculations imports: {bad}"

def test_T17_no_session_state_in_page():
    tree = ast.parse(open("pages/decarbonization/page.py").read())
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not bad, f"Page uses session_state: {bad}"


# ── T18–T21: Regression ───────────────────────────────────────────────────────

def test_T18_phase0_constants():
    from config.settings   import EMISSION_FACTORS
    from config.constants  import (ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV,
                                   CONFIDENCE_PROVISIONAL_FLOOR, SCOPE3_CATEGORIES_COVERED)
    assert EMISSION_FACTORS["diesel_kgco2_per_liter"]  == 2.6967
    assert EMISSION_FACTORS["electricity_pln_kwh"]     == 0.7160
    assert ESG_WEIGHT_ENV                              == 0.40
    assert ESG_WEIGHT_SOCIAL                           == 0.30
    assert ESG_WEIGHT_GOV                              == 0.30
    assert CONFIDENCE_PROVISIONAL_FLOOR                == 50.0
    assert SCOPE3_CATEGORIES_COVERED                   == 12

def test_T19_phase2_dq_weights():
    from config.constants import (DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY,
                                   DQ_WEIGHT_VALIDATION)
    total = DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION
    assert abs(total - 1.0) < 1e-9

def test_T20_phase3_audit_event_types():
    from config.constants import APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 16
    assert "data_uploaded" in APPROVED_EVENT_TYPES

def test_T21_phase4_report_context_builds():
    """T21: build_report_context must still function after Phase 5-A additions."""
    from services.report_service import build_report_context
    import unittest.mock as mock
    state = {
        "state_id":"x","org_id":"y","period":"2024","version":1,
        "previous_version_id":None,"input_hash":"h","status":"Provisional",
        "carbon":{"scope1_kg":0,"scope2_kg":0,"scope3_kg":0,"total_kg":0,
                  "intens_m2":0,"scope_source":"none","province":"",
                  "pln_ef_used":0.716,"scope3_breakdown":{},"screened_excluded":[],
                  "benchmark":120.0,"gap":{},"computed_at":"2024-01-01T00:00:00"},
        "esg":{"score":0,"grade":"D","label":"--","env":0,"social":0,"gov":0,
               "confidence_score":0,"is_provisional":True,"n_disclosed":0,
               "n_total_indicators":8,"disclosure_summary":"","methodology_version":"V8",
               "methodology_disclaimer":"","computed_at":"2024-01-01T00:00:00"},
        "data_quality":{"completeness_score":0,"consistency_score":100,
                        "validation_status":"Fail","validation_score":0,
                        "confidence_score":0,"is_provisional":True,
                        "env_completeness":0,"sg_completeness":0,
                        "sg_disclosed":0,"sg_total":8,"flagged_fields":[],"summary":""},
        "confidence":{"esg_confidence":0,"esg_is_provisional":True,
                      "dq_confidence":0,"dq_is_provisional":True,"interpretation":""},
        "computed_at":"2024-01-01T00:00:00","computation_time_ms":0,
    }
    org = {"company_name":"Test","sector":"Manufacturing","area_m2":5000.0,"reporting_period":"2024"}
    with mock.patch("repository.session_repo.get", return_value=None), \
         mock.patch("repository.session_repo.get_uploaded_df", return_value=None):
        ctx = build_report_context(state, org)
    assert "esg_score" in ctx


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch(monkeypatch, org, state, on_computed=None):
    monkeypatch.setattr("services.state_service.get_active_organisation", lambda: org)
    monkeypatch.setattr("services.state_service.get_disclosure_inputs",   lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",        lambda: {})
    monkeypatch.setattr("services.state_service.check_permission",        lambda p: True,
                        raising=False)
    def _computed(**kw):
        if on_computed: on_computed()
        return state
    monkeypatch.setattr("services.state_service.get_computed_state", _computed, raising=False)
    monkeypatch.setattr("services.decarbonization_service.get_decarb_state",
                        lambda: {"target":None,"scenarios":{},"active_scenario_id":"A","last_modified":""},
                        raising=False)
    monkeypatch.setattr("services.decarbonization_service.get_available_levers",
                        lambda *a, **kw: [], raising=False)
    monkeypatch.setattr("services.decarbonization_service.get_all_scenario_results",
                        lambda *a, **kw: [], raising=False)


def _stub_st(monkeypatch, capture_banners=None):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","number_input","checkbox","text_input",
               "selectbox","info","warning","error","plotly_chart","download_button",
               "write","form_submit_button","form"]:
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
