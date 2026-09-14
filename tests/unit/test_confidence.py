"""Unit tests for calculations/confidence.py"""
import pytest


def test_esg_confidence_full_disclosure():
    from calculations.confidence import compute_esg_confidence
    inputs = {
        "water_recycled_pct": 30.0,
        "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0,
        "women_workforce_pct": 35.0,
        "injury_rate": 0.5,
        "board_independence_pct": 55.0,
        "women_board_pct": 20.0,
        "has_code_of_conduct": True,
    }
    conf = compute_esg_confidence(inputs)
    assert conf == 100.0


def test_esg_confidence_no_disclosure():
    from calculations.confidence import compute_esg_confidence
    conf = compute_esg_confidence({})
    assert conf == 0.0


def test_esg_confidence_half_disclosure():
    from calculations.confidence import compute_esg_confidence
    inputs = {
        "water_recycled_pct": 30.0,
        "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0,
        "women_workforce_pct": 35.0,
    }
    conf = compute_esg_confidence(inputs)
    assert conf == 50.0


def test_is_provisional_below_floor():
    from calculations.confidence import is_esg_provisional
    assert is_esg_provisional(49.9) is True


def test_is_provisional_at_floor():
    from calculations.confidence import is_esg_provisional
    assert is_esg_provisional(50.0) is False


def test_is_provisional_above_floor():
    from calculations.confidence import is_esg_provisional
    assert is_esg_provisional(75.0) is False


def test_build_confidence_score_schema():
    from calculations.confidence import build_confidence_score
    r = build_confidence_score(esg_conf=80.0, dq_conf=75.0)
    assert "esg_confidence" in r
    assert "esg_is_provisional" in r
    assert "dq_confidence" in r
    assert "dq_is_provisional" in r
    assert "interpretation" in r


def test_build_confidence_score_both_provisional():
    from calculations.confidence import build_confidence_score
    r = build_confidence_score(esg_conf=20.0, dq_conf=30.0)
    assert r["esg_is_provisional"] is True
    assert r["dq_is_provisional"] is True


def test_build_confidence_score_neither_provisional():
    from calculations.confidence import build_confidence_score
    r = build_confidence_score(esg_conf=80.0, dq_conf=85.0)
    assert r["esg_is_provisional"] is False
    assert r["dq_is_provisional"] is False


def test_count_disclosed_all():
    from calculations.confidence import count_disclosed
    inputs = {
        "water_recycled_pct": 30.0, "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0, "women_workforce_pct": 35.0,
        "injury_rate": 0.5, "board_independence_pct": 55.0,
        "women_board_pct": 20.0, "has_code_of_conduct": True,
    }
    n, total = count_disclosed(inputs)
    assert n == 8
    assert total == 8


def test_count_disclosed_none():
    from calculations.confidence import count_disclosed
    n, total = count_disclosed({})
    assert n == 0
    assert total == 8


def test_confidence_zero_value_not_disclosed():
    """Zero values should not count as disclosed."""
    from calculations.confidence import compute_esg_confidence
    inputs = {"injury_rate": 0, "board_independence_pct": 0}
    conf = compute_esg_confidence(inputs)
    assert conf == 0.0
