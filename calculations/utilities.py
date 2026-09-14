"""
CarbonLens — Shared calculation utilities.
Pure functions only. No I/O. No Streamlit.
"""
from __future__ import annotations
import hashlib
import json
import logging
from typing import Any, Optional

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


def hash_inputs(
    org_id: str, period: str, df_hash: str,
    disclosure_hash: str = "", scope_hash: str = "",
) -> str:
    """
    Derive the canonical ComputedState input_hash from ALL calculation
    inputs that can change the result — not just the dataset.

    Phase 6 fix: disclosure_hash/scope_hash were previously omitted from
    this fingerprint, meaning editing S/G disclosure values or manual
    scope entries without ALSO changing org/period/dataset could return a
    stale cached ComputedState. The only reason this wasn't an observed bug
    is that every known mutation call site happened to also call
    state_service.invalidate() manually — a discipline-based safety net,
    not a structural one. Including these hashes closes the gap the same
    way the dataset hash already did, so a future mutation site that
    forgets to call invalidate() still can't return stale results.

    disclosure_hash/scope_hash default to "" so this remains backward
    compatible with any caller that only has org_id/period/df_hash.
    """
    raw = f"{org_id}:{period}:{df_hash}:{disclosure_hash}:{scope_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_dict(d: Optional[dict]) -> str:
    """
    Stable SHA-256 hex digest of a dict's contents, independent of key
    insertion order (sorted before serialising). Used to fingerprint
    disclosure_inputs/scope_inputs for the canonical input hash.
    Returns a fixed empty-dict hash for None, so "no input" is still a
    well-defined, stable fingerprint rather than an empty string that could
    collide with other empty-ish inputs.
    """
    if not d:
        d = {}
    canonical = json.dumps(d, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_strings(*parts: str) -> str:
    """
    Generic deterministic fingerprint over an arbitrary number of string
    parts, colon-joined then SHA-256'd. Used for cache keys that aren't
    shaped like the org/period/dataset ComputedState fingerprint (e.g. the
    forecast cache, which keys on dataset + DQ status only) — kept separate
    from hash_inputs() so a reader never has to wonder why an unrelated
    value was passed as "org_id".
    """
    raw = ":".join(str(p) for p in parts)
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
            # calculations/ must stay free of logging/I/O side effects (pure
            # functions only, per architecture invariant) — silent fallback
            # is the correct behaviour here, not an oversight
            # (Phase 5-B Fix 9C: reviewed, kept silent).
            pass
        return super().default(obj)
