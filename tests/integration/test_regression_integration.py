"""
CarbonLens V8 — Cross-page architecture regression tests (Sprint 11).

Verifies that every production page:
  1. Has zero calculation imports
  2. Has no direct st.session_state access
  3. Has no disallowed repository imports
  4. Has a callable render() function
  5. Has state_service as primary data source (calls get_computed_state)

Also verifies platform-wide invariants:
  6. All Phase 0 constants unchanged
  7. All approved event types present
  8. ComputedState version increments correctly
  9. Dual confidence architecture not violated
  10. Service layer is not bypassed by any page
"""
import ast
import importlib
import os
import pytest


PRODUCTION_PAGES = [
    "pages/executive_summary/page.py",
    "pages/carbon_accounting/page.py",
    "pages/esg_analytics/page.py",
    "pages/data_quality/page.py",
    "pages/governance/page.py",
]

ALLOWED_REPO = "repository.session_repo"   # only module pages may import from repo/


# ── 1. Zero calculation imports ───────────────────────────────────────────────

@pytest.mark.parametrize("page_path", PRODUCTION_PAGES)
def test_page_has_no_calculation_imports(page_path):
    src  = open(page_path).read()
    tree = ast.parse(src)
    bad  = [n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
            and n.module.startswith("calculations")]
    assert not bad, (
        f"{page_path} imports from calculations/: {bad}\n"
        "All calculations must go through state_service or carbon_service."
    )


# ── 2. No direct st.session_state ─────────────────────────────────────────────

@pytest.mark.parametrize("page_path", PRODUCTION_PAGES)
def test_page_has_no_session_state_access(page_path):
    src  = open(page_path).read()
    tree = ast.parse(src)
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "session_state"]
    assert not bad, (
        f"{page_path} accesses st.session_state directly: {bad}\n"
        "All session access must go through repository.session_repo."
    )


# ── 3. No disallowed repository imports ───────────────────────────────────────

@pytest.mark.parametrize("page_path", PRODUCTION_PAGES)
def test_page_has_no_disallowed_repository_imports(page_path):
    src     = open(page_path).read()
    tree    = ast.parse(src)
    bad     = [n.module for n in ast.walk(tree)
               if isinstance(n, ast.ImportFrom) and n.module
               and n.module.startswith("repository")
               and n.module != ALLOWED_REPO]
    assert not bad, (
        f"{page_path} imports from disallowed repository module(s): {bad}\n"
        f"Only {ALLOWED_REPO!r} is permitted (for navigation only)."
    )


# ── 4. All pages have callable render() ───────────────────────────────────────

@pytest.mark.parametrize("page_path", PRODUCTION_PAGES)
def test_page_has_callable_render(page_path):
    module_path = page_path.replace("/", ".").replace(".py", "")
    mod = importlib.import_module(module_path)
    assert callable(getattr(mod, "render", None)), \
        f"{page_path} does not have a callable render() function"


# ── 5. Pages import state_service as primary data source ─────────────────────

@pytest.mark.parametrize("page_path", PRODUCTION_PAGES)
def test_page_imports_state_service(page_path):
    src  = open(page_path).read()
    tree = ast.parse(src)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert any("state_service" in imp for imp in imports), \
        f"{page_path} does not import state_service — where does it get ComputedState?"


# ── 6. Phase 0 constants unchanged ───────────────────────────────────────────

def test_diesel_ef_phase0_h3():
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["diesel_kgco2_per_liter"] == 2.6967, \
        "Phase 0 H3 regression: diesel EF must be 2.6967 kg CO2e/L"


def test_pln_national_ef_kepmen():
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["electricity_pln_kwh"] == 0.7160, \
        "Phase 0 H3 regression: PLN national EF must be 0.7160 per Kepmen ESDM No.18/2023"


def test_esg_pillar_weights():
    from config.constants import ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV
    assert ESG_WEIGHT_ENV    == 0.40, "Phase 0 C2: E weight must be 0.40"
    assert ESG_WEIGHT_SOCIAL == 0.30, "Phase 0 C2: S weight must be 0.30"
    assert ESG_WEIGHT_GOV    == 0.30, "Phase 0 C2: G weight must be 0.30"
    assert abs(ESG_WEIGHT_ENV + ESG_WEIGHT_SOCIAL + ESG_WEIGHT_GOV - 1.0) < 1e-9


def test_provisional_floor():
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR
    assert CONFIDENCE_PROVISIONAL_FLOOR == 50.0, "Phase 0 C3: provisional floor must be 50%"


def test_scope3_coverage():
    from config.constants import SCOPE3_CATEGORIES_COVERED, SCOPE3_CATEGORIES_TOTAL, SCOPE3_SCREENED_EXCLUDED
    assert SCOPE3_CATEGORIES_COVERED == 12, "Phase 0 H2: 12 Scope 3 categories"
    assert SCOPE3_CATEGORIES_TOTAL   == 15, "Phase 0 H2: 15 total Scope 3 categories"
    assert len(SCOPE3_SCREENED_EXCLUDED) == 3, "Phase 0 H2: 3 categories excluded"


def test_dq_weights_sum_to_one():
    from config.constants import DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION
    total = DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION
    assert abs(total - 1.0) < 1e-9, f"DQ weights must sum to 1.0, got {total}"


# ── 7. All approved event types present ───────────────────────────────────────

def test_approved_event_types_count():
    from config.constants import APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 16, \
        f"Expected 13 approved event types, got {len(APPROVED_EVENT_TYPES)}"


def test_approved_event_types_are_strings():
    from config.constants import APPROVED_EVENT_TYPES
    for et in APPROVED_EVENT_TYPES:
        assert isinstance(et, str) and len(et) > 0, f"Invalid event type: {et!r}"


# ── 8. ComputedState version increments correctly ─────────────────────────────

def test_computed_state_version_increments():
    from state.computed import assemble
    from models.carbon import make_zero_inventory
    from models.esg    import make_provisional_esg
    from models.data_quality import make_no_data_quality
    from config.constants import STATE_STATUS_NO_DATA

    carbon = make_zero_inventory("org-v-test","2024","")
    esg    = make_provisional_esg("org-v-test")
    dq     = make_no_data_quality()

    s1 = assemble("org-v-test", "2024", carbon, esg, dq)
    s2 = assemble("org-v-test", "2024", carbon, esg, dq, previous=s1)
    s3 = assemble("org-v-test", "2024", carbon, esg, dq, previous=s2)

    assert s1["version"] == 1
    assert s2["version"] == 2
    assert s3["version"] == 3
    assert s2["previous_version_id"] == s1["state_id"]
    assert s3["previous_version_id"] == s2["state_id"]


def test_computed_state_immutability():
    """Once assembled, a ComputedState dict's content must not change."""
    from state.computed import assemble
    from models.carbon import make_zero_inventory
    from models.esg    import make_provisional_esg
    from models.data_quality import make_no_data_quality
    import copy

    carbon = make_zero_inventory("org-imm","2024","")
    esg    = make_provisional_esg("org-imm")
    dq     = make_no_data_quality()
    state  = assemble("org-imm","2024",carbon,esg,dq)
    orig   = copy.deepcopy(state)

    # Attempting to modify should not affect the original values
    # (Python dicts don't enforce immutability; we verify
    # the assemble function creates a new object each call)
    state2 = assemble("org-imm","2024",carbon,esg,dq,previous=state)
    assert state2["state_id"] != state["state_id"]
    assert state["version"] == orig["version"]   # state unchanged by s2 creation


# ── 9. Dual confidence architecture not violated ──────────────────────────────

def test_dual_confidence_independence():
    """ESG confidence and DQ confidence must be independently computable."""
    from calculations.confidence import compute_esg_confidence, build_confidence_score
    from calculations.data_quality import blend_dq_confidence

    # High S/G disclosure, low DQ
    esg_conf = compute_esg_confidence({
        "water_recycled_pct": 30, "employee_turnover_pct": 8,
        "training_hours_per_employee": 24, "women_workforce_pct": 35,
        "injury_rate": 0.5, "board_independence_pct": 55,
        "women_board_pct": 20, "has_code_of_conduct": True,
    })
    dq_conf = blend_dq_confidence(20.0, 50.0, 0.0, True)  # Low DQ

    assert esg_conf == 100.0, "Full S/G disclosure → ESG conf should be 100%"
    assert dq_conf  <= 40.0,  "Fail validation → DQ conf should be ≤ 40%"
    assert esg_conf != dq_conf, "ESG and DQ confidence must be independent"

    conf = build_confidence_score(esg_conf, dq_conf)
    assert conf["esg_confidence"]  == esg_conf
    assert conf["dq_confidence"]   == dq_conf
    assert conf["esg_confidence"]  != conf["dq_confidence"]


def test_confidence_score_model_has_required_fields():
    from calculations.confidence import build_confidence_score
    conf = build_confidence_score(75.0, 80.0)
    for key in ("esg_confidence","esg_is_provisional",
                "dq_confidence","dq_is_provisional","interpretation"):
        assert key in conf, f"ConfidenceScore missing field: {key}"


# ── 10. Service layer not bypassed ────────────────────────────────────────────

def test_services_not_bypassed_by_pages():
    """No production page imports carbon_service or esg_service directly."""
    for page_path in PRODUCTION_PAGES:
        src  = open(page_path).read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "carbon_service" not in node.module or "state_service" in node.module, \
                    f"{page_path} imports carbon_service directly"
                assert "esg_service" not in node.module, \
                    f"{page_path} imports esg_service directly"
                assert "data_quality_service" not in node.module, \
                    f"{page_path} imports data_quality_service directly"


def test_calculations_not_imported_anywhere_in_pages():
    """Scan all page Python files for calculation imports."""
    violations = []
    for root, _, files in os.walk("pages"):
        for fname in files:
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            path = os.path.join(root, fname)
            src  = open(path).read()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if (isinstance(node, ast.ImportFrom) and node.module
                        and node.module.startswith("calculations")):
                    violations.append(f"{path}: {node.module}")
    assert not violations, (
        f"Calculation imports found in pages/:\n" +
        "\n".join(f"  {v}" for v in violations)
    )
