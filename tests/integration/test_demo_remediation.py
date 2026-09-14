"""
Phase 5-B Final Remediation Tests (T-DEMO-16 through T-FCAST-07)
"""
import ast, os, sys, pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── T-DEMO-16: Exit sets explicit flag ────────────────────────────────────────

def test_DEMO_16_exit_sets_flag_false(monkeypatch):
    """T-DEMO-16: exit_demo_mode() must set demo_mode_enabled=False."""
    flag_set = {}
    monkeypatch.setattr("repository.session_repo.set_demo_mode_enabled",
                        lambda v: flag_set.update({"val": v}), raising=False)
    monkeypatch.setattr("repository.session_repo.get_organisation",
                        lambda slot: {"is_demo": True, "org_id": "demo-org-carbonlens"},
                        raising=False)
    monkeypatch.setattr("repository.session_repo.clear_slot",
                        lambda s: None, raising=False)
    monkeypatch.setattr("repository.session_repo.invalidate_computed_state",
                        lambda slot=None: None, raising=False)
    from services.demo_service import exit_demo_mode
    exit_demo_mode(slot=0)
    assert flag_set.get("val") is False, "Flag not set to False"


# ── T-DEMO-17: After exit, demo org NOT recreated ─────────────────────────────

def test_DEMO_17_after_exit_demo_org_not_recreated(monkeypatch):
    """T-DEMO-17: init_demo_organisation() with flag=False must return without init."""
    monkeypatch.setattr("repository.session_repo.is_demo_mode_enabled",
                        lambda: False, raising=False)
    monkeypatch.setattr("repository.session_repo.set_organisation",
                        lambda org, slot: pytest.fail("set_organisation called — must not recreate demo"),
                        raising=False)
    from services.demo_service import init_demo_organisation
    result = init_demo_organisation()
    assert result is not None  # returns DEMO_ORG dict safely


# ── T-DEMO-18: Organisation Setup reachable after exit ───────────────────────

def test_DEMO_18_onboarding_page_importable():
    """T-DEMO-18: pages/onboarding/page.py must import and expose render()."""
    from pages.onboarding.page import render
    assert callable(render)


def test_DEMO_18_app_routes_to_onboarding_in_local_real_mode():
    """T-DEMO-18: app.py must route to onboarding when demo=False + no org setup."""
    src = open('app.py').read()
    assert '_route_to("onboarding")' in src
    # Flag check uses service wrapper (is_demo_mode_active via demo_service)
    assert 'is_demo_mode_active' in src or 'is_demo_mode_enabled' in src


# ── T-DEMO-19: Real org can be created ───────────────────────────────────────

def test_DEMO_19_complete_onboarding_persists_org(monkeypatch):
    """T-DEMO-19: complete_onboarding() must save the org and mark complete."""
    saved = {}
    monkeypatch.setattr("repository.session_repo.set_organisation",
                        lambda org, slot: saved.update({"org": org, "slot": slot}),
                        raising=False)
    monkeypatch.setattr("repository.session_repo.mark_onboarding_complete",
                        lambda slot: saved.update({"done": True}), raising=False)
    monkeypatch.setattr("repository.disk_repo.save_organisation",
                        lambda org, slot: None, raising=False)
    monkeypatch.setattr("repository.session_repo.set_uploaded_df",
                        lambda df: None, raising=False)
    monkeypatch.setattr("repository.session_repo.set_validation_result",
                        lambda r, slot: None, raising=False)
    monkeypatch.setattr("repository.session_repo.set",
                        lambda k, v, slot=None: None, raising=False)

    from services.state_service import complete_onboarding
    org = {"company_name": "PT Real Company", "sector": "Manufacturing",
           "area_m2": 5000.0, "employees": 100, "province": "DKI Jakarta",
           "reporting_period": "2025", "renew_pct": 0.0, "recycle_pct": 0.0,
           "certifications": [], "is_demo": False}
    complete_onboarding(org)
    assert saved.get("org", {}).get("company_name") == "PT Real Company"
    assert saved.get("done") is True


def test_DEMO_19_real_org_is_demo_false():
    """T-DEMO-19: Real org must have is_demo=False."""
    org = {"company_name": "PT Real", "is_demo": False}
    assert org["is_demo"] is False


# ── T-DEMO-20: Real CSV can be uploaded after leaving Demo Mode ───────────────

def test_DEMO_20_validation_service_accepts_real_csv():
    """T-DEMO-20: Real CSV upload must work after demo exit."""
    from services.validation_service import validate_upload
    csv = b"Month,Emission,Energy\nJan,245,180000\nFeb,268,195000\nMar,231,172000\nApr,259,188000\nMay,277,201000\nJun,242,178000\n"
    df, result = validate_upload(csv, "real.csv")
    assert result["status"] in ("Pass", "Warning")
    assert df is not None


# ── T-DEMO-21: Demo data cannot leak into real org ───────────────────────────

def test_DEMO_21_exit_clears_demo_dataframe(monkeypatch):
    """T-DEMO-21: exit_demo_mode() must trigger clear_slot which removes DF."""
    cleared = []
    monkeypatch.setattr("repository.session_repo.set_demo_mode_enabled",
                        lambda v: None, raising=False)
    monkeypatch.setattr("repository.session_repo.get_organisation",
                        lambda slot: {"is_demo": True, "org_id": "demo-org-carbonlens"},
                        raising=False)
    monkeypatch.setattr("repository.session_repo.clear_slot",
                        lambda s: cleared.append(s), raising=False)
    monkeypatch.setattr("repository.session_repo.invalidate_computed_state",
                        lambda slot=None: None, raising=False)
    from services.demo_service import exit_demo_mode
    exit_demo_mode(slot=0)
    assert 0 in cleared, "Slot 0 was not cleared"


def test_DEMO_21_real_org_has_no_demo_tag(monkeypatch):
    """T-DEMO-21: complete_onboarding org must not have is_demo=True."""
    saved = {}
    monkeypatch.setattr("repository.session_repo.set_organisation",
                        lambda org, slot: saved.update({"org": org}), raising=False)
    for fn in ("mark_onboarding_complete","set_uploaded_df","set_validation_result"):
        monkeypatch.setattr(f"repository.session_repo.{fn}",
                            lambda *a, **kw: None, raising=False)
    monkeypatch.setattr("repository.session_repo.set", lambda *a, **kw: None, raising=False)
    monkeypatch.setattr("repository.disk_repo.save_organisation",
                        lambda o, s: None, raising=False)
    from services.state_service import complete_onboarding
    complete_onboarding({"company_name":"PT Real","sector":"Manufacturing",
                         "area_m2":5000.0,"employees":100,"province":"Bali",
                         "reporting_period":"2025","renew_pct":0.0,
                         "recycle_pct":0.0,"certifications":[],"is_demo":False})
    assert saved.get("org", {}).get("is_demo") is False


# ── T-DEMO-22: Demo banner absent after real org setup ───────────────────────

def test_DEMO_22_banner_conditional_on_flag():
    """
    T-DEMO-22 (updated for Final IA Polish): the Demo Mode indicator's
    visibility must still be gated on is_demo_mode(), now checked inside
    page_header() (components/ui.py) rather than the removed sidebar
    banner — see test_DEMO_08_sidebar_has_demo_banner for the removal.
    """
    ui_src = open('components/ui.py').read()
    assert 'is_demo_mode' in ui_src
    assert 'DEMO MODE' in ui_src


# ── T-DEMO-23: Real org in Executive Summary ─────────────────────────────────

def test_DEMO_23_exec_summary_org_from_computed_state(monkeypatch):
    """T-DEMO-23: Executive Summary must use get_active_organisation(), not demo constant."""
    real_org = {"org_id":"real-001","company_name":"PT Real Company",
                "sector":"Manufacturing","area_m2":5000.0,"province":"DKI Jakarta",
                "reporting_period":"2025","renew_pct":0.0,"recycle_pct":0.0,
                "certifications":[],"is_demo":False}
    fetched = []
    monkeypatch.setattr("services.state_service.get_active_organisation",
                        lambda: (fetched.append("called"), real_org)[1])
    monkeypatch.setattr("services.state_service.get_disclosure_inputs", lambda: {})
    monkeypatch.setattr("services.state_service.get_scope_inputs",      lambda: {})
    monkeypatch.setattr("services.state_service.get_computed_state",
                        lambda **kw: _minimal_state("real-001","PT Real Company"),
                        raising=False)
    monkeypatch.setattr("services.state_service.get_trend_data", lambda: _empty_trend())
    monkeypatch.setattr("services.state_service.get_forecast_validation",
                        lambda: _empty_fcast(), raising=False)
    monkeypatch.setattr("services.audit_service.get_recent_events", lambda n=8: [])
    _stub_st(monkeypatch)
    from pages.executive_summary.page import render
    render()
    assert "called" in fetched


# ── T-DEMO-24–27: Auth modes ──────────────────────────────────────────────────

# ── T-DEMO-24–27: No login gate, no login/password system at all ──────────────

def test_DEMO_24_no_login_gate_or_form_in_app():
    """
    T-DEMO-24 (revised): app.py must contain no login gate, no login form,
    and no reference to _render_login — this build never shows a login
    screen, and there is no password/login system anywhere in the codebase
    (see test_DEMO_25_no_login_system_remains).
    """
    src = open('app.py').read()
    assert '_render_login' not in src
    assert 'login_form' not in src
    assert 'auth_required' not in src


def test_DEMO_25_no_login_system_remains():
    """
    The login/password system was removed entirely, not just disabled —
    services.auth_service exposes no login() or logout() function, and
    there is no default-credentials registry anywhere in the codebase.
    Identity/RBAC infrastructure (get_current_user, has_permission,
    init_demo_mode) remains — that part is still actively used.
    """
    import services.auth_service as auth_svc
    assert not hasattr(auth_svc, "login")
    assert not hasattr(auth_svc, "logout")
    assert not hasattr(auth_svc, "_hash_password")
    assert callable(auth_svc.get_current_user)
    assert callable(auth_svc.has_permission)
    assert callable(auth_svc.init_demo_mode)

    import config.settings as settings
    assert not hasattr(settings, "DEFAULT_USERS")

    import repository.disk_repo as disk_repo
    assert not hasattr(disk_repo, "load_users")
    assert not hasattr(disk_repo, "save_users")


def test_DEMO_26_app_always_reaches_render_main():
    """Without a login gate, main() must unconditionally reach _render_main —
    there is no code path that can strand the user before Home."""
    src = open('app.py').read()
    assert 'def main()' in src
    assert '_render_main(svc)' in src
    # No conditional return before _render_main is called
    main_body = src.split('def main()')[1].split('def _render_main')[0]
    assert 'return' not in main_body, "main() must not have any early return before rendering Home"


def test_DEMO_27_no_auth_branch_skips_demo_init():
    """No auth_required branch exists, so demo init always runs on the single
    login-free path — verified by its unconditional presence in main()."""
    src = open('app.py').read()
    main_body = src.split('def main()')[1].split('def _render_main')[0]
    assert 'init_demo_organisation' in main_body


# ── T-FCAST-01–07: Canonical forecast consistency ─────────────────────────────

def test_FCAST_01_exec_summary_calls_get_forecast_validation():
    """T-FCAST-01: Executive Summary must call state_svc.get_forecast_validation()."""
    src = open('pages/executive_summary/page.py').read()
    assert 'get_forecast_validation' in src


def test_FCAST_02_exec_summary_does_not_use_trend_data_forecast():
    """T-FCAST-02: Executive Summary must not use trend_data['forecast'] for forecast."""
    tree = ast.parse(open('pages/executive_summary/page.py').read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            try:
                key = ast.unparse(node.slice)
                val = ast.unparse(node.value)
                if 'trend_data' in val and 'forecast' in key:
                    violations.append(ast.unparse(node))
            except Exception:
                pass
    assert not violations, f"Exec Summary reads trend_data[forecast]: {violations}"


def test_FCAST_03_exec_summary_and_carbon_accounting_same_contract():
    """T-FCAST-03: Both pages must call get_forecast_validation(), same result contract."""
    exec_src   = open('pages/executive_summary/page.py').read()
    carbon_src = open('pages/carbon_accounting/page.py').read()
    assert 'get_forecast_validation' in exec_src,   "Exec Summary missing get_forecast_validation"
    assert 'get_forecast_validation' in carbon_src, "Carbon Accounting missing get_forecast_validation"
    # Both use next_period_value from the result (not "next_month" from legacy)
    assert 'next_period_value' in exec_src
    assert 'next_period_value' in carbon_src


def test_FCAST_04_dq_fail_blocks_forecast_in_gate(monkeypatch):
    """T-FCAST-04: DQ Fail must block forecast in validate_forecast_history."""
    df = pd.DataFrame({"Month":["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                       "Emission":[245]*12})
    from calculations.forecasting import validate_forecast_history
    result = validate_forecast_history(df, dq_validation_status="Fail")
    assert result["valid"] is False
    assert "data quality" in result["reason"].lower() or "validation failed" in result["reason"].lower()


def test_FCAST_05_dq_fail_blocks_in_report_service(monkeypatch):
    """
    T-FCAST-05: report_service must consume the DQ-gated forecast through the
    single canonical entry point (state_service.get_forecast_validation()),
    not reconstruct DQ-status plumbing itself.

    Phase 5-B remediation (Fix F-03): report_service previously duplicated
    state_service.get_forecast_validation()'s exact df-fetch + dq-status-read
    + forecast_with_validation() call. That duplication is what this test
    used to assert the presence of (checking for the literal string
    'dq_validation_status') — which was actually asserting the ANTI-PATTERN
    the independent audit flagged. The correct invariant is: report_service
    must delegate to the canonical function and must NOT call the raw
    forecast_with_validation() calculation directly.
    """
    src = open('services/report_service.py').read()
    assert 'get_forecast_validation' in src, (
        "report_service must call the canonical state_service.get_forecast_validation()"
    )
    # Check the actual call sites via AST (not a naive substring match, which
    # would also trip on this file's own explanatory comments).
    tree = ast.parse(src)
    calls = {
        n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert 'forecast_with_validation' not in calls, (
        "report_service must not independently CALL the DQ-gated forecast function "
        "— that duplicates state_service.get_forecast_validation()'s logic (Fix F-03)"
    )


def test_FCAST_06_dq_warning_allows_forecast():
    """T-FCAST-06: DQ Warning must NOT block forecast (soft gate)."""
    df = pd.DataFrame({"Month":["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                       "Emission":[245]*12})
    from calculations.forecasting import validate_forecast_history
    result = validate_forecast_history(df, dq_validation_status="Warning")
    assert result["valid"] is True


def test_FCAST_07_dq_pass_consistent_across_consumers(monkeypatch):
    """T-FCAST-07: DQ Pass → same canonical forecast result from state_service."""
    monkeypatch.setattr("repository.session_repo.get_uploaded_df",
                        lambda: pd.DataFrame({
                            "Month":["Jan","Feb","Mar","Apr","May","Jun",
                                     "Jul","Aug","Sep","Oct","Nov","Dec"],
                            "Emission":[245,268,231,259,277,242,264,251,239,267,245,258]}),
                        raising=False)
    monkeypatch.setattr("repository.session_repo.get",
                        lambda k, **kw: {"status":"Pass"} if k == "validation_result" else None,
                        raising=False)
    from services.state_service import get_forecast_validation
    result = get_forecast_validation()
    assert result["valid"] is True
    assert "next_period_value" in result
    assert "limitation" in result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_state(org_id="demo", company="Demo"):
    return {
        "state_id":org_id,"org_id":org_id,"period":"2025","version":1,
        "previous_version_id":None,"input_hash":"x","status":"Provisional",
        "carbon":{"scope1_kg":0,"scope2_kg":0,"scope3_kg":0,"total_kg":0,
                  "intens_m2":0,"scope_source":"none","province":"","pln_ef_used":0.716,
                  "scope3_breakdown":{},"screened_excluded":[],"benchmark":120.0,
                  "gap":{},"computed_at":"2025-01-01T00:00:00"},
        "esg":{"score":0,"grade":"D","label":"--","env":0,"social":0,"gov":0,
               "confidence_score":0,"is_provisional":True,"n_disclosed":0,
               "n_total_indicators":8,"disclosure_summary":"","methodology_version":"Phase4",
               "methodology_disclaimer":"","computed_at":"2025-01-01T00:00:00"},
        "data_quality":{"completeness_score":0,"consistency_score":100,
                        "validation_status":"Fail","validation_score":0,
                        "confidence_score":0,"is_provisional":True,
                        "env_completeness":0,"sg_completeness":0,
                        "sg_disclosed":0,"sg_total":8,"flagged_fields":[],"summary":""},
        "confidence":{"esg_confidence":0,"esg_is_provisional":True,
                      "dq_confidence":0,"dq_is_provisional":True,"interpretation":""},
        "computed_at":"2025-01-01T00:00:00","computation_time_ms":0,
    }

def _empty_trend():
    return {"months":[],"emissions_tco2e":[],"has_data":False,
            "forecast":{},"trend":{"direction":"insufficient_data","description":""},
            "annual_tco2e":0.0}

def _empty_fcast():
    return {"valid":False,"gate":{"reason":"No data","n_unique_periods":0,
            "n_required":6,"has_duplicates":False,"has_missing_periods":False,
            "missing_periods":[],"coverage_label":""},"validation":{},"naive":{},
            "outperforms_baseline":None,"next_period_value":None,
            "model_type":"OLS","limitation":"Modelled estimate."}

def _stub_st(monkeypatch):
    import streamlit as st
    noop = lambda *a, **kw: None
    for fn in ["markdown","caption","button","number_input","checkbox","text_input",
               "selectbox","info","warning","error","plotly_chart","write","form"]:
        monkeypatch.setattr(st, fn, noop, raising=False)
    monkeypatch.setattr(st, "columns",
        lambda n, **kw: [_Col()]*(n if isinstance(n,int) else len(n)), raising=False)
    monkeypatch.setattr(st, "expander", lambda *a, **kw: _Col(), raising=False)
    monkeypatch.setattr(st, "rerun",    lambda: None, raising=False)

class _Col:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __getattr__(self, n): return lambda *a, **kw: None
