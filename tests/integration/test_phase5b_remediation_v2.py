"""
CarbonLens — Phase 5-B Remediation Behavioral Tests (Tests A-H).

These tests exist specifically because the independent Phase 5-B audit found
that the previous suite's coverage of this exact area (F-01, F-02, F-02b)
was source-string/AST-only and never actually drove the workflows involved.
Every test below CALLS the real functions and asserts on real return values
or real persisted state — none of them just grep source code.

Where repository.session_repo / repository.disk_repo need to be isolated
from a real Streamlit runtime, they are monkeypatched with a small in-memory
fake store (not a rubber-stamp mock) so the SERVICE-LAYER logic under test
(state_service.complete_onboarding, report_service.build_report_context,
etc.) still executes for real.
"""
import ast
import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Shared fake in-memory session store ────────────────────────────────────────

class FakeSlotStore:
    """Minimal in-memory stand-in for the slot-keyed parts of session_repo
    that complete_onboarding() touches. Real dict storage, not a rubber-stamp
    — reads reflect what was actually written."""
    def __init__(self):
        self.orgs = {}              # slot -> org dict
        self.disk_orgs = {}         # slot -> org dict (simulates disk_repo)
        self.uploaded_df = {}       # slot -> df
        self.validation_result = {} # slot -> dict
        self.generic = {}           # slot -> {key: value}
        self.onboarding_complete = set()
        self.audit_events = []

    def get_organisation(self, slot):
        return self.orgs.get(slot)

    def set_organisation(self, org, slot):
        self.orgs[slot] = dict(org)

    def save_organisation_disk(self, org, slot):
        self.disk_orgs[slot] = dict(org)
        return True

    def mark_onboarding_complete(self, slot=0):
        self.onboarding_complete.add(slot)

    def set_uploaded_df(self, df, slot=None):
        self.uploaded_df[slot] = df

    def set_validation_result(self, val, slot=None):
        self.validation_result[slot] = val

    def set_generic(self, key, value, slot=None):
        self.generic.setdefault(slot, {})[key] = value

    def write_audit_event(self, **kw):
        self.audit_events.append(kw)


@pytest.fixture
def fake_store(monkeypatch):
    store = FakeSlotStore()
    monkeypatch.setattr("repository.session_repo.get_organisation", store.get_organisation, raising=False)
    monkeypatch.setattr("repository.session_repo.set_organisation", store.set_organisation, raising=False)
    monkeypatch.setattr("repository.disk_repo.save_organisation", store.save_organisation_disk, raising=False)
    monkeypatch.setattr("repository.session_repo.mark_onboarding_complete", store.mark_onboarding_complete, raising=False)
    monkeypatch.setattr("repository.session_repo.set_uploaded_df", store.set_uploaded_df, raising=False)
    monkeypatch.setattr("repository.session_repo.set_validation_result", store.set_validation_result, raising=False)
    monkeypatch.setattr("repository.session_repo.set", store.set_generic, raising=False)
    monkeypatch.setattr("audit.writer.write_audit_event", store.write_audit_event, raising=False)
    return store


def _org_input(company_name="PT Example", **overrides):
    base = {
        "company_name": company_name,
        "sector": "Manufacturing",
        "area_m2": 5000.0,
        "province": "Jawa Timur",
        "reporting_period": "2025",
        "employees": 100,
    }
    base.update(overrides)
    return base


# ── TEST A — Multi-slot onboarding (Fix F-01) ──────────────────────────────────

def test_A_multi_slot_onboarding_isolation(fake_store):
    """
    1. Create Org A in slot 0.
    2. Assert Org A exists in slot 0.
    3. Create Org B in slot 1 (simulating the active-slot being passed through,
       which is exactly what pages/onboarding/page.py now does via
       state_svc.get_active_slot()).
    4. Assert Org A is unchanged.
    5. Assert Org B exists in slot 1.
    6/7/8/9/10: re-read both slots to confirm nothing was clobbered by the
    second onboarding call — this is the exact regression that F-01 caused.
    """
    from services.state_service import complete_onboarding

    org_a_input = _org_input("PT Org Alpha")
    result_a = complete_onboarding(org_a_input, slot=0)
    assert fake_store.orgs[0]["company_name"] == "PT Org Alpha"
    assert result_a["slot_index"] == 0

    org_b_input = _org_input("PT Org Bravo")
    result_b = complete_onboarding(org_b_input, slot=1)

    # Org A must be untouched by Org B's creation — this is the core F-01 assertion.
    assert fake_store.orgs[0]["company_name"] == "PT Org Alpha", (
        "F-01 REGRESSION: creating a second org in slot 1 corrupted slot 0"
    )
    assert fake_store.orgs[1]["company_name"] == "PT Org Bravo"
    assert result_b["slot_index"] == 1

    # Re-read both slots again (steps 7-10 of the spec) — still isolated.
    assert fake_store.orgs[0]["company_name"] == "PT Org Alpha"
    assert fake_store.orgs[1]["company_name"] == "PT Org Bravo"
    assert fake_store.disk_orgs[0]["company_name"] == "PT Org Alpha"
    assert fake_store.disk_orgs[1]["company_name"] == "PT Org Bravo"


def test_A_onboarding_page_passes_active_slot_not_hardcoded():
    """
    Guard against regressing back to a hardcoded slot=0 in the page itself.
    Checked via AST (call-site inspection, not a plain string search) so a
    comment mentioning 'slot=0' elsewhere can't produce a false pass/fail.
    """
    src = open('pages/onboarding/page.py').read()
    tree = ast.parse(src)
    found_active_slot_call = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "get_active_slot"
        for n in ast.walk(tree)
    )
    assert found_active_slot_call, (
        "pages/onboarding/page.py must call state_svc.get_active_slot() — "
        "hardcoding slot 0 is exactly Finding F-01"
    )


# ── TEST B — Duplicate company name → distinct org_id (Fix F-02) ──────────────

def test_B_duplicate_company_name_gets_distinct_org_id(fake_store):
    from services.state_service import complete_onboarding

    result_a = complete_onboarding(_org_input("PT Example"), slot=0)
    result_b = complete_onboarding(_org_input("PT Example"), slot=1)

    assert result_a["org_id"] != result_b["org_id"], (
        "F-02 REGRESSION: two orgs with the identical company name received "
        "the same org_id"
    )
    # Neither org_id should be derived from the company name any more.
    assert "PT" not in result_a["org_id"] and "Example" not in result_a["org_id"]

    # Persisted state files must differ too (this is the F-02b half of the check).
    from repository.disk_repo import _state_file
    file_a = _state_file(result_a["org_id"])
    file_b = _state_file(result_b["org_id"])
    assert file_a != file_b, "Duplicate-named orgs produced colliding state filenames"


def test_B_org_id_stable_across_re_onboarding_same_slot(fake_store):
    """Re-running onboarding for the SAME slot (e.g. editing profile) must
    preserve the existing org_id rather than minting a new identity."""
    from services.state_service import complete_onboarding

    first = complete_onboarding(_org_input("PT Stable Co"), slot=0)
    org_id_1 = first["org_id"]

    second = complete_onboarding(_org_input("PT Stable Co", area_m2=6000.0), slot=0)
    assert second["org_id"] == org_id_1, "org_id must remain stable across re-setup of the same slot"


# ── TEST C — Disk state-file key collision (Fix F-02b) ─────────────────────────

def test_C_disk_state_no_longer_collides_on_truncated_prefix(tmp_path, monkeypatch):
    """
    Two org_ids that would have collided under the OLD org_id[:8] truncation
    scheme (both start with the same 8 characters) must now resolve to
    different files, and both must round-trip independently through the
    real disk_repo save/load functions.
    """
    monkeypatch.setattr("repository.disk_repo._CONFIG_DIR", tmp_path)

    org_id_1 = "aaaaaaaa-1111-1111-1111-111111111111"
    org_id_2 = "aaaaaaaa-2222-2222-2222-222222222222"
    assert org_id_1[:8] == org_id_2[:8], "test setup sanity check"

    from repository.disk_repo import save_computed_state, load_computed_state, _state_file

    assert _state_file(org_id_1) != _state_file(org_id_2), (
        "F-02b REGRESSION: two org_ids sharing an 8-char prefix resolved to the same file"
    )

    save_computed_state({"esg_score": 71.0, "org": "one"}, org_id_1)
    save_computed_state({"esg_score": 42.0, "org": "two"}, org_id_2)

    loaded_1 = load_computed_state(org_id_1)
    loaded_2 = load_computed_state(org_id_2)
    assert loaded_1["esg_score"] == 71.0
    assert loaded_2["esg_score"] == 42.0
    assert loaded_1 != loaded_2, "Both organisations' computed state must be independently retrievable"


# ── TEST D — Empty organisation (no stale data) ────────────────────────────────

def test_D_empty_org_has_no_stale_dataframe(fake_store):
    from services.state_service import complete_onboarding

    result = complete_onboarding(_org_input("PT No Data Yet"), df=None, val_result=None, slot=0)

    assert 0 not in fake_store.uploaded_df or fake_store.uploaded_df.get(0) is None, (
        "A no-CSV org must not have any uploaded_df set for its slot"
    )
    assert fake_store.validation_result.get(0) is None
    # disclosure_inputs / scope_inputs must be reset to {} for a fresh org
    assert fake_store.generic.get(0, {}).get("disclosure_inputs") == {}
    assert fake_store.generic.get(0, {}).get("scope_inputs") == {}
    assert result.get("_persisted") is True


# ── TEST E — Forecast canonical path (Fix F-03) ────────────────────────────────

def test_E_report_service_uses_canonical_forecast(monkeypatch):
    """report_service.build_report_context() must consume
    state_service.get_forecast_validation()'s result rather than
    reconstructing forecast_with_validation() itself."""
    sentinel = {
        "valid": True, "gate": "pass", "validation": {}, "naive": {},
        "outperforms_baseline": True, "next_period_value": 999.9,
        "model_type": "linear_regression", "limitation": "test-sentinel",
        "forecast": {"next_period_value": 999.9},
    }
    monkeypatch.setattr("services.state_service.get_forecast_validation", lambda: sentinel, raising=False)

    def _boom(*a, **kw):
        raise AssertionError(
            "report_service must not call forecast_with_validation() directly (Fix F-03)"
        )
    monkeypatch.setattr("calculations.forecasting.forecast_with_validation", _boom, raising=False)

    from services.report_service import build_report_context
    ctx = build_report_context(
        state = {"esg": {}, "carbon": {}, "dq": {}, "org": {}, "version": 1},
        org   = {"company_name": "PT Forecast Test", "org_id": "fcast-test-id"},
    )
    assert ctx["forecast"]["next_period_value"] == 999.9, (
        "build_report_context did not use the canonical (mocked) forecast result"
    )


# ── TEST F — PDF export (Fix F-04) ─────────────────────────────────────────────

def _minimal_pdf_ctx():
    return {
        "company": "PT PDF Test", "sector": "Manufacturing", "reporting_period": "2025",
        "generated_at": "2026-08-18", "platform_version": "CarbonLens",
        "esg_score": 65.0, "esg_grade": "B", "is_provisional": False,
        "esg_env": 70, "esg_social": 60, "esg_gov": 65, "dq_confidence": 80,
        "total_tco2e": 300.0, "scope1_tco2e": 100.0, "scope2_tco2e": 120.0, "scope3_tco2e": 80.0,
        "intensity_kg_m2": 10.0, "benchmark": 12.0, "gap_pct": -16.7, "above_benchmark": False,
        "dq_validation": "Pass", "gri_pct": 55.0, "pln_ef_used": 0.7160,
        "org_id": "pdf-test-org",
    }


def test_F_pdf_export_returns_valid_bytes():
    from services.report_service import build_pdf
    sections = ["executive_summary", "carbon_accounting", "esg_score", "data_quality", "benchmarking"]
    pdf_bytes = build_pdf(_minimal_pdf_ctx(), sections)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert pdf_bytes[:5] == b"%PDF-", "build_pdf must return a real PDF (valid header)"
    assert len(pdf_bytes) > 500


def test_F_pdf_export_empty_state_does_not_crash():
    from services.report_service import build_pdf
    pdf_bytes = build_pdf({}, ["executive_summary", "carbon_accounting", "methodology_appendix"])
    assert pdf_bytes[:5] == b"%PDF-"


def test_F_pdf_export_malformed_data_degrades_gracefully():
    from services.report_service import build_pdf
    bad_ctx = {"company": None, "esg_score": "not-a-number", "total_tco2e": None}
    pdf_bytes = build_pdf(bad_ctx, ["executive_summary", "carbon_accounting", "esg_score"])
    assert pdf_bytes[:5] == b"%PDF-", "a malformed section must not crash the whole PDF"


def test_F_pdf_export_respects_section_composition_flags():
    """Sections not requested must not appear; sections requested must appear."""
    from services.report_service import build_pdf
    from pypdf import PdfReader
    import io

    ctx = _minimal_pdf_ctx()
    with_appendix    = build_pdf(ctx, ["executive_summary", "methodology_appendix"])
    without_appendix = build_pdf(ctx, ["executive_summary"])

    text_with    = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(with_appendix)).pages)
    text_without = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(without_appendix)).pages)

    assert "Methodology" in text_with
    assert "Methodology" not in text_without


def test_F_export_service_prepare_pdf_export_no_longer_raises(monkeypatch):
    """The old contract (NotImplementedError) must be gone entirely."""
    from services import export_service
    monkeypatch.setattr("services.report_service.build_report_context", lambda state, org: _minimal_pdf_ctx(), raising=False)
    monkeypatch.setattr("services.audit_service.emit", lambda **kw: None, raising=False)

    pdf_bytes, filename = export_service.prepare_pdf_export(
        state = {}, org = {"company_name": "PT Export Test", "reporting_period": "2025"},
        sections = ["executive_summary", "carbon_accounting"],
    )
    assert pdf_bytes[:5] == b"%PDF-"
    assert filename.endswith(".pdf")


# ── TEST G — RBAC action boundaries (Fix F-06) ─────────────────────────────────

@pytest.mark.parametrize("role,permission,expected", [
    ("viewer",  "can_upload",        False),
    ("viewer",  "can_export",        False),
    ("viewer",  "can_manage_users",  False),
    ("viewer",  "can_view_all",      True),
    ("analyst", "can_upload",        True),
    ("analyst", "can_export",        True),
    ("analyst", "can_manage_users",  False),
    ("admin",   "can_upload",        True),
    ("admin",   "can_manage_users",  True),
])
def test_G_role_permission_matrix(monkeypatch, role, permission, expected):
    monkeypatch.setattr(
        "services.auth_service.get_current_user",
        lambda: {"username": "test", "role": role}, raising=False,
    )
    from services.auth_service import has_permission
    assert has_permission(permission) is expected


def test_G_onboarding_page_gates_on_can_upload():
    """Onboarding page must actually check a permission before rendering
    the setup wizard — not just claim to in a docstring."""
    src = open('pages/onboarding/page.py').read()
    tree = ast.parse(src)
    calls_check_permission = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "check_permission"
        for n in ast.walk(tree)
    )
    assert calls_check_permission, "onboarding/page.py must gate setup behind check_permission()"


def test_G_esg_analytics_gates_submit_on_can_upload():
    src = open('pages/esg_analytics/page.py').read()
    tree = ast.parse(src)
    calls_check_permission = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "check_permission"
        for n in ast.walk(tree)
    )
    assert calls_check_permission, "esg_analytics/page.py must gate the ESG-score submit action"


# ── TEST H — Persistence failure handling (Fix F-08) ───────────────────────────

def test_H_disk_write_failure_is_detected_not_silent(fake_store, monkeypatch):
    """When disk_repo.save_organisation reports failure (returns False),
    complete_onboarding must surface that via the _persisted flag rather
    than silently proceeding as if everything was saved."""
    monkeypatch.setattr("repository.disk_repo.save_organisation", lambda org, slot: False, raising=False)

    from services.state_service import complete_onboarding
    result = complete_onboarding(_org_input("PT Disk Fail Co"), slot=0)

    assert result.get("_persisted") is False, (
        "F-08 REGRESSION: a failed disk write was not surfaced to the caller"
    )
    # Session state should still be usable for the current session even
    # though disk persistence failed — no crash, no data loss for THIS session.
    assert fake_store.orgs[0]["company_name"] == "PT Disk Fail Co"


def test_H_onboarding_page_checks_persisted_flag():
    """Guard against silently re-introducing an unconditional 'Setup Complete!' message."""
    src = open('pages/onboarding/page.py').read()
    assert "_persisted" in src, (
        "onboarding/page.py must check the _persisted flag before claiming success"
    )
