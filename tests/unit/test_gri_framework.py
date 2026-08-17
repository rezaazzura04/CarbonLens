"""Unit tests for calculations/gri_framework.py"""
import pytest
import pandas as pd


@pytest.fixture
def full_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar"],
        "Emission": [245, 268, 231],
        "Energy":   [180000, 195000, 172000],
        "Waste":    [12.4, 11.8, 13.1],
    })


@pytest.fixture
def full_disclosure():
    return {
        "water_recycled_pct": 30.0,
        "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0,
        "women_workforce_pct": 35.0,
        "injury_rate": 0.5,
        "board_independence_pct": 55.0,
        "women_board_pct": 20.0,
        "has_code_of_conduct": True,
        "recycle_pct": 25.0,
    }


def test_run_gap_analysis_returns_list(full_df, full_disclosure):
    from calculations.gri_framework import run_gap_analysis
    result = run_gap_analysis(full_disclosure, full_df)
    assert isinstance(result, list)
    assert len(result) > 0


def test_run_gap_analysis_schema(full_df, full_disclosure):
    from calculations.gri_framework import run_gap_analysis
    result = run_gap_analysis(full_disclosure, full_df)
    for r in result:
        assert "id" in r
        assert "standard" in r
        assert "title" in r
        assert "pillar" in r
        assert "covered" in r
        assert isinstance(r["covered"], bool)


def test_run_gap_analysis_no_data():
    from calculations.gri_framework import run_gap_analysis
    result = run_gap_analysis({}, None)
    assert isinstance(result, list)
    for r in result:
        # With no data and no disclosure, most should be uncovered
        assert isinstance(r["covered"], bool)


def test_gri_coverage_full(full_df, full_disclosure):
    from calculations.gri_framework import run_gap_analysis, gri_coverage_pct
    result = run_gap_analysis(full_disclosure, full_df)
    pct = gri_coverage_pct(result)
    assert 0.0 <= pct <= 100.0
    assert pct > 50.0  # Full disclosure + full dataset should be > 50%


def test_gri_coverage_empty():
    from calculations.gri_framework import gri_coverage_pct
    assert gri_coverage_pct([]) == 0.0


def test_gri_coverage_none_covered():
    from calculations.gri_framework import gri_coverage_pct
    result = [{"covered": False}] * 10
    assert gri_coverage_pct(result) == 0.0


def test_gri_coverage_all_covered():
    from calculations.gri_framework import gri_coverage_pct
    result = [{"covered": True}] * 10
    assert gri_coverage_pct(result) == 100.0


def test_gri_coverage_by_pillar(full_df, full_disclosure):
    from calculations.gri_framework import run_gap_analysis, gri_coverage_by_pillar
    result = run_gap_analysis(full_disclosure, full_df)
    by_pillar = gri_coverage_by_pillar(result)
    assert set(by_pillar.keys()) == {"E", "S", "G"}
    for pct in by_pillar.values():
        assert 0.0 <= pct <= 100.0


def test_energy_coverage_with_energy_column(full_df):
    from calculations.gri_framework import run_gap_analysis
    result = run_gap_analysis({}, full_df)
    energy_indicators = [r for r in result if r["id"] == "GRI-302-1"]
    assert len(energy_indicators) == 1
    assert energy_indicators[0]["covered"] is True


def test_energy_coverage_without_energy_column():
    from calculations.gri_framework import run_gap_analysis
    df = pd.DataFrame({"Month": ["Jan"], "Emission": [245]})
    result = run_gap_analysis({}, df)
    energy_indicators = [r for r in result if r["id"] == "GRI-302-1"]
    assert energy_indicators[0]["covered"] is False
