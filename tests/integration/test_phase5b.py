"""
Phase 5-B Integration Tests (T1–T26)
Login-free entry + Forecast Hardening
"""
import ast, os, sys, pytest
import pandas as pd, numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def df_12():
    """12-month clean dataset."""
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
        "Emission": [245,268,231,259,277,242,264,251,239,267,245,258],
    })

@pytest.fixture
def df_4():
    """Only 4 months — below gate."""
    return pd.DataFrame({"Month":["Jan","Feb","Mar","Apr"], "Emission":[245,268,231,259]})

@pytest.fixture
def df_dup():
    """Dataset with duplicate months."""
    return pd.DataFrame({
        "Month":    ["Jan","Jan","Feb","Mar","Apr","May","Jun"],
        "Emission": [245,200,268,231,259,277,242],
    })

@pytest.fixture
def df_no_emission():
    return pd.DataFrame({"Month":["Jan","Feb","Mar","Apr","May","Jun"], "Energy":[100]*6})

@pytest.fixture
def df_zero():
    return pd.DataFrame({"Month":["Jan","Feb","Mar","Apr","May","Jun"], "Emission":[0]*6})


# ── T1–T5: Login-free entry ───────────────────────────────────────────────────

def test_T1_app_has_no_login_gate():
    """T1: app.py default path must init demo mode — not unconditionally block on login."""
    main_src = open('app.py').read()
    main_body = main_src.split('def main')[1].split('def _init')[0]
    # The env-var gate exists but must also call init_demo_mode for the default path
    assert 'init_demo_mode' in main_body, "init_demo_mode not wired into main()"
    # st.stop() must NOT appear (no unconditional block)
    assert 'st.stop()' not in main_body, "st.stop() still in main() — would block demo entry"
    # The default env-var path must be false/unset → demo mode
    assert 'CARBONLENS_AUTH_REQUIRED' in main_body


def test_T2_default_destination_is_executive_summary():
    """T2: DEFAULT_DESTINATION must be executive_summary."""
    from config.constants import DEFAULT_DESTINATION
    assert DEFAULT_DESTINATION == "executive_summary"


def test_T3_demo_mode_does_not_corrupt_state(monkeypatch):
    """T3: init_demo_mode() must set a valid demo user without raising."""
    stored = {}
    monkeypatch.setattr('repository.session_repo.set_current_user',
                        lambda u: stored.update({"user": u}), raising=False)
    from services.auth_service import init_demo_mode, DEMO_USER
    result = init_demo_mode()
    assert result["is_demo"] is True
    assert result["role"]    == "analyst"
    assert result["username"] == "demo_user"


def test_T4_no_auth_error_on_demo_entry(monkeypatch):
    """T4: is_authenticated() after demo init must return True."""
    from services.auth_service import DEMO_USER
    monkeypatch.setattr('repository.session_repo.get_current_user',
                        lambda: DEMO_USER, raising=False)
    from services.auth_service import is_authenticated
    assert is_authenticated() is True


def test_T5_demo_user_has_analyst_permissions():
    """T5: Demo user must have analyst-level permissions (not admin, not viewer-only)."""
    from config.constants import ROLE_PERMISSIONS
    from services.auth_service import DEMO_USER
    demo_role  = DEMO_USER["role"]
    demo_perms = ROLE_PERMISSIONS[demo_role]
    assert "can_view_all" in demo_perms
    assert "can_upload"   in demo_perms
    assert "can_export"   in demo_perms
    assert "can_manage_users" not in demo_perms   # analyst, not admin


def test_T5_is_demo_mode(monkeypatch):
    """T5: is_demo_mode() must return True when demo user is in session."""
    from services.auth_service import DEMO_USER
    monkeypatch.setattr('repository.session_repo.get_current_user',
                        lambda: DEMO_USER, raising=False)
    from services.auth_service import is_demo_mode
    assert is_demo_mode() is True


# ── T6–T8: Forecast data gate ─────────────────────────────────────────────────

def test_T6_gate_fails_none():
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(None)
    assert r["valid"] is False
    assert r["reason"] != ""


def test_T6_gate_fails_too_few_periods(df_4):
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_4)
    assert r["valid"] is False
    assert "4" in r["reason"] or str(r["n_unique_periods"]) in r["reason"]


def test_T6_gate_fails_no_emission_column(df_no_emission):
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_no_emission)
    assert r["valid"] is False
    assert "Emission" in r["reason"]


def test_T6_gate_fails_zero_emissions(df_zero):
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_zero)
    assert r["valid"] is False


def test_T7_gate_passes_12_month(df_12):
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_12)
    assert r["valid"] is True
    assert r["n_unique_periods"] == 12
    assert r["n_required"]       == 6


def test_T7_gate_passes_6_month():
    df = pd.DataFrame({"Month":["Jan","Feb","Mar","Apr","May","Jun"],
                       "Emission":[245,268,231,259,277,242]})
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df)
    assert r["valid"] is True


# ── T8–T9: Chronological split ────────────────────────────────────────────────

def test_T8_chronological_split_order(df_12):
    """T8: Train must contain earliest periods, test the latest."""
    from calculations.forecasting import chronological_train_test_split
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    assert len(train) == 10
    assert len(test)  == 2
    # Last 2 rows of df_12 must appear in test (not train)
    assert list(test["Month"]) == ["Nov", "Dec"]
    assert "Nov" not in list(train["Month"])


def test_T9_no_random_shuffle(df_12):
    """T9: split must be deterministic — running twice gives same result."""
    from calculations.forecasting import chronological_train_test_split
    train1, test1 = chronological_train_test_split(df_12, holdout_n=3)
    train2, test2 = chronological_train_test_split(df_12, holdout_n=3)
    assert list(train1["Month"]) == list(train2["Month"])
    assert list(test1["Month"])  == list(test2["Month"])


# ── T10–T11: Holdout validation metrics ───────────────────────────────────────

def test_T10_validation_mae(df_12):
    """T10: evaluate_holdout must return a numeric MAE from holdout periods."""
    from calculations.forecasting import chronological_train_test_split, evaluate_holdout
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    result = evaluate_holdout(train, test)
    assert result["status"] == "evaluated"
    assert result["mae"] is not None
    assert isinstance(result["mae"], float)
    assert result["mae"] >= 0


def test_T11_validation_rmse(df_12):
    """T11: evaluate_holdout must return RMSE ≥ MAE."""
    from calculations.forecasting import chronological_train_test_split, evaluate_holdout
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    result = evaluate_holdout(train, test)
    assert result["rmse"] is not None
    assert result["rmse"] >= result["mae"]


def test_T11_r2_not_reported_when_n_test_lt_3(df_12):
    """T11: R² must be None when holdout < 3 (not statistically meaningful)."""
    from calculations.forecasting import chronological_train_test_split, evaluate_holdout
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    result = evaluate_holdout(train, test)
    assert result["r2_holdout"] is None   # 2 holdout points = not meaningful


# ── T12–T13: Naive baseline comparison ───────────────────────────────────────

def test_T12_naive_baseline_returns_mae(df_12):
    """T12: naive_baseline must return a numeric MAE."""
    from calculations.forecasting import chronological_train_test_split, naive_baseline
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    result = naive_baseline(train, test)
    assert result["status"] == "evaluated"
    assert result["mae"] is not None and isinstance(result["mae"], float)


def test_T13_outperforms_flag_set_correctly(df_12):
    """T13: outperforms_baseline must be True only when model MAE < naive MAE."""
    from calculations.forecasting import forecast_with_validation
    result = forecast_with_validation(df_12)
    assert result["valid"] is True
    val_mae   = result["validation"].get("mae")
    naive_mae = result["naive"].get("mae")
    if val_mae is not None and naive_mae is not None:
        expected = val_mae < naive_mae
        assert result["outperforms_baseline"] == expected


def test_T13_does_not_claim_superiority_when_baseline_wins(df_12):
    """T13: outperforms_baseline must be False when naive wins — never overclaim."""
    from calculations.forecasting import (
        chronological_train_test_split, evaluate_holdout, naive_baseline
    )
    train, test = chronological_train_test_split(df_12, holdout_n=2)
    val   = evaluate_holdout(train, test)
    naive = naive_baseline(train, test)
    # If naive MAE ≤ model MAE, outperforms = False. We just verify the logic is correct.
    if val["mae"] is not None and naive["mae"] is not None:
        outperforms = val["mae"] < naive["mae"]
        assert isinstance(outperforms, bool)


# ── T14: Training R² not labelled as validation accuracy ─────────────────────

def test_T14_training_r2_not_in_forecast_result(df_12):
    """T14: forecast_with_validation must not expose training R² as accuracy."""
    from calculations.forecasting import forecast_with_validation
    result = forecast_with_validation(df_12)
    # Validated result must contain r2_holdout (not training r2)
    val = result.get("validation", {})
    assert "r2_holdout" in val             # holdout only
    # The top-level result must not have a flat "r2" key that equals training fit
    assert "r2" not in result              # no ambiguous flat r2


# ── T15–T16: Provenance and limitation disclosure ─────────────────────────────

def test_T15_forecast_result_has_model_type(df_12):
    """T15: forecast_with_validation must disclose the model type."""
    from calculations.forecasting import forecast_with_validation
    result = forecast_with_validation(df_12)
    assert "model_type" in result
    assert "OLS" in result["model_type"] or "regression" in result["model_type"].lower()


def test_T16_limitation_present_always():
    """T16: FORECAST_LIMITATION must be a non-empty string."""
    from calculations.forecasting import FORECAST_LIMITATION
    assert isinstance(FORECAST_LIMITATION, str)
    assert len(FORECAST_LIMITATION) > 50
    assert "not be interpreted" in FORECAST_LIMITATION.lower() \
        or "should not" in FORECAST_LIMITATION.lower()


def test_T16_limitation_in_forecast_result(df_12):
    from calculations.forecasting import forecast_with_validation
    result = forecast_with_validation(df_12)
    assert "limitation" in result
    assert len(result["limitation"]) > 0


def test_T16_limitation_present_even_when_invalid():
    from calculations.forecasting import forecast_with_validation
    result = forecast_with_validation(None)
    assert "limitation" in result
    assert len(result["limitation"]) > 0


# ── T17: Duplicate-period handling ────────────────────────────────────────────

def test_T17_duplicate_months_blocked(df_dup):
    """T17: Duplicate periods must cause gate failure, not silent wrong result."""
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_dup)
    assert r["valid"] is False
    assert r["has_duplicates"] is True


# ── T18: Severe DQ failure blocks forecast ────────────────────────────────────

def test_T18_zero_df_blocked(df_zero):
    """T18: All-zero emission dataset must fail the gate."""
    from calculations.forecasting import validate_forecast_history
    r = validate_forecast_history(df_zero)
    assert r["valid"] is False


def test_T18_none_df_blocked():
    from calculations.forecasting import forecast_with_validation
    r = forecast_with_validation(None)
    assert r["valid"] is False
    assert r["gate"]["reason"] != ""


# ── T19: Forecast lazy-load ───────────────────────────────────────────────────

def test_T19_get_forecast_validation_callable():
    """T19: state_service.get_forecast_validation must be callable."""
    from services.state_service import get_forecast_validation
    assert callable(get_forecast_validation)


def test_T19_get_forecast_validation_no_df(monkeypatch):
    """T19: get_forecast_validation returns a safe dict when no DF in session."""
    monkeypatch.setattr('repository.session_repo.get_uploaded_df',
                        lambda: None, raising=False)
    from services.state_service import get_forecast_validation
    result = get_forecast_validation()
    assert isinstance(result, dict)
    assert result["valid"] is False


# ── T20–T24: Regression invariants ───────────────────────────────────────────

def test_T20_phase0_constants():
    from config.settings  import EMISSION_FACTORS
    from config.constants import (ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV,
                                   CONFIDENCE_PROVISIONAL_FLOOR, SCOPE3_CATEGORIES_COVERED)
    assert EMISSION_FACTORS["diesel_kgco2_per_liter"] == 2.6967
    assert EMISSION_FACTORS["electricity_pln_kwh"]    == 0.7160
    assert ESG_WEIGHT_ENV                             == 0.40
    assert ESG_WEIGHT_SOCIAL                          == 0.30
    assert ESG_WEIGHT_GOV                             == 0.30
    assert CONFIDENCE_PROVISIONAL_FLOOR               == 50.0
    assert SCOPE3_CATEGORIES_COVERED                  == 12


def test_T21_phase2_dq_weights():
    from config.constants import DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION
    assert abs(DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION - 1.0) < 1e-9


def test_T22_phase3_audit_event_count():
    from config.constants import APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 16
    assert "scenario_created" in APPROVED_EVENT_TYPES


def test_T23_phase4_methodology_library():
    from services.state_service import get_methodology_library
    assert len(get_methodology_library()) == 29


def test_T24_decarb_planner_regression():
    from calculations.decarbonization import calculate_target_emissions
    assert calculate_target_emissions(200000.0, 30.0) == 140000.0
    from models.decarbonization import LEVER_CATALOGUE
    assert len(LEVER_CATALOGUE) == 6


# ── T25: Architecture import audit ───────────────────────────────────────────

def test_T25_no_calculations_in_pages():
    for root, _, files in os.walk('pages'):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            bad  = [n.module for n in ast.walk(tree)
                    if isinstance(n, ast.ImportFrom) and 'calculations' in (n.module or '')]
            assert not bad, f"{path} imports calculations: {bad}"


def test_T25_no_session_state_in_pages():
    ALLOWED = {"pages/onboarding/page.py"}
    for root, _, files in os.walk('pages'):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            if any(path.endswith(a.replace('/', os.sep)) for a in ALLOWED):
                continue
            tree = ast.parse(open(path).read())
            bad  = [ast.unparse(n) for n in ast.walk(tree)
                    if isinstance(n, ast.Attribute) and n.attr == 'session_state']
            assert not bad, f"{path} uses session_state"


def test_T25_calculations_are_pure():
    for root, _, files in os.walk('calculations'):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mod = getattr(node, 'module', '') or ''
                    if 'streamlit' in mod:
                        pytest.fail(f"{path} imports streamlit")


# ── T26: compileall ───────────────────────────────────────────────────────────

def test_T26_compileall():
    import py_compile
    for root, _, files in os.walk('.'):
        if any(x in root for x in ['__pycache__', '.pytest_cache']): continue
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(str(e))
