"""Unit tests for calculations/data_quality.py"""
import pytest
import pandas as pd


@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
        "Emission": [245, 268, 231, 259, 277, 242,
                     264, 251, 239, 267, 245, 258],
        "Energy":   [180000]*12,
    })


@pytest.fixture
def df_with_outlier(clean_df):
    df = clean_df.copy()
    df.loc[7, "Emission"] = 2100   # August outlier
    return df


def test_detect_outliers_clean_df(clean_df):
    from calculations.data_quality import detect_outliers
    out = detect_outliers(clean_df)
    assert len(out) == 0


def test_detect_outliers_with_outlier(df_with_outlier):
    from calculations.data_quality import detect_outliers
    out = detect_outliers(df_with_outlier)
    assert len(out) >= 1


def test_detect_outliers_none():
    from calculations.data_quality import detect_outliers
    out = detect_outliers(None)
    assert out.empty


def test_detect_outliers_too_few_rows():
    from calculations.data_quality import detect_outliers
    df = pd.DataFrame({"Emission": [100, 200]})
    out = detect_outliers(df)
    assert out.empty


def test_score_env_completeness_with_data(clean_df):
    from calculations.data_quality import score_env_completeness
    pct, flags = score_env_completeness(clean_df)
    assert pct > 80.0
    assert not any(f["field_name"] == "Emission" for f in flags)


def test_score_env_completeness_no_data():
    from calculations.data_quality import score_env_completeness
    pct, flags = score_env_completeness(None)
    assert pct == 0.0
    assert any(f["severity"] == "high" for f in flags)


def test_score_sg_completeness_full():
    from calculations.data_quality import score_sg_completeness
    inputs = {
        "water_recycled_pct": 30.0, "employee_turnover_pct": 8.0,
        "training_hours_per_employee": 24.0, "women_workforce_pct": 35.0,
        "injury_rate": 0.5, "board_independence_pct": 55.0,
        "women_board_pct": 20.0, "has_code_of_conduct": True,
    }
    pct, n, total, flags = score_sg_completeness(inputs)
    assert pct == 100.0
    assert n == 8
    assert len(flags) == 0


def test_score_sg_completeness_empty():
    from calculations.data_quality import score_sg_completeness
    pct, n, total, flags = score_sg_completeness({})
    assert pct == 0.0
    assert n == 0
    assert len(flags) == 8


def test_blend_dq_confidence_basic():
    from calculations.data_quality import blend_dq_confidence
    conf = blend_dq_confidence(100.0, 100.0, 100.0, False)
    assert conf == 100.0


def test_blend_dq_confidence_fail_cap():
    from calculations.data_quality import blend_dq_confidence
    conf = blend_dq_confidence(80.0, 80.0, 0.0, True)
    assert conf <= 40.0


def test_validation_to_score():
    from calculations.data_quality import validation_to_score
    assert validation_to_score("Pass")    == 100.0
    assert validation_to_score("Warning") == 70.0
    assert validation_to_score("Fail")    == 0.0
    assert validation_to_score("Unknown") == 0.0


def test_compute_full_dq_score_clean(clean_df):
    from calculations.data_quality import compute_full_dq_score
    result = compute_full_dq_score(
        df=clean_df,
        disclosure_inputs={},
        validation_status="Pass",
    )
    assert "confidence_score" in result
    assert "flagged_fields" in result
    assert result["validation_status"] == "Pass"
    assert result["confidence_score"] >= 0.0


def test_compute_full_dq_score_no_data():
    from calculations.data_quality import compute_full_dq_score
    result = compute_full_dq_score(
        df=None, disclosure_inputs={}, validation_status="Fail",
    )
    assert result["confidence_score"] <= 40.0
    assert result["is_provisional"] is True


def test_compute_full_dq_score_deduplicates_flags(clean_df):
    from calculations.data_quality import compute_full_dq_score
    result = compute_full_dq_score(
        df=clean_df, disclosure_inputs={}, validation_status="Pass",
    )
    keys = [(f["field_name"], f["reason"]) for f in result["flagged_fields"]]
    assert len(keys) == len(set(keys)), "Duplicate flags found"
