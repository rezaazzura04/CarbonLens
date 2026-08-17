"""
CarbonLens V8 — Decarbonization Planner models.
Phase 5-A: Target Tracker + Scenario Simulator.

Pure TypedDicts. No business logic.
"""
from __future__ import annotations
from typing import Optional, TypedDict


class MitigationLever(TypedDict):
    """One mitigation action within a scenario."""
    lever_id:            str     # canonical ID e.g. "energy_efficiency"
    name:                str
    scope:               str     # "1" | "2" | "3" | "1+2"
    category:            str     # affected emission category
    reduction_pct:       float   # % reduction applied to affected scope/category
    implementation_year: int
    assumption_type:     str     # "user-provided" | "carbonlens-default"
    source:              str     # assumption source / reference
    estimated_reduction_kg: float  # pre-computed kg CO2e reduction
    confidence:          str     # "Low" | "Medium" | "High"
    limitation:          str     # honest limitation statement


class ScenarioConfig(TypedDict):
    """One named decarbonization scenario."""
    id:          str         # "A" | "B" | "C"
    name:        str
    description: str
    levers:      list        # list[MitigationLever]
    created_at:  str
    modified_at: str


class ReductionTarget(TypedDict):
    """User-defined reduction target."""
    baseline_period:     str     # e.g. "2024"
    target_year:         str     # e.g. "2030"
    reduction_target_pct: float  # 0–100
    baseline_kg:         float   # from ComputedState — never re-calculated here
    target_kg:           float   # baseline × (1 − pct/100)
    assumption_type:     str     # "user-provided"


class ScenarioResult(TypedDict):
    """Computed output for one scenario."""
    scenario_id:      str
    scenario_name:    str
    total_kg:         float
    scope1_kg:        float
    scope2_kg:        float
    scope3_kg:        float
    reduction_kg:     float
    reduction_pct:    float
    target_gap_kg:    float     # positive = above target, negative = below
    above_target:     bool
    lever_breakdown:  list      # [{lever_id, reduction_kg, pct_contribution}]


class DecarbonizationState(TypedDict):
    """Complete persisted state for the Decarbonization Planner."""
    target:             Optional[dict]   # ReductionTarget or None
    scenarios:          dict             # {"A": ScenarioConfig, "B": ..., "C": ...}
    active_scenario_id: str              # "A" | "B" | "C"
    last_modified:      str


def make_empty_decarb_state() -> dict:
    """Return a safe empty DecarbonizationState."""
    return {
        "target":             None,
        "scenarios":          {},
        "active_scenario_id": "A",
        "last_modified":      "",
    }


# Lever catalogue — canonical definitions for all supported levers
LEVER_CATALOGUE: list[dict] = [
    {
        "lever_id":    "energy_efficiency",
        "name":        "Energy Efficiency",
        "scope":       "1+2",
        "category":    "All combustion and electricity",
        "default_reduction_pct": 10.0,
        "unit":        "% reduction in S1+S2 emissions",
        "source":      "CarbonLens default — industry average retrofit assumption",
        "assumption_type": "carbonlens-default",
        "confidence":  "Medium",
        "limitation":  (
            "Assumes proportional reduction across all S1+S2 sources. "
            "Actual savings depend on which equipment is retrofitted."
        ),
    },
    {
        "lever_id":    "renewable_electricity",
        "name":        "Renewable Electricity",
        "scope":       "2",
        "category":    "Grid electricity (PLN substitution)",
        "default_reduction_pct": 30.0,
        "unit":        "% of electricity from renewable sources",
        "source":      "CarbonLens default — reduces PLN grid factor proportionally",
        "assumption_type": "carbonlens-default",
        "confidence":  "Medium",
        "limitation":  (
            "Assumes on-site solar or PPA. Market renewable tariff and "
            "residual PLN consumption vary by contract."
        ),
    },
    {
        "lever_id":    "fuel_switching",
        "name":        "Fuel Switching (Diesel → B30 Biodiesel)",
        "scope":       "1",
        "category":    "Diesel combustion",
        "default_reduction_pct": 20.0,
        "unit":        "% of diesel replaced by B30 biodiesel",
        "source":      "CarbonLens default — B30 blend reduces net CO2e by ~20%",
        "assumption_type": "carbonlens-default",
        "confidence":  "Medium",
        "limitation":  (
            "Biogenic CO2 excluded per GHG Protocol biogenic accounting. "
            "Actual blend ratio and supply availability vary."
        ),
    },
    {
        "lever_id":    "electrification",
        "name":        "Electrification of Mobile Equipment",
        "scope":       "1",
        "category":    "Petrol/diesel combustion (fleet)",
        "default_reduction_pct": 25.0,
        "unit":        "% of fleet electrified",
        "source":      "CarbonLens default — full electrification of replaced share",
        "assumption_type": "carbonlens-default",
        "confidence":  "Low",
        "limitation":  (
            "Moves emissions from S1 to S2. Net effect depends on PLN grid "
            "carbon intensity at the time of electrification."
        ),
    },
    {
        "lever_id":    "waste_reduction",
        "name":        "Waste Reduction & Diversion",
        "scope":       "3",
        "category":    "Scope 3 Cat 5 — Waste generated",
        "default_reduction_pct": 30.0,
        "unit":        "% reduction in Scope 3 waste category",
        "source":      "CarbonLens default — landfill diversion target",
        "assumption_type": "carbonlens-default",
        "confidence":  "Medium",
        "limitation":  (
            "Applied only to Cat 5 waste emissions. Requires accurate "
            "waste tonnage data for meaningful projection."
        ),
    },
    {
        "lever_id":    "supply_chain",
        "name":        "Supply Chain Engagement",
        "scope":       "3",
        "category":    "Scope 3 Cat 1 — Purchased goods & services",
        "default_reduction_pct": 10.0,
        "unit":        "% reduction in Cat 1 purchased goods emissions",
        "source":      "CarbonLens default — supplier engagement assumption",
        "assumption_type": "carbonlens-default",
        "confidence":  "Low",
        "limitation":  (
            "Modelled estimate only. Actual reductions require supplier-level "
            "data collection and verification. High uncertainty."
        ),
    },
]
