"""Unit tests for calculations/esg_scoring.py"""
import pytest


def test_carbon_sub_score_at_benchmark():
    from calculations.esg_scoring import calculate_carbon_sub_score
    assert calculate_carbon_sub_score(120.0, 120.0) == 100.0


def test_carbon_sub_score_zero_emissions():
    from calculations.esg_scoring import calculate_carbon_sub_score
    assert calculate_carbon_sub_score(0.0, 120.0) == 100.0


def test_carbon_sub_score_double_benchmark():
    from calculations.esg_scoring import calculate_carbon_sub_score
    assert calculate_carbon_sub_score(240.0, 120.0) == 0.0


def test_carbon_sub_score_capped_at_100():
    from calculations.esg_scoring import calculate_carbon_sub_score
    assert calculate_carbon_sub_score(10.0, 120.0) == 100.0


def test_calculate_env_score_perfect():
    from calculations.esg_scoring import calculate_env_score
    score = calculate_env_score(
        intensity_kg_m2=0.0, benchmark=120.0,
        renew_pct=100.0, recycle_pct=100.0, water_recycled_pct=100.0,
    )
    assert score == 100.0


def test_calculate_env_score_zero():
    from calculations.esg_scoring import calculate_env_score
    score = calculate_env_score(
        intensity_kg_m2=240.0, benchmark=120.0,
        renew_pct=0.0, recycle_pct=0.0, water_recycled_pct=0.0,
    )
    assert score == 0.0


def test_calculate_env_score_clamped():
    from calculations.esg_scoring import calculate_env_score
    score = calculate_env_score(
        intensity_kg_m2=0.0, benchmark=120.0,
        renew_pct=150.0, recycle_pct=200.0, water_recycled_pct=999.0,
    )
    assert 0.0 <= score <= 100.0


def test_calculate_social_score_perfect():
    from calculations.esg_scoring import calculate_social_score
    score = calculate_social_score(
        employee_turnover_pct=0.0, training_hours_per_emp=40.0,
        women_workforce_pct=50.0, injury_rate=0.0,
    )
    assert score == 100.0


def test_calculate_social_score_zero():
    from calculations.esg_scoring import calculate_social_score
    score = calculate_social_score(
        employee_turnover_pct=25.0, training_hours_per_emp=0.0,
        women_workforce_pct=0.0, injury_rate=10.0,
    )
    assert score == 0.0


def test_calculate_gov_score_full_disclosure():
    from calculations.esg_scoring import calculate_gov_score
    score = calculate_gov_score(
        board_independence_pct=50.0, disclosure_score=100.0,
        has_code_of_conduct=True, women_board_pct=40.0,
        certifications=["ISO 14001", "ISO 50001", "PROPER", "GHG Verified"],
    )
    assert score == 100.0


def test_calculate_gov_score_no_disclosure():
    from calculations.esg_scoring import calculate_gov_score
    score = calculate_gov_score(
        board_independence_pct=0.0, disclosure_score=0.0,
        has_code_of_conduct=False, women_board_pct=0.0,
        certifications=[],
    )
    assert score == 0.0


def test_composite_esg_weights():
    """Phase 0 C2: composite = E×0.40 + S×0.30 + G×0.30"""
    from calculations.esg_scoring import calculate_composite_esg_score
    score = calculate_composite_esg_score(100.0, 100.0, 100.0)
    assert score == 100.0

    score2 = calculate_composite_esg_score(100.0, 0.0, 0.0)
    assert abs(score2 - 40.0) < 0.01

    score3 = calculate_composite_esg_score(0.0, 100.0, 0.0)
    assert abs(score3 - 30.0) < 0.01


def test_assign_grade_boundaries():
    from calculations.esg_scoring import assign_grade
    assert assign_grade(85.0)[0] == "A"
    assert assign_grade(75.0)[0] == "B+"
    assert assign_grade(60.0)[0] == "B"
    assert assign_grade(45.0)[0] == "C"
    assert assign_grade(44.9)[0] == "D"
    assert assign_grade(0.0)[0]  == "D"


def test_assign_grade_labels():
    from calculations.esg_scoring import assign_grade
    assert assign_grade(90.0)[1] == "Industry Leader"
    assert assign_grade(80.0)[1] == "Above Average"


def test_score_indicator_linear():
    from calculations.esg_scoring import score_indicator
    assert score_indicator(0.0, 0.0, 100.0) == 0.0
    assert score_indicator(50.0, 0.0, 100.0) == 50.0
    assert score_indicator(100.0, 0.0, 100.0) == 100.0


def test_score_indicator_inverse():
    from calculations.esg_scoring import score_indicator
    # Inverse: lo=0 maps to 100, hi=100 maps to 0
    assert score_indicator(0.0, 0.0, 100.0, inverse=True) == 100.0
    assert score_indicator(100.0, 0.0, 100.0, inverse=True) == 0.0
