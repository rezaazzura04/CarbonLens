"""
CarbonLens V8 — CarbonInventory and EmissionFactor models.
"""
from __future__ import annotations
from typing import Optional
from typing import TypedDict


class CarbonInventory(TypedDict):
    """Complete GHG inventory result for one organisation in one period."""
    org_id:            str
    period:            str
    scope1_kg:         float   # All values in kg (converted to tonnes for display only)
    scope2_kg:         float
    scope3_kg:         float
    total_kg:          float   # Invariant: total_kg == scope1_kg + scope2_kg + scope3_kg
    intens_m2:         float   # kg CO2e / m² — intensity normalised by floor area
    scope_source:      str     # "carbon_accounting"|"csv_scope_columns"|"csv_estimate"|"none"
    province:          str     # Province used for PLN grid factor selection
    pln_ef_used:       float   # kg CO2e/kWh applied to scope2 calculation
    scope3_breakdown:  dict    # Category-level kg values: {"cat1_purchased_goods": 1234.0, ...}
    screened_excluded: list    # Category IDs excluded with rationale strings
    computed_at:       str     # ISO 8601


class EmissionFactor(TypedDict):
    """A single emission factor with complete provenance metadata."""
    factor_id:       str     # Unique slug e.g. "scope1-diesel-kgco2e-per-liter"
    name:            str
    category:        str     # "Scope 1 -- Combustion" | "Scope 2 -- Grid" | "Scope 3"
    key:             str     # Key in config/settings.py EMISSION_FACTORS dict
    value:           float   # Current CO2e factor
    unit:            str     # e.g. "kg CO2e / litre"
    gas_coverage:    str     # Gas species included
    source:          str     # Primary source reference
    source_year:     int
    gwp_basis:       str     # GWP standard e.g. "IPCC AR6 (2021)"
    regulation:      str     # Applicable regulation if any
    co2_only_value:  float   # Pre-Phase-0-H3 value (0.0 if not applicable)
    effective_from:  str     # ISO date when this value became active
    last_reviewed:   str     # Sprint or phase reference


def make_zero_inventory(org_id: str, period: str, province: str) -> CarbonInventory:
    """Return a zero-emission inventory for sessions with no carbon data yet."""
    import datetime
    from config.settings import get_pln_ef
    return CarbonInventory(
        org_id            = org_id,
        period            = period,
        scope1_kg         = 0.0,
        scope2_kg         = 0.0,
        scope3_kg         = 0.0,
        total_kg          = 0.0,
        intens_m2         = 0.0,
        scope_source      = "none",
        province          = province,
        pln_ef_used       = get_pln_ef(province),
        scope3_breakdown  = {},
        screened_excluded = [],
        computed_at       = datetime.datetime.now().isoformat(timespec="seconds"),
    )
