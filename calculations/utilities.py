"""
CarbonLens V8 — Shared calculation utilities.
Pure functions only. No I/O. No Streamlit.
"""
from __future__ import annotations
import hashlib
import json
import logging
from typing import Any

log = logging.getLogger("carbonlens.calculations.utilities")


def normalise_month_column(df) -> Any:
    """Normalise month column strings: 'January' → 'Jan', 'JANUARY' → 'Jan'."""
    import pandas as pd
    MONTH_MAP = {
        "january":"Jan","february":"Feb","march":"Mar","april":"Apr",
        "may":"May","june":"Jun","july":"Jul","august":"Aug",
        "september":"Sep","october":"Oct","november":"Nov","december":"Dec",
        "jan":"Jan","feb":"Feb","mar":"Mar","apr":"Apr",
        "jun":"Jun","jul":"Jul","aug":"Aug","sep":"Sep",
        "oct":"Oct","nov":"Nov","dec":"Dec",
    }
    if "Month" in df.columns:
        df = df.copy()
        df["Month"] = df["Month"].astype(str).str.strip().str.lower().map(
            lambda x: MONTH_MAP.get(x, x)
        )
    return df


def hash_dataframe(df) -> str:
    """Return a stable SHA-256 hex digest of a DataFrame's canonical CSV repr."""
    import pandas as pd
    return hashlib.sha256(
        df.to_csv(index=False).encode("utf-8")
    ).hexdigest()


def hash_inputs(org_id: str, period: str, df_hash: str) -> str:
    """Derive the ComputedState input_hash from its three components."""
    raw = f"{org_id}:{period}:{df_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def kg_to_tonne(kg: float) -> float:
    """Convert kilograms to metric tonnes."""
    return kg / 1000.0


def tonne_to_kg(t: float) -> float:
    """Convert metric tonnes to kilograms."""
    return t * 1000.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide numerator by denominator; return default if denominator is zero."""
    if not denominator:
        return default
    return numerator / denominator


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


class NumpyEncoder(json.JSONEncoder):
    """
    JSON encoder that handles numpy scalar types and arrays.
    Usage: json.dumps(obj, cls=NumpyEncoder)
    """
    def default(self, obj: Any) -> Any:
        try:
            import numpy as np
            if isinstance(obj, np.integer):  return int(obj)
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.bool_):    return bool(obj)
            if isinstance(obj, np.ndarray):  return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)
