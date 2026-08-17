"""Integration tests for services/esg_service.py"""
import pytest


@pytest.fixture
def org():
    return {
        "org_id": "test-org-001", "sector": "Manufacturing",
        "area_m2": 5000.0, "renew_pct": 20.0,
        "recycle_pct": 15.0, "certifications": ["ISO 14001"],
        "reporting_period": "2024",
    }


@pytest.fixture
def full_disclosure():
    return {
        "water_recycled_pct": 30.0, "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0, "women_workforce_pct": 35.0,
        "injury_rate": 0.5, "board_independence_pct": 55.0,
        "women_board_pct": 20.0, "has_code_of_conduct": True,
        "disclosure_score": 70.0,
    }


@pytest.fixture
def carbon():
    return {
        "intens_m2": 80.0, "benchmark": 120.0,
        "scope1_kg": 50000.0, "scope2_kg": 100000.0, "scope3_kg": 25000.0,
        "total_kg": 175000.0,
    }


def test_compute_esg_score_returns_schema(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, full_disclosure, carbon)
    required = ["org_id","score","grade","label","env","social","gov",
                "confidence_score","is_provisional","methodology_version"]
    for key in required:
        assert key in r, f"Missing key: {key}"


def test_compute_esg_score_range(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, full_disclosure, carbon)
    assert 0.0 <= r["score"] <= 100.0
    assert 0.0 <= r["env"] <= 100.0
    assert 0.0 <= r["social"] <= 100.0
    assert 0.0 <= r["gov"] <= 100.0


def test_compute_esg_score_no_disclosure_is_provisional(org, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, {}, carbon)
    assert r["is_provisional"] is True
    assert r["confidence_score"] == 0.0


def test_compute_esg_score_full_disclosure_substantive(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, full_disclosure, carbon)
    assert r["is_provisional"] is False
    assert r["confidence_score"] == 100.0


def test_compute_esg_score_grade_assigned(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, full_disclosure, carbon)
    assert r["grade"] in {"A", "B+", "B", "C", "D"}


def test_compute_esg_score_composite_weights(org, carbon):
    """Score must follow E×0.40 + S×0.30 + G×0.30 weighting."""
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, {}, carbon)
    expected = round(r["env"] * 0.40 + r["social"] * 0.30 + r["gov"] * 0.30, 2)
    assert abs(r["score"] - expected) < 0.1


def test_compute_esg_score_n_disclosed_counted(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    r = compute_esg_score(org, full_disclosure, carbon)
    assert r["n_disclosed"] == 8
    assert r["n_total_indicators"] == 8


def test_compute_esg_score_methodology_version(org, full_disclosure, carbon):
    from services.esg_service import compute_esg_score
    from config.constants import CURRENT_METHODOLOGY_VERSION
    r = compute_esg_score(org, full_disclosure, carbon)
    assert r["methodology_version"] == CURRENT_METHODOLOGY_VERSION
