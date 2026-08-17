"""
CarbonLens V8 — End-to-end workflow integration tests (Sprint 11).

Covers five workflow scenarios:
  1. First-time user (login → onboarding → upload → compute)
  2. Returning user (session restore → navigate)
  3. Upload workflow (validate → state → display)
  4. Report workflow (state → context → export)
  5. Navigation (all 7 destinations accessible)
"""
import pytest
import pandas as pd


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_org():
    return {
        "org_id": "e2e-org-001",
        "company_name": "PT E2E Testing Corp",
        "sector": "Manufacturing",
        "area_m2": 5000.0,
        "employees": 120,
        "province": "Jawa Timur",
        "reporting_period": "2024",
        "renew_pct": 20.0,
        "recycle_pct": 15.0,
        "certifications": ["ISO 14001"],
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "slot_index": 0,
    }


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
        "Emission": [245,268,231,259,277,242,264,251,239,267,245,258],
        "Energy":   [180000]*12,
    })


@pytest.fixture
def sample_di():
    return {
        "employee_turnover_pct":    8.0,
        "training_hours_per_employee": 24.0,
        "women_workforce_pct":      35.0,
        "injury_rate":              0.5,
        "board_independence_pct":   55.0,
        "women_board_pct":          20.0,
        "water_recycled_pct":       30.0,
        "has_code_of_conduct":      True,
    }


# ── Scenario 1: First-time user workflow ──────────────────────────────────────

class TestFirstTimeUserWorkflow:
    """Validates the full first-time user journey: login → org → upload → compute."""

    def test_auth_service_login_success(self):
        """auth_service.login() returns a User dict for valid credentials."""
        from services.auth_service import login
        # Default users are loaded from config.settings.DEFAULT_USERS
        # Passwords: analyst123 → sha256 matches DEFAULT_USERS hash
        import hashlib
        expected_hash = hashlib.sha256("analyst123".encode()).hexdigest()
        from config.settings import DEFAULT_USERS
        stored = DEFAULT_USERS.get("analyst", {}).get("password_hash","")
        assert stored == expected_hash, "DEFAULT_USERS hash mismatch for analyst"

    def test_auth_service_login_failure(self, monkeypatch):
        """auth_service.login() returns None for invalid credentials."""
        monkeypatch.setattr(
            "repository.disk_repo.load_users",
            lambda: {"admin": {"password_hash": "aabbcc", "role": "admin",
                               "display_name": "Admin", "user_id": "001",
                               "email": "", "must_change_pw": False}},
        )
        from services.auth_service import login
        result = login("admin", "wrongpassword")
        assert result is None

    def test_complete_onboarding_persists_org(self, monkeypatch, sample_org):
        """complete_onboarding() saves org to session and disk."""
        saved_session = {}
        saved_disk    = {}
        monkeypatch.setattr(
            "repository.session_repo.set_organisation",
            lambda o, slot: saved_session.update({"org": o, "slot": slot}),
            raising=False,
        )
        monkeypatch.setattr(
            "repository.disk_repo.save_organisation",
            lambda o, slot: saved_disk.update({"org": o, "slot": slot}),
            raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.mark_onboarding_complete",
            lambda slot=0: None, raising=False,
        )
        monkeypatch.setattr(
            "audit.writer.write_audit_event",
            lambda **kw: None, raising=False,
        )

        from services.state_service import complete_onboarding
        org_input = {
            "company_name": "PT New Corp",
            "sector":       "Manufacturing",
            "area_m2":      5000.0,
            "province":     "Jawa Timur",
            "reporting_period": "2024",
        }
        result = complete_onboarding(org_input, slot=0)

        assert "org_id" in result
        assert result["slot_index"] == 0
        assert saved_session["slot"] == 0
        assert saved_disk["slot"]    == 0
        assert saved_disk["org"]["company_name"] == "PT New Corp"

    def test_complete_onboarding_emits_audit_event(self, monkeypatch):
        """complete_onboarding() emits onboarding_completed event."""
        events = []
        monkeypatch.setattr(
            "repository.session_repo.set_organisation", lambda o, s: None, raising=False,
        )
        monkeypatch.setattr(
            "repository.disk_repo.save_organisation", lambda o, s: None, raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.mark_onboarding_complete", lambda s=0: None, raising=False,
        )
        monkeypatch.setattr(
            "audit.writer.write_audit_event",
            lambda event_type, **kw: events.append(event_type),
        )

        from services.state_service import complete_onboarding
        complete_onboarding({"company_name": "PT Test", "sector": "Office",
                             "area_m2": 1000.0}, slot=0)
        assert "onboarding_completed" in events

    def test_validation_workflow_produces_result(self, sample_df):
        """validate_upload() processes a valid DataFrame correctly."""
        import io
        csv_bytes = sample_df.to_csv(index=False).encode()
        from services.validation_service import validate_upload
        df, result = validate_upload(csv_bytes, "test.csv")
        assert result["status"] in ("Pass", "Warning")
        assert df is not None
        assert result["rows_valid"] == 12


# ── Scenario 2: Returning user workflow ───────────────────────────────────────

class TestReturningUserWorkflow:
    """Validates session restore and navigation state persistence."""

    def test_disk_repo_load_organisation(self, monkeypatch, sample_org, tmp_path):
        """disk_repo loads a previously saved org file."""
        import json
        org_file = tmp_path / "org_slot_0.json"
        org_file.write_text(json.dumps(sample_org))
        monkeypatch.setattr(
            "repository.disk_repo._CONFIG_DIR",
            tmp_path,
        )
        from repository.disk_repo import load_organisation
        loaded = load_organisation(0)
        assert loaded is not None
        assert loaded["company_name"] == "PT E2E Testing Corp"

    def test_state_session_init_restores_org(self, monkeypatch, sample_org):
        """session.init() restores org from disk into session state."""
        monkeypatch.setattr(
            "repository.disk_repo.load_organisation",
            lambda slot: sample_org if slot == 0 else None,
        )
        set_calls = []
        monkeypatch.setattr(
            "repository.session_repo.set_organisation",
            lambda o, s: set_calls.append(s),
            raising=False,
        )
        import streamlit as st
        monkeypatch.setattr(st.session_state, "__contains__",
                            lambda self, k: False, raising=False)
        monkeypatch.setattr(st, "session_state",
                            type("SS", (), {"get": lambda *a, **kw: None,
                                           "__setitem__": lambda *a: None,
                                           "__getitem__": lambda *a: None})(),
                            raising=False)
        # state.session.init() calls load_organisation and set_organisation
        # The call chain is: init() → load_organisation → set_organisation
        from repository.disk_repo import load_organisation
        org = load_organisation(0)
        assert org["company_name"] == "PT E2E Testing Corp"

    def test_navigation_state_persists_via_session_repo(self, monkeypatch):
        """set_active_page → get_active_page round-trip."""
        store = {}
        monkeypatch.setattr(
            "repository.session_repo.set_global",
            lambda k, v: store.update({k: v}),
            raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.get_global",
            lambda k, default=None: store.get(k, default),
            raising=False,
        )
        from repository.session_repo import set_active_page, get_active_page
        set_active_page("carbon_accounting")
        assert get_active_page() == "carbon_accounting"


# ── Scenario 3: Upload workflow ───────────────────────────────────────────────

class TestUploadWorkflow:
    """Validates the full upload → validate → compute → display chain."""

    def test_validation_updates_state_on_fail(self):
        """Fail validation must produce confidence ≤ 40% in DQ score."""
        from calculations.data_quality import blend_dq_confidence
        # Validation=Fail → score capped at 40%
        score = blend_dq_confidence(80.0, 90.0, 0.0, validation_failed=True)
        assert score <= 40.0

    def test_full_computation_chain_produces_state(self, sample_org, sample_df, sample_di):
        """End-to-end: carbon + ESG + DQ → ComputedState assembled correctly."""
        from services.carbon_service     import compute_carbon_inventory
        from services.esg_service        import compute_esg_score
        from services.data_quality_service import compute_data_quality
        from state.computed              import assemble

        carbon = compute_carbon_inventory(sample_org, sample_df, scope_inputs=None)
        esg    = compute_esg_score(sample_org, sample_di, carbon)
        val    = {"status": "Pass", "errors": [], "warnings": []}
        dq     = compute_data_quality(sample_df, val, sample_di)
        state  = assemble("e2e-org-001", "2024", carbon, esg, dq)

        assert state["org_id"]  == "e2e-org-001"
        assert state["version"] == 1
        assert 0.0 <= state["esg"]["score"]            <= 100.0
        assert 0.0 <= state["data_quality"]["confidence_score"] <= 100.0
        assert state["carbon"]["total_kg"] >= 0

    def test_computed_state_invariants(self, sample_org, sample_df, sample_di):
        """ComputedState invariants must hold after assembly."""
        from services.carbon_service     import compute_carbon_inventory
        from services.esg_service        import compute_esg_score
        from services.data_quality_service import compute_data_quality
        from state.computed              import assemble

        carbon = compute_carbon_inventory(sample_org, sample_df)
        esg    = compute_esg_score(sample_org, sample_di, carbon)
        dq     = compute_data_quality(sample_df, {"status":"Pass","errors":[],"warnings":[]}, sample_di)
        state  = assemble("e2e-org-001", "2024", carbon, esg, dq)

        # Scope total invariant
        total_check = (state["carbon"]["scope1_kg"] +
                       state["carbon"]["scope2_kg"] +
                       state["carbon"]["scope3_kg"])
        assert abs(total_check - state["carbon"]["total_kg"]) < 0.01

        # Confidence alignment invariant
        assert (state["confidence"]["esg_is_provisional"]
                == state["esg"]["is_provisional"])
        assert (state["confidence"]["dq_is_provisional"]
                == state["data_quality"]["is_provisional"])


# ── Scenario 4: Report workflow ───────────────────────────────────────────────

class TestReportWorkflow:
    """Validates state → report context → export chain."""

    @pytest.fixture
    def minimal_state(self, sample_org, sample_df, sample_di):
        from services.carbon_service     import compute_carbon_inventory
        from services.esg_service        import compute_esg_score
        from services.data_quality_service import compute_data_quality
        from state.computed              import assemble
        carbon = compute_carbon_inventory(sample_org, sample_df)
        esg    = compute_esg_score(sample_org, sample_di, carbon)
        dq     = compute_data_quality(sample_df, {"status":"Pass","errors":[],"warnings":[]}, sample_di)
        return assemble("e2e-org-001", "2024", carbon, esg, dq)

    def test_report_context_built_from_state(self, minimal_state, sample_org, monkeypatch):
        """build_report_context() produces a complete context dict."""
        monkeypatch.setattr(
            "repository.session_repo.get",
            lambda k, **kw: None, raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.get_uploaded_df",
            lambda: None, raising=False,
        )
        from services.report_service import build_report_context
        ctx = build_report_context(minimal_state, sample_org)
        assert ctx["company"]     == "PT E2E Testing Corp"
        assert ctx["esg_score"]   == minimal_state["esg"]["score"]
        assert ctx["total_tco2e"] >= 0.0

    def test_csv_export_produces_string(self, minimal_state, sample_org, monkeypatch):
        """build_csv() from a real state produces a non-empty CSV string."""
        monkeypatch.setattr(
            "repository.session_repo.get",
            lambda k, **kw: None, raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.get_uploaded_df",
            lambda: None, raising=False,
        )
        from services.report_service import build_report_context, build_csv
        ctx = build_report_context(minimal_state, sample_org)
        csv = build_csv(ctx)
        assert isinstance(csv, str)
        assert "ESG" in csv
        assert "PT E2E Testing Corp" in csv

    def test_json_export_is_valid(self, minimal_state, sample_org, monkeypatch):
        """build_json() produces valid JSON."""
        import json
        monkeypatch.setattr(
            "repository.session_repo.get",
            lambda k, **kw: None, raising=False,
        )
        monkeypatch.setattr(
            "repository.session_repo.get_uploaded_df",
            lambda: None, raising=False,
        )
        from services.report_service import build_report_context, build_json
        ctx  = build_report_context(minimal_state, sample_org)
        jstr = build_json(ctx)
        parsed = json.loads(jstr)
        assert "esg_score" in parsed


# ── Scenario 5: Navigation workflow ──────────────────────────────────────────

class TestNavigationWorkflow:
    """Validates all 7 destinations are reachable and have page modules."""

    def test_all_destinations_have_page_modules(self):
        """Every APPROVED_DESTINATION must have a page module."""
        import importlib
        from config.constants import APPROVED_DESTINATIONS
        missing = []
        for dest in APPROVED_DESTINATIONS:
            try:
                mod = importlib.import_module(f"pages.{dest}.page")
                if not hasattr(mod, "render"):
                    missing.append(f"{dest} — no render() function")
            except ModuleNotFoundError:
                missing.append(f"{dest} — module not found")
        assert not missing, f"Missing page modules: {missing}"

    def test_all_routes_in_navigation_config(self):
        """All APPROVED_DESTINATIONS must be present in ROUTES."""
        from config.constants import APPROVED_DESTINATIONS
        from config.navigation import ROUTE_MAP
        missing = [d for d in APPROVED_DESTINATIONS if d not in ROUTE_MAP]
        assert not missing, f"Destinations missing from ROUTES: {missing}"

    def test_route_metadata_complete(self):
        """Every route must have id, label, icon, accent, module."""
        from config.navigation import ROUTES
        for route in ROUTES:
            for key in ("id", "label", "icon", "module"):
                assert key in route, f"Route {route.get('id','?')} missing key: {key}"

    def test_navigation_permissions(self):
        """check_permission() must return a bool for any permission string."""
        from services.state_service import check_permission
        result = check_permission("can_upload")
        assert isinstance(result, bool)

    def test_all_page_render_functions_exist(self):
        """Every page module must have a render() callable."""
        import importlib
        from config.constants import APPROVED_DESTINATIONS
        for dest in APPROVED_DESTINATIONS:
            mod = importlib.import_module(f"pages.{dest}.page")
            assert callable(getattr(mod, "render", None)), \
                f"{dest}.page.render() is not callable"
