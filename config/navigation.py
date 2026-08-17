"""
CarbonLens V8 — Navigation configuration.

Single source of truth for all V8 destinations, tab definitions,
and route metadata. No page file may define its own route list.
"""

from config.settings import PAGE_COLORS


# ── V8 seven-destination route registry ──────────────────────────────────────

ROUTES: list[dict] = [
    {
        "id":       "executive_summary",
        "label":    "Executive Summary",
        "icon":     "◉",
        "tier":     "core",
        "accent":   PAGE_COLORS["executive_summary"]["accent"],
        "light":    PAGE_COLORS["executive_summary"]["light"],
        "module":   "pages.executive_summary.page",
    },
    {
        "id":       "carbon_accounting",
        "label":    "Carbon Accounting",
        "icon":     "◈",
        "tier":     "core",
        "accent":   PAGE_COLORS["carbon_accounting"]["accent"],
        "light":    PAGE_COLORS["carbon_accounting"]["light"],
        "module":   "pages.carbon_accounting.page",
    },
    {
        "id":       "esg_analytics",
        "label":    "ESG Analytics",
        "icon":     "◆",
        "tier":     "core",
        "accent":   PAGE_COLORS["esg_analytics"]["accent"],
        "light":    PAGE_COLORS["esg_analytics"]["light"],
        "module":   "pages.esg_analytics.page",
    },
    {
        "id":       "data_quality",
        "label":    "Data Quality",
        "icon":     "◇",
        "tier":     "core",
        "accent":   PAGE_COLORS["data_quality"]["accent"],
        "light":    PAGE_COLORS["data_quality"]["light"],
        "module":   "pages.data_quality.page",
    },
    {
        "id":       "reporting_compliance",
        "label":    "Reporting & Compliance",
        "icon":     "◎",
        "tier":     "core",
        "accent":   PAGE_COLORS["reporting_compliance"]["accent"],
        "light":    PAGE_COLORS["reporting_compliance"]["light"],
        "module":   "pages.reporting_compliance.page",
    },
    {
        "id":       "decarbonization",
        "label":    "Decarbonization",
        "icon":     "◐",
        "tier":     "advanced",
        "accent":   PAGE_COLORS["decarbonization"]["accent"],
        "light":    PAGE_COLORS["decarbonization"]["light"],
        "module":   "pages.decarbonization.page",
    },
    {
        "id":       "governance",
        "label":    "Governance & Audit",
        "icon":     "◑",
        "tier":     "core",
        "accent":   PAGE_COLORS["governance"]["accent"],
        "light":    PAGE_COLORS["governance"]["light"],
        "module":   "pages.governance.page",
    },
]

ROUTE_MAP: dict[str, dict] = {r["id"]: r for r in ROUTES}
DEFAULT_DESTINATION = "executive_summary"
ONBOARDING_DESTINATION = "onboarding"


def get_route(destination_id: str) -> dict:
    """Return route metadata for a destination ID. Raises KeyError if not found."""
    if destination_id not in ROUTE_MAP:
        raise KeyError(f"Unknown destination: {destination_id!r}")
    return ROUTE_MAP[destination_id]


def get_accent(destination_id: str) -> str:
    """Return the accent colour hex string for a destination. Falls back to default."""
    return ROUTE_MAP.get(destination_id, {}).get("accent", "#0EA5E9")


# ── Tab definitions per destination ──────────────────────────────────────────

CARBON_TABS: list[dict] = [
    {"id": "inventory",      "label": "Scope 1/2/3 Inventory"},
    {"id": "consolidation",  "label": "Multi-Entity Consolidation", "tier": "advanced"},
    {"id": "spatial",        "label": "GIS Intelligence",           "tier": "advanced"},
    {"id": "forecast",       "label": "Forecast",                   "tier": "advanced"},
]

ESG_TABS: list[dict] = [
    {"id": "scoring",        "label": "Scoring & Indicators"},
    {"id": "benchmarking",   "label": "Benchmarking"},
    {"id": "historical",     "label": "Historical Trends"},
    {"id": "supplier",       "label": "Supplier Scorecard",          "tier": "advanced"},
]

DATA_QUALITY_TABS: list[dict] = [
    {"id": "dashboard",      "label": "Quality Dashboard"},
    {"id": "alerts",         "label": "Alerts & Anomalies"},
]

REPORTING_TABS: list[dict] = [
    {"id": "gri",            "label": "GRI Disclosure Readiness"},
    {"id": "regulatory",     "label": "Regulatory Alignment"},
    {"id": "builder",        "label": "Report Builder"},
    {"id": "exports",        "label": "Exports"},
]

DECARB_TABS: list[dict] = [
    {"id": "planner",        "label": "Scenario & Target Planner"},
    {"id": "offsets",        "label": "Carbon Credits"},
]

GOVERNANCE_TABS: list[dict] = [
    {"id": "audit_trail",    "label": "Audit Trail"},
    {"id": "methodology",    "label": "Methodology Library"},
    {"id": "emission_factors","label": "Emission Factors"},
    {"id": "user_management","label": "User Management"},
]


def tab_labels(tab_list: list[dict]) -> list[str]:
    """Return display labels for a tab definition list."""
    return [t["label"] for t in tab_list]
