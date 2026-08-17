"""
CarbonLens V8 — MethodologyEntry and EmissionFactorEntry models.
"""
from __future__ import annotations
from typing import TypedDict


class MethodologyEntry(TypedDict):
    """One documented methodology rule, weight, or threshold."""
    entry_id:      str    # URL-safe slug e.g. "env-pillar-weight-40pct"
    category:      str    # Grouping label for Governance Library tab
    name:          str
    value:         str    # Display string e.g. "40%"
    formula:       str    # Formula as display string
    gri_reference: str    # GRI codes if applicable, empty string if none
    source:        str    # Authoritative reference
    rationale:     str    # One sentence: why this value
    introduced_in: str    # Phase/sprint reference e.g. "Phase 0 C2"


class EmissionFactorEntry(TypedDict):
    """
    A documented emission factor entry for the Governance Emission Factor Library.
    Read from config/settings.py at call time — never duplicates the constant.
    """
    name:           str
    category:       str    # "Scope 1 -- Combustion" | "Scope 2 -- Grid" | "Scope 3"
    key:            str    # Key in EMISSION_FACTORS dict (empty for PLN subsystem keys)
    value:          float  # Current CO2e factor (read from config)
    unit:           str
    gas_coverage:   str
    source:         str
    source_year:    int
    gwp_basis:      str
    regulation:     str
    co2_only_value: float  # Pre-Phase-0-H3 value; 0.0 if not applicable
    last_reviewed:  str    # Sprint reference
    notes:          str
