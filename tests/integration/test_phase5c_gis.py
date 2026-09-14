"""
CarbonLens — Phase 5-C: Spatial / Land-Use Context (Experimental).

Covers:
  - calculations/gis_math.py pure functions (AGB proxy, forest masking,
    carbon stock, loss trend)
  - services/gis_service.py orchestration (synthetic fallback, live-EE
    attempt structure, audit emission)
  - state_service.py wiring (session persistence, lazy-load flag)
  - Architecture: never queried on initial page render; page only imports
    permitted services; calculations stay pure
  - Credibility fixes: honest citation (not falsely claiming to reproduce
    Saatchi et al.'s actual regression), structural forest-only masking
    (no function accepts a pre-blended whole-AOI NDVI for biomass)
"""
import ast
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── calculations/gis_math.py — pure function behavior ──────────────────────

def test_ndvi_to_agb_proxy_basic():
    from calculations.gis_math import ndvi_to_agb_proxy
    r = ndvi_to_agb_proxy(0.72)
    assert r["agb_mg_ha"] > 0
    assert r["saturated"] is False
    assert "agb_formula" in r and "citation" in r


def test_ndvi_to_agb_proxy_saturation_flag():
    from calculations.gis_math import ndvi_to_agb_proxy
    from config.constants import NDVI_SATURATION_THRESHOLD
    r_low  = ndvi_to_agb_proxy(NDVI_SATURATION_THRESHOLD - 0.1)
    r_high = ndvi_to_agb_proxy(NDVI_SATURATION_THRESHOLD + 0.1)
    assert r_low["saturated"] is False
    assert r_high["saturated"] is True


def test_ndvi_to_agb_proxy_clamps_out_of_range_input():
    from calculations.gis_math import ndvi_to_agb_proxy
    r_neg = ndvi_to_agb_proxy(-5.0)
    r_big = ndvi_to_agb_proxy(50.0)
    assert r_neg["agb_mg_ha"] >= 0
    assert r_big["agb_mg_ha"] > 0   # doesn't explode/crash on out-of-range input


def test_agb_formula_and_carbon_formula_do_not_collide():
    """Regression guard for the exact bug caught during development: both
    dicts previously used the key 'formula', so merging them silently
    dropped the AGB formula string."""
    from calculations.gis_math import ndvi_to_agb_proxy, agb_to_carbon_stock
    agb = ndvi_to_agb_proxy(0.6)
    carbon = agb_to_carbon_stock(agb["agb_mg_ha"], 100.0)
    assert set(agb.keys()) & set(carbon.keys()) == set(), "key collision reintroduced"
    combined = {**agb, **carbon}
    assert "agb_formula" in combined
    assert "carbon_formula" in combined


def test_agb_to_carbon_stock_uses_ipcc_default_factor():
    from calculations.gis_math import agb_to_carbon_stock
    from config.constants import BIOMASS_TO_CARBON_FACTOR
    r = agb_to_carbon_stock(agb_mg_ha=10.0, forest_area_ha=100.0)
    expected_tc = 10.0 * 100.0 * BIOMASS_TO_CARBON_FACTOR
    assert abs(r["carbon_stock_tc"] - expected_tc) < 0.5


def test_estimate_forest_carbon_stock_never_blends_land_cover():
    """
    Fix M5 (structural, not just documented): feeding a HIGH agriculture
    NDVI must not inflate the biomass estimate — only the forest-class NDVI
    may influence agb_mg_ha, regardless of what the other classes' NDVI
    values are.
    """
    from calculations.gis_math import estimate_forest_carbon_stock

    land_cover = {"forest_pct": 30, "agriculture_pct": 70, "water_pct": 0,
                  "built_up_pct": 0, "other_pct": 0}

    low_other = estimate_forest_carbon_stock(
        land_cover, {"forest": 0.5, "agriculture": 0.1, "water": 0, "built_up": 0, "other": 0},
        aoi_area_ha=1000.0,
    )
    high_other = estimate_forest_carbon_stock(
        land_cover, {"forest": 0.5, "agriculture": 0.9, "water": 0, "built_up": 0, "other": 0},
        aoi_area_ha=1000.0,
    )
    assert low_other["agb_mg_ha"] == high_other["agb_mg_ha"], (
        "Non-forest NDVI must never affect the biomass estimate — masking was bypassed"
    )


def test_estimate_forest_carbon_stock_zero_forest_gives_zero_carbon():
    from calculations.gis_math import estimate_forest_carbon_stock
    r = estimate_forest_carbon_stock(
        {"forest_pct": 0, "agriculture_pct": 100, "water_pct": 0, "built_up_pct": 0, "other_pct": 0},
        {"forest": 0.9, "agriculture": 0.9, "water": 0.9, "built_up": 0.9, "other": 0.9},
        aoi_area_ha=500.0,
    )
    assert r["carbon_stock_tc"] == 0.0
    assert r["forest_area_ha"] == 0.0


def test_classify_forest_loss_trend_handles_edge_cases():
    from calculations.gis_math import classify_forest_loss_trend
    assert classify_forest_loss_trend([])["direction"] == "insufficient_data"
    assert classify_forest_loss_trend([100])["direction"] == "insufficient_data"
    assert classify_forest_loss_trend([0, 50])["direction"] == "insufficient_data"  # first<=0 guard
    assert classify_forest_loss_trend([100, 150])["direction"] == "increasing"
    assert classify_forest_loss_trend([100, 60])["direction"] == "decreasing"
    assert classify_forest_loss_trend([100, 105])["direction"] == "stable"


def test_gis_math_module_has_no_streamlit_or_session_state():
    """Architecture invariant: calculations/ must stay pure — no Streamlit,
    no session state, no I/O."""
    src = open('calculations/gis_math.py').read()
    tree = ast.parse(src)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert not any(m.startswith("streamlit") for m in imported_modules)
    assert "session_state" not in src


# ── Credibility fix C4: honest citation ─────────────────────────────────────

def test_agb_citation_does_not_falsely_claim_saatchi_reproduction():
    from config.constants import NDVI_AGB_PROXY_CITATION
    text = NDVI_AGB_PROXY_CITATION.lower()
    assert "not a reproduction" in text or "not a direct reproduction" in text
    assert "saatchi" in text   # still names the real source it's loosely inspired by
    assert "proxy" in text or "simplified" in text


# ── services/gis_service.py — orchestration ─────────────────────────────────

def test_run_spatial_query_falls_back_to_synthetic_without_credentials(monkeypatch):
    """In any environment without real Earth Engine credentials configured
    (true for this dev/test environment), run_spatial_query must gracefully
    fall back rather than raise."""
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.gis_service import run_spatial_query
    r = run_spatial_query(lat=-7.5, lon=112.2, radius_km=5.0, province="Jawa Timur")
    assert r["data_source"] == "synthetic_fallback"
    assert r["carbon_stock_tc"] >= 0
    assert "loss_trend" in r


def test_run_spatial_query_synthetic_is_deterministic_per_location(monkeypatch):
    """Same lat/lon must produce the same synthetic land-cover breakdown
    within a session — not re-randomised on every call."""
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.gis_service import run_spatial_query
    r1 = run_spatial_query(lat=-6.2, lon=106.8, radius_km=5.0, province="DKI Jakarta")
    r2 = run_spatial_query(lat=-6.2, lon=106.8, radius_km=5.0, province="DKI Jakarta")
    assert r1["land_cover"] == r2["land_cover"]


def test_run_spatial_query_different_locations_differ(monkeypatch):
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    from services.gis_service import run_spatial_query
    r1 = run_spatial_query(lat=-6.2, lon=106.8, radius_km=5.0, province="DKI Jakarta")
    r2 = run_spatial_query(lat=3.5, lon=98.6, radius_km=5.0, province="Sumatera Utara")
    assert r1["land_cover"] != r2["land_cover"]


def test_run_spatial_query_emits_gis_query_run_audit_event(monkeypatch):
    captured = {}
    def _fake_write(**kw):
        captured.update(kw)
    monkeypatch.setattr("audit.writer.write_audit_event", _fake_write, raising=False)

    from services.gis_service import run_spatial_query
    run_spatial_query(lat=-7.5, lon=112.2, radius_km=5.0, province="Jawa Timur",
                       org_id="org-123", company_name="PT Test")
    assert captured.get("event_type") == "gis_query_run"
    assert captured.get("org_id") == "org-123"


def test_gis_query_run_is_an_approved_event_type():
    from config.constants import APPROVED_EVENT_TYPES
    assert "gis_query_run" in APPROVED_EVENT_TYPES


def test_live_earth_engine_attempt_never_raises_on_missing_credentials():
    """This dev/test environment has earthengine-api installed but no
    credentials — _try_live_earth_engine must return None, never raise."""
    from services.gis_service import _try_live_earth_engine
    result = _try_live_earth_engine(lat=-7.5, lon=112.2, radius_km=5.0)
    assert result is None


def test_earthengine_api_is_genuinely_installed():
    """Fix for audit finding 4.1: earthengine-api must be a real, importable
    dependency, not just referenced in a comment."""
    import ee
    assert ee is not None


def test_math_area_ha_conversion():
    from services.gis_service import math_area_ha
    import math
    r = math_area_ha(1.0)
    assert abs(r - (math.pi * 100)) < 1.0   # 1km radius circle in hectares


# ── state_service.py wiring ──────────────────────────────────────────────────

def test_state_service_run_spatial_query_persists_and_opens_panel(monkeypatch):
    monkeypatch.setattr("audit.writer.write_audit_event", lambda **kw: None, raising=False)
    import services.state_service as svc
    result = svc.run_spatial_query(lat=-7.5, lon=112.2, radius_km=5.0, province="Jawa Timur")
    assert svc.get_spatial_context() is not None
    assert svc.get_spatial_context()["data_source"] == result["data_source"]
    assert svc.is_spatial_panel_open() is True


def test_state_service_spatial_panel_closed_by_default(monkeypatch):
    import services.state_service as svc
    from repository.session_repo import set_spatial_panel_open
    # Explicitly reset for this slot/test isolation
    set_spatial_panel_open(False)
    assert svc.is_spatial_panel_open() is False
    assert svc.get_spatial_context() is None or isinstance(svc.get_spatial_context(), dict)


# ── Architecture: never queried on initial page render ──────────────────────

def test_carbon_accounting_page_never_calls_run_spatial_query_unconditionally():
    """
    AST check: run_spatial_query() may only appear as a Call inside a
    function body that is NOT render() itself at module level — it must be
    reachable only from inside a button-click branch. We approximate this
    by confirming render() itself contains no direct call to
    run_spatial_query — only to the section function, which internally
    gates it behind st.button(...).
    """
    src = open('pages/carbon_accounting/page.py').read()
    tree = ast.parse(src)
    render_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "render")
    render_calls = {
        n.func.attr for n in ast.walk(render_fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "run_spatial_query" not in render_calls, (
        "render() must never call run_spatial_query directly — only inside a button handler"
    )


def test_spatial_query_call_is_gated_behind_a_button_click():
    """The only call sites of state_svc.run_spatial_query in the page must
    be inside an `if st.button(...)` block."""
    src = open('pages/carbon_accounting/page.py').read()
    tree = ast.parse(src)

    def _is_inside_button_if(node, tree):
        for parent in ast.walk(tree):
            if isinstance(parent, ast.If):
                if any(n is node for n in ast.walk(parent)):
                    test_src = ast.dump(parent.test)
                    if "button" in test_src:
                        return True
        return False

    call_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "run_spatial_query"
    ]
    assert call_nodes, "expected at least one run_spatial_query call site in the page"
    for node in call_nodes:
        assert _is_inside_button_if(node, tree), "run_spatial_query call is not gated behind a button click"


def test_carbon_accounting_page_docstring_lists_gis_service():
    src = open('pages/carbon_accounting/page.py').read()
    assert "gis_service" in src.split('"""')[1]   # module docstring


def test_spatial_section_always_shows_experimental_badge():
    src = open('pages/carbon_accounting/page.py').read()
    assert "EXPERIMENTAL" in src


# ── Config sanity ────────────────────────────────────────────────────────────

def test_all_onboarding_provinces_have_centroids():
    from pages.onboarding.page import PROVINCES
    from config.constants import PROVINCE_CENTROIDS
    missing = [p for p in PROVINCES if p not in PROVINCE_CENTROIDS]
    assert not missing, f"Provinces missing centroid coordinates: {missing}"


def test_province_centroids_are_plausible_indonesia_coordinates():
    from config.constants import PROVINCE_CENTROIDS
    for province, (lat, lon) in PROVINCE_CENTROIDS.items():
        assert -11 <= lat <= 6, f"{province} latitude {lat} outside Indonesia's range"
        assert 95 <= lon <= 141, f"{province} longitude {lon} outside Indonesia's range"
