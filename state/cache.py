"""
CarbonLens — Input-hash cache for ComputedState and forecast (Phase 6).

Caches by deterministic input_hash (see calculations.utilities.hash_inputs).
No TTL-based expiry — cache is only invalidated by input changes or an
explicit invalidate_org() call. This eliminates the stale-data risk from
TTL caching within a session.

Phase 6 fix — session isolation: this module previously backed its cache
with a bare module-level Python dict (`_cache: dict = {}`). Since Python
modules are imported once per server process, that dict was silently
SHARED across every concurrent browser session on the same running
Streamlit server — a real correctness/isolation bug for any deployment
serving more than one session at a time, and inconsistent with the
architecture invariant that repository/session_repo.py is the sole owner
of session-scoped state. The cache is now backed by session_repo's global
(non-slot) session storage, so each browser session gets its own cache,
exactly like every other piece of session state in this app.
"""

from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.state.cache")

_COMPUTED_STATE_KEY = "computed_state_cache"
_FORECAST_KEY       = "forecast_cache"
_EXPORT_KEY         = "export_cache"


def _get_store(key: str) -> dict:
    """Return this session's cache dict for `key`, initialising it in
    session_repo on first access."""
    from repository.session_repo import get_global, set_global
    store = get_global(key, None)
    if store is None:
        store = {}
        set_global(key, store)
    return store


def _save_store(key: str, store: dict) -> None:
    from repository.session_repo import set_global
    set_global(key, store)


# ── ComputedState cache ─────────────────────────────────────────────────────

def get(input_hash: str) -> Optional[dict]:
    """Return cached ComputedState dict for the given input_hash, or None."""
    hit = _get_store(_COMPUTED_STATE_KEY).get(input_hash)
    log.debug(f"ComputedState cache {'HIT' if hit else 'MISS'} for hash {input_hash[:12]}...")
    return hit


def put(input_hash: str, state: dict) -> None:
    """Store a ComputedState dict under its input_hash."""
    store = _get_store(_COMPUTED_STATE_KEY)
    store[input_hash] = state
    _save_store(_COMPUTED_STATE_KEY, store)
    log.debug(f"ComputedState cache SET for hash {input_hash[:12]}... (v{state.get('version', '?')})")


def invalidate_org(org_id: str) -> int:
    """
    Remove all cached ComputedState entries for a given org_id, and clear
    the whole session's forecast cache (forecast cache values don't carry
    org_id, so a targeted removal isn't possible cheaply — it's small and
    cheap to rebuild, and this only runs on an explicit mutation, not on
    every render).
    """
    store = _get_store(_COMPUTED_STATE_KEY)
    keys = [h for h, s in store.items() if s.get("org_id") == org_id]
    for k in keys:
        del store[k]
    _save_store(_COMPUTED_STATE_KEY, store)

    clear_forecast()

    if keys:
        log.info(f"Cache invalidated {len(keys)} ComputedState entries for org {org_id[:8]}")
    return len(keys)


def clear_all() -> None:
    """Remove all cached ComputedState, forecast, and export entries for
    this session. Used on session reset."""
    from repository.session_repo import set_global
    set_global(_COMPUTED_STATE_KEY, {})
    set_global(_FORECAST_KEY, {})
    set_global(_EXPORT_KEY, {})
    log.debug("Cache cleared (ComputedState + forecast + export)")


def is_stale(org_id: str, current_input_hash: str) -> bool:
    """Return True if no cached state exists for the current input_hash."""
    return get(current_input_hash) is None


def size() -> int:
    """Return current number of cached ComputedState entries this session."""
    return len(_get_store(_COMPUTED_STATE_KEY))


# ── Forecast cache (Phase 6 — previously uncached, recomputed on every call) ──

def get_forecast(forecast_hash: str) -> Optional[dict]:
    """Return a cached forecast_with_validation() result, or None."""
    hit = _get_store(_FORECAST_KEY).get(forecast_hash)
    log.debug(f"Forecast cache {'HIT' if hit else 'MISS'} for hash {forecast_hash[:12]}...")
    return hit


def put_forecast(forecast_hash: str, result: dict) -> None:
    """Store a forecast result under its input hash."""
    store = _get_store(_FORECAST_KEY)
    store[forecast_hash] = result
    _save_store(_FORECAST_KEY, store)
    log.debug(f"Forecast cache SET for hash {forecast_hash[:12]}...")


def clear_forecast() -> None:
    """Remove all cached forecast entries for this session."""
    _save_store(_FORECAST_KEY, {})


# ── Export cache (Phase 6 — Excel/PDF generation deferred + cached) ──────────

def get_export(export_hash: str) -> Optional[tuple]:
    """Return a cached (bytes, filename) export tuple, or None."""
    hit = _get_store(_EXPORT_KEY).get(export_hash)
    log.debug(f"Export cache {'HIT' if hit else 'MISS'} for hash {export_hash[:12]}...")
    return hit


def put_export(export_hash: str, data: tuple) -> None:
    """Store a (bytes, filename) export tuple under its input hash."""
    store = _get_store(_EXPORT_KEY)
    store[export_hash] = data
    _save_store(_EXPORT_KEY, store)
    log.debug(f"Export cache SET for hash {export_hash[:12]}...")
