"""
CarbonLens V8 — Platform-wide constants.

All threshold values, approved string lists, and fixed parameters live here.
No constant may be defined outside this module or config/settings.py.
"""

# ── Platform identity ─────────────────────────────────────────────────────────
PLATFORM_NAME    = "CarbonLens"
PLATFORM_VERSION = "V8"
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

# ── V8 destination IDs ────────────────────────────────────────────────────────
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
CURRENT_METHODOLOGY_VERSION = "V8-Phase4"

DEFAULT_DESTINATION = "executive_summary"
