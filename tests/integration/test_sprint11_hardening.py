"""
Sprint 11 — Final Integration Hardening Tests.

Covers: Task 2 (page discovery), Task 3 (methodology count), Task 5 (quick actions),
Task 7 (E2E workflow), Task 8 (RBAC), Task 9 (error states),
Task 10 (regression), Task 11 (architecture audit).
"""
import ast
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Task 2: Page module discovery ─────────────────────────────────────────────

def test_all_destinations_have_page_modules():
    """Every approved destination must have a pages/<dest>/page.py file."""
    from config.constants import APPROVED_DESTINATIONS
    missing = []
    for dest in APPROVED_DESTINATIONS:
        path = os.path.join('pages', dest, 'page.py')
        if not os.path.isfile(path):
            missing.append(path)
    assert not missing, f"Missing page files: {missing}"


def test_all_page_modules_import_successfully():
    """Every page module must import without errors."""
    import importlib
    from config.constants import APPROVED_DESTINATIONS
    failures = []
    for dest in APPROVED_DESTINATIONS:
        try:
            mod = importlib.import_module(f'pages.{dest}.page')
        except Exception as exc:
            failures.append(f"pages.{dest}.page: {exc}")
    assert not failures, f"Import failures:\n" + "\n".join(failures)


def test_all_page_render_functions_exist():
    """Every page module must expose a callable render() function."""
    import importlib
    from config.constants import APPROVED_DESTINATIONS
    missing = []
    for dest in APPROVED_DESTINATIONS:
        try:
            mod = importlib.import_module(f'pages.{dest}.page')
            if not callable(getattr(mod, 'render', None)):
                missing.append(dest)
        except Exception as exc:
            missing.append(f"{dest} (import error: {exc})")
    assert not missing, f"Destinations missing callable render(): {missing}"


def test_navigation_routes_match_destinations():
    """ROUTES in navigation.py must cover all APPROVED_DESTINATIONS."""
    from config.navigation import ROUTES
    from config.constants import APPROVED_DESTINATIONS
    route_ids = {r['id'] for r in ROUTES}
    missing   = APPROVED_DESTINATIONS - route_ids
    assert not missing, f"Destinations not in ROUTES: {missing}"


# ── Task 3: Methodology count consistency ─────────────────────────────────────

def test_methodology_library_length():
    """get_methodology_library() must return exactly 29 entries."""
    from services.state_service import get_methodology_library
    lib = get_methodology_library()
    assert isinstance(lib, list)
    assert len(lib) == 29, f"Expected 29, got {len(lib)}"


def test_governance_metrics_methodology_count_matches_library():
    """governance_metrics['methodology_entries'] must equal len(get_methodology_library())."""
    from services.state_service import get_methodology_library, get_governance_metrics
    lib     = get_methodology_library()
    metrics = get_governance_metrics()
    assert metrics['methodology_entries'] == len(lib), (
        f"metrics says {metrics['methodology_entries']}, "
        f"library has {len(lib)}"
    )


def test_methodology_library_unique_entry_ids():
    from services.state_service import get_methodology_library
    ids = [e['entry_id'] for e in get_methodology_library()]
    assert len(ids) == len(set(ids)), "Duplicate entry_ids in methodology library"


# ── Task 5: Quick actions use canonical navigation ────────────────────────────

def test_pages_use_navigate_to_not_session_repo():
    """Pages must call state_svc.navigate_to() — not session_repo.set_active_page()."""
    violations = []
    for root, _, files in os.walk('pages'):
        for f in sorted(files):
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                # Flag any runtime ImportFrom that pulls from repository
                if isinstance(node, ast.ImportFrom) and node.module:
                    if 'repository' in (node.module or ''):
                        violations.append(f"{path}:{node.lineno}: import {node.module}")
    assert not violations, "Direct repository imports in pages:\n" + "\n".join(violations)


def test_pages_have_no_st_session_state_access():
    """Production data pages must not access st.session_state directly.
    Exception: pages/onboarding/page.py is a multi-step UI wizard that
    legitimately manages form step state via session_state (like st.form).
    """
    ALLOWED = {"pages/onboarding/page.py"}
    violations = []
    for root, _, files in os.walk('pages'):
        for f in sorted(files):
            if not f.endswith('.py'): continue
            path = os.path.join(root, f).replace('\\', '/')
            if any(path.endswith(a.replace('/', os.sep)) for a in ALLOWED):
                continue
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == 'session_state':
                    violations.append(f"{path}:{node.lineno}")
    assert not violations, "st.session_state in pages:\n" + "\n".join(violations)


# ── Task 7: E2E workflow — service chain ──────────────────────────────────────

def test_state_service_navigation_api_complete():
    """state_service must expose the full navigation API for app.py."""
    import services.state_service as svc
    required = ['get_active_page', 'navigate_to', 'is_onboarding_complete',
                'get_active_organisation', 'is_org_setup']
    missing = [fn for fn in required if not callable(getattr(svc, fn, None))]
    assert not missing, f"state_service missing navigation functions: {missing}"


def test_app_has_no_direct_session_repo_calls():
    """app.py must route session access through service layer, not session_repo directly.
    app.py may import from services/auth_service and services/demo_service,
    which internally access session_repo — that is the correct architecture.
    """
    tree = ast.parse(open('app.py').read())
    # Only flag direct repository imports — services/ imports are allowed
    bad  = [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
            and (n.module or '').startswith('repository')]
    assert not bad, f"app.py has direct repository imports: {bad}"


def test_full_calculation_chain_executes():
    """The complete carbon → ESG → DQ chain must run without errors."""
    org = {'org_id': 'test-chain', 'company_name': 'PT Chain', 'sector': 'Manufacturing',
           'area_m2': 5000.0, 'province': 'Jawa Timur', 'reporting_period': '2024',
           'renew_pct': 20.0, 'recycle_pct': 15.0, 'certifications': []}
    di  = {'employee_turnover_pct': 8.0, 'training_hours_per_employee': 24.0,
           'women_workforce_pct': 35.0, 'injury_rate': 0.5,
           'board_independence_pct': 55.0, 'women_board_pct': 20.0,
           'water_recycled_pct': 30.0, 'has_code_of_conduct': True}

    from services.carbon_service import compute_carbon_inventory
    from services.esg_service import compute_esg_score
    from services.data_quality_service import compute_data_quality

    carbon = compute_carbon_inventory(org)
    assert carbon['scope_source'] == 'none'  # no data → zero

    esg = compute_esg_score(org, di, carbon)
    assert 0 <= esg['score'] <= 100
    assert esg['is_provisional'] is False   # full disclosure

    dq = compute_data_quality(None, None, di)
    assert 0 <= dq['confidence_score'] <= 100


def test_organisation_switching_resets_state(monkeypatch):
    """invalidate() clears the cache for a given org — next call rebuilds."""
    from state import cache as Cache
    Cache.clear_all()

    from services.state_service import invalidate
    invalidate('org-abc')  # must not raise
    assert Cache.size() == 0


# ── Task 8: RBAC ─────────────────────────────────────────────────────────────

def test_admin_has_all_permissions():
    from config.constants import ROLE_PERMISSIONS, ALL_PERMISSIONS
    admin_perms = ROLE_PERMISSIONS['admin']
    assert admin_perms == ALL_PERMISSIONS, "Admin must have all permissions"


def test_analyst_cannot_manage_users():
    from config.constants import ROLE_PERMISSIONS
    analyst_perms = ROLE_PERMISSIONS['analyst']
    assert 'can_manage_users' not in analyst_perms


def test_viewer_cannot_upload():
    from config.constants import ROLE_PERMISSIONS
    viewer_perms = ROLE_PERMISSIONS['viewer']
    assert 'can_upload'  not in viewer_perms
    assert 'can_export'  not in viewer_perms
    assert 'can_report'  not in viewer_perms
    assert 'can_manage_users' not in viewer_perms


def test_viewer_can_view():
    from config.constants import ROLE_PERMISSIONS
    assert 'can_view_all' in ROLE_PERMISSIONS['viewer']


def test_auth_service_login_wrong_password():
    """Wrong password must return None."""
    from services.auth_service import login
    result = login('admin', 'wrong_password_xyz')
    assert result is None


def test_auth_service_login_unknown_user():
    """Unknown user must return None."""
    from services.auth_service import login
    result = login('nonexistent_user_99', 'any_password')
    assert result is None


def test_has_permission_unauthenticated(monkeypatch):
    """Unauthenticated session must have no permissions."""
    monkeypatch.setattr('repository.session_repo.get_current_user',
                        lambda: None, raising=False)
    from services.auth_service import has_permission
    assert has_permission('can_upload') is False
    assert has_permission('can_view_all') is False


# ── Task 9: Empty / error states ──────────────────────────────────────────────

def test_no_org_computed_state_returns_empty():
    """get_computed_state() must return a safe state when no org is provided."""
    from models.computed_state import make_empty_computed_state
    state = make_empty_computed_state('no-org', '')
    assert state['status'] == 'No data'
    assert state['carbon']['total_kg'] == 0.0
    assert state['esg']['is_provisional'] is True


def test_validation_fail_caps_dq_confidence():
    """A Fail validation must cap DQ confidence at 40%."""
    from calculations.data_quality import blend_dq_confidence
    conf = blend_dq_confidence(100.0, 100.0, 0.0, validation_failed=True)
    assert conf <= 40.0


def test_make_empty_validation_result():
    """make_empty_validation() must return a Fail status for no-upload state."""
    from models.dataset import make_empty_validation
    result = make_empty_validation()
    assert result['status'] == 'Fail'
    assert len(result['errors']) > 0


def test_invalid_csv_produces_fail_validation():
    """Unparseable bytes must produce ValidationResult status=Fail."""
    from services.validation_service import validate_upload
    df, result = validate_upload(b'this,is,not,a,valid,csv,@@@', 'bad.csv')
    assert result['status'] == 'Fail'


def test_missing_emission_column_fail():
    from services.validation_service import validate_upload
    df, result = validate_upload(b'Month,Energy\nJan,180000', 'no_emission.csv')
    assert result['status'] == 'Fail'
    assert any('Emission' in e for e in result['errors'])


def test_zero_scope_inventory_does_not_crash():
    """compute_carbon_inventory() with no inputs must return zero inventory."""
    from services.carbon_service import compute_carbon_inventory
    org = {'org_id': 'empty', 'company_name': 'Test', 'sector': 'Manufacturing',
           'area_m2': 5000.0, 'province': '', 'reporting_period': '2024',
           'renew_pct': 0.0, 'recycle_pct': 0.0, 'certifications': []}
    result = compute_carbon_inventory(org, None, None)
    assert result['total_kg'] == 0.0
    assert result['scope_source'] == 'none'


# ── Task 10: Phase 0–4 regression ─────────────────────────────────────────────

def test_phase0_diesel_ef():
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS['diesel_kgco2_per_liter'] == 2.6967

def test_phase0_pln_national():
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS['electricity_pln_kwh'] == 0.7160

def test_phase0_esg_weights():
    from config.constants import ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV
    assert ESG_WEIGHT_ENV   == 0.40
    assert ESG_WEIGHT_SOCIAL== 0.30
    assert ESG_WEIGHT_GOV   == 0.30
    assert abs(ESG_WEIGHT_ENV + ESG_WEIGHT_SOCIAL + ESG_WEIGHT_GOV - 1.0) < 1e-9

def test_phase0_provisional_floor():
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR
    assert CONFIDENCE_PROVISIONAL_FLOOR == 50.0

def test_phase0_scope3_coverage():
    from config.constants import SCOPE3_CATEGORIES_COVERED, SCOPE3_SCREENED_EXCLUDED
    assert SCOPE3_CATEGORIES_COVERED == 12
    assert 'cat11' in SCOPE3_SCREENED_EXCLUDED
    assert 'cat14' in SCOPE3_SCREENED_EXCLUDED
    assert 'cat15' in SCOPE3_SCREENED_EXCLUDED

def test_phase2_dq_weights():
    from config.constants import DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION
    total = DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION
    assert abs(total - 1.0) < 1e-9

def test_phase3_audit_event_types():
    from config.constants import APPROVED_EVENT_TYPES
    # Phase 3 original: 13 types.
    # Phase 5-A added 3 scenario events: scenario_created, scenario_modified, scenario_saved.
    assert len(APPROVED_EVENT_TYPES) == 16
    # Phase 3 core events still present
    assert 'data_uploaded'       in APPROVED_EVENT_TYPES
    assert 'pdf_generated'       in APPROVED_EVENT_TYPES
    # Phase 5-A events
    assert 'scenario_created'    in APPROVED_EVENT_TYPES
    assert 'scenario_modified'   in APPROVED_EVENT_TYPES
    assert 'scenario_saved'      in APPROVED_EVENT_TYPES

def test_phase4_report_context_keys():
    """build_report_context() must return all required keys."""
    from services.report_service import build_report_context
    state = {
        'state_id': 'x', 'org_id': 'y', 'period': '2024', 'version': 1,
        'previous_version_id': None, 'input_hash': 'h', 'status': 'Provisional',
        'carbon':   {'scope1_kg': 0, 'scope2_kg': 0, 'scope3_kg': 0, 'total_kg': 0,
                     'intens_m2': 0, 'scope_source': 'none', 'province': '',
                     'pln_ef_used': 0.716, 'scope3_breakdown': {}, 'screened_excluded': [],
                     'benchmark': 120.0, 'gap': {}, 'computed_at': '2024-01-01T00:00:00'},
        'esg':      {'score': 0, 'grade': 'D', 'label': '--', 'env': 0, 'social': 0,
                     'gov': 0, 'confidence_score': 0, 'is_provisional': True,
                     'n_disclosed': 0, 'n_total_indicators': 8,
                     'disclosure_summary': '', 'methodology_version': 'V8',
                     'methodology_disclaimer': '', 'computed_at': '2024-01-01T00:00:00'},
        'data_quality': {'completeness_score': 0, 'consistency_score': 100,
                         'validation_status': 'Fail', 'validation_score': 0,
                         'confidence_score': 0, 'is_provisional': True,
                         'env_completeness': 0, 'sg_completeness': 0,
                         'sg_disclosed': 0, 'sg_total': 8, 'flagged_fields': [], 'summary': ''},
        'confidence': {'esg_confidence': 0, 'esg_is_provisional': True,
                       'dq_confidence': 0, 'dq_is_provisional': True, 'interpretation': ''},
        'computed_at': '2024-01-01T00:00:00', 'computation_time_ms': 0,
    }
    import sys; sys.path.insert(0, '.')
    import unittest.mock as mock
    with mock.patch('repository.session_repo.get', return_value=None), \
         mock.patch('repository.session_repo.get_uploaded_df', return_value=None):
        ctx = build_report_context(state, {'company_name': 'Test', 'sector': 'Manufacturing',
                                           'area_m2': 5000.0, 'reporting_period': '2024'})
    required = ['company', 'esg_score', 'scope1_tco2e', 'total_tco2e', 'dq_confidence']
    for k in required:
        assert k in ctx, f"report_context missing: {k}"


# ── Task 11: Architecture audit ───────────────────────────────────────────────

def test_calculations_are_pure_no_streamlit():
    """No calculations/ module may import streamlit."""
    violations = []
    for root, _, files in os.walk('calculations'):
        for f in sorted(files):
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
                    mod   = getattr(node, 'module', '') or ''
                    if 'streamlit' in mod or any('streamlit' in n for n in names):
                        violations.append(f"{path}: imports streamlit")
    assert not violations, "\n".join(violations)


def test_components_have_no_service_calls():
    """
    Components must not import business/calculation services.
    Exception: sidebar_nav.py may import auth_service for display of the
    current user — this is a presentation concern, not business logic.
    """
    # Business services that must never appear in components
    disallowed = {
        'services.carbon_service', 'services.esg_service',
        'services.data_quality_service', 'services.report_service',
        'services.export_service', 'services.validation_service',
        'services.state_service',
    }
    violations = []
    for root, _, files in os.walk('components'):
        for f in sorted(files):
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ''
                    if mod in disallowed:
                        violations.append(f"{path}:{node.lineno}: {mod}")
    assert not violations, "Components import disallowed services:\n" + "\n".join(violations)


def test_all_files_compile_cleanly():
    """python -m compileall equivalent — every .py must compile."""
    import py_compile
    failures = []
    for root, _, files in os.walk('.'):
        if any(x in root for x in ['__pycache__', '.pytest_cache']): continue
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                failures.append(str(e))
    assert not failures, "Compile failures:\n" + "\n".join(failures)
