"""
CarbonLens V7 — Multi-company session state manager
Supports up to 5 companies. Active company drives all modules.
Disk persistence per company slot.
"""

from __future__ import annotations
import os, json, tempfile, hashlib
import streamlit as st
import pandas as pd

_CACHE_DIR = os.path.join(tempfile.gettempdir(), "carbonlens_v6_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

MAX_SLOTS = 5

# ── Default company template ──────────────────────────────────────────────────
def _default_company(slot: int = 0) -> dict:
    return {
        "company_name":              "",
        "sector":                    "Manufacturing",
        "area_m2":                   5000.0,
        "employees":                 100,
        "renew_pct":                 5,
        "recycle_pct":               20,
        "certifications":            [],
        "esg_grade":                 "—",
        "esg_label":                 "—",
        "esg_env_score":             0,
        "esg_social_score":          0,
        "esg_gov_score":             0,
        "esg_score":                 0,
        "onboarding_done":           False,
        "completeness":              94.0,
        "uploaded_df":               None,
        "prev_year_df":              None,
        "historical_data":           {},   # {year: {"emission": float, "energy": float, "water": float, "waste": float, "employees": int}}
        "gis_result":                None,
        "gis_province":              None,
        "gis_regency":               None,
        "s3_business_travel_km":     0.0,
        "s3_employee_commute_km":    0.0,
        "s3_purchased_goods_spend":  0.0,
        "s3_waste_tonnes":           0.0,
        "s3_upstream_transport_tkm": 0.0,
        "emission_factors":          None,
        "emission_factors_source":   "PLN RUPTL 2023 / Kepmen ESDM 18/2023",
        "emission_factors_updated":  "",
        "supplier_table":             None,
        "scope3_cat1_override_tco2e": None,
        "scope3_cat1_source":         "",
        "consolidation_entities":     None,
        # Carbon Accounting — computed scope totals (canonical, shared across platform)
        "ca_scope1_kg":   0.0,   # Scope 1 total in kg CO2e (from carbon_accounting.py)
        "ca_scope2_kg":   0.0,   # Scope 2 total in kg CO2e
        "ca_scope3_kg":   0.0,   # Scope 3 total in kg CO2e (activity-based)
        "ca_total_kg":    0.0,   # Grand total kg CO2e
        "ca_has_data":    False, # True when user has entered any accounting data
        "ca_intens_m2":   0.0,   # Carbon intensity kg/m2
        "ca_intens_emp":  0.0,   # Carbon intensity kg/employee
        "ca_intens_rev":  0.0,   # Carbon intensity kg/Rp miliar
        "province":       "",   # Selected province for PLN grid EF
        "facility_lat":   None,  # Facility latitude — feeds GEE NDVI/carbon stock analysis
        "facility_lon":   None,  # Facility longitude
        "facility_buffer_km": 2.0,  # Analysis radius around facility for GEE queries
        "facility_land_use_history": "",  # e.g. "Converted from oil palm plantation, 2018"
        "materials_table": None,  # GRI 301-1/301-2 — list of dicts: material, quantity_tonnes, unit, recycled_pct

        # ── Social indicators (GRI 401/403/404/405) ────────────────────────
        "water_recycled_pct":          0.0,
        "employee_turnover_pct":       None,
        "training_hours_per_employee": None,
        "women_workforce_pct":         None,
        "women_management_pct":        None,
        "injury_rate":                 None,

        # ── Governance indicators (GRI 2-9 to 2-24, 205) ────────────────────
        "board_independence_pct":      None,
        "women_board_pct":             None,
        "has_code_of_conduct":         None,
        "has_whistleblower_policy":    None,
        "anti_corruption_training_pct": None,

        # ── Canonical ESG breakdown (set once by ESG Analytics, read everywhere) ──
        "esg_breakdown":   None,   # full sub-indicator dict from calculate_esg_score()
        "esg_intensity":   0.0,    # canonical carbon intensity used for ESG (kg CO2e/m2)
        "esg_computed_at": "",     # timestamp / source marker
    }

# Keys shared across all companies (platform-level)
_GLOBAL_KEYS = {
    "active_slot":    0,           # which company is active (0–4)
    "active_page":    "profile",
    "copilot_history": [],
}


def init():
    """Initialize global keys + all company slots. Restore from disk."""
    # Global keys
    for k, v in _GLOBAL_KEYS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Company slots
    if "companies" not in st.session_state:
        st.session_state["companies"] = [_default_company(i) for i in range(MAX_SLOTS)]

    _restore_from_disk()


# ── Active slot helpers ───────────────────────────────────────────────────────

def _slot() -> int:
    return int(st.session_state.get("active_slot", 0))

def _co() -> dict:
    """Return active company dict (mutable reference)."""
    return st.session_state["companies"][_slot()]

def get(key: str, default=None):
    """Get value from active company or global keys."""
    if key in _GLOBAL_KEYS:
        return st.session_state.get(key, default)
    co = _co()
    val = co.get(key, default)
    return val if val is not None else default

def set(key: str, value):
    """Set value in active company or global keys."""
    if key in _GLOBAL_KEYS:
        st.session_state[key] = value
    else:
        _co()[key] = value
    _persist_to_disk()

def set_company_profile(name: str, sector: str, area_m2: float,
                        employees: int, renew_pct: int,
                        recycle_pct: int, certifications: list):
    co = _co()
    co.update(dict(
        company_name=name, sector=sector, area_m2=area_m2,
        employees=employees, renew_pct=renew_pct,
        recycle_pct=recycle_pct, certifications=certifications,
        onboarding_done=True,
    ))
    _persist_to_disk()

def clear():
    """Clear active company data."""
    slot = _slot()
    st.session_state["companies"][slot] = _default_company(slot)
    _delete_slot_cache(slot)


# ── Multi-company management ──────────────────────────────────────────────────

def get_all_companies() -> list[dict]:
    """Return list of all company dicts (including empty slots)."""
    return st.session_state.get("companies", [_default_company(i) for i in range(MAX_SLOTS)])

def get_active_slot() -> int:
    return _slot()

def set_active_slot(slot: int):
    """Switch active company. Triggers rerun from caller."""
    slot = max(0, min(slot, MAX_SLOTS - 1))
    st.session_state["active_slot"] = slot

def get_company_summary() -> list[dict]:
    """For sidebar: return list of {slot, name, grade, has_data}."""
    companies = get_all_companies()
    result = []
    for i, co in enumerate(companies):
        result.append({
            "slot":     i,
            "name":     co.get("company_name", "") or f"Company {i+1}",
            "grade":    co.get("esg_grade", "—"),
            "score":    co.get("esg_score", 0),
            "sector":   co.get("sector", "—"),
            "has_data": co.get("uploaded_df") is not None,
            "setup":    bool(co.get("company_name", "").strip()),
        })
    return result

def company_count() -> int:
    """Number of configured (non-empty) company slots."""
    return sum(1 for co in get_all_companies() if co.get("company_name","").strip())

def get_comparison_data() -> list[dict]:
    """Return KPI snapshots of all configured companies for comparison."""
    result = []
    for co in get_all_companies():
        if not co.get("company_name","").strip():
            continue
        df = co.get("uploaded_df")
        if df is not None and "Emission" in df.columns:
            total = float(df["Emission"].sum())
        else:
            total = 0.0
        result.append({
            "name":    co["company_name"],
            "sector":  co.get("sector","—"),
            "total":   total,
            "grade":   co.get("esg_grade","—"),
            "score":   co.get("esg_score", 0),
            "renew":   co.get("renew_pct", 0),
            "area_m2": co.get("area_m2", 5000),
        })
    return result


# ── Disk persistence ──────────────────────────────────────────────────────────

def _session_id() -> str:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            return hashlib.md5(ctx.session_id.encode()).hexdigest()[:12]
    except Exception:
        pass
    return "default"

def _slot_paths(slot: int) -> dict:
    sid = _session_id()
    base = os.path.join(_CACHE_DIR, f"{sid}_slot{slot}")
    return {"df": f"{base}_df.csv", "prev": f"{base}_prev.csv", "meta": f"{base}_meta.json"}

def _persist_to_disk():
    try:
        for slot, co in enumerate(st.session_state.get("companies", [])):
            p = _slot_paths(slot)
            df = co.get("uploaded_df")
            if df is not None and isinstance(df, pd.DataFrame):
                df.to_csv(p["df"], index=False)
            prev = co.get("prev_year_df")
            if prev is not None and isinstance(prev, pd.DataFrame):
                prev.to_csv(p["prev"], index=False)
            meta_keys = ["company_name","sector","area_m2","employees","renew_pct",
                         "recycle_pct","certifications","onboarding_done","esg_grade",
                         "esg_score","esg_env_score","esg_social_score","esg_gov_score","esg_label","completeness",
                         "s3_business_travel_km","s3_employee_commute_km",
                         "s3_purchased_goods_spend","s3_waste_tonnes",
                         "s3_upstream_transport_tkm",
                         "ca_scope1_kg","ca_scope2_kg","ca_scope3_kg",
                         "ca_total_kg","ca_has_data","ca_intens_m2",
                         "ca_intens_emp","ca_intens_rev",
                         "emission_factors","emission_factors_source","emission_factors_updated",
                         "historical_data","supplier_table",
                         "scope3_cat1_override_tco2e","scope3_cat1_source",
                         "facility_lat","facility_lon","facility_buffer_km",
                         "facility_land_use_history","materials_table",
                         "water_recycled_pct","employee_turnover_pct",
                         "training_hours_per_employee","women_workforce_pct",
                         "women_management_pct","injury_rate",
                         "board_independence_pct","women_board_pct",
                         "has_code_of_conduct","has_whistleblower_policy",
                         "anti_corruption_training_pct",
                         "esg_breakdown","esg_intensity","esg_computed_at"]
            meta = {k: co.get(k) for k in meta_keys}
            with open(p["meta"], "w") as f:
                json.dump(meta, f, default=str)
    except Exception:
        pass

def _restore_from_disk():
    try:
        companies = st.session_state.get("companies", [])
        for slot, co in enumerate(companies):
            p = _slot_paths(slot)
            if co.get("uploaded_df") is None and os.path.exists(p["df"]):
                df = pd.read_csv(p["df"])
                if not df.empty and "Emission" in df.columns:
                    co["uploaded_df"] = df
            if co.get("prev_year_df") is None and os.path.exists(p["prev"]):
                prev = pd.read_csv(p["prev"])
                if not prev.empty:
                    co["prev_year_df"] = prev
            if os.path.exists(p["meta"]):
                with open(p["meta"]) as f:
                    meta = json.load(f)
                for k, v in meta.items():
                    if not co.get(k):
                        co[k] = v
    except Exception:
        pass

def _delete_slot_cache(slot: int):
    try:
        for path in _slot_paths(slot).values():
            if os.path.exists(path):
                os.remove(path)
    except Exception:
        pass

def set_scope_results(scope1_kg: float, scope2_kg: float, scope3_kg: float,
                       area_m2: float = 1.0, employees: int = 1,
                       revenue_rp: float = 0.0):
    """
    Store Carbon Accounting results to shared state.
    Called by carbon_accounting.py after every recalculation.
    All downstream pages (Dashboard, ESG Reporting, Data Export) read from here.
    """
    import streamlit as st
    total = scope1_kg + scope2_kg + scope3_kg
    st.session_state["ca_scope1_kg"]  = round(scope1_kg, 2)
    st.session_state["ca_scope2_kg"]  = round(scope2_kg, 2)
    st.session_state["ca_scope3_kg"]  = round(scope3_kg, 2)
    st.session_state["ca_total_kg"]   = round(total, 2)
    st.session_state["ca_has_data"]   = (total > 0)
    st.session_state["ca_intens_m2"]  = round(total / max(area_m2, 1), 4)
    st.session_state["ca_intens_emp"] = round(total / max(employees, 1), 2)
    st.session_state["ca_intens_rev"] = round(total / max(revenue_rp, 0.001), 2) if revenue_rp > 0 else 0.0
    _persist_to_disk()


def get_scope_results() -> dict:
    """
    Read canonical scope totals. Falls back to ratio-estimates from uploaded CSV
    when Carbon Accounting hasn't been used yet — always returns consistent values.
    """
    import streamlit as st
    import pandas as pd

    has_ca = st.session_state.get("ca_has_data", False)
    if has_ca:
        return {
            "scope1_kg":  st.session_state.get("ca_scope1_kg", 0.0),
            "scope2_kg":  st.session_state.get("ca_scope2_kg", 0.0),
            "scope3_kg":  st.session_state.get("ca_scope3_kg", 0.0),
            "total_kg":   st.session_state.get("ca_total_kg",  0.0),
            "intens_m2":  st.session_state.get("ca_intens_m2", 0.0),
            "source":     "carbon_accounting",
        }

    # Fallback: derive from uploaded ESG CSV (ratio-based, clearly labelled)
    df = st.session_state.get("uploaded_df")
    if df is not None and "Emission" in df.columns:
        total_tco2 = float(df["Emission"].sum())
        total_kg   = total_tco2 * 1000
        area       = float(st.session_state.get("area_m2", 5000))

        # If the CSV provides Scope1/Scope2 columns directly, use those (more
        # accurate than the 0.295/0.436/0.269 generic ratio split).
        if "Scope1_tCO2e" in df.columns and "Scope2_tCO2e" in df.columns:
            s1_kg = float(df["Scope1_tCO2e"].sum()) * 1000
            s2_kg = float(df["Scope2_tCO2e"].sum()) * 1000
            s3_kg = max(total_kg - s1_kg - s2_kg, 0.0)
            return {
                "scope1_kg":  round(s1_kg, 2),
                "scope2_kg":  round(s2_kg, 2),
                "scope3_kg":  round(s3_kg, 2),
                "total_kg":   round(total_kg, 2),
                "intens_m2":  round(total_kg / max(area, 1), 4),
                "source":     "csv_scope_columns",
            }

        return {
            "scope1_kg":  round(total_kg * 0.295, 2),
            "scope2_kg":  round(total_kg * 0.436, 2),
            "scope3_kg":  round(total_kg * 0.269, 2),
            "total_kg":   round(total_kg, 2),
            "intens_m2":  round(total_kg / max(area, 1), 4),
            "source":     "csv_estimate",   # flag so UI can show disclaimer
        }

    return {
        "scope1_kg": 0.0, "scope2_kg": 0.0, "scope3_kg": 0.0,
        "total_kg": 0.0,  "intens_m2": 0.0, "source": "none",
    }


# ── Canonical ESG computation — SINGLE SOURCE OF TRUTH ─────────────────────────
def compute_canonical_esg(force: bool = False) -> dict:
    """
    Compute (or return cached) ESG score using the canonical intensity from
    get_scope_results() and all Social/Governance indicators from session state.

    This is the ONLY function that should call calculate_esg_score() for
    display purposes. All pages (Dashboard, ESG Reporting, AI Consultant,
    Benchmarking, Data Export, etc.) must call this instead of computing
    their own intensity/ESG — this guarantees one score across the platform.

    Set force=True to recompute even if cached (e.g. after new data upload).
    """
    import streamlit as st
    from utils.calculations import calculate_esg_score, dataset_overview

    cached = st.session_state.get("esg_breakdown")
    if cached and not force and "breakdown" in cached and "data_provided" in cached:
        return cached

    scope = get_scope_results()
    intensity = scope["intens_m2"]  # kg CO2e / m2 — canonical unit

    # Data completeness — from uploaded dataset if available, else stored default
    df = st.session_state.get("uploaded_df")
    if df is not None:
        completeness = dataset_overview(df).get("completeness", 94.0)
    else:
        completeness = st.session_state.get("completeness", 94.0)

    esg = calculate_esg_score(
        intensity                    = intensity,
        data_completeness            = completeness,
        renew_pct                    = float(st.session_state.get("renew_pct", 5)),
        recycle_pct                  = float(st.session_state.get("recycle_pct", 20)),
        water_recycled_pct           = float(st.session_state.get("water_recycled_pct", 0) or 0),
        employee_turnover_pct        = st.session_state.get("employee_turnover_pct"),
        training_hours_per_employee  = st.session_state.get("training_hours_per_employee"),
        women_workforce_pct          = st.session_state.get("women_workforce_pct"),
        women_management_pct         = st.session_state.get("women_management_pct"),
        injury_rate                  = st.session_state.get("injury_rate"),
        board_independence_pct       = st.session_state.get("board_independence_pct"),
        women_board_pct              = st.session_state.get("women_board_pct"),
        has_code_of_conduct          = st.session_state.get("has_code_of_conduct"),
        has_whistleblower_policy     = st.session_state.get("has_whistleblower_policy"),
        anti_corruption_training_pct = st.session_state.get("anti_corruption_training_pct"),
        certifications_count         = len(st.session_state.get("certifications") or []),
    )

    # Persist canonical result
    st.session_state["esg_breakdown"]   = esg
    st.session_state["esg_intensity"]   = intensity
    st.session_state["esg_grade"]       = esg["grade"]
    st.session_state["esg_score"]       = esg["score"]
    st.session_state["esg_label"]       = esg["label"]
    st.session_state["esg_env_score"]   = esg["env"]
    st.session_state["esg_social_score"]= esg["social"]
    st.session_state["esg_gov_score"]   = esg["gov"]
    import datetime as _dt
    st.session_state["esg_computed_at"] = _dt.datetime.now().isoformat()
    # Sync grade & scores into the active company slot so sidebar reads correctly
    slot = st.session_state.get("active_slot", 0)
    companies = st.session_state.get("companies", [])
    if 0 <= slot < len(companies):
        companies[slot]["esg_grade"]       = esg["grade"]
        companies[slot]["esg_score"]       = esg["score"]
        companies[slot]["esg_env_score"]   = esg["env"]
        companies[slot]["esg_social_score"]= esg["social"]
        companies[slot]["esg_gov_score"]   = esg["gov"]
        companies[slot]["esg_label"]       = esg["label"]  
    _persist_to_disk()

    return esg


# ── Emission factor management ────────────────────────────────────────────────
def get_emission_factors() -> dict:
    """Return active emission factors — company override or platform default."""
    from config.settings import EMISSION_FACTORS
    co = _co()
    custom = co.get("emission_factors")
    if custom:
        merged = dict(EMISSION_FACTORS)
        merged.update(custom)
        return merged
    return dict(EMISSION_FACTORS)


def save_emission_factors(factors: dict, source: str = "Custom", updated_at: str = ""):
    """Persist custom emission factors for the active company."""
    co = _co()
    co["emission_factors"]        = factors
    co["emission_factors_source"] = source
    co["emission_factors_updated"]= updated_at
    _persist_to_disk()


def reset_emission_factors():
    """Revert active company to platform default emission factors."""
    co = _co()
    co.pop("emission_factors", None)
    co.pop("emission_factors_source", None)
    co.pop("emission_factors_updated", None)
    _persist_to_disk()


# ── Multi-year historical data ────────────────────────────────────────────────
def get_historical_data() -> dict:
    """Return {year: {emission, energy, water, waste, employees}} dict for active company."""
    return _co().get("historical_data", {}) or {}


def save_historical_year(year: int, data: dict):
    """Save/update one year of historical totals for the active company."""
    co = _co()
    hist = dict(co.get("historical_data", {}) or {})
    hist[str(year)] = data
    co["historical_data"] = hist
    _persist_to_disk()


def delete_historical_year(year: int):
    co = _co()
    hist = dict(co.get("historical_data", {}) or {})
    hist.pop(str(year), None)
    co["historical_data"] = hist
    _persist_to_disk()


def compute_cagr(values: list[float]) -> float | None:
    """Compound Annual Growth Rate from first to last value across N periods."""
    if len(values) < 2 or values[0] <= 0:
        return None
    n = len(values) - 1
    try:
        return (values[-1] / values[0]) ** (1 / n) - 1
    except (ZeroDivisionError, ValueError):
        return None
