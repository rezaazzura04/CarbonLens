"""
CarbonLens V8 — Input-hash cache for ComputedState.

Caches ComputedState by input_hash (SHA-256 of org_id + period + df_hash).
No TTL-based expiry — cache is only invalidated by input changes.
This eliminates the stale-data risk from TTL caching within a session.
"""

from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.state.cache")

# In-session cache: {input_hash: ComputedState dict}
_cache: dict[str, dict] = {}


def get(input_hash: str) -> Optional[dict]:
    """
    Return cached ComputedState dict for the given input_hash, or None.

    Cache hit only when hash matches exactly — no fuzzy matching.
    """
    hit = _cache.get(input_hash)
    if hit:
        log.debug(f"Cache HIT for hash {input_hash[:12]}...")
    else:
        log.debug(f"Cache MISS for hash {input_hash[:12]}...")
    return hit


def put(input_hash: str, state: dict) -> None:
    """Store a ComputedState dict under its input_hash."""
    _cache[input_hash] = state
    log.debug(f"Cache SET for hash {input_hash[:12]}... (v{state.get('version', '?')})")


def invalidate_org(org_id: str) -> int:
    """
    Remove all cached states for a given org_id.
    Returns the number of entries removed.
    """
    keys = [h for h, s in _cache.items() if s.get("org_id") == org_id]
    for k in keys:
        del _cache[k]
    if keys:
        log.info(f"Cache invalidated {len(keys)} entries for org {org_id[:8]}")
    return len(keys)


def clear_all() -> None:
    """Remove all cached states. Used on session reset."""
    count = len(_cache)
    _cache.clear()
    log.debug(f"Cache cleared ({count} entries removed)")


def is_stale(org_id: str, current_input_hash: str) -> bool:
    """
    Return True if no cached state exists for the current input_hash.
    A True return means recomputation is required.
    """
    return get(current_input_hash) is None


def size() -> int:
    """Return current number of cached states."""
    return len(_cache)
