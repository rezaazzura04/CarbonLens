"""
CarbonLens V8 — GHG inventory calculations (Scope 1, 2, 3).

Pure functions. No Streamlit. No I/O. No side effects.
All emission factors sourced from config.settings.EMISSION_FACTORS.
Phase 0 H3 fix: all combustion factors use full CO2e (CH4 + N2O included).
Source: IPCC 2006 Guidelines Vol.2 + AR6 GWP100.
Scope 2: Kepmen ESDM No.18/2023.
"""
from __future__ import annotations
import logging
from typing import Optional

log = logging.getLogger("carbonlens.calculations.ghg")


# ── PLN emission factor resolver ──────────────────────────────────────────────

def resolve_pln_ef(province: str) -> float:
    """
    Return the PLN grid emission factor (kg CO2e/kWh) for the given province.
    Falls back to national average if province is not in the subsystem map.
    Source: Kepmen ESDM No.18/2023, Appendix II.

    Parameters
    ----------
    province : Province name (Indonesian). Empty string → national average.

    Returns
    -------
    float : Emission factor in kg CO2e per kWh.
    """
    from config.settings import get_pln_ef
    return get_pln_ef(province)


# ── Scope 1: Combustion emissions ─────────────────────────────────────────────

def calculate_scope1(
    diesel_liters:  float = 0.0,
    petrol_liters:  float = 0.0,
    lpg_kg:         float = 0.0,
    natural_gas_m3: float = 0.0,
    cng_m3:         float = 0.0,
    coal_kg:        float = 0.0,
    biomass_kg:     float = 0.0,
) -> dict:
    """
    Calculate total Scope 1 combustion emissions.

    Each fuel quantity is multiplied by its approved emission factor.
    Biomass is reported separately at 0.0 kg CO2e (biogenic, net zero
    per GHG Protocol biogenic accounting policy).
    Phase 0 H3: all factors include CH4 and N2O (full CO2e).

    Parameters
    ----------
    diesel_liters  : Diesel consumed (litres).
    petrol_liters  : Petrol/RON95 consumed (litres).
    lpg_kg         : LPG consumed (kg).
    natural_gas_m3 : Natural gas consumed (m³).
    cng_m3         : CNG consumed (m³).
    coal_kg        : Coal consumed (kg).
    biomass_kg     : Biomass consumed (kg) — reported separately, excluded from total.

    Returns
    -------
    dict with keys:
        total_kg  : float  — total Scope 1 kg CO2e (excl. biogenic biomass)
        breakdown : dict   — per-fuel kg CO2e
        inputs    : dict   — input quantities for provenance
    """
    _validate_non_negative("diesel_liters",  diesel_liters)
    _validate_non_negative("petrol_liters",  petrol_liters)
    _validate_non_negative("lpg_kg",         lpg_kg)
    _validate_non_negative("natural_gas_m3", natural_gas_m3)
    _validate_non_negative("cng_m3",         cng_m3)
    _validate_non_negative("coal_kg",        coal_kg)
    _validate_non_negative("biomass_kg",     biomass_kg)

    from config.settings import EMISSION_FACTORS as EF
    breakdown = {
        "diesel":      round(diesel_liters  * EF["diesel_kgco2_per_liter"],       4),
        "petrol":      round(petrol_liters  * EF["petrol_kgco2_per_liter"],       4),
        "lpg":         round(lpg_kg         * EF["lpg_kgco2_per_kg"],             4),
        "natural_gas": round(natural_gas_m3 * EF["natural_gas_kgco2_per_m3"],    4),
        "cng":         round(cng_m3         * EF["cng_kgco2_per_m3"],             4),
        "coal":        round(coal_kg        * EF["coal_kgco2_per_kg"],            4),
        "biomass":     0.0,   # biogenic — excluded from total (net zero)
    }
    total_kg = sum(v for k, v in breakdown.items() if k != "biomass")
    return {
        "total_kg":  round(total_kg, 4),
        "breakdown": breakdown,
        "inputs": {
            "diesel_liters":  diesel_liters,
            "petrol_liters":  petrol_liters,
            "lpg_kg":         lpg_kg,
            "natural_gas_m3": natural_gas_m3,
            "cng_m3":         cng_m3,
            "coal_kg":        coal_kg,
            "biomass_kg":     biomass_kg,
        },
    }


# ── Scope 2: Grid electricity emissions ───────────────────────────────────────

def calculate_scope2(
    electricity_kwh: float,
    pln_ef:          float,
) -> dict:
    """
    Calculate Scope 2 market-based grid electricity emissions.
    pln_ef must be pre-resolved from resolve_pln_ef() — never looked up here.
    Source: Kepmen ESDM No.18/2023, Appendix II.

    Parameters
    ----------
    electricity_kwh : Total electricity consumed (kWh).
    pln_ef          : PLN grid emission factor (kg CO2e/kWh).

    Returns
    -------
    dict with keys:
        total_kg : float — Scope 2 kg CO2e
        ef_used  : float — emission factor applied
        inputs   : dict  — input quantities for provenance
    """
    _validate_non_negative("electricity_kwh", electricity_kwh)
    if pln_ef <= 0:
        raise ValueError(
            f"pln_ef must be positive, got {pln_ef}. "
            "Use resolve_pln_ef() to obtain the approved factor."
        )
    total_kg = round(electricity_kwh * pln_ef, 4)
    return {
        "total_kg": total_kg,
        "ef_used":  pln_ef,
        "inputs":   {"electricity_kwh": electricity_kwh},
    }


# ── Scope 3: Value chain emissions (12 of 15 categories) ─────────────────────

def calculate_scope3(
    cat1_spend:             float = 0.0,   # Purchased goods & services (USD)
    cat2_spend:             float = 0.0,   # Capital goods (USD)
    cat3_kwh:               float = 0.0,   # Energy upstream losses (kWh)
    cat4_tonne_km:          float = 0.0,   # Upstream transport (tonne-km)
    cat5_waste_kg:          float = 0.0,   # Waste generated (kg)
    cat6_travel_km:         float = 0.0,   # Business travel (km)
    cat7_commute_km:        float = 0.0,   # Employee commute (km)
    cat8_leased_spend:      float = 0.0,   # Upstream leased assets (USD)
    cat9_downstream_tkm:    float = 0.0,   # Downstream transport (tonne-km)
    cat10_processing_spend: float = 0.0,   # Processing of sold products (USD)
    cat12_eol_kg:           float = 0.0,   # End-of-life treatment (kg)
    cat13_downstream_spend: float = 0.0,   # Downstream leased assets (USD)
) -> dict:
    """
    Calculate Scope 3 value chain emissions across 12 contributing categories.
    Categories 11 (Use of sold products), 14 (Franchises), and 15 (Investments)
    are screened and excluded with documented rationale per GHG Protocol.

    Source: GHG Protocol Corporate Value Chain (Scope 3) Standard.
    Emission factors: DEFRA 2023, USEEIO v2.0, GLEC Framework v3.

    Returns
    -------
    dict with keys:
        total_kg          : float — total Scope 3 kg CO2e
        breakdown         : dict  — per-category kg CO2e
        screened_excluded : list  — excluded category IDs with rationale
        inputs            : dict  — input quantities
    """
    from config.settings import SCOPE3_EMISSION_FACTORS as S3EF
    from config.constants import SCOPE3_SCREENED_EXCLUDED

    inputs = {
        "cat1_spend": cat1_spend, "cat2_spend": cat2_spend,
        "cat3_kwh": cat3_kwh, "cat4_tonne_km": cat4_tonne_km,
        "cat5_waste_kg": cat5_waste_kg, "cat6_travel_km": cat6_travel_km,
        "cat7_commute_km": cat7_commute_km, "cat8_leased_spend": cat8_leased_spend,
        "cat9_downstream_tkm": cat9_downstream_tkm,
        "cat10_processing_spend": cat10_processing_spend,
        "cat12_eol_kg": cat12_eol_kg,
        "cat13_downstream_spend": cat13_downstream_spend,
    }
    for key, val in inputs.items():
        _validate_non_negative(key, val)

    breakdown = {
        "cat1_purchased_goods":   round(cat1_spend             * S3EF["cat1_purchased_goods"]["ef"],   4),
        "cat2_capital_goods":     round(cat2_spend             * S3EF["cat2_capital_goods"]["ef"],     4),
        "cat3_energy_upstream":   round(cat3_kwh               * S3EF["cat3_energy_upstream"]["ef"],   4),
        "cat4_transport_upstream":round(cat4_tonne_km          * S3EF["cat4_transport_upstream"]["ef"],4),
        "cat5_waste":             round(cat5_waste_kg          * S3EF["cat5_waste"]["ef"],             4),
        "cat6_business_travel":   round(cat6_travel_km         * S3EF["cat6_business_travel"]["ef"],   4),
        "cat7_employee_commute":  round(cat7_commute_km        * S3EF["cat7_employee_commute"]["ef"],  4),
        "cat8_upstream_leased":   round(cat8_leased_spend      * S3EF["cat8_upstream_leased"]["ef"],   4),
        "cat9_downstream_transport": round(cat9_downstream_tkm * S3EF["cat9_downstream_transport"]["ef"], 4),
        "cat10_processing":       round(cat10_processing_spend * S3EF["cat10_processing"]["ef"],       4),
        "cat12_end_of_life":      round(cat12_eol_kg           * S3EF["cat12_end_of_life"]["ef"],      4),
        "cat13_downstream_leased":round(cat13_downstream_spend * S3EF["cat13_downstream_leased"]["ef"],4),
    }
    total_kg = round(sum(breakdown.values()), 4)
    screened = [
        f"{cat_id}: {rationale}"
        for cat_id, rationale in SCOPE3_SCREENED_EXCLUDED.items()
    ]
    return {
        "total_kg":          total_kg,
        "breakdown":         breakdown,
        "screened_excluded": screened,
        "inputs":            inputs,
    }


# ── Carbon intensity ──────────────────────────────────────────────────────────

def calculate_intensity(total_kg: float, area_m2: float) -> float:
    """
    Calculate carbon intensity as kg CO2e per m² per year.

    Parameters
    ----------
    total_kg : Total GHG emissions (kg CO2e).
    area_m2  : Building floor area (m²). Must be > 0.

    Returns
    -------
    float : Intensity in kg CO2e/m²/yr. Returns 0.0 if area_m2 is zero.
    """
    if area_m2 <= 0:
        return 0.0
    return round(total_kg / area_m2, 4)


def aggregate_scope_totals(
    scope1: dict,
    scope2: dict,
    scope3: dict,
    area_m2: float,
) -> dict:
    """
    Aggregate Scope 1/2/3 results into a complete carbon inventory summary.

    Parameters
    ----------
    scope1  : Output of calculate_scope1().
    scope2  : Output of calculate_scope2().
    scope3  : Output of calculate_scope3().
    area_m2 : Building floor area (m²).

    Returns
    -------
    dict with keys: scope1_kg, scope2_kg, scope3_kg, total_kg, intens_m2.
    """
    s1 = scope1.get("total_kg", 0.0)
    s2 = scope2.get("total_kg", 0.0)
    s3 = scope3.get("total_kg", 0.0)
    total = round(s1 + s2 + s3, 4)
    return {
        "scope1_kg": s1,
        "scope2_kg": s2,
        "scope3_kg": s3,
        "total_kg":  total,
        "intens_m2": calculate_intensity(total, area_m2),
    }


# ── Shared validation helper ──────────────────────────────────────────────────

def _validate_non_negative(name: str, value: float) -> None:
    """Raise ValueError if value is negative."""
    if value < 0:
        raise ValueError(
            f"{name} must be >= 0, got {value}. "
            "Negative emission quantities are not physically meaningful."
        )
