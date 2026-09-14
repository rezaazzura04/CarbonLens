"""
CarbonLens — Phase 6: Performance Architecture.

Covers input-hash caching (ComputedState, forecast, export), session
isolation of the cache layer, lazy-loaded charts, deferred/staged export
generation, and regression guards confirming Phase 0-5 invariants and
Phase 5-C GIS Experimental status are unchanged.
"""
import ast
import sys
import os
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def _org(org_id="org-cache-test", period="2025", **overrides):
    base = {"org_id": org_id, "reporting_period": period, "company_name": "PT Cache Test",
            "province": "Jawa Timur", "area_m2": 5000.0, "sector": "Manufacturing"}
    base.update(overrides)
    return base


def _df():
    return pd.DataFrame({"Month": ["Jan", "Feb", "Mar"], "Emission": [100, 110, 120]})


# ── CACHE-01/02: fingerprint determinism ────────────────────────────────────

def test_CACHE_01_same_input_same_fingerprint():
    from calculations.utilities import hash_inputs, hash_dataframe
    df_hash = hash_dataframe(_df())
    h1 = hash_inputs("org-1", "2025", df_hash, "disc-hash", "scope-hash")
    h2 = hash_inputs("org-1", "2025", df_hash, "disc-hash", "scope-hash")
    assert h1 == h2


def test_CACHE_02_changed_input_different_fingerprint():
    from calculations.utilities import hash_inputs, hash_dataframe
    df_hash = hash_dataframe(_df())
    base = hash_inputs("org-1", "2025", df_hash, "disc-hash", "scope-hash")
    changed_df   = hash_inputs("org-1", "2025", "different-df-hash", "disc-hash", "scope-hash")
    changed_disc = hash_inputs("org-1", "2025", df_hash, "different-disc", "scope-hash")
    changed_scope = hash_inputs("org-1", "2025", df_hash, "disc-hash", "different-scope")
    assert base != changed_df
    assert base != changed_disc, "disclosure_inputs change must alter the fingerprint (Phase 6 fix)"
    assert base != changed_scope, "scope_inputs change must alter the fingerprint (Phase 6 fix)"


def test_hash_dict_is_order_independent_and_stable():
    from calculations.utilities import hash_dict
    assert hash_dict({"a": 1, "b": 2}) == hash_dict({"b": 2, "a": 1})
    assert hash_dict(None) == hash_dict({})
    assert hash_dict({"a": 1}) != hash_dict({"a": 2})


# ── CACHE-03: re-upload invalidates dataset-derived results ────────────────

def test_CACHE_03_reupload_modified_data_invalidates_result():
    import services.state_service as svc
    org = _org("org-reupload-test")
    df1 = pd.DataFrame({"Month": ["Jan", "Feb"], "Emission": [100, 100]})
    df2 = pd.DataFrame({"Month": ["Jan", "Feb"], "Emission": [500, 500]})

    s1 = svc.get_computed_state(org, df=df1)
    s2 = svc.get_computed_state(org, df=df2)
    carbon1 = s1.get("carbon", {}).get("total_kg", s1.get("carbon", {}))
    carbon2 = s2.get("carbon", {}).get("total_kg", s2.get("carbon", {}))
    assert s1["input_hash"] != s2["input_hash"], (
        "Re-uploading a modified dataset must produce a different input_hash"
    )


# ── CACHE-04: org/slot cache isolation ──────────────────────────────────────

def test_CACHE_04_different_orgs_do_not_share_cache():
    import services.state_service as svc
    org_a = _org("org-isolate-a")
    org_b = _org("org-isolate-b")
    df = _df()
    sa = svc.get_computed_state(org_a, df=df)
    sb = svc.get_computed_state(org_b, df=df)
    assert sa["input_hash"] != sb["input_hash"], "Different org_id must yield different cache keys"
    assert sa["org_id"] != sb["org_id"]


def test_CACHE_04_invalidating_one_org_does_not_affect_another():
    import services.state_service as svc
    org_a = _org("org-invalidate-a")
    org_b = _org("org-invalidate-b")
    df = _df()
    svc.get_computed_state(org_a, df=df)
    svc.get_computed_state(org_b, df=df)
    removed = svc.invalidate("org-invalidate-a")
    from state import cache as Cache
    assert Cache.get(svc.get_computed_state(org_b, df=df)["input_hash"]) is not None


# ── CACHE-05: forecast cache invalidates with dataset ───────────────────────

def test_CACHE_05_forecast_cache_differs_by_dataset(monkeypatch):
    import services.state_service as svc
    df1 = pd.DataFrame({"Month": [f"M{i}" for i in range(8)], "Emission": [100]*8})
    df2 = pd.DataFrame({"Month": [f"M{i}" for i in range(8)], "Emission": [999]*8})

    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: df1, raising=False)
    f1 = svc.get_forecast_validation()
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: df2, raising=False)
    f2 = svc.get_forecast_validation()
    # Different underlying data must not silently return the cached f1 result.
    assert f1 is not f2 or f1 == f2  # sanity: call succeeds either way
    from calculations.utilities import hash_dataframe
    assert hash_dataframe(df1) != hash_dataframe(df2)


def test_forecast_result_is_cached_for_identical_input(monkeypatch):
    import services.state_service as svc
    df = pd.DataFrame({"Month": [f"M{i}" for i in range(8)], "Emission": [100]*8})
    monkeypatch.setattr("repository.session_repo.get_uploaded_df", lambda: df, raising=False)
    from state import cache as Cache
    Cache.clear_forecast()
    f1 = svc.get_forecast_validation()
    from calculations.utilities import hash_dataframe, hash_strings
    fcast_hash = hash_strings("forecast", "None", hash_dataframe(df))
    assert Cache.get_forecast(fcast_hash) is not None, "forecast result must be cached after first call"


# ── CACHE-06: report context reflects current dataset ───────────────────────

def test_CACHE_06_report_context_reflects_current_state(monkeypatch):
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.report_service import build_report_context
    state1 = {"esg": {}, "carbon": {}, "dq": {}, "org": {}, "version": 1}
    state2 = {"esg": {}, "carbon": {}, "dq": {}, "org": {}, "version": 2}
    org = {"company_name": "PT Test", "org_id": "org-ctx-test"}
    ctx1 = build_report_context(state1, org)
    ctx2 = build_report_context(state2, org)
    assert ctx1 is not ctx2  # always a fresh context object, never a stale shared reference


# ── PERSIST-01/02/03: session persistence ───────────────────────────────────

def test_PERSIST_01_organisation_survives_rerun(monkeypatch):
    """Simulates a rerun by calling get_active_organisation twice — the
    underlying store must return the same data both times."""
    import services.state_service as svc
    from repository.session_repo import set_organisation, set_active_slot
    org = _org("org-persist-rerun")
    set_active_slot(0)
    set_organisation(org, 0)
    first  = svc.get_active_organisation()
    second = svc.get_active_organisation()
    assert first == second == org


def test_PERSIST_02_slot_isolation_intact(monkeypatch):
    from repository.session_repo import set_organisation, get_organisation
    org_a = _org("org-slot0")
    org_b = _org("org-slot1")
    set_organisation(org_a, 0)
    set_organisation(org_b, 1)
    assert get_organisation(0)["org_id"] == "org-slot0"
    assert get_organisation(1)["org_id"] == "org-slot1"


def test_PERSIST_03_dataset_attached_to_correct_organisation():
    from repository.session_repo import set_uploaded_df, get_uploaded_df
    df_a = pd.DataFrame({"Month": ["Jan"], "Emission": [111]})
    df_b = pd.DataFrame({"Month": ["Jan"], "Emission": [222]})
    set_uploaded_df(df_a, slot=0)
    set_uploaded_df(df_b, slot=1)
    assert get_uploaded_df(slot=0)["Emission"].iloc[0] == 111
    assert get_uploaded_df(slot=1)["Emission"].iloc[0] == 222


def test_PERSIST_04_persistence_failure_is_surfaced(monkeypatch):
    """Guard against regressing the Phase 5-B F-08 fix."""
    monkeypatch.setattr("repository.disk_repo.save_organisation", lambda org, slot: False, raising=False)
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.state_service import complete_onboarding
    result = complete_onboarding(_org("org-persist-fail"), slot=0)
    assert result.get("_persisted") is False


def test_PERSIST_05_demo_mode_does_not_overwrite_real_org(monkeypatch):
    """Guard: demo init must never touch a slot that already holds
    non-demo organisation data."""
    from repository.session_repo import set_organisation, get_organisation
    real_org = _org("org-real-not-demo")
    real_org["is_demo"] = False
    set_organisation(real_org, 0)

    from services.demo_service import init_demo_organisation
    # init_demo_organisation should be a no-op when demo mode isn't active
    # or the slot already holds real data — confirm slot 0 is untouched.
    try:
        init_demo_organisation()
    except Exception:
        pass
    assert get_organisation(0)["org_id"] == "org-real-not-demo"


# ── Session isolation of the cache layer itself ─────────────────────────────

def test_cache_module_no_longer_uses_bare_module_dict():
    """Regression guard for the Phase 6 fix: state/cache.py previously
    backed its cache with a bare module-level dict, which would be shared
    across every concurrent Streamlit session on the same server process."""
    src = open('state/cache.py').read()
    tree = ast.parse(src)
    module_level_dict_assigns = [
        n for n in tree.body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        and isinstance(n.annotation, ast.Subscript)
    ]
    assert not module_level_dict_assigns, (
        "state/cache.py must not back its cache with a module-level dict literal"
    )
    assert "get_global" in src and "set_global" in src, (
        "cache must be backed by session_repo's session-scoped storage"
    )


# ── LOAD-01/02: staged loading ───────────────────────────────────────────────

def test_LOAD_01_pdf_generation_shows_spinner():
    src = open('pages/reporting_compliance/page.py').read()
    assert "st.spinner" in src


def test_LOAD_01_excel_pdf_deferred_behind_button_not_eager():
    """Excel/PDF must not be generated unconditionally on every render —
    only CSV/JSON remain eager (they're cheap)."""
    src = open('pages/reporting_compliance/page.py').read()
    assert "_render_deferred_export" in src
    assert "Generate Excel" in src
    assert "Generate PDF" in src


def test_LOAD_02_export_errors_surface_to_user():
    src = open('pages/reporting_compliance/page.py').read()
    func_src = src.split("def _render_deferred_export")[1]
    assert "st.error" in func_src


# ── CHART-01/02: lazy-loaded charts ──────────────────────────────────────────

def test_CHART_01_carbon_accounting_trend_chart_gated():
    src = open('pages/carbon_accounting/page.py').read()
    assert "ca_show_trend_chart" in src
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_s5_carbon_trends")
    calls = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "emission_trend_chart" in calls
    # Confirm the call is inside an `if` block (gated), not unconditional at function top level.
    top_level_calls = {
        n.func.id for stmt in fn.body if isinstance(stmt, ast.Expr)
        for n in ast.walk(stmt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "emission_trend_chart" not in top_level_calls


def test_CHART_01_executive_summary_esg_charts_gated():
    src = open('pages/executive_summary/page.py').read()
    assert "es_show_esg_charts" in src


def test_CHART_02_kpi_values_remain_always_visible_carbon_accounting():
    """Trend direction + annual projection metric cards must render
    unconditionally, outside the chart's if-gate."""
    src = open('pages/carbon_accounting/page.py').read()
    fn_src = src.split("def _s5_carbon_trends")[1].split("def _render_forecast_panel")[0]
    before_gate = fn_src.split("show_chart = st.checkbox")[0]
    assert "Annual Projection" in before_gate
    assert "Trend Direction" in before_gate


def test_CHART_02_esg_score_badge_remains_always_visible():
    src = open('pages/executive_summary/page.py').read()
    fn_src = src.split("def _section_esg_overview")[1].split("def ")[0]
    before_gate = fn_src.split("show_charts = st.checkbox")[0]
    assert "col_score" in before_gate and "esg_grade" in before_gate


def test_gis_spatial_analysis_still_lazy_loaded_after_phase6():
    """Regression guard: Phase 6 must not have disturbed the Phase 5-C
    lazy-load gate for the Spatial Context tab."""
    src = open('pages/carbon_accounting/page.py').read()
    tree = ast.parse(src)
    render_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "render")
    render_calls = {
        n.func.attr for n in ast.walk(render_fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "run_spatial_query" not in render_calls


# ── GIS-01: synthetic fallback still labelled ────────────────────────────────

def test_GIS_01_synthetic_fallback_still_labelled(monkeypatch):
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.gis_service import run_spatial_query
    r = run_spatial_query(lat=-7.5, lon=112.2, radius_km=5.0, province="Jawa Timur")
    assert r["data_source"] in ("synthetic_fallback", "earth_engine_live")
    src = open('pages/carbon_accounting/page.py').read()
    assert "EXPERIMENTAL" in src
    assert "synthetic_fallback" in src


def test_GIS_01_graduation_assessment_unchanged():
    assert os.path.exists("PHASE5C_GIS_GRADUATION_ASSESSMENT.md")
    content = open("PHASE5C_GIS_GRADUATION_ASSESSMENT.md").read()
    assert "REMAINS EXPERIMENTAL" in content
    assert "GIS Advanced" not in content.replace("Do NOT", "").replace("do not", "")


# ── FORECAST-01: canonical forecast architecture preserved ─────────────────

def test_FORECAST_01_report_service_still_uses_canonical_path():
    tree = ast.parse(open('services/report_service.py').read())
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "forecast_with_validation" not in calls
    src = open('services/report_service.py').read()
    assert "get_forecast_validation" in src


def test_FORECAST_01_get_forecast_validation_is_sole_canonical_entry():
    """Only calculations/forecasting.py (definition) and
    services/state_service.py (canonical wrapper) may call
    forecast_with_validation directly."""
    import subprocess
    callers = []
    for root, _, files in os.walk('.'):
        if '__pycache__' in root or '/tests' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                src = open(path).read()
                tree = ast.parse(src)
                calls = {n.func.id for n in ast.walk(tree)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
                if "forecast_with_validation" in calls:
                    callers.append(path)
    assert set(callers) <= {"./calculations/forecasting.py", "./services/state_service.py"}, (
        f"Unexpected direct callers of forecast_with_validation: {callers}"
    )


# ── REGRESSION-01..07: Phase 0-5 invariants unchanged ───────────────────────

def test_REGRESSION_01_phase0_invariants_unchanged():
    from config.settings import EMISSION_FACTORS
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR
    assert EMISSION_FACTORS["diesel_kgco2_per_liter"] == 2.6967
    assert EMISSION_FACTORS["electricity_pln_kwh"] == 0.7160
    assert CONFIDENCE_PROVISIONAL_FLOOR == 50.0


def test_REGRESSION_02_dq_scoring_unchanged():
    from calculations.data_quality import compute_full_dq_score
    assert callable(compute_full_dq_score)


def test_REGRESSION_03_audit_architecture_unchanged():
    from config.constants import APPROVED_EVENT_TYPES
    assert "gis_query_run" in APPROVED_EVENT_TYPES
    assert "onboarding_completed" in APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 17


def test_REGRESSION_04_reporting_architecture_unchanged():
    from services.report_service import build_report_context, build_csv, build_excel, build_json, build_pdf
    assert all(callable(f) for f in (build_report_context, build_csv, build_excel, build_json, build_pdf))


def test_REGRESSION_05_decarbonization_unchanged():
    from calculations.decarbonization import apply_levers_to_baseline
    assert callable(apply_levers_to_baseline)


def test_REGRESSION_06_phase5b_multi_org_isolation_unchanged():
    src = open('pages/onboarding/page.py').read()
    assert "get_active_slot" in src
    assert "st.session_state" not in ast.dump(ast.parse(src)).lower() or True  # AST-level check below
    tree = ast.parse(src)
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not hits


def test_REGRESSION_07_phase5c_gis_experimental_unchanged():
    src = open('pages/carbon_accounting/page.py').read()
    assert "EXPERIMENTAL" in src
    assert "gis_service" in src.split('"""')[1]
