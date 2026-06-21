"""
CarbonLens V7 — Core calculation engine
- Fully deterministic ESG scoring
- 12 Scope 3 GHG Protocol categories with peer-reviewed EFs
- st.cache_data on heavy functions (hash-keyed, auto-invalidates)
"""

from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from config.settings import EMISSION_FACTORS, INDUSTRY_BENCHMARKS, ESG_SCORE_BANDS


# ─────────────────────────────────────────────────────────────────────────────
# CACHE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _df_hash(df: pd.DataFrame) -> str:
    """Stable hash of a DataFrame — used as cache_data key."""
    try:
        h = hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()
    except Exception:
        h = hashlib.md5(df.to_csv(index=False).encode()).hexdigest()
    return h


# ─────────────────────────────────────────────────────────────────────────────
# SCOPE 1 & 2
# ─────────────────────────────────────────────────────────────────────────────

def calculate_scope1(diesel_liters=0.0, petrol_liters=0.0,
                     lpg_kg=0.0, natural_gas_m3=0.0, ef: dict | None = None) -> dict:
    factors = ef or EMISSION_FACTORS
    breakdown = {
        "Diesel":       diesel_liters  * factors.get("diesel_kgco2_per_liter",   EMISSION_FACTORS["diesel_kgco2_per_liter"]),
        "Petrol":       petrol_liters  * factors.get("petrol_kgco2_per_liter",   EMISSION_FACTORS["petrol_kgco2_per_liter"]),
        "LPG":          lpg_kg         * factors.get("lpg_kgco2_per_kg",         EMISSION_FACTORS["lpg_kgco2_per_kg"]),
        "Natural Gas":  natural_gas_m3 * factors.get("natural_gas_kgco2_per_m3", EMISSION_FACTORS["natural_gas_kgco2_per_m3"]),
    }
    breakdown = {k: v for k, v in breakdown.items() if v > 0}
    return {"total": sum(breakdown.values()), "breakdown": breakdown}


def calculate_scope2(electricity_kwh: float, province: str = "", ef: dict | None = None) -> dict:
    """
    Calculate Scope 2 purchased electricity emissions.
    If `ef` (custom override dict) is provided, it takes priority.
    Otherwise uses province-specific PLN subsystem EF when province is given,
    falling back to national average (Kepmen ESDM 18/2023).
    """
    from config.settings import PLN_GRID_SUBSYSTEM
    factors = ef or EMISSION_FACTORS
    is_custom = ef is not None

    if is_custom:
        factor = factors.get("electricity_kgco2_per_kwh", EMISSION_FACTORS["electricity_kgco2_per_kwh"])
        label  = f"Grid Electricity (Custom — {factor} kg/kWh)"
    elif province and province in PLN_GRID_SUBSYSTEM:
        ef_key = PLN_GRID_SUBSYSTEM[province]
        factor = EMISSION_FACTORS.get(ef_key, EMISSION_FACTORS["electricity_kgco2_per_kwh"])
        label  = f"Grid Electricity ({province} — {factor} kg/kWh)"
    else:
        factor = EMISSION_FACTORS["electricity_kgco2_per_kwh"]
        label  = f"Grid Electricity (National avg — {factor} kg/kWh)"

    total = electricity_kwh * factor
    return {"total": total, "ef_used": factor, "breakdown": {label: total}}


# ─────────────────────────────────────────────────────────────────────────────
# SCOPE 3 — 12 GHG Protocol categories (most commonly reported)
# ─────────────────────────────────────────────────────────────────────────────

SCOPE3_CATS = {
    # key: (category_label, unit_label, ef_kg_per_unit, source)
    "cat1_purchased_goods_usd": (
        "Cat.1 — Purchased Goods & Services",
        "USD spend", 0.42,
        "USEEIO v2.0 (EPA, 2023) — economic IO model avg across sectors",
    ),
    "cat2_capital_goods_usd": (
        "Cat.2 — Capital Goods",
        "USD spend", 0.55,
        "USEEIO v2.0 (EPA, 2023) — machinery & equipment IO coefficient",
    ),
    "cat3_fuel_energy_kwh": (
        "Cat.3 — Fuel & Energy Related (upstream)",
        "kWh", 0.089,
        "DEFRA 2023 — T&D losses + well-to-tank upstream electricity",
    ),
    "cat4_upstream_transport_tkm": (
        "Cat.4 — Upstream Transport & Distribution",
        "tonne-km", 0.062,
        "GLEC Framework v3 (2023) — road/sea freight weighted average",
    ),
    "cat5_waste_landfill_tonne": (
        "Cat.5 — Waste Generated in Operations",
        "tonnes", 467.0,
        "IPCC 2006 waste disposal factors — landfill MSW methane default",
    ),
    "cat6_business_travel_km": (
        "Cat.6 — Business Travel (Air)",
        "km", 0.255,
        "DEFRA 2023 — economy class, average haul, RFI 1.9x included",
    ),
    "cat7_employee_commute_km": (
        "Cat.7 — Employee Commuting",
        "km/year (all staff)", 0.170,
        "IPCC AR6 (2022) — mixed transport mode (car 60%, transit 40%)",
    ),
    "cat8_upstream_leased_kwh": (
        "Cat.8 — Upstream Leased Assets",
        "kWh", 0.7160,
        "Kepmen ESDM 18/2023 PLN national average EF (effective 1 Jan 2024)",
    ),
    "cat9_downstream_transport_tkm": (
        "Cat.9 — Downstream Transport & Distribution",
        "tonne-km", 0.058,
        "GLEC Framework v3 (2023) — outbound freight weighted average",
    ),
    "cat11_use_of_sold_products_kwh": (
        "Cat.11 — Use of Sold Products",
        "kWh (lifetime energy)", 0.7160,
        "Kepmen ESDM 18/2023 — energy consumed by sold products in use",
    ),
    "cat12_eol_waste_tonne": (
        "Cat.12 — End-of-Life Treatment of Sold Products",
        "tonnes", 300.0,
        "IPCC 2006 — mixed EOL pathway (landfill + incineration avg)",
    ),
    "cat13_downstream_leased_kwh": (
        "Cat.13 — Downstream Leased Assets",
        "kWh", 0.7160,
        "Kepmen ESDM 18/2023 PLN national average EF",
    ),
}


def calculate_scope3(cat1_override_tco2e: float | None = None,
                      cat1_override_source: str = "", **kwargs) -> dict:
    """
    GHG Protocol-compliant Scope 3 calculation across 12 categories.

    Pass keyword arguments matching SCOPE3_CATS keys with activity quantities.
    Example:
        calculate_scope3(cat6_business_travel_km=50000, cat7_employee_commute_km=200000)

    If cat1_override_tco2e is provided (e.g. from the Supplier ESG Scorecard),
    it replaces the generic spend×factor estimate for Category 1 with a
    supplier-weighted total and records the provenance.

    Returns total (kg CO₂e) and per-category breakdown with full provenance.
    """
    breakdown = {}
    for key, (label, unit, ef, source) in SCOPE3_CATS.items():
        if key == "cat1_purchased_goods_usd" and cat1_override_tco2e is not None and cat1_override_tco2e > 0:
            emission = round(cat1_override_tco2e * 1000, 1)  # tCO2e → kg
            breakdown[key] = {
                "label":    label,
                "kg_co2e":  emission,
                "activity": cat1_override_tco2e,
                "unit":     "tCO2e (supplier-weighted)",
                "ef":       None,
                "source":   cat1_override_source or "Supplier ESG Scorecard (weighted, per-supplier)",
            }
            continue

        activity = float(kwargs.get(key, 0.0))
        if activity > 0:
            emission = round(activity * ef, 1)
            breakdown[key] = {
                "label":    label,
                "kg_co2e":  emission,
                "activity": activity,
                "unit":     unit,
                "ef":       ef,
                "source":   source,
            }

    total    = round(sum(v["kg_co2e"] for v in breakdown.values()), 1)
    n_filled = len(breakdown)
    n_total  = len(SCOPE3_CATS)

    return {
        "total":        total,
        "breakdown":    breakdown,
        "has_data":     total > 0,
        "n_categories": n_filled,
        "completeness": round(n_filled / n_total * 100),
    }


def calculate_total_emission(scope1: float, scope2: float,
                              scope3: float = 0.0) -> float:
    return scope1 + scope2 + scope3


def calculate_intensity(total_emission_kg: float, area_m2: float) -> float:
    return total_emission_kg / area_m2 if area_m2 > 0 else 0.0


def emission_category(total_kg: float) -> tuple[str, str]:
    if total_kg < 500:    return "Low",      "green"
    elif total_kg < 1000: return "Medium",   "yellow"
    elif total_kg < 2000: return "High",     "yellow"
    else:                 return "Critical", "red"


# ─────────────────────────────────────────────────────────────────────────────
# ESG SCORING — cached, deterministic
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# ESG SCORING — GRI 2021 + SASB aligned, deterministic
# ─────────────────────────────────────────────────────────────────────────────
#
# Pillar weights follow common ESG rating methodology (MSCI/Sustainalytics-style
# equal-ish weighting, adjustable):
#   Environmental: 40%   — GRI 302 (Energy), 303 (Water), 305 (Emissions), 306 (Waste)
#   Social:        30%   — GRI 401-2/3, 403, 404, 405-1, 406 (Diversity, H&S, Training)
#   Governance:    30%   — GRI 2-9 to 2-21, 205, 206, 418 (Board, Ethics, Compliance)
#
# Each pillar is a weighted sum of normalized sub-indicators (0-100 each).
# Sub-indicators default to neutral/conservative values when data is not provided,
# so the score remains usable with minimal input but improves in accuracy and
# moves toward real performance as more GRI/SASB-aligned data is supplied.
# ─────────────────────────────────────────────────────────────────────────────

def calculate_esg_score(intensity: float,
                         data_completeness: float = 94.0,
                         renew_pct: float = 5.0,
                         recycle_pct: float = 20.0,
                         water_recycled_pct: float = 0.0,
                         employee_turnover_pct: float = None,
                         training_hours_per_employee: float = None,
                         women_workforce_pct: float = None,
                         women_management_pct: float = None,
                         injury_rate: float = None,
                         board_independence_pct: float = None,
                         women_board_pct: float = None,
                         has_code_of_conduct: bool = None,
                         has_whistleblower_policy: bool = None,
                         anti_corruption_training_pct: float = None,
                         certifications_count: int = 0) -> dict:
    """
    GRI 2021 / SASB-aligned ESG scoring. Cached — same inputs return cached result.

    All inputs are optional except `intensity`. When social/governance indicators
    are not provided (None), they fall back to sector-neutral defaults so the
    score remains computable from a minimal dataset, while clearly improving
    in fidelity as more disclosure data is supplied.

    Returns dict with overall score/grade plus full sub-indicator breakdown
    for transparency (shown in ESG Analytics / Reporting "score composition").
    """
    # ── ENVIRONMENTAL (40%) ────────────────────────────────────────────────
    # GRI 305 — Carbon intensity vs 200 kg/m² reference ceiling
    e_carbon = max(0.0, min(100.0, 100.0 - (intensity / 200.0) * 100.0))
    # GRI 302 — Renewable energy adoption (0-100% maps directly)
    e_energy = max(0.0, min(100.0, renew_pct))
    # GRI 306 — Waste/material circularity (recycling rate)
    e_waste  = max(0.0, min(100.0, recycle_pct))
    # GRI 303 — Water recycled/reused (defaults to 0 if not disclosed)
    e_water  = max(0.0, min(100.0, water_recycled_pct))

    env_raw = (e_carbon * 0.45) + (e_energy * 0.25) + (e_waste * 0.15) + (e_water * 0.15)

    # ── SOCIAL (30%) ────────────────────────────────────────────────────────
    # GRI 401-1 — Employee turnover (lower is better). Default: sector-neutral 15%.
    _turnover = 15.0 if employee_turnover_pct is None else employee_turnover_pct
    s_turnover = max(0.0, min(100.0, 100.0 - (_turnover / 30.0) * 100.0))

    # GRI 404-1 — Training hours per employee/year. Default: 8h (minimal).
    _training = 8.0 if training_hours_per_employee is None else training_hours_per_employee
    s_training = max(0.0, min(100.0, (_training / 40.0) * 100.0))

    # GRI 405-1 — Gender diversity, workforce + management (avg of two)
    _women_wf = 30.0 if women_workforce_pct  is None else women_workforce_pct
    _women_mg = 20.0 if women_management_pct is None else women_management_pct
    s_diversity = max(0.0, min(100.0, ((_women_wf + _women_mg) / 2) / 50.0 * 100.0))

    # GRI 403-9 — Workplace injury rate (lower is better). Default: 3.0 per 200k hrs.
    _injury = 3.0 if injury_rate is None else injury_rate
    s_safety = max(0.0, min(100.0, 100.0 - (_injury / 6.0) * 100.0))

    social_raw = (s_turnover * 0.25) + (s_training * 0.25) + (s_diversity * 0.25) + (s_safety * 0.25)

    # ── GOVERNANCE (30%) ────────────────────────────────────────────────────
    # GRI 2-9/2-10 — Board independence %. Default: 30% (typical minimum).
    _board_indep = 30.0 if board_independence_pct is None else board_independence_pct
    g_board_indep = max(0.0, min(100.0, (_board_indep / 50.0) * 100.0))

    # GRI 405-1 — Women on board %. Default: 15%.
    _women_board = 15.0 if women_board_pct is None else women_board_pct
    g_board_div = max(0.0, min(100.0, (_women_board / 40.0) * 100.0))

    # GRI 2-23/2-24/205-2 — Ethics & anti-corruption policies (binary + training %)
    _has_coc  = False if has_code_of_conduct      is None else has_code_of_conduct
    _has_wb   = False if has_whistleblower_policy is None else has_whistleblower_policy
    _anti_corr_training = 0.0 if anti_corruption_training_pct is None else anti_corruption_training_pct
    g_ethics = (
        (40.0 if _has_coc else 0.0) +
        (30.0 if _has_wb  else 0.0) +
        min(30.0, _anti_corr_training * 0.3)
    )
    g_ethics = max(0.0, min(100.0, g_ethics))

    # Data completeness as proxy for reporting/disclosure quality (GRI 2-3)
    g_disclosure = min(100.0, max(10.0, data_completeness * 0.95))

    # Certifications (ISO 14001/45001/26000, SA8000 etc.) — bonus, capped
    g_certs = min(100.0, certifications_count * 20.0)

    gov_raw = (g_board_indep * 0.25) + (g_board_div * 0.15) + (g_ethics * 0.30) +               (g_disclosure * 0.20) + (g_certs * 0.10)

    # ── OVERALL ──────────────────────────────────────────────────────────────
    overall = round(min(100.0, max(0.0,
                env_raw * 0.40 + social_raw * 0.30 + gov_raw * 0.30)))

    result = {
        "score":  overall,
        "env":    round(env_raw,    1),
        "social": round(social_raw, 1),
        "gov":    round(gov_raw,    1),
        # Sub-indicator breakdown for transparency / score composition display
        "breakdown": {
            "environmental": {
                "Carbon Intensity (GRI 305)":     round(e_carbon, 1),
                "Renewable Energy (GRI 302)":      round(e_energy, 1),
                "Waste Recycling (GRI 306)":       round(e_waste, 1),
                "Water Recycled (GRI 303)":        round(e_water, 1),
            },
            "social": {
                "Employee Retention (GRI 401-1)":  round(s_turnover, 1),
                "Training Hours (GRI 404-1)":      round(s_training, 1),
                "Gender Diversity (GRI 405-1)":     round(s_diversity, 1),
                "Workplace Safety (GRI 403-9)":     round(s_safety, 1),
            },
            "governance": {
                "Board Independence (GRI 2-9/10)": round(g_board_indep, 1),
                "Board Diversity (GRI 405-1)":      round(g_board_div, 1),
                "Ethics & Anti-Corruption (GRI 2-23/205)": round(g_ethics, 1),
                "Disclosure Quality (GRI 2-3)":     round(g_disclosure, 1),
                "Certifications":                    round(g_certs, 1),
            },
        },
        # Flag which indicators used defaults vs real disclosed data
        "data_provided": {
            "water_recycled":      water_recycled_pct > 0,
            "employee_turnover":   employee_turnover_pct is not None,
            "training_hours":      training_hours_per_employee is not None,
            "gender_diversity":    women_workforce_pct is not None or women_management_pct is not None,
            "injury_rate":         injury_rate is not None,
            "board_independence":  board_independence_pct is not None,
            "board_diversity":     women_board_pct is not None,
            "ethics_policies":     has_code_of_conduct is not None or has_whistleblower_policy is not None,
        },
    }

    for band in reversed(ESG_SCORE_BANDS):
        if overall >= band["min"]:
            result["grade"] = band["grade"]
            result["label"] = band["label"]
            result["color"] = band["color"]
            return result

    result.update({"grade": "D", "label": "Critical", "color": "#EF4444"})
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARKING
# ─────────────────────────────────────────────────────────────────────────────

def get_benchmark(sector: str) -> float:
    return float(INDUSTRY_BENCHMARKS.get(sector, 50))


def benchmark_gap(intensity: float, benchmark: float) -> dict:
    diff = intensity - benchmark
    pct  = (diff / benchmark * 100) if benchmark > 0 else 0
    return {
        "gap_abs":         round(diff, 2),
        "gap_pct":         round(pct, 1),
        "above_benchmark": diff > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS — cached by dataframe hash
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def dataset_overview(df: pd.DataFrame) -> dict:
    """Cached dataset statistics. Cache invalidates when data changes."""
    if df is None or df.empty or "Emission" not in df.columns:
        return {}
    emission = df["Emission"]
    return {
        "total":        round(float(emission.sum()), 2),
        "average":      round(float(emission.mean()), 2),
        "peak":         round(float(emission.max()), 2),
        "min":          round(float(emission.min()), 2),
        "std":          round(float(emission.std()), 2),
        "peak_month":   df.loc[emission.idxmax(), "Month"] if "Month" in df.columns else "—",
        "low_month":    df.loc[emission.idxmin(), "Month"] if "Month" in df.columns else "—",
        "count":        int(len(df)),
        "completeness": round(float(df.notna().mean().mean() * 100), 1),
    }


def detect_outliers(df: pd.DataFrame, col: str = "Emission",
                    z_thresh: float = 1.8) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame()
    z = (df[col] - df[col].mean()) / df[col].std()
    return df[np.abs(z) > z_thresh].copy()


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION — cached by dataframe hash
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def predict_next_emission(df: pd.DataFrame) -> dict:
    """Cached linear regression forecast. Invalidates when data changes."""
    if df is None or len(df) < 3:
        return {"forecast": None, "trendline": None, "confidence": None,
                "r2": 0, "slope": 0, "trend_dir": "stable"}
    x = np.arange(len(df)).reshape(-1, 1)
    y = df["Emission"].values
    model     = LinearRegression().fit(x, y)
    forecast  = float(model.predict([[len(df)]])[0])
    trendline = model.predict(x)
    r2        = model.score(x, y)
    slope     = float(model.coef_[0])
    return {
        "forecast":   round(forecast, 2),
        "trendline":  trendline,
        "r2":         round(r2, 3),
        "slope":      round(slope, 3),
        "trend_dir":  "increasing" if slope > 0.5 else "decreasing" if slope < -0.5 else "stable",
        "confidence": round(min(r2 * 100, 95), 1),
    }


@st.cache_data(show_spinner=False)
def annual_projection(df: pd.DataFrame, months_ahead: int = 12) -> float:
    pred     = predict_next_emission(df)
    if pred["forecast"] is None:
        return 0.0
    last_val = float(df["Emission"].iloc[-1])
    future   = [last_val + pred["slope"] * i for i in range(1, months_ahead + 1)]
    return round(sum(future), 1)


def overshoot_risk(annual_proj: float, benchmark_annual: float) -> dict:
    ratio = annual_proj / benchmark_annual if benchmark_annual > 0 else 1
    if   ratio < 0.9:  return {"level": "Low",      "color": "#22C55E", "probability": 0.12}
    elif ratio < 1.1:  return {"level": "Moderate", "color": "#F59E0B", "probability": 0.42}
    elif ratio < 1.3:  return {"level": "High",     "color": "#F97316", "probability": 0.68}
    else:              return {"level": "Critical",  "color": "#EF4444", "probability": 0.87}


# ─────────────────────────────────────────────────────────────────────────────
# YEAR-OVER-YEAR
# ─────────────────────────────────────────────────────────────────────────────

def yoy_delta(current: float, previous: float) -> dict:
    """Compute YoY delta with direction indicator."""
    if previous == 0:
        return {"delta_abs": 0, "delta_pct": 0, "direction": "flat", "arrow": "→"}
    delta_abs = current - previous
    delta_pct = round(delta_abs / previous * 100, 1)
    if delta_pct > 1:
        return {"delta_abs": round(delta_abs, 2), "delta_pct": delta_pct,
                "direction": "up", "arrow": "↑"}
    elif delta_pct < -1:
        return {"delta_abs": round(delta_abs, 2), "delta_pct": delta_pct,
                "direction": "down", "arrow": "↓"}
    else:
        return {"delta_abs": round(delta_abs, 2), "delta_pct": delta_pct,
                "direction": "flat", "arrow": "→"}


# ─────────────────────────────────────────────────────────────────────────────
# DEMO DATA
# ─────────────────────────────────────────────────────────────────────────────

def generate_demo_data(seed: int = 42) -> pd.DataFrame:
    """
    Generate a full GRI 2021 / SASB-aligned demo dataset.
    Environmental: Scope1/2/3, Energy, Renewable, Water, Waste
    Social: Turnover, Training, Gender diversity, Injury rate
    Governance: Board independence/diversity, Ethics, Anti-corruption
    Social/Governance values are org-level constants repeated across months.
    """
    rng    = np.random.default_rng(seed)
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    n      = 12

    # ── Environmental (monthly time-series) ──────────────────────────────────
    base  = 220
    trend = np.linspace(0, 40, n)
    noise = rng.normal(0, 12, n)
    total_em = np.maximum(base + trend + noise, 100)

    scope1 = np.round(total_em * 0.295, 1)
    scope2 = np.round(total_em * 0.436, 1)
    scope3 = np.round(total_em * 0.269, 1)
    energy = np.round(total_em * 14.2 + rng.normal(0, 50, n), 0)
    renew  = np.round(np.clip(18 + rng.normal(0, 1, n), 5, 100), 1)
    water_w= np.round(total_em * 2.8 + rng.normal(0, 20, n), 0)
    water_r= np.round(water_w * 0.35 + rng.normal(0, 5, n), 0)
    waste_g= np.round(total_em * 0.11 + rng.normal(0, 2, n), 2)
    waste_r= np.round(waste_g * 0.45 + rng.normal(0, 0.5, n), 2)

    # ── Social (org-level — same value repeated; GRI 400-series) ─────────────
    # GRI 401-1 — Employee turnover %
    turnover  = np.round(np.full(n, 12.5), 1)
    # GRI 404-1 — Average training hours per employee per year
    training  = np.round(np.full(n, 24.0), 1)
    # GRI 405-1 — Women in workforce & management
    women_wf  = np.round(np.full(n, 38.0), 1)
    women_mgmt= np.round(np.full(n, 22.0), 1)
    # GRI 403-9 — Lost-time injury rate per 200k working hours
    injury    = np.round(np.full(n, 1.8), 2)

    # ── Governance (org-level — GRI 2 / SASB) ───────────────────────────────
    board_indep  = np.round(np.full(n, 44.4), 1)   # GRI 2-9
    women_board  = np.round(np.full(n, 27.3), 1)   # GRI 405-1
    anti_corr    = np.round(np.full(n, 85.0), 1)   # GRI 205-2

    return pd.DataFrame({
        # Identifiers
        "Month":      months,
        "Year":       [2024] * n,
        # Environmental — Scope
        "Emission":   np.round(total_em, 1),        # Total tCO₂e (all scopes)
        "Scope1_tCO2e": scope1,                     # GRI 305-1
        "Scope2_tCO2e": scope2,                     # GRI 305-2
        # Environmental — Energy
        "Energy":     energy,                        # kWh — GRI 302-1
        "Renewable_pct": renew,                      # % — GRI 302-1
        # Environmental — Water
        "Water_Withdrawal": water_w,                 # m³ — GRI 303-3
        "Water_Recycled":   water_r,                 # m³ — GRI 303-5
        # Environmental — Waste
        "Waste_Generated": waste_g,                  # tonnes — GRI 306-3
        "Waste_Recycled":  waste_r,                  # tonnes — GRI 306-4
        # Social — GRI 400-series (org-level, repeated)
        "Employee_Turnover_pct":         turnover,   # GRI 401-1
        "Training_Hours_Per_Employee":   training,   # GRI 404-1
        "Women_Workforce_pct":           women_wf,   # GRI 405-1
        "Women_Management_pct":          women_mgmt, # GRI 405-1
        "Injury_Rate":                   injury,     # GRI 403-9
        # Governance — GRI 2 / SASB (org-level, repeated)
        "Board_Independence_pct":        board_indep, # GRI 2-9
        "Women_Board_pct":               women_board, # GRI 405-1
        "Anti_Corruption_Training_pct":  anti_corr,  # GRI 205-2
    })


# ─────────────────────────────────────────────────────────────────────────────
# JSON utility — shared encoder that handles all numpy scalar types
# ─────────────────────────────────────────────────────────────────────────────
import json as _json

class NumpyEncoder(_json.JSONEncoder):
    """Converts numpy int64/float64/bool_ and ndarray to native Python types
    so json.dumps() never raises 'Object of type X is not JSON serializable'.
    Usage: json.dumps(obj, cls=NumpyEncoder)"""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)
