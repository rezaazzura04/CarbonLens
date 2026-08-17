"""Integration tests for services/data_quality_service.py"""
import pytest
import pandas as pd


@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
        "Emission": [245,268,231,259,277,242,264,251,239,267,245,258],
        "Energy":   [180000]*12,
    })


@pytest.fixture
def pass_validation():
    return {"status": "Pass", "errors": [], "warnings": []}


@pytest.fixture
def fail_validation():
    return {"status": "Fail", "errors": ["Required column missing"], "warnings": []}


@pytest.fixture
def full_disclosure():
    return {
        "water_recycled_pct": 30.0, "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0, "women_workforce_pct": 35.0,
        "injury_rate": 0.5, "board_independence_pct": 55.0,
        "women_board_pct": 20.0, "has_code_of_conduct": True,
    }


def test_compute_dq_returns_schema(clean_df, pass_validation, full_disclosure):
    from services.data_quality_service import compute_data_quality
    r = compute_data_quality(clean_df, pass_validation, full_disclosure)
    for key in ["completeness_score","consistency_score","confidence_score",
                "is_provisional","flagged_fields","validation_status"]:
        assert key in r, f"Missing: {key}"


def test_compute_dq_pass_validation_high_confidence(clean_df, pass_validation, full_disclosure):
    from services.data_quality_service import compute_data_quality
    r = compute_data_quality(clean_df, pass_validation, full_disclosure)
    assert r["confidence_score"] > 60.0
    assert r["validation_status"] == "Pass"


def test_compute_dq_fail_validation_capped(clean_df, fail_validation):
    from services.data_quality_service import compute_data_quality
    r = compute_data_quality(clean_df, fail_validation, {})
    assert r["confidence_score"] <= 40.0


def test_compute_dq_no_data():
    from services.data_quality_service import compute_data_quality
    r = compute_data_quality(None, None, None)
    assert r["is_provisional"] is True
    assert r["confidence_score"] <= 40.0


def test_compute_dq_flags_deduped(clean_df, pass_validation):
    from services.data_quality_service import compute_data_quality
    r = compute_data_quality(clean_df, pass_validation, {})
    keys = [(f["field_name"], f["reason"]) for f in r["flagged_fields"]]
    assert len(keys) == len(set(keys))


def test_compute_dq_full_disclosure_improves_score(clean_df, pass_validation, full_disclosure):
    from services.data_quality_service import compute_data_quality
    low  = compute_data_quality(clean_df, pass_validation, {})
    high = compute_data_quality(clean_df, pass_validation, full_disclosure)
    assert high["confidence_score"] >= low["confidence_score"]
