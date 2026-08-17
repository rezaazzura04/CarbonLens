"""
CarbonLens V8 — Demo Service.
Single canonical demo initialization path.

Provides the TWO-MODE model:
  A. DEMO MODE    — CARBONLENS_AUTH_REQUIRED=false (default)
  B. REAL MODE    — CARBONLENS_AUTH_REQUIRED=true

Demo Mode initialises a clearly synthetic organisation and dataset
so the application is immediately explorable from a fresh launch.

IMPORTANT:
- Never presents demo data as real organisational data
- The UI must visibly identify Demo Mode
- init_demo_organisation() is idempotent — safe to call on every render
- Demo data cannot leak into real organisation slots (slot 0 only)
- One canonical function: init_demo_organisation()
"""
from __future__ import annotations
import logging
import pandas as pd

log = logging.getLogger("carbonlens.services.demo")

# ── Demo Organisation Profile ─────────────────────────────────────────────────

DEMO_ORG: dict = {
    "org_id":           "demo-org-carbonlens",
    "company_name":     "CarbonLens Demo Organisation",
    "sector":           "Manufacturing",
    "area_m2":          8500.0,
    "employees":        250,
    "province":         "Jawa Timur",
    "reporting_period": "2025",
    "renew_pct":        15.0,
    "recycle_pct":      20.0,
    "certifications":   ["ISO 14001"],
    "is_demo":          True,
}

# ── Demo Disclosure Inputs (S/G indicators for ESG scoring) ───────────────────

DEMO_DISCLOSURE: dict = {
    "employee_turnover_pct":       8.5,
    "training_hours_per_employee": 28.0,
    "women_workforce_pct":         38.0,
    "injury_rate":                 0.4,
    "board_independence_pct":      55.0,
    "women_board_pct":             25.0,
    "water_recycled_pct":          30.0,
    "has_code_of_conduct":         True,
    "disclosure_score":            80.0,
}

# ── Demo Scope Inputs (Carbon Accounting form values) ─────────────────────────

DEMO_SCOPE_INPUTS: dict = {
    "diesel_liters":    8500.0,
    "petrol_liters":    2200.0,
    "electricity_kwh":  125000.0,
    "cat5_waste_kg":    3500.0,
}

# ── Demo Dataset (12 months — satisfies Phase 5-B forecast gate: ≥ 6 periods) -

DEMO_EMISSIONS_DATA = {
    "Month":    ["Jan","Feb","Mar","Apr","May","Jun",
                 "Jul","Aug","Sep","Oct","Nov","Dec"],
    "Emission": [245,  268,  231,  259,  277,  242,
                 264,  251,  239,  267,  245,  258],
    "Energy":   [180000,195000,172000,188000,201000,178000,
                 192000,183000,175000,196000,182000,190000],
    "Waste":    [12.4, 13.1, 11.8, 12.9, 14.2, 12.0,
                 13.5, 12.7, 11.9, 13.8, 12.3, 13.2],
    "Water":    [480,  510,  465,  495,  525,  475,
                 505,  490,  468,  512,  478,  498],
}

DEMO_VALIDATION_RESULT: dict = {
    "status":                 "Pass",
    "errors":                 [],
    "warnings":               ["Demo data — not real organisational data."],
    "columns_present":        ["Month","Emission","Energy","Waste","Water"],
    "rows_valid":             12,
    "rows_total":             12,
    "normalisation_applied":  False,
}


def get_demo_dataframe() -> pd.DataFrame:
    """Return the demo emissions DataFrame. Always fresh — never mutated."""
    return pd.DataFrame(DEMO_EMISSIONS_DATA)


# ── Canonical demo initialization ─────────────────────────────────────────────

def is_demo_initialised() -> bool:
    """Return True if demo mode is enabled AND the demo org is in slot 0."""
    try:
        from repository.session_repo import is_demo_mode_enabled, get_organisation
        if not is_demo_mode_enabled():
            return False    # flag is off — never consider demo initialised
        org = get_organisation(slot=0)
        return bool(org and org.get("is_demo") and
                    org.get("org_id") == DEMO_ORG["org_id"])
    except Exception:
        return False


def init_demo_organisation() -> dict:
    """
    Idempotent demo initialisation.

    Sets:
      - Demo org profile in session slot 0
      - Demo dataset (12 months, satisfies forecast gate)
      - Demo disclosure inputs (S/G indicators)
      - Demo scope inputs (Carbon Accounting)
      - Demo validation result (Pass)
      - Marks onboarding complete for slot 0

    Returns the DEMO_ORG dict.

    Must NEVER be called for real organisation slots (slot > 0).
    Demo data is always in slot 0 and always marked is_demo=True.
    """
    # Check explicit demo mode flag first — never init if flag is off
    from repository.session_repo import is_demo_mode_enabled, set_demo_mode_enabled
    if not is_demo_mode_enabled():
        log.debug("init_demo_organisation: demo_mode_enabled=False — skipping")
        return DEMO_ORG

    if is_demo_initialised():
        return DEMO_ORG   # already done — idempotent

    try:
        from repository.session_repo import (
            set_organisation,
            mark_onboarding_complete,
            set as _set,
            set_uploaded_df,
            set_validation_result,
        )

        # 1. Persist demo org to slot 0
        set_organisation(DEMO_ORG, slot=0)
        mark_onboarding_complete(slot=0)

        # 2. Load demo dataset into session
        set_uploaded_df(get_demo_dataframe())

        # 3. Persist validation result
        set_validation_result(DEMO_VALIDATION_RESULT, slot=0)

        # 4. Persist disclosure inputs and scope inputs
        _set("disclosure_inputs", DEMO_DISCLOSURE,   slot=0)
        _set("scope_inputs",      DEMO_SCOPE_INPUTS, slot=0)

        log.info("Demo organisation initialised in slot 0")

    except Exception as exc:
        log.warning(f"init_demo_organisation failed: {exc}")

    return DEMO_ORG


def exit_demo_mode(slot: int = 0) -> None:
    """
    Exit Demo Mode deterministically.

    1. Sets demo_mode_enabled = False (prevents reinitialisation)
    2. Clears ALL demo-tagged state from slot 0
    3. Invalidates ComputedState cache

    After this call, init_demo_organisation() will not run again
    until demo_mode_enabled is explicitly set to True.

    Called when user clicks "Set Up My Organisation".
    """
    try:
        from repository.session_repo import (
            set_demo_mode_enabled,
            clear_slot,
            get_organisation,
            invalidate_computed_state,
        )
        # Step 1: Disable demo mode flag FIRST — this prevents reinit
        set_demo_mode_enabled(False)
        log.info("Demo Mode disabled (demo_mode_enabled=False)")

        # Step 2: Clear demo data only if slot 0 has the demo org
        if slot == 0:
            org = get_organisation(slot=0)
            if org and org.get("is_demo"):
                clear_slot(0)
                invalidate_computed_state(slot=0)
                log.info("Demo data cleared from slot 0 — ready for real org setup")

    except Exception as exc:
        log.warning(f"exit_demo_mode failed: {exc}")


def get_demo_org_context() -> dict:
    """
    Return a safe summary of the demo context for UI display.
    All fields clearly labelled as demo.
    """
    return {
        "is_demo":          True,
        "company_name":     DEMO_ORG["company_name"],
        "sector":           DEMO_ORG["sector"],
        "reporting_period": DEMO_ORG["reporting_period"],
        "n_months":         len(DEMO_EMISSIONS_DATA["Month"]),
        "disclaimer":       "Demo Data — Not real organisational data",
    }


def is_demo_mode_active() -> bool:
    """Return True if the demo_mode_enabled flag is set in session. Service-layer wrapper."""
    try:
        from repository.session_repo import is_demo_mode_enabled
        return is_demo_mode_enabled()
    except Exception:
        return False


def enable_demo_mode() -> None:
    """Set demo_mode_enabled=True. Service-layer wrapper for app.py."""
    try:
        from repository.session_repo import set_demo_mode_enabled
        set_demo_mode_enabled(True)
    except Exception:
        pass


def flag_was_set() -> bool:
    """Return True if the demo_mode_enabled flag has been written this session."""
    try:
        from repository.session_repo import _DEMO_MODE_KEY
        import streamlit as st
        return _DEMO_MODE_KEY in st.session_state
    except Exception:
        return False
