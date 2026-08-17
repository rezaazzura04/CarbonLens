"""Unit tests for calculations/ghg.py"""
import pytest


def test_scope1_zero_inputs():
    from calculations.ghg import calculate_scope1
    r = calculate_scope1()
    assert r["total_kg"] == 0.0
    assert r["breakdown"]["biomass"] == 0.0


def test_scope1_diesel_only():
    from calculations.ghg import calculate_scope1
    from config.settings import EMISSION_FACTORS as EF
    r = calculate_scope1(diesel_liters=100.0)
    expected = round(100.0 * EF["diesel_kgco2_per_liter"], 4)
    assert r["total_kg"] == expected
    assert r["breakdown"]["diesel"] == expected


def test_scope1_biomass_excluded_from_total():
    from calculations.ghg import calculate_scope1
    r = calculate_scope1(biomass_kg=500.0, diesel_liters=0.0)
    assert r["total_kg"] == 0.0
    assert r["breakdown"]["biomass"] == 0.0


def test_scope1_all_fuels():
    from calculations.ghg import calculate_scope1
    r = calculate_scope1(
        diesel_liters=100, petrol_liters=50, lpg_kg=30,
        natural_gas_m3=20, cng_m3=10, coal_kg=40
    )
    assert r["total_kg"] > 0
    assert len(r["breakdown"]) == 7


def test_scope1_negative_raises():
    from calculations.ghg import calculate_scope1
    with pytest.raises(ValueError, match="diesel_liters"):
        calculate_scope1(diesel_liters=-1.0)


def test_scope1_h3_fix_diesel_factor():
    """Phase 0 H3: diesel EF must be full CO2e (2.6967), not CO2-only (2.68)."""
    from config.settings import EMISSION_FACTORS as EF
    assert EF["diesel_kgco2_per_liter"] == 2.6967


def test_scope2_basic():
    from calculations.ghg import calculate_scope2
    r = calculate_scope2(electricity_kwh=1000.0, pln_ef=0.716)
    assert r["total_kg"] == round(1000.0 * 0.716, 4)
    assert r["ef_used"] == 0.716


def test_scope2_zero_kwh():
    from calculations.ghg import calculate_scope2
    r = calculate_scope2(electricity_kwh=0.0, pln_ef=0.716)
    assert r["total_kg"] == 0.0


def test_scope2_invalid_ef():
    from calculations.ghg import calculate_scope2
    with pytest.raises(ValueError, match="pln_ef"):
        calculate_scope2(electricity_kwh=100.0, pln_ef=0.0)


def test_scope2_negative_kwh_raises():
    from calculations.ghg import calculate_scope2
    with pytest.raises(ValueError, match="electricity_kwh"):
        calculate_scope2(electricity_kwh=-100.0, pln_ef=0.716)


def test_scope3_zero_inputs():
    from calculations.ghg import calculate_scope3
    r = calculate_scope3()
    assert r["total_kg"] == 0.0
    assert len(r["screened_excluded"]) == 3   # cat11, cat14, cat15


def test_scope3_single_category():
    from calculations.ghg import calculate_scope3
    from config.settings import SCOPE3_EMISSION_FACTORS as EF
    r = calculate_scope3(cat5_waste_kg=1000.0)
    expected = round(1000.0 * EF["cat5_waste"]["ef"], 4)
    assert r["breakdown"]["cat5_waste"] == expected


def test_scope3_negative_raises():
    from calculations.ghg import calculate_scope3
    with pytest.raises(ValueError, match="cat5_waste_kg"):
        calculate_scope3(cat5_waste_kg=-10.0)


def test_calculate_intensity_basic():
    from calculations.ghg import calculate_intensity
    assert calculate_intensity(12000.0, 100.0) == 120.0


def test_calculate_intensity_zero_area():
    from calculations.ghg import calculate_intensity
    assert calculate_intensity(12000.0, 0.0) == 0.0


def test_aggregate_scope_totals():
    from calculations.ghg import aggregate_scope_totals
    s1 = {"total_kg": 1000.0}
    s2 = {"total_kg": 2000.0}
    s3 = {"total_kg": 500.0}
    r  = aggregate_scope_totals(s1, s2, s3, area_m2=100.0)
    assert r["total_kg"]  == 3500.0
    assert r["scope1_kg"] == 1000.0
    assert r["intens_m2"] == 35.0


def test_resolve_pln_ef_known_province():
    from calculations.ghg import resolve_pln_ef
    from config.settings import PLN_GRID_SUBSYSTEM, PLN_SUBSYSTEM_FACTORS
    prov = "Jawa Timur"
    expected = PLN_SUBSYSTEM_FACTORS[PLN_GRID_SUBSYSTEM[prov]]
    assert resolve_pln_ef(prov) == expected


def test_resolve_pln_ef_unknown_province():
    from calculations.ghg import resolve_pln_ef
    from config.settings import EMISSION_FACTORS
    ef = resolve_pln_ef("Unknown Province XYZ")
    assert ef == EMISSION_FACTORS["electricity_pln_kwh"]
