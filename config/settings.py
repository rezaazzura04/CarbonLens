"""
CarbonLens V7 — Settings
Typography scale, navigation groups, colors.
"""

# ── App page config (required by app.py at startup) ───────────────────────────
PAGE_CONFIG = {
    "page_title": "CarbonLens — Climate Intelligence Platform",
    "page_icon": "🌊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {"Get Help": None, "Report a bug": None,
                   "About": "CarbonLens V7 — Climate Intelligence Platform"},
}

# ── Typography Scale (3-size system — enforced across all components) ─────────
# heading  = 15px 700   → section titles, card titles
# body     = 12px 400   → body text, descriptions, table cells
# caption  = 10px 600   → labels, badges, uppercase meta
# value    = 22px 700   → KPI numbers, metrics
# title    = 22px 800   → page titles
# subtitle = 12px 400   → page subtitles
TYPO = {
    "title":    ("22px", "800"),
    "heading":  ("15px", "700"),
    "body":     ("12px", "400"),
    "caption":  ("10px", "600"),
    "value":    ("22px", "700"),
    "label":    ("10px", "700"),   # uppercase label
}

# ── Navigation — 4 clear groups ───────────────────────────────────────────────
NAVIGATION = [
    # CORE — every user starts here
    {"id": "profile",           "label": "Home",               "icon": "⌂",  "group": "Core"},
    {"id": "dashboard",         "label": "Dashboard",          "icon": "▦",  "group": "Core"},
    {"id": "esg_analytics",     "label": "ESG Analytics",      "icon": "◈",  "group": "Core"},
    {"id": "carbon_accounting", "label": "Carbon Accounting",  "icon": "◍",  "group": "Core"},
    # ANALYSIS — after data is loaded
    {"id": "ai_consultant",     "label": "AI Consultant",      "icon": "✦",  "group": "Analysis"},
    {"id": "ai_prediction",     "label": "AI Predictions",     "icon": "◎",  "group": "Analysis"},
    {"id": "scenario_sim",      "label": "Scenario Simulator", "icon": "⧖",  "group": "Analysis"},
    {"id": "benchmarking",      "label": "Benchmarking",       "icon": "◉",  "group": "Analysis"},
    {"id": "gis_intelligence",  "label": "GIS Intelligence",   "icon": "▣",  "group": "Analysis"},
    {"id": "historical",        "label": "Historical Trend",   "icon": "📅", "group": "Analysis"},
    # COMPLIANCE — regulatory & reporting
    {"id": "pojk_compliance",   "label": "POJK 51 / BRSR",     "icon": "📋", "group": "Compliance"},
    {"id": "gri_gap",           "label": "GRI Gap Analysis",   "icon": "📊", "group": "Compliance"},
    {"id": "supplier_scorecard","label": "Supplier Scorecard", "icon": "🏭", "group": "Compliance"},
    {"id": "consolidation",     "label": "Multi-Entity",       "icon": "🏢", "group": "Compliance"},
    # REPORTS — outputs
    {"id": "esg_reporting",     "label": "ESG Reporting",      "icon": "▤",  "group": "Reports"},
    {"id": "target_tracker",    "label": "Target Tracker",     "icon": "🎯", "group": "Reports"},
    {"id": "carbon_credit",     "label": "Carbon Credits",     "icon": "🌱", "group": "Reports"},
    {"id": "data_export",       "label": "Data Export",        "icon": "⬡",  "group": "Reports"},
    {"id": "alerts",            "label": "Alert Center",       "icon": "🔔", "group": "Reports"},
    # ADMIN
    {"id": "user_management",   "label": "User Management",    "icon": "👥", "group": "Admin"},
]

# ── Page accent colors ─────────────────────────────────────────────────────────
PAGE_COLORS = {
    "profile":           {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "dashboard":         {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "esg_analytics":     {"accent": "#6366F1", "light": "#EEF2FF"},
    "carbon_accounting": {"accent": "#10B981", "light": "#ECFDF5"},
    "ai_consultant":     {"accent": "#8B5CF6", "light": "#F5F3FF"},
    "ai_prediction":     {"accent": "#8B5CF6", "light": "#F5F3FF"},
    "scenario_sim":      {"accent": "#F97316", "light": "#FFF7ED"},
    "benchmarking":      {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "gis_intelligence":  {"accent": "#10B981", "light": "#ECFDF5"},
    "historical":        {"accent": "#6366F1", "light": "#EEF2FF"},
    "pojk_compliance":   {"accent": "#6366F1", "light": "#EEF2FF"},
    "gri_gap":           {"accent": "#10B981", "light": "#ECFDF5"},
    "supplier_scorecard":{"accent": "#F97316", "light": "#FFF7ED"},
    "consolidation":     {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "esg_reporting":     {"accent": "#0EA5E9", "light": "#E0F2FE"},
    "target_tracker":    {"accent": "#10B981", "light": "#ECFDF5"},
    "data_export":       {"accent": "#10B981", "light": "#ECFDF5"},
    "carbon_credit":     {"accent": "#10B981", "light": "#ECFDF5"},
    "alerts":            {"accent": "#F43F5E", "light": "#FFF1F2"},
    "user_management":   {"accent": "#64748B", "light": "#F1F5F9"},
}

# ── Global colors ─────────────────────────────────────────────────────────────
# Restored full key set (old pages reference info/success/etc.) + new aliases
# (neutral/surface/muted/subtle) kept for newer component code.
COLORS = {
    "primary":      "#0EA5E9",
    "primary_dark": "#0284C7",
    "primary_light":"#E0F2FE",
    "secondary":    "#6366F1",
    "secondary_light":"#EEF2FF",
    "accent":       "#10B981",
    "warning":      "#F97316",
    "danger":       "#F43F5E",
    "success":      "#10B981",
    "info":         "#38BDF8",
    "co2":          "#F97316",
    "green":        "#22C55E",
    "ocean":        "#0891B2",
    "neutral":      "#64748B",
    "bg":           "#F8FAFC",
    "bg_dark":      "#E2E8F0",
    "surface":      "#FFFFFF",
    "card":         "#FFFFFF",
    "border":       "#E2E8F0",
    "border_light": "#E2E8F0",
    "text":         "#0F172A",
    "muted":        "#64748B",
    "text_muted":   "#64748B",
    "subtle":       "#94A3B8",
    "text_light":   "#94A3B8",
}

# ── Plotly theme ──────────────────────────────────────────────────────────────
# Restored full key set (primary_color/gridcolor/paper_color/palette/font_size
# are used by ~10 chart call sites) + new grid_color alias.
PLOTLY_THEME = {
    "font_family":    "Inter, system-ui, sans-serif",
    "font_color":     "#374151",
    "font_size":      12,
    "bg_color":       "rgba(0,0,0,0)",
    "paper_color":    "rgba(0,0,0,0)",
    "gridcolor":      "#E2E8F0",
    "grid_color":     "#E2E8F0",
    "primary_color":  "#0EA5E9",
    "secondary_color":"#06B6D4",
    "palette": ["#0EA5E9","#06B6D4","#6366F1","#10B981","#F97316","#8B5CF6","#F43F5E","#64748B"],
}

# ── Industry benchmarks (kg CO2e / m² / yr) ───────────────────────────────────
# NOTE: kept on the original kg/m² scale + sector names — these are the keys
# referenced by PEER_DATA (benchmarking.py), get_benchmark(), and profile.py's
# sector dropdown. A 0–1.5 scale was tried here at one point but didn't match
# any other module's units, so it's reverted rather than left half-migrated.
INDUSTRY_BENCHMARKS = {
    "Office": 50, "University": 70, "Manufacturing": 120,
    "Hospital": 150, "Retail": 80, "Data Center": 200,
    "Hotel": 90, "Mining": 180, "F&B Processing": 110,
}

ESG_SCORE_BANDS = [
    {"min": 0,   "max": 20,  "grade": "D",  "label": "Critical",  "color": "#F43F5E"},
    {"min": 20,  "max": 40,  "grade": "C",  "label": "Poor",      "color": "#F97316"},
    {"min": 40,  "max": 60,  "grade": "B-", "label": "Moderate",  "color": "#F59E0B"},
    {"min": 60,  "max": 75,  "grade": "B+", "label": "Good",      "color": "#38BDF8"},
    {"min": 75,  "max": 90,  "grade": "A-", "label": "Very Good", "color": "#0EA5E9"},
    {"min": 90,  "max": 100, "grade": "A",  "label": "Excellent", "color": "#0284C7"},
]

# ─────────────────────────────────────────────────────────────────────────────
# EMISSION FACTORS
# Sources:
#   PLN: Keputusan Menteri ESDM No. 18 Tahun 2023 (effective 1 Jan 2024)
#   Diesel/Petrol/LPG: IPCC AR6 WG3 (2022) + Ministry of Energy Indonesia
#   Natural Gas: IPCC 2006 GL Vol.2 + PUIL 2011 conversion factors
# ─────────────────────────────────────────────────────────────────────────────
EMISSION_FACTORS = {
    # PLN National Grid — Kepmen ESDM 18/2023 (updated from 0.85 → 0.7160)
    "electricity_kgco2_per_kwh":       0.7160,

    # PLN Regional Subsystem EFs (Kepmen ESDM 18/2023, Appendix II)
    "electricity_java_bali_kgco2_per_kwh":   0.6900,  # Jawa-Bali (highest renewables share)
    "electricity_sumatra_kgco2_per_kwh":     0.7430,  # Sumatera
    "electricity_kalimantan_kgco2_per_kwh":  0.8200,  # Kalimantan (coal-heavy)
    "electricity_sulawesi_kgco2_per_kwh":    0.7050,  # Sulawesi
    "electricity_maluku_papua_kgco2_per_kwh":0.7800,  # Maluku & Papua
    "electricity_ntt_ntb_kgco2_per_kwh":     0.8500,  # NTT & NTB (most coal-dependent)

    # Direct combustion — IPCC AR6 + Ditjen EBTKE Kementerian ESDM (2023)
    "diesel_kgco2_per_liter":    2.68,   # Biosolar B35 blended — 2.68 kg CO2e/L
    "petrol_kgco2_per_liter":    2.31,   # Pertalite/Pertamax
    "lpg_kgco2_per_kg":          2.98,   # LPG 3kg / Bright Gas
    "natural_gas_kgco2_per_m3":  2.04,   # Pipeline gas (Pertamina Gas)
    "cng_kgco2_per_m3":          1.96,   # Compressed natural gas
    "coal_kgco2_per_kg":         2.42,   # Sub-bituminous coal (Kalimantan avg)
    "biomass_kgco2_per_kg":      0.00,   # IPCC biogenic — net zero per GHG Protocol
}

# PLN grid subsystem lookup by province
PLN_GRID_SUBSYSTEM = {
    "DKI Jakarta":          "electricity_java_bali_kgco2_per_kwh",
    "Jawa Barat":           "electricity_java_bali_kgco2_per_kwh",
    "Jawa Tengah":          "electricity_java_bali_kgco2_per_kwh",
    "Jawa Timur":           "electricity_java_bali_kgco2_per_kwh",
    "DIY Yogyakarta":       "electricity_java_bali_kgco2_per_kwh",
    "Banten":               "electricity_java_bali_kgco2_per_kwh",
    "Bali":                 "electricity_java_bali_kgco2_per_kwh",
    "Sumatera Utara":       "electricity_sumatra_kgco2_per_kwh",
    "Sumatera Barat":       "electricity_sumatra_kgco2_per_kwh",
    "Sumatera Selatan":     "electricity_sumatra_kgco2_per_kwh",
    "Riau":                 "electricity_sumatra_kgco2_per_kwh",
    "Lampung":              "electricity_sumatra_kgco2_per_kwh",
    "Aceh":                 "electricity_sumatra_kgco2_per_kwh",
    "Jambi":                "electricity_sumatra_kgco2_per_kwh",
    "Bengkulu":             "electricity_sumatra_kgco2_per_kwh",
    "Kepulauan Riau":       "electricity_sumatra_kgco2_per_kwh",
    "Bangka Belitung":      "electricity_sumatra_kgco2_per_kwh",
    "Kalimantan Timur":     "electricity_kalimantan_kgco2_per_kwh",
    "Kalimantan Selatan":   "electricity_kalimantan_kgco2_per_kwh",
    "Kalimantan Tengah":    "electricity_kalimantan_kgco2_per_kwh",
    "Kalimantan Barat":     "electricity_kalimantan_kgco2_per_kwh",
    "Kalimantan Utara":     "electricity_kalimantan_kgco2_per_kwh",
    "Sulawesi Selatan":     "electricity_sulawesi_kgco2_per_kwh",
    "Sulawesi Tengah":      "electricity_sulawesi_kgco2_per_kwh",
    "Sulawesi Utara":       "electricity_sulawesi_kgco2_per_kwh",
    "Sulawesi Tenggara":    "electricity_sulawesi_kgco2_per_kwh",
    "Gorontalo":            "electricity_sulawesi_kgco2_per_kwh",
    "Sulawesi Barat":       "electricity_sulawesi_kgco2_per_kwh",
    "Papua":                "electricity_maluku_papua_kgco2_per_kwh",
    "Papua Barat":          "electricity_maluku_papua_kgco2_per_kwh",
    "Maluku":               "electricity_maluku_papua_kgco2_per_kwh",
    "Maluku Utara":         "electricity_maluku_papua_kgco2_per_kwh",
    "Nusa Tenggara Timur":  "electricity_ntt_ntb_kgco2_per_kwh",
    "Nusa Tenggara Barat":  "electricity_ntt_ntb_kgco2_per_kwh",
    # 2022/2023 Papua province split — same subsystem as parent provinces
    "Papua Tengah":         "electricity_maluku_papua_kgco2_per_kwh",
    "Papua Pegunungan":     "electricity_maluku_papua_kgco2_per_kwh",
    "Papua Selatan":        "electricity_maluku_papua_kgco2_per_kwh",
    "Papua Barat Daya":     "electricity_maluku_papua_kgco2_per_kwh",
}

MAX_COMPANIES = 5
