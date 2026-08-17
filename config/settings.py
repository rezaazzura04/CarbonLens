"""
CarbonLens V8 — Platform configuration registry.

All emission factors, benchmarks, score bands, and lookup tables.
Values are sourced from approved regulatory and scientific references.
No value in this file may be hardcoded elsewhere in the codebase.

Phase 0 H3 fix applied: all Scope 1 combustion factors include CH4 and N2O
converted using IPCC AR6 GWP100 (CH4-fossil=29.8, N2O=273).
Previous CO2-only values are preserved for audit trail in the emission factor registry.
"""

# ── Scope 1: Combustion emission factors ──────────────────────────────────────
# Source: IPCC 2006 Guidelines for National GHG Inventories, Vol.2 Ch.2 Table 2.4
# GWP basis: IPCC AR6 (2021) — CH4-fossil=29.8, N2O=273
# Phase 0 H3 fix: updated from CO2-only to full CO2e

EMISSION_FACTORS: dict[str, float] = {
    # Scope 1 — liquid fuels
    "diesel_kgco2_per_liter":       2.6967,   # kg CO2e/L (was 2.68 CO2-only pre-H3)
    "petrol_kgco2_per_liter":       2.3254,   # kg CO2e/L (was 2.32 CO2-only pre-H3)
    "lpg_kgco2_per_kg":             3.1172,   # kg CO2e/kg
    # Scope 1 — gaseous fuels
    "natural_gas_kgco2_per_m3":     2.1692,   # kg CO2e/m³
    "cng_kgco2_per_m3":             2.1692,   # kg CO2e/m³ (same base as natural gas)
    # Scope 1 — solid fuels
    "coal_kgco2_per_kg":            2.7264,   # kg CO2e/kg (bituminous)
    # Scope 1 — biogenic (net zero per GHG Protocol biogenic accounting)
    "biomass_kgco2_per_kg":         0.0,       # Biogenic CO2 excluded from totals
    # Scope 2 — PLN national average grid
    "electricity_pln_kwh":          0.7160,   # kg CO2e/kWh — Kepmen ESDM No.18/2023
}

# CO2-only predecessor values — preserved for Phase 3 audit trail in EmissionFactorEntry
EMISSION_FACTORS_CO2_ONLY: dict[str, float] = {
    "diesel_kgco2_per_liter":   2.68,
    "petrol_kgco2_per_liter":   2.32,
    "lpg_kgco2_per_kg":         2.98,
    "natural_gas_kgco2_per_m3": 1.96,
    "cng_kgco2_per_m3":         1.96,
    "coal_kgco2_per_kg":        2.42,
}

# ── Scope 2: PLN regional grid emission factors ───────────────────────────────
# Source: Kepmen ESDM No.18/2023, Appendix II
# Province → subsystem key mapping

PLN_GRID_SUBSYSTEM: dict[str, str] = {
    # Jawa–Bali system
    "DKI Jakarta":          "electricity_pln_jawa_bali",
    "Jawa Barat":           "electricity_pln_jawa_bali",
    "Jawa Tengah":          "electricity_pln_jawa_bali",
    "DI Yogyakarta":        "electricity_pln_jawa_bali",
    "Jawa Timur":           "electricity_pln_jawa_bali",
    "Banten":               "electricity_pln_jawa_bali",
    "Bali":                 "electricity_pln_jawa_bali",
    # Sumatra system
    "Aceh":                 "electricity_pln_sumatra",
    "Sumatera Utara":       "electricity_pln_sumatra",
    "Sumatera Barat":       "electricity_pln_sumatra",
    "Riau":                 "electricity_pln_sumatra",
    "Kepulauan Riau":       "electricity_pln_sumatra",
    "Jambi":                "electricity_pln_sumatra",
    "Sumatera Selatan":     "electricity_pln_sumatra",
    "Bangka Belitung":      "electricity_pln_sumatra",
    "Bengkulu":             "electricity_pln_sumatra",
    "Lampung":              "electricity_pln_sumatra",
    # Kalimantan system
    "Kalimantan Barat":     "electricity_pln_kalimantan",
    "Kalimantan Tengah":    "electricity_pln_kalimantan",
    "Kalimantan Selatan":   "electricity_pln_kalimantan",
    "Kalimantan Timur":     "electricity_pln_kalimantan",
    "Kalimantan Utara":     "electricity_pln_kalimantan",
    # Sulawesi system
    "Sulawesi Utara":       "electricity_pln_sulawesi",
    "Gorontalo":            "electricity_pln_sulawesi",
    "Sulawesi Tengah":      "electricity_pln_sulawesi",
    "Sulawesi Barat":       "electricity_pln_sulawesi",
    "Sulawesi Selatan":     "electricity_pln_sulawesi",
    "Sulawesi Tenggara":    "electricity_pln_sulawesi",
    # Maluku–Papua system
    "Maluku":               "electricity_pln_maluku_papua",
    "Maluku Utara":         "electricity_pln_maluku_papua",
    "Papua":                "electricity_pln_maluku_papua",
    "Papua Barat":          "electricity_pln_maluku_papua",
    # NTT/NTB system
    "Nusa Tenggara Barat":  "electricity_pln_ntt_ntb",
    "Nusa Tenggara Timur":  "electricity_pln_ntt_ntb",
}

PLN_SUBSYSTEM_FACTORS: dict[str, float] = {
    "electricity_pln_jawa_bali":    0.7810,   # kg CO2e/kWh
    "electricity_pln_sumatra":      0.7610,   # kg CO2e/kWh
    "electricity_pln_kalimantan":   0.8120,   # kg CO2e/kWh
    "electricity_pln_sulawesi":     0.7430,   # kg CO2e/kWh
    "electricity_pln_maluku_papua": 0.8940,   # kg CO2e/kWh
    "electricity_pln_ntt_ntb":      0.8310,   # kg CO2e/kWh
}

def get_pln_ef(province: str) -> float:
    """
    Resolve PLN grid emission factor for a given province.
    Falls back to national average if province is not in the subsystem map.
    Source: Kepmen ESDM No.18/2023, Appendix II.
    """
    subsystem_key = PLN_GRID_SUBSYSTEM.get(province)
    if subsystem_key:
        return PLN_SUBSYSTEM_FACTORS.get(subsystem_key, EMISSION_FACTORS["electricity_pln_kwh"])
    return EMISSION_FACTORS["electricity_pln_kwh"]

# ── Scope 3: Category emission factors ───────────────────────────────────────
# Sources vary by category: DEFRA, USEEIO, GLEC, IPCC
SCOPE3_EMISSION_FACTORS: dict[str, dict] = {
    "cat1_purchased_goods": {
        "ef": 2.5,    # kg CO2e per USD spend (USEEIO sector average)
        "unit": "kg CO2e / USD",
        "source": "USEEIO v2.0",
    },
    "cat2_capital_goods": {
        "ef": 0.38,   # kg CO2e per USD
        "unit": "kg CO2e / USD",
        "source": "USEEIO v2.0",
    },
    "cat3_energy_upstream": {
        "ef": 0.053,  # kg CO2e per kWh (upstream losses)
        "unit": "kg CO2e / kWh",
        "source": "DEFRA 2023",
    },
    "cat4_transport_upstream": {
        "ef": 0.1,    # kg CO2e per tonne-km (road average)
        "unit": "kg CO2e / tonne-km",
        "source": "GLEC Framework v3",
    },
    "cat5_waste": {
        "ef": 0.467,  # kg CO2e per kg waste (landfill average)
        "unit": "kg CO2e / kg",
        "source": "DEFRA 2023",
    },
    "cat6_business_travel": {
        "ef": 0.255,  # kg CO2e per km (average domestic flight)
        "unit": "kg CO2e / km",
        "source": "DEFRA 2023",
    },
    "cat7_employee_commute": {
        "ef": 0.17,   # kg CO2e per km (passenger vehicle average)
        "unit": "kg CO2e / km",
        "source": "DEFRA 2023",
    },
    "cat8_upstream_leased": {
        "ef": 0.38,   # kg CO2e per USD rental spend
        "unit": "kg CO2e / USD",
        "source": "USEEIO v2.0",
    },
    "cat9_downstream_transport": {
        "ef": 0.1,    # kg CO2e per tonne-km
        "unit": "kg CO2e / tonne-km",
        "source": "GLEC Framework v3",
    },
    "cat10_processing": {
        "ef": 1.2,    # kg CO2e per USD processing spend
        "unit": "kg CO2e / USD",
        "source": "USEEIO v2.0",
    },
    "cat12_end_of_life": {
        "ef": 0.467,  # kg CO2e per kg product mass
        "unit": "kg CO2e / kg",
        "source": "DEFRA 2023",
    },
    "cat13_downstream_leased": {
        "ef": 0.038,  # kg CO2e per USD lease revenue
        "unit": "kg CO2e / USD",
        "source": "USEEIO v2.0",
    },
    # Categories 11, 14, 15 are screened and excluded (see constants.py)
}

# ── Industry carbon intensity benchmarks ──────────────────────────────────────
# Unit: kg CO2e / m² / year
# Source: CarbonLens internal estimates. Phase 0 C5 fix.
# NOTE: These are illustrative estimates. Independent validation required
#       before use in formal regulatory submissions.
INDUSTRY_BENCHMARKS: dict[str, float] = {
    "Manufacturing":   120.0,
    "Office":           45.0,
    "Retail":           65.0,
    "Hospitality":     180.0,
    "Healthcare":       85.0,
    "Education":        40.0,
    "Logistics":       200.0,
    "Technology":       35.0,
    "Energy":          350.0,
    "Agriculture":     280.0,
    "Mining":          420.0,
    "Construction":    150.0,
}

INDUSTRY_BENCHMARKS_PROVENANCE: str = (
    "Illustrative sector intensity estimates compiled for CarbonLens V8 (Phase 0 C5 fix). "
    "Sources: ENERGY STAR Building Benchmark Data (US EPA), CDP 2023 Corporate Disclosure "
    "Averages, IEA Energy Efficiency Indicators. Independent third-party validation required "
    "before use in formal POJK 51 or GRI submissions."
)

# ── ESG score bands ───────────────────────────────────────────────────────────
# Source: CarbonLens internal grading system. Phase 0 C2 fix.
ESG_SCORE_BANDS: list[dict] = [
    {"min": 85, "max": 100, "grade": "A",  "label": "Industry Leader"},
    {"min": 75, "max": 84,  "grade": "B+", "label": "Above Average"},
    {"min": 60, "max": 74,  "grade": "B",  "label": "Satisfactory"},
    {"min": 45, "max": 59,  "grade": "C",  "label": "Developing"},
    {"min":  0, "max": 44,  "grade": "D",  "label": "Needs Improvement"},
]

def assign_grade(score: float) -> tuple[str, str]:
    """Return (grade, label) for a given ESG score."""
    for band in ESG_SCORE_BANDS:
        if band["min"] <= score <= band["max"]:
            return band["grade"], band["label"]
    return "D", "Needs Improvement"

# ── Page colour accents ───────────────────────────────────────────────────────
PAGE_COLORS: dict[str, dict[str, str]] = {
    "executive_summary":    {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "carbon_accounting":    {"accent": "#10B981", "light": "#D1FAE5"},
    "esg_analytics":        {"accent": "#6366F1", "light": "#EDE9FE"},
    "data_quality":         {"accent": "#F97316", "light": "#FEF3C7"},
    "reporting_compliance": {"accent": "#0891B2", "light": "#CFFAFE"},
    "decarbonization":      {"accent": "#059669", "light": "#ECFDF5"},
    "governance":           {"accent": "#7C3AED", "light": "#EDE9FE"},
}

# ── Default user registry (development / fresh deployment) ───────────────────
DEFAULT_USERS: dict[str, dict] = {
    "admin": {
        "user_id":        "00000000-0000-0000-0000-000000000001",
        "display_name":   "Administrator",
        "password_hash":  "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
        "role":           "admin",
        "email":          "admin@carbonlens.io",
        "must_change_pw": False,
    },
    "analyst": {
        "user_id":        "00000000-0000-0000-0000-000000000002",
        "display_name":   "ESG Analyst",
        "password_hash":  "20249749412d73a3f5799f6f1dcf910e7b4aa3ce4de133b1f8a63c044792a4e9",
        "role":           "analyst",
        "email":          "analyst@carbonlens.io",
        "must_change_pw": False,
    },
    "viewer": {
        "user_id":        "00000000-0000-0000-0000-000000000003",
        "display_name":   "Viewer",
        "password_hash":  "65375049b9e4d7cad6c9ba286fdeb9394b28135a3e84136404cfccfdcc438894",
        "role":           "viewer",
        "email":          "viewer@carbonlens.io",
        "must_change_pw": False,
    },
}
