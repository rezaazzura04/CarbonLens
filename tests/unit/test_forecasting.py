"""Unit tests for calculations/forecasting.py"""
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def rising_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun"],
        "Emission": [100, 120, 140, 160, 180, 200],
    })


@pytest.fixture
def falling_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun"],
        "Emission": [200, 180, 160, 140, 120, 100],
    })


@pytest.fixture
def stable_df():
    return pd.DataFrame({
        "Month":    ["Jan","Feb","Mar","Apr","May","Jun"],
        "Emission": [150, 151, 149, 150, 151, 150],
    })


def test_detect_trend_rising(rising_df):
    from calculations.forecasting import detect_trend
    r = detect_trend(rising_df)
    assert r["direction"] == "rising"
    assert r["slope_kg_mo"] > 0


def test_detect_trend_falling(falling_df):
    from calculations.forecasting import detect_trend
    r = detect_trend(falling_df)
    assert r["direction"] == "falling"
    assert r["slope_kg_mo"] < 0


def test_detect_trend_stable(stable_df):
    from calculations.forecasting import detect_trend
    r = detect_trend(stable_df)
    assert r["direction"] == "stable"


def test_detect_trend_no_data():
    from calculations.forecasting import detect_trend
    r = detect_trend(None)
    assert r["direction"] == "insufficient_data"


def test_detect_trend_too_few():
    from calculations.forecasting import detect_trend
    df = pd.DataFrame({"Month": ["Jan","Feb"], "Emission": [100, 200]})
    r = detect_trend(df)
    assert r["direction"] == "insufficient_data"


def test_predict_next_emission_rising(rising_df):
    from calculations.forecasting import predict_next_emission
    r = predict_next_emission(rising_df)
    assert r["next_month"] > 200      # Should predict above last value
    assert r["trend"] == "rising"
    assert r["r2"] > 0.9              # Linear data → high R²
    assert r["n_months"] == 6


def test_predict_next_emission_no_data():
    from calculations.forecasting import predict_next_emission
    r = predict_next_emission(None)
    assert r["next_month"] == 0.0
    assert r["trend"] == "insufficient_data"
    assert r["n_months"] == 0


def test_predict_next_emission_non_negative(falling_df):
    """Predicted value must never be negative."""
    from calculations.forecasting import predict_next_emission
    r = predict_next_emission(falling_df)
    assert r["next_month"] >= 0.0


def test_annual_projection_12_months():
    from calculations.forecasting import annual_projection
    df = pd.DataFrame({
        "Emission": [100.0] * 12,
    })
    result = annual_projection(df)
    assert result == 1200.0


def test_annual_projection_fewer_months():
    from calculations.forecasting import annual_projection
    df = pd.DataFrame({"Emission": [100.0, 200.0, 150.0]})
    # mean = 150, annual = 150*12 = 1800
    result = annual_projection(df)
    assert abs(result - 1800.0) < 0.01


def test_annual_projection_no_data():
    from calculations.forecasting import annual_projection
    assert annual_projection(None) == 0.0


def test_annual_projection_empty():
    from calculations.forecasting import annual_projection
    assert annual_projection(pd.DataFrame()) == 0.0
