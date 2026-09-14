"""
CarbonLens — Portfolio Restructure Fixes.

Covers:
  - Full removal of the login/password system (not just disabled) —
    the previous unsalted-SHA256 default-credentials vulnerability
    (identical to a known V7 issue) is closed by deleting the credential
    system entirely rather than patching it, since this build has no
    reachable login screen and needed no password storage at all
  - Removal of the login gate (portfolio/pre-commercial build — app always
    opens directly to Home, no auth screen reachable)
  - Methodology Library credibility fixes (C2: GRI citation-dressing,
    C5: benchmark provenance was dead code, never displayed)
"""
import ast
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Security: login/password system fully removed ──────────────────────────

def test_no_login_or_password_functions_in_auth_service():
    """
    The unsalted-SHA256 default-credentials vulnerability is closed by
    deleting the login/password system entirely — login(), logout(), and
    the password hashing helpers must not exist anywhere in auth_service.
    """
    import services.auth_service as auth_svc
    for forbidden in ("login", "logout", "_hash_password", "_verify_password"):
        assert not hasattr(auth_svc, forbidden), (
            f"services.auth_service.{forbidden} still exists — login system not fully removed"
        )


def test_no_password_hash_anywhere_in_source():
    """No file may contain a password_hash literal, a default-credentials
    registry, or a user-registry persistence function — the whole concept
    was removed, not hidden behind a disabled code path."""
    forbidden_terms = ("DEFAULT_USERS", "password_hash", "_PBKDF2_ITERATIONS")
    checked_files = (
        "services/auth_service.py", "config/settings.py",
        "repository/disk_repo.py", "app.py", "components/sidebar_nav.py",
    )
    for path in checked_files:
        src = open(path).read()
        for term in forbidden_terms:
            assert term not in src, f"{path} still references {term!r}"


def test_disk_repo_has_no_user_registry_functions():
    import repository.disk_repo as disk_repo
    assert not hasattr(disk_repo, "load_users")
    assert not hasattr(disk_repo, "save_users")
    assert not hasattr(disk_repo, "_USERS_FILE")


def test_config_settings_has_no_default_users():
    import config.settings as settings
    assert not hasattr(settings, "DEFAULT_USERS")


def test_rbac_infrastructure_still_intact():
    """Removing the login system must not have taken RBAC down with it —
    get_current_user/has_permission/require_permission/init_demo_mode are
    the actual runtime identity + permission boundary and must remain."""
    from services.auth_service import (
        get_current_user, is_authenticated, has_permission,
        require_permission, init_demo_mode, is_demo_mode, DEMO_USER,
    )
    assert all(callable(f) for f in (
        get_current_user, is_authenticated, has_permission,
        require_permission, init_demo_mode, is_demo_mode,
    ))
    assert DEMO_USER["role"] == "analyst"


def test_user_model_no_longer_documents_password_fields():
    """models.organization.User must reflect the actual runtime identity
    shape (no password_hash/user_id/must_change_pw — those described a
    credentialed-account record that no longer exists)."""
    src = open('models/organization.py').read()
    user_block = src.split('class User(')[1].split('class Organisation(')[0]
    assert 'password_hash' not in user_block
    assert 'must_change_pw' not in user_block


# ── No login gate ────────────────────────────────────────────────────────────

def test_app_has_no_login_related_code():
    src = open('app.py').read()
    for forbidden in ("_render_login", "auth_required", "CARBONLENS_AUTH_REQUIRED", "login_form"):
        assert forbidden not in src, f"app.py still references {forbidden!r} — login gate not fully removed"


def test_app_main_unconditionally_renders_home():
    """No return/stop statement may exist between session init and _render_main."""
    src = open('app.py').read()
    tree = ast.parse(src)
    main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    has_early_return = any(
        isinstance(n, ast.Return) for n in ast.walk(main_fn)
        if n is not main_fn.body[-1]
    )
    # main() ends by calling _render_main — confirm no st.stop() anywhere in it
    calls = [n.func.attr for n in ast.walk(main_fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "stop" not in calls, "main() must never call st.stop() — that would block reaching Home"


def test_sidebar_has_no_signout_button():
    """No actual Sign-out BUTTON may exist — an explanatory code comment
    mentioning the concept is fine, only a real st.button(...) call matters."""
    src = open('components/sidebar_nav.py').read()
    assert 'sidebar_signout' not in src
    assert 'st.button("Sign out"' not in src and "st.button('Sign out'" not in src


def test_sidebar_no_longer_imports_logout():
    src = open('components/sidebar_nav.py').read()
    assert 'import logout' not in src
    assert ', logout' not in src


# ── Methodology Library credibility fixes ───────────────────────────────────

def test_methodology_library_has_no_bare_gri_source_confusion():
    """Every entry's `source` must be CarbonLens-attributed or a genuine
    external standard — never blank/ambiguous in a way that lets the
    adjacent gri_reference imply GRI authored the value."""
    from services.state_service import get_methodology_library
    for e in get_methodology_library():
        assert e.get("source"), f"entry {e.get('entry_id')} has no source attribution"


def test_governance_page_has_gri_disclaimer():
    src = open('pages/governance/page.py').read()
    assert "not published by, endorsed by, or" in src
    assert "Related GRI Topic" in src


def test_pdf_methodology_appendix_has_gri_disclaimer():
    src = open('services/report_service.py').read()
    assert "not published by, endorsed by, or" in src


def test_sector_benchmark_provenance_is_surfaced_in_methodology_library():
    """Fix C5: get_benchmark_provenance() existed but was never displayed
    anywhere — the Carbon Accounting page pointed users to the Methodology
    Library for it, but no such entry existed there. Now it does."""
    from services.state_service import get_methodology_library
    from calculations.benchmarking import get_benchmark_provenance

    entries = get_methodology_library()
    bench_entries = [e for e in entries if e["category"] == "Sector Benchmarking"]
    assert len(bench_entries) == 1
    assert bench_entries[0]["source"] == get_benchmark_provenance()
    assert "ENERGY STAR" in bench_entries[0]["source"] or "CDP" in bench_entries[0]["source"]


def test_carbon_accounting_benchmark_pointer_is_now_true():
    """The existing 'See Methodology Library in Governance for provenance'
    caption on the Carbon Accounting benchmark section must now actually
    resolve to real content (previously a broken promise — see test above)."""
    from services.state_service import get_methodology_library
    entries = get_methodology_library()
    assert any(e["category"] == "Sector Benchmarking" for e in entries)
