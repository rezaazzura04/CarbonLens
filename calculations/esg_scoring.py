"""
CarbonLens V8 — ESG pillar and sub-indicator scoring.
Pure functions. Phase 0 C1/C2 fix: sector-aware, weighted pillar model.
Source: GRI 2021 / SASB-aligned indicator mapping.
"""
from __future__ import annotations
import logging

log = logging.getLogger("carbonlens.calculations.esg_scoring")


# ── Environmental pillar ──────────────────────────────────────────────────────

def calculate_carbon_sub_score(intensity: float, benchmark: float) -> float:
    """
    Score carbon performance relative to sector benchmark (0–100).
    At or below benchmark → 100. At 2× benchmark → 0. Linear between.
    """
    if benchmark <= 0:
        return 0.0
    if intensity <= 0:
        return 100.0
    ratio = intensity / benchmark          # 1.0 = at benchmark
    score = max(0.0, 100.0 * (2.0 - ratio))   # 100 at ratio≤1, 0 at ratio≥2
    return round(min(100.0, score), 2)


def calculate_env_score(
    intensity_kg_m2:     float,
    benchmark:           float,
    renew_pct:           float,
    recycle_pct:         float,
    water_recycled_pct:  float,
) -> float:
    """
    Calculate Environmental pillar score (0–100).
    Sub-indicators: Carbon(45%), Energy(25%), Waste(15%), Water(15%).
    Source: Phase 0 C1 fix. GRI 305, 302, 306, 303.

    Parameters
    ----------
    intensity_kg_m2    : Carbon intensity (kg CO2e/m²/yr).
    benchmark          : Sector benchmark intensity (kg CO2e/m²/yr).
    renew_pct          : Renewable energy percentage (0–100).
    recycle_pct        : Waste recycling rate percentage (0–100).
    water_recycled_pct : Water recycling rate percentage (0–100).
    """
    from config.constants import ENV_WEIGHT_CARBON, ENV_WEIGHT_ENERGY, ENV_WEIGHT_WASTE, ENV_WEIGHT_WATER
    from calculations.utilities import clamp

    carbon_score = calculate_carbon_sub_score(intensity_kg_m2, benchmark)
    energy_score = clamp(renew_pct)
    waste_score  = clamp(recycle_pct)
    water_score  = clamp(water_recycled_pct)

    composite = (
        carbon_score * ENV_WEIGHT_CARBON +
        energy_score * ENV_WEIGHT_ENERGY +
        waste_score  * ENV_WEIGHT_WASTE  +
        water_score  * ENV_WEIGHT_WATER
    )
    return round(clamp(composite), 2)


# ── Social pillar ─────────────────────────────────────────────────────────────

def calculate_social_score(
    employee_turnover_pct:  float,
    training_hours_per_emp: float,
    women_workforce_pct:    float,
    injury_rate:            float,
) -> float:
    """
    Calculate Social pillar score (0–100).
    Sub-indicators: Retention(25%), Training(25%), Diversity(25%), Safety(25%).
    Source: Phase 0 C1 fix. GRI 401, 403, 404, 405.

    Parameters
    ----------
    employee_turnover_pct  : Annual employee turnover rate (%). Lower is better.
    training_hours_per_emp : Training hours per employee per year. Higher is better.
    women_workforce_pct    : Women in workforce percentage (0–100).
    injury_rate            : Work-related injuries per 100 workers. Lower is better.
    """
    from config.constants import (
        SOCIAL_WEIGHT_TURNOVER, SOCIAL_WEIGHT_TRAINING,
        SOCIAL_WEIGHT_DIVERSITY, SOCIAL_WEIGHT_SAFETY
    )
    from calculations.utilities import clamp

    # Turnover: 0% = 100, 20%+ = 0 (linear decay)
    turnover_score = clamp(100.0 - employee_turnover_pct * 5.0)

    # Training: 0h = 0, 40h = 100 (linear, capped at 100)
    training_score = clamp(training_hours_per_emp / 40.0 * 100.0)

    # Diversity: 50% women = 100, 0% = 0 (linear, capped)
    diversity_score = clamp(women_workforce_pct * 2.0)

    # Safety: 0 injuries = 100, 2+ per 100 = 0 (linear decay)
    safety_score = clamp(100.0 - injury_rate * 50.0)

    composite = (
        turnover_score  * SOCIAL_WEIGHT_TURNOVER  +
        training_score  * SOCIAL_WEIGHT_TRAINING  +
        diversity_score * SOCIAL_WEIGHT_DIVERSITY +
        safety_score    * SOCIAL_WEIGHT_SAFETY
    )
    return round(clamp(composite), 2)


# ── Governance pillar ─────────────────────────────────────────────────────────

def calculate_gov_score(
    board_independence_pct: float,
    disclosure_score:       float,
    has_code_of_conduct:    bool,
    women_board_pct:        float,
    certifications:         list,
) -> float:
    """
    Calculate Governance pillar score (0–100).
    Sub-indicators: BoardInd(25%), Disclosure(20%), Ethics(30%), BoardDiv(15%), Certs(10%).
    Source: Phase 0 C1 fix. GRI 2-9, 2-10, 205.

    Parameters
    ----------
    board_independence_pct : % of independent board directors.
    disclosure_score       : ESG disclosure completeness (0–100).
    has_code_of_conduct    : True if ethics/anti-corruption policy exists.
    women_board_pct        : Women on board percentage (0–100).
    certifications         : List of ESG/ISO certifications held.
    """
    from config.constants import (
        GOV_WEIGHT_BOARD_IND, GOV_WEIGHT_DISCLOSURE, GOV_WEIGHT_ETHICS,
        GOV_WEIGHT_BOARD_DIV, GOV_WEIGHT_CERTS
    )
    from calculations.utilities import clamp

    # Board independence: 50% = 100, linear
    board_ind_score = clamp(board_independence_pct * 2.0)

    # Disclosure: already 0–100 scale
    disclosure_s = clamp(disclosure_score)

    # Ethics: binary
    ethics_score = 100.0 if has_code_of_conduct else 0.0

    # Board diversity: 40% women = 100
    board_div_score = clamp(women_board_pct * 2.5)

    # Certifications: each adds 25 points, max 100
    cert_score = clamp(len(certifications) * 25.0)

    composite = (
        board_ind_score  * GOV_WEIGHT_BOARD_IND  +
        disclosure_s     * GOV_WEIGHT_DISCLOSURE +
        ethics_score     * GOV_WEIGHT_ETHICS     +
        board_div_score  * GOV_WEIGHT_BOARD_DIV  +
        cert_score       * GOV_WEIGHT_CERTS
    )
    return round(clamp(composite), 2)


# ── Composite ESG score ───────────────────────────────────────────────────────

def calculate_composite_esg_score(env: float, social: float, gov: float) -> float:
    """
    Calculate composite ESG score: E×0.40 + S×0.30 + G×0.30.
    Phase 0 C2 fix. Weights sourced from config.constants.
    """
    from config.constants import ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV
    from calculations.utilities import clamp
    score = env * ESG_WEIGHT_ENV + social * ESG_WEIGHT_SOCIAL + gov * ESG_WEIGHT_GOV
    return round(clamp(score), 2)


def assign_grade(score: float) -> tuple:
    """
    Assign ESG grade and label for a composite score.
    Phase 0 C2 fix. Bands from config.settings.ESG_SCORE_BANDS.

    Returns
    -------
    tuple : (grade: str, label: str)  e.g. ("B+", "Above Average")
    """
    from config.settings import ESG_SCORE_BANDS
    for band in ESG_SCORE_BANDS:
        if band["min"] <= score <= band["max"]:
            return band["grade"], band["label"]
    return "D", "Needs Improvement"


def score_indicator(value: float, lo: float, hi: float, inverse: bool = False) -> float:
    """
    Linearly map a raw indicator value to a 0–100 score.

    Parameters
    ----------
    value   : Raw indicator value.
    lo      : Value that maps to 0 (or 100 if inverse).
    hi      : Value that maps to 100 (or 0 if inverse).
    inverse : If True, higher raw value = lower score.
    """
    from calculations.utilities import clamp, safe_divide
    if hi == lo:
        return 0.0
    ratio = safe_divide(value - lo, hi - lo, default=0.0)
    score = (1.0 - ratio) * 100.0 if inverse else ratio * 100.0
    return clamp(score)
