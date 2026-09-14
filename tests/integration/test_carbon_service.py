"""Integration tests for services/carbon_service.py"""
import pytest
import pandas as pd


@pytest.fixture
def org():
    return {
        "org_id": "test-org-001", "company_name": "PT Test",
        "sector": "Manufacturing", "area_m2": 5000.0,
        "province": "Jawa Timur", "reporting_period": "2024",
        "renew_pct": 0.0, "recycle_pct": 0.0, "certifications": [],
    }


@pytest.fixture
def scope_inputs():
    return {
        "diesel_liters": 1000.0, "petrol_liters": 500.0,
        "electricity_kwh": 50000.0, "cat5_waste_kg": 2000.0,
    }


@pytest.fixture
def emission_df():
    return pd.DataFrame({
        "Month": ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"],
        "Emission": [245,268,231,259,277,242,264,251,239,267,245,258],
    })


def test_determine_scope_source_carbon_accounting(org, scope_inputs):
    from services.carbon_service import determine_scope_source
    assert determine_scope_source(org, None, scope_inputs) == "carbon_accounting"


def test_determine_scope_source_csv_estimate(org, emission_df):
    from services.carbon_service import determine_scope_source
    assert determine_scope_source(org, emission_df, None) == "csv_estimate"


def test_determine_scope_source_csv_scope_columns(org):
    from services.carbon_service import determine_scope_source
    df = pd.DataFrame({"Month":["Jan"],"Emission":[245],"Scope1":[50],"Scope2":[150],"Scope3":[45]})
    assert determine_scope_source(org, df, None) == "csv_scope_columns"


def test_determine_scope_source_none(org):
    from services.carbon_service import determine_scope_source
    assert determine_scope_source(org, None, None) == "none"


def test_compute_carbon_inventory_from_form(org, scope_inputs):
    from services.carbon_service import compute_carbon_inventory
    result = compute_carbon_inventory(org, None, scope_inputs)
    assert result["scope_source"] == "carbon_accounting"
    assert result["total_kg"] > 0
    assert result["scope1_kg"] > 0
    assert result["scope2_kg"] > 0
    assert result["org_id"] == "test-org-001"


def test_compute_carbon_inventory_total_equals_sum(org, scope_inputs):
    from services.carbon_service import compute_carbon_inventory
    r = compute_carbon_inventory(org, None, scope_inputs)
    expected = round(r["scope1_kg"] + r["scope2_kg"] + r["scope3_kg"], 2)
    assert abs(r["total_kg"] - expected) < 0.01


def test_compute_carbon_inventory_intensity_calculated(org, scope_inputs):
    from services.carbon_service import compute_carbon_inventory
    r = compute_carbon_inventory(org, None, scope_inputs)
    expected_intens = r["total_kg"] / org["area_m2"]
    assert abs(r["intens_m2"] - expected_intens) < 0.01


def test_compute_carbon_inventory_from_csv(org, emission_df):
    from services.carbon_service import compute_carbon_inventory
    r = compute_carbon_inventory(org, emission_df, None)
    assert r["scope_source"] == "csv_estimate"
    assert r["total_kg"] > 0


def test_compute_carbon_inventory_none_source(org):
    from services.carbon_service import compute_carbon_inventory
    r = compute_carbon_inventory(org, None, None)
    assert r["scope_source"] == "none"
    assert r["total_kg"] == 0.0
    assert r["intens_m2"] == 0.0


def test_compute_carbon_inventory_pln_ef_resolved(org, scope_inputs):
    from services.carbon_service import compute_carbon_inventory
    from config.settings import PLN_GRID_SUBSYSTEM, PLN_SUBSYSTEM_FACTORS
    r = compute_carbon_inventory(org, None, scope_inputs)
    prov = org["province"]
    expected_ef = PLN_SUBSYSTEM_FACTORS[PLN_GRID_SUBSYSTEM[prov]]
    assert r["pln_ef_used"] == expected_ef


def test_compute_carbon_inventory_has_benchmark(org, scope_inputs):
    from services.carbon_service import compute_carbon_inventory
    r = compute_carbon_inventory(org, None, scope_inputs)
    assert "benchmark" in r
    assert r["benchmark"] > 0
    assert "gap" in r
