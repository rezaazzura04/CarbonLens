"""
CarbonLens V8 — Carbon intensity benchmark calculations.
Pure functions. Phase 0 C5 fix: sector benchmarks are illustrative estimates.
"""
from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.calculations.benchmarking")


def get_benchmark(sector: str) -> float:
    """
    Return the carbon intensity benchmark (kg CO2e/m²/yr) for a sector.
    Falls back to Manufacturing benchmark if sector is unknown.

    Parameters
    ----------
    sector : Sector name matching INDUSTRY_BENCHMARKS key.

    Returns
    -------
    float : Benchmark value in kg CO2e/m²/yr.
    """
    from config.settings import INDUSTRY_BENCHMARKS
    if sector in INDUSTRY_BENCHMARKS:
        return INDUSTRY_BENCHMARKS[sector]
    log.warning(f"Unknown sector {sector!r} — using Manufacturing benchmark")
    return INDUSTRY_BENCHMARKS.get("Manufacturing", 120.0)


def benchmark_gap(intensity: float, benchmark: float) -> dict:
    """
    Calculate the gap between an organisation's carbon intensity and its sector benchmark.

    Parameters
    ----------
    intensity : Organisation's carbon intensity (kg CO2e/m²/yr).
    benchmark : Sector benchmark intensity (kg CO2e/m²/yr). Must be > 0.

    Returns
    -------
    dict with keys:
        gap_pct          : float — percentage above (+) or below (-) benchmark
        gap_abs          : float — absolute gap (kg CO2e/m²/yr)
        above_benchmark  : bool  — True if organisation exceeds benchmark
        performance_label: str   — human-readable performance description
        reduction_needed_pct: float — % reduction needed to reach benchmark (0 if at/below)
    """
    if benchmark <= 0:
        raise ValueError(f"benchmark must be > 0, got {benchmark}")
    if intensity < 0:
        raise ValueError(f"intensity must be >= 0, got {intensity}")

    gap_abs = round(intensity - benchmark, 4)
    gap_pct = round((intensity - benchmark) / benchmark * 100, 2)
    above   = intensity > benchmark

    if intensity == 0:
        label = "Zero emissions — best-in-class"
    elif not above:
        label = f"{abs(gap_pct):.1f}% below {benchmark:.0f} kg/m² benchmark"
    elif gap_pct <= 25:
        label = f"{gap_pct:.1f}% above benchmark — near-benchmark performance"
    elif gap_pct <= 75:
        label = f"{gap_pct:.1f}% above benchmark — material improvement needed"
    else:
        label = f"{gap_pct:.1f}% above benchmark — significant decarbonisation required"

    reduction_needed = max(0.0, round(gap_pct, 2)) if above else 0.0

    return {
        "gap_pct":             gap_pct,
        "gap_abs":             gap_abs,
        "above_benchmark":     above,
        "performance_label":   label,
        "reduction_needed_pct": reduction_needed,
    }


def get_benchmark_provenance() -> str:
    """Return the provenance statement for all sector benchmarks."""
    from config.settings import INDUSTRY_BENCHMARKS_PROVENANCE
    return INDUSTRY_BENCHMARKS_PROVENANCE


def all_benchmarks() -> dict:
    """Return the complete sector benchmark registry."""
    from config.settings import INDUSTRY_BENCHMARKS
    return dict(INDUSTRY_BENCHMARKS)
