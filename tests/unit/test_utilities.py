"""Unit tests for calculations/utilities.py"""
import pytest
import pandas as pd


def test_safe_divide_normal():
    from calculations.utilities import safe_divide
    assert safe_divide(10.0, 2.0) == 5.0


def test_safe_divide_zero_denominator():
    from calculations.utilities import safe_divide
    assert safe_divide(10.0, 0.0, default=0.0) == 0.0
    assert safe_divide(10.0, 0.0, default=-1.0) == -1.0


def test_clamp_within_range():
    from calculations.utilities import clamp
    assert clamp(50.0) == 50.0


def test_clamp_below_lo():
    from calculations.utilities import clamp
    assert clamp(-10.0) == 0.0


def test_clamp_above_hi():
    from calculations.utilities import clamp
    assert clamp(110.0) == 100.0


def test_clamp_custom_bounds():
    from calculations.utilities import clamp
    assert clamp(5.0, lo=0.0, hi=10.0) == 5.0
    assert clamp(-1.0, lo=0.0, hi=10.0) == 0.0
    assert clamp(15.0, lo=0.0, hi=10.0) == 10.0


def test_kg_to_tonne():
    from calculations.utilities import kg_to_tonne
    assert kg_to_tonne(1000.0) == 1.0
    assert kg_to_tonne(0.0) == 0.0


def test_tonne_to_kg():
    from calculations.utilities import tonne_to_kg
    assert tonne_to_kg(1.0) == 1000.0


def test_hash_inputs_deterministic():
    from calculations.utilities import hash_inputs
    h1 = hash_inputs("org-1", "2024", "abc")
    h2 = hash_inputs("org-1", "2024", "abc")
    assert h1 == h2


def test_hash_inputs_different_for_different_inputs():
    from calculations.utilities import hash_inputs
    assert hash_inputs("org-1", "2024", "abc") != hash_inputs("org-2", "2024", "abc")
    assert hash_inputs("org-1", "2024", "abc") != hash_inputs("org-1", "2025", "abc")
    assert hash_inputs("org-1", "2024", "abc") != hash_inputs("org-1", "2024", "xyz")


def test_hash_inputs_returns_hex_string():
    from calculations.utilities import hash_inputs
    h = hash_inputs("org-1", "2024", "abc")
    assert isinstance(h, str)
    assert len(h) == 64   # SHA-256 hex


def test_hash_dataframe():
    from calculations.utilities import hash_dataframe
    df = pd.DataFrame({"Month": ["Jan","Feb"], "Emission": [100, 200]})
    h = hash_dataframe(df)
    assert isinstance(h, str)
    assert len(h) == 64


def test_hash_dataframe_deterministic():
    from calculations.utilities import hash_dataframe
    df = pd.DataFrame({"Month": ["Jan"], "Emission": [100]})
    assert hash_dataframe(df) == hash_dataframe(df)


def test_normalise_month_column_long_names():
    from calculations.utilities import normalise_month_column
    df = pd.DataFrame({"Month": ["January","February","MARCH"]})
    result = normalise_month_column(df)
    assert list(result["Month"]) == ["Jan", "Feb", "Mar"]


def test_normalise_month_already_short():
    from calculations.utilities import normalise_month_column
    df = pd.DataFrame({"Month": ["Jan","Feb","Mar"]})
    result = normalise_month_column(df)
    assert list(result["Month"]) == ["Jan", "Feb", "Mar"]


def test_normalise_month_no_month_column():
    from calculations.utilities import normalise_month_column
    df = pd.DataFrame({"Emission": [100, 200]})
    result = normalise_month_column(df)
    assert list(result.columns) == ["Emission"]


def test_numpy_encoder():
    import json, numpy as np
    from calculations.utilities import NumpyEncoder
    obj = {"a": np.int64(5), "b": np.float32(3.14), "c": np.array([1,2,3])}
    result = json.dumps(obj, cls=NumpyEncoder)
    parsed = json.loads(result)
    assert parsed["a"] == 5
    assert isinstance(parsed["c"], list)
