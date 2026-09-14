"""
CarbonLens — Platform-wide constants.

All threshold values, approved string lists, and fixed parameters live here.
No constant may be defined outside this module or config/settings.py.
"""

# ── Platform identity ─────────────────────────────────────────────────────────
PLATFORM_NAME    = "CarbonLens"
PLATFORM_VERSION = "1.0"
PLATFORM_BUILD   = "Phase 4 · Production Foundation"

# ── Organisation slot management ─────────────────────────────────────────────
MAX_ORG_SLOTS = 5

PLACEHOLDER_NAMES: tuple[str, ...] = (
    "",
    "My Organization",
    "Your Organization",
    "Uploaded Organization",
    "Organisation",
)

# ── ESG confidence and provisional status ─────────────────────────────────────
CONFIDENCE_PROVISIONAL_FLOOR: float = 50.0
# Scores with ESG confidence below this threshold are labelled "Provisional".
# Source: Phase 0 C3 fix. Value requires Architecture Review Board approval to change.

# ── Outlier detection tiers ───────────────────────────────────────────────────
OUTLIER_REVIEW_Z: float = 2.0   # Z-score threshold for Data Quality REVIEW tier flag
OUTLIER_ALERT_Z:  float = 3.0   # Z-score threshold for Alerts & Anomalies tab

# ── Data Quality blending weights ─────────────────────────────────────────────
DQ_WEIGHT_COMPLETENESS: float = 0.40
DQ_WEIGHT_CONSISTENCY:  float = 0.35
DQ_WEIGHT_VALIDATION:   float = 0.25
# Must sum to 1.0. Source: Phase 2 implementation.

DQ_VALIDATION_SCORE_PASS:    float = 100.0
DQ_VALIDATION_SCORE_WARNING: float = 70.0
DQ_VALIDATION_SCORE_FAIL:    float = 0.0
DQ_CONFIDENCE_CAP_ON_FAIL:   float = 40.0

# ── ESG pillar weights ────────────────────────────────────────────────────────
ESG_WEIGHT_ENV:     float = 0.40
ESG_WEIGHT_SOCIAL:  float = 0.30
ESG_WEIGHT_GOV:     float = 0.30
# Source: Phase 0 C2 fix. GRI 2021 aligned. Must sum to 1.0.

# ── Social sub-indicator weights ──────────────────────────────────────────────
SOCIAL_WEIGHT_TURNOVER:   float = 0.25
SOCIAL_WEIGHT_TRAINING:   float = 0.25
SOCIAL_WEIGHT_DIVERSITY:  float = 0.25
SOCIAL_WEIGHT_SAFETY:     float = 0.25

# ── Governance sub-indicator weights ─────────────────────────────────────────
GOV_WEIGHT_BOARD_IND:     float = 0.25
GOV_WEIGHT_DISCLOSURE:    float = 0.20
GOV_WEIGHT_ETHICS:        float = 0.30
GOV_WEIGHT_BOARD_DIV:     float = 0.15
GOV_WEIGHT_CERTS:         float = 0.10

# ── Environmental sub-indicator weights ──────────────────────────────────────
ENV_WEIGHT_CARBON:    float = 0.45
ENV_WEIGHT_ENERGY:    float = 0.25
ENV_WEIGHT_WASTE:     float = 0.15
ENV_WEIGHT_WATER:     float = 0.15

# ── Scope 3 coverage declaration ─────────────────────────────────────────────
SCOPE3_CATEGORIES_COVERED:  int = 12
SCOPE3_CATEGORIES_TOTAL:    int = 15
SCOPE3_SCREENED_EXCLUDED: dict[str, str] = {
    "cat11": "Use of sold products — screened as not relevant (platform/service provider)",
    "cat14": "Franchises — screened as not relevant (non-franchise business model)",
    "cat15": "Investments — screened as not relevant (non-financial entity)",
}
# Source: Phase 0 H2 fix. GHG Protocol Corporate Value Chain Standard.

# ── S/G disclosure fields ─────────────────────────────────────────────────────
DISCLOSURE_FIELDS: tuple[str, ...] = (
    "water_recycled",
    "employee_turnover",
    "training_hours",
    "gender_diversity",
    "injury_rate",
    "board_independence",
    "board_diversity",
    "ethics_policies",
)
# 8 fields total. Confidence = n_disclosed / len(DISCLOSURE_FIELDS) * 100.

# ── Audit event taxonomy ──────────────────────────────────────────────────────
APPROVED_EVENT_TYPES: frozenset[str] = frozenset({
    # Phase 3 — original 13 types
    "user_login",
    "user_logout",
    "role_change",
    "user_created",
    "user_deleted",
    "data_uploaded",
    "carbon_recalculated",
    "esg_score_recalculated",
    "dq_score_recalculated",
    "report_exported",
    "pdf_generated",
    "quality_flag_actioned",
    "onboarding_completed",
    # Phase 5-A — Decarbonization Planner events
    "scenario_created",
    "scenario_modified",
    "scenario_saved",
    # Phase 5-C — Spatial / Land-Use Context events (Experimental)
    "gis_query_run",
})
MAX_AUDIT_SESSION_ENTRIES = 500
AUDIT_LOG_FILENAME        = "audit_log.jsonl"
AUDIT_LOG_MAX_BYTES       = 10 * 1024 * 1024  # 10 MB rotation threshold

# ── RBAC permissions ──────────────────────────────────────────────────────────
ALL_PERMISSIONS: frozenset[str] = frozenset({
    "can_upload",
    "can_export",
    "can_report",
    "can_manage_users",
    "can_edit_profile",
    "can_view_all",
})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin":   frozenset({
        "can_upload", "can_export", "can_report",
        "can_manage_users", "can_edit_profile", "can_view_all",
    }),
    "analyst": frozenset({"can_upload", "can_export", "can_view_all"}),
    "viewer":  frozenset({"can_view_all"}),
}

APPROVED_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS.keys())

# ── FlaggedField reason and severity taxonomy ─────────────────────────────────
APPROVED_FLAG_REASONS: frozenset[str] = frozenset({
    "missing", "out_of_range", "outlier", "estimated_default",
})
APPROVED_FLAG_SEVERITIES: frozenset[str] = frozenset({"high", "medium", "low"})

# ── Report section IDs ────────────────────────────────────────────────────────
APPROVED_REPORT_SECTIONS: frozenset[str] = frozenset({
    "executive_summary",
    "carbon_accounting",
    "esg_score",
    "data_quality",
    "benchmarking",
    "reporting_compliance",
    "methodology_appendix",
    "emission_factor_appendix",
    "audit_summary",
})
APPROVED_EXPORT_FORMATS: frozenset[str] = frozenset({"pdf", "csv", "excel", "json"})

# ── Scope source taxonomy ─────────────────────────────────────────────────────
APPROVED_SCOPE_SOURCES: frozenset[str] = frozenset({
    "carbon_accounting",
    "csv_scope_columns",
    "csv_estimate",
    "none",
})

# ── Validation result status ──────────────────────────────────────────────────
VALIDATION_PASS    = "Pass"
VALIDATION_WARNING = "Warning"
VALIDATION_FAIL    = "Fail"
APPROVED_VALIDATION_STATUSES: frozenset[str] = frozenset({
    VALIDATION_PASS, VALIDATION_WARNING, VALIDATION_FAIL,
})

# ── ComputedState lifecycle ───────────────────────────────────────────────────
STATE_STATUS_PROVISIONAL = "Provisional"
STATE_STATUS_SUBSTANTIVE = "Substantive"
STATE_STATUS_NO_DATA     = "No data"

# ── destination IDs ────────────────────────────────────────────────────────
APPROVED_DESTINATIONS: frozenset[str] = frozenset({
    "executive_summary",
    "carbon_accounting",
    "esg_analytics",
    "data_quality",
    "reporting_compliance",
    "decarbonization",
    "governance",
})

# ── Performance targets ───────────────────────────────────────────────────────
COMPUTATION_TIMEOUT_MS = 500    # Target max for full ComputedState assembly
PDF_GENERATION_TIMEOUT_S = 5    # Target max for full PDF with all appendices

# ── Methodology version tracking ─────────────────────────────────────────────
CURRENT_METHODOLOGY_VERSION = "Phase4"

DEFAULT_DESTINATION = "executive_summary"

# ── Phase 5-C — Spatial / Land-Use Context (Experimental) ─────────────────────
# GIS lives as a single opt-in tab inside Carbon Accounting, never a standalone
# nav destination, never called on initial page load (see services/gis_service.py
# and pages/carbon_accounting/page.py::_s8_spatial_context).

# Approximate provincial centroid coordinates (WGS84, decimal degrees).
# Used only as an approximate site location for illustrative spatial queries —
# NOT a precise facility coordinate. This is why the feature is labelled
# "Modelled estimate": a province-centroid buffer is a coarse proxy for an
# actual facility footprint, appropriate for an Experimental exploratory tab,
# not for a regulatory land-use disclosure.
PROVINCE_CENTROIDS: dict[str, tuple[float, float]] = {
    "Aceh": (4.6951, 96.7494), "Bali": (-8.4095, 115.1889),
    "Bangka Belitung": (-2.7411, 106.4406), "Banten": (-6.4058, 106.0640),
    "Bengkulu": (-3.7928, 102.2608), "DI Yogyakarta": (-7.7956, 110.3695),
    "DKI Jakarta": (-6.2088, 106.8456), "Gorontalo": (0.6999, 122.4467),
    "Jambi": (-1.6101, 103.6131), "Jawa Barat": (-6.9147, 107.6098),
    "Jawa Tengah": (-7.1510, 110.1403), "Jawa Timur": (-7.5361, 112.2384),
    "Kalimantan Barat": (-0.2787, 111.4753), "Kalimantan Selatan": (-3.0926, 115.2838),
    "Kalimantan Tengah": (-1.6815, 113.3824), "Kalimantan Timur": (0.5387, 116.4194),
    "Kalimantan Utara": (3.0731, 116.0414), "Kepulauan Riau": (3.9457, 108.1429),
    "Lampung": (-4.5586, 105.4068), "Maluku": (-3.2385, 130.1453),
    "Maluku Utara": (1.5709, 127.8087), "Nusa Tenggara Barat": (-8.6529, 117.3616),
    "Nusa Tenggara Timur": (-8.6574, 121.0794), "Papua": (-4.2699, 138.0804),
    "Papua Barat": (-1.3361, 133.1747), "Riau": (0.2933, 101.7068),
    "Sulawesi Barat": (-2.8441, 119.2321), "Sulawesi Selatan": (-3.6688, 119.9741),
    "Sulawesi Tengah": (-1.4300, 121.4456), "Sulawesi Tenggara": (-4.1449, 122.1746),
    "Sulawesi Utara": (0.6246, 123.9750), "Sumatera Barat": (-0.7399, 100.8000),
    "Sumatera Selatan": (-3.3194, 104.9147), "Sumatera Utara": (2.1154, 99.5451),
}

# NDVI → AGB proxy — HONESTLY relabeled (Fix C4). The original codebase this
# platform succeeds attributed this exact single-variable exponential form
# directly to Saatchi et al. (2011, PNAS), whose actual pantropical biomass
# map was fit via an ensemble of ICESat lidar + MODIS + QSCAT/SRTM texture +
# ancillary data — not a single-variable NDVI regression. That citation did
# not support the specific formula attached to it. This build keeps the same
# functional form (no independently-derived alternative is available without
# real calibration data) but relabels it accurately: a simplified proxy whose
# coefficients were chosen to fall within the broad biomass ranges Saatchi et
# al. report for tropical moist forest — not a reproduction of their model.
NDVI_AGB_PROXY_A: float = 3.8
NDVI_AGB_PROXY_B: float = -0.75
NDVI_AGB_PROXY_CITATION: str = (
    "Simplified single-variable NDVI-AGB proxy, coefficients chosen to fall "
    "within pantropical tropical-moist-forest biomass ranges reported in "
    "Saatchi et al. (2011, PNAS) — NOT a reproduction of their ensemble "
    "lidar/MODIS/SRTM regression. Treat as an illustrative order-of-magnitude "
    "estimate only, not a calibrated biomass measurement."
)
# NDVI saturates at moderate-to-high biomass/LAI (~3-4) — exactly the regime
# "tropical moist forest" sits in. Above this threshold the proxy is flagged
# as saturated/unreliable rather than silently returned as a precise figure.
NDVI_SATURATION_THRESHOLD: float = 0.80

# IPCC 2006 Guidelines for National GHG Inventories, Vol. 4, Ch. 4 default:
# above-ground biomass is ~47% carbon by dry mass.
BIOMASS_TO_CARBON_FACTOR: float = 0.47
# CO2/C molecular weight ratio (44.01 / 12.01) — standard conversion from
# carbon mass to CO2-equivalent mass.
CARBON_TO_CO2_RATIO: float = 44.0 / 12.0
