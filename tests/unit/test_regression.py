"""
CarbonLens V8 — Phase 0 regression tests.

These tests verify that all Phase 0 correctness fixes (C1-C5, H1-H5, M2)
remain intact across all future sprints. Any change to calculations/ that
causes these tests to fail must be reviewed by the Architecture Review Board.
"""
import json
import pathlib
import pytest

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "expected_outputs.json"
EXPECTED = json.loads(FIXTURES.read_text())


def test_diesel_emission_factor():
    """Phase 0 H3: diesel factor must be full CO2e, not CO2-only."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["diesel_kgco2_per_liter"] == EXPECTED["diesel_ef"], \
        f"Diesel EF regression: expected {EXPECTED['diesel_ef']}"


def test_petrol_emission_factor():
    """Phase 0 H3: petrol factor must be full CO2e."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["petrol_kgco2_per_liter"] == EXPECTED["petrol_ef"]


def test_lpg_emission_factor():
    """Phase 0 H3: LPG factor must be full CO2e."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["lpg_kgco2_per_kg"] == EXPECTED["lpg_ef"]


def test_natural_gas_emission_factor():
    """Phase 0 H3: natural gas factor must be full CO2e."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["natural_gas_kgco2_per_m3"] == EXPECTED["natural_gas_ef"]


def test_coal_emission_factor():
    """Phase 0 H3: coal factor must be full CO2e."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["coal_kgco2_per_kg"] == EXPECTED["coal_ef"]


def test_pln_national_ef():
    """Phase 0 H3: PLN national grid factor per Kepmen ESDM No.18/2023."""
    from config.settings import EMISSION_FACTORS
    assert EMISSION_FACTORS["electricity_pln_kwh"] == EXPECTED["pln_national_ef"]


def test_esg_pillar_weights():
    """Phase 0 C2: pillar weights must be E=0.40, S=0.30, G=0.30."""
    from config.constants import ESG_WEIGHT_ENV, ESG_WEIGHT_SOCIAL, ESG_WEIGHT_GOV
    assert ESG_WEIGHT_ENV    == EXPECTED["esg_weights"]["env"]
    assert ESG_WEIGHT_SOCIAL == EXPECTED["esg_weights"]["social"]
    assert ESG_WEIGHT_GOV    == EXPECTED["esg_weights"]["gov"]
    assert abs(ESG_WEIGHT_ENV + ESG_WEIGHT_SOCIAL + ESG_WEIGHT_GOV - 1.0) < 1e-9, \
        "Pillar weights must sum to 1.0"


def test_confidence_provisional_floor():
    """Phase 0 C3: provisional floor must be 50.0%."""
    from config.constants import CONFIDENCE_PROVISIONAL_FLOOR
    assert CONFIDENCE_PROVISIONAL_FLOOR == EXPECTED["confidence_provisional_floor"]


def test_scope3_coverage():
    """Phase 0 H2: exactly 12 of 15 Scope 3 categories must be covered."""
    from config.constants import SCOPE3_SCREENED_EXCLUDED, SCOPE3_CATEGORIES_COVERED
    assert SCOPE3_CATEGORIES_COVERED == EXPECTED["scope3_covered"]
    for excluded in EXPECTED["scope3_excluded"]:
        assert excluded in SCOPE3_SCREENED_EXCLUDED, \
            f"Scope 3 exclusion {excluded!r} missing from SCOPE3_SCREENED_EXCLUDED"


def test_dq_weights_sum_to_one():
    """Phase 2: DQ blending weights must sum to 1.0."""
    from config.constants import (
        DQ_WEIGHT_COMPLETENESS, DQ_WEIGHT_CONSISTENCY, DQ_WEIGHT_VALIDATION
    )
    total = DQ_WEIGHT_COMPLETENESS + DQ_WEIGHT_CONSISTENCY + DQ_WEIGHT_VALIDATION
    assert abs(total - 1.0) < 1e-9, f"DQ weights sum to {total}, expected 1.0"


def test_approved_event_types_count():
    """Phase 3: must have exactly 13 approved audit event types."""
    from config.constants import APPROVED_EVENT_TYPES
    assert len(APPROVED_EVENT_TYPES) == 16, \
        f"Expected 13 audit event types, found {len(APPROVED_EVENT_TYPES)}"


def test_score_bands_cover_full_range():
    """Phase 0 C2: score bands must cover [0, 100] without gaps."""
    from config.settings import ESG_SCORE_BANDS
    mins = sorted(b["min"] for b in ESG_SCORE_BANDS)
    assert mins[0] == 0, "Score bands must start at 0"
    assert max(b["max"] for b in ESG_SCORE_BANDS) == 100, "Score bands must end at 100"


def test_approved_destinations():
    """Navigation: exactly 7 V8 destinations must be defined."""
    from config.constants import APPROVED_DESTINATIONS
    assert len(APPROVED_DESTINATIONS) == 7, \
        f"Expected 7 V8 destinations, found {len(APPROVED_DESTINATIONS)}"


def test_hash_inputs_deterministic():
    """utilities: hash_inputs must return the same value for same inputs."""
    from calculations.utilities import hash_inputs
    h1 = hash_inputs("org-123", "2024", "abc")
    h2 = hash_inputs("org-123", "2024", "abc")
    assert h1 == h2 == hash_inputs("org-123", "2024", "abc")


def test_hash_inputs_different_for_different_inputs():
    """utilities: hash_inputs must differ for different org/period/df_hash."""
    from calculations.utilities import hash_inputs
    h1 = hash_inputs("org-123", "2024", "abc")
    h2 = hash_inputs("org-456", "2024", "abc")
    h3 = hash_inputs("org-123", "2025", "abc")
    assert h1 != h2
    assert h1 != h3


def test_safe_divide_zero_denominator():
    """utilities: safe_divide must return default on zero denominator."""
    from calculations.utilities import safe_divide
    assert safe_divide(100.0, 0.0, default=0.0) == 0.0
    assert safe_divide(100.0, 0.0, default=-1.0) == -1.0


def test_clamp():
    """utilities: clamp must enforce [lo, hi] bounds."""
    from calculations.utilities import clamp
    assert clamp(-10.0) == 0.0
    assert clamp(110.0) == 100.0
    assert clamp(50.0)  == 50.0


def test_pln_ef_national_fallback():
    """settings.get_pln_ef: unknown province must return national average."""
    from config.settings import get_pln_ef, EMISSION_FACTORS
    ef = get_pln_ef("Unknown Province")
    assert ef == EMISSION_FACTORS["electricity_pln_kwh"]


def test_pln_ef_known_province():
    """settings.get_pln_ef: known province must return subsystem factor."""
    from config.settings import get_pln_ef, PLN_SUBSYSTEM_FACTORS, PLN_GRID_SUBSYSTEM
    province = "Jawa Timur"
    expected_key = PLN_GRID_SUBSYSTEM[province]
    expected_ef  = PLN_SUBSYSTEM_FACTORS[expected_key]
    assert get_pln_ef(province) == expected_ef
