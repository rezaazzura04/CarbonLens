"""CarbonLens V8 — Icon registry. All icons are Unicode characters."""
# Navigation
EXEC_SUMMARY   = "◉"
CARBON         = "◈"
ESG            = "◆"
DATA_QUALITY   = "◇"
REPORTING      = "◎"
DECARB         = "◐"
GOVERNANCE     = "◑"

# Status
CHECK          = "✓"
WARN           = "⚠"
ERROR_ICON     = "✕"
INFO_ICON      = "ℹ"
STAR           = "★"

# Trend
TREND_UP       = "↑"
TREND_DOWN     = "↓"
TREND_STABLE   = "→"
TREND_UNKNOWN  = "~"

TREND_ICONS = {
    "rising":             TREND_UP,
    "falling":            TREND_DOWN,
    "stable":             TREND_STABLE,
    "insufficient_data":  TREND_UNKNOWN,
}

# Pillars
ENV_ICON  = "🌱"
SOC_ICON  = "👥"
GOV_ICON  = "🏛"

PILLAR_ICONS = {"E": ENV_ICON, "S": SOC_ICON, "G": GOV_ICON}

# Grades
GRADE_ICONS = {"A": "★", "B+": "◆", "B": "◇", "C": "◌", "D": "○"}
