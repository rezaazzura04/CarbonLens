"""Unit tests for calculations/benchmarking.py"""
import pytest


def test_get_benchmark_known_sector():
    from calculations.benchmarking import get_benchmark
    from config.settings import INDUSTRY_BENCHMARKS
    assert get_benchmark("Manufacturing") == INDUSTRY_BENCHMARKS["Manufacturing"]


def test_get_benchmark_unknown_falls_back():
    from calculations.benchmarking import get_benchmark
    from config.settings import INDUSTRY_BENCHMARKS
    val = get_benchmark("UnknownSectorXYZ")
    assert val == INDUSTRY_BENCHMARKS.get("Manufacturing", 120.0)


def test_benchmark_gap_at_benchmark():
    from calculations.benchmarking import benchmark_gap
    r = benchmark_gap(120.0, 120.0)
    assert r["gap_pct"] == 0.0
    assert r["gap_abs"] == 0.0
    assert r["above_benchmark"] is False
    assert r["reduction_needed_pct"] == 0.0


def test_benchmark_gap_above():
    from calculations.benchmarking import benchmark_gap
    r = benchmark_gap(180.0, 120.0)
    assert r["above_benchmark"] is True
    assert abs(r["gap_pct"] - 50.0) < 0.01
    assert r["reduction_needed_pct"] == 50.0


def test_benchmark_gap_below():
    from calculations.benchmarking import benchmark_gap
    r = benchmark_gap(60.0, 120.0)
    assert r["above_benchmark"] is False
    assert r["gap_pct"] < 0
    assert r["reduction_needed_pct"] == 0.0


def test_benchmark_gap_zero_intensity():
    from calculations.benchmarking import benchmark_gap
    r = benchmark_gap(0.0, 120.0)
    assert not r["above_benchmark"]
    assert "Zero emissions" in r["performance_label"]


def test_benchmark_gap_invalid_benchmark():
    from calculations.benchmarking import benchmark_gap
    with pytest.raises(ValueError, match="benchmark"):
        benchmark_gap(100.0, 0.0)


def test_benchmark_gap_negative_intensity():
    from calculations.benchmarking import benchmark_gap
    with pytest.raises(ValueError, match="intensity"):
        benchmark_gap(-10.0, 120.0)


def test_all_benchmarks_returns_dict():
    from calculations.benchmarking import all_benchmarks
    benchmarks = all_benchmarks()
    assert isinstance(benchmarks, dict)
    assert "Manufacturing" in benchmarks
    assert all(isinstance(v, (int, float)) for v in benchmarks.values())
