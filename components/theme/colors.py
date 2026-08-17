"""
CarbonLens V8 — Design colour palette.
Single source of truth for every colour used across components.
"""

# ── Core brand ────────────────────────────────────────────────────────────────
BRAND_DARK      = "#0F172A"   # Page titles, primary text
BRAND_ACCENT    = "#0EA5E9"   # Primary CTA, active nav, default KPI accent
BRAND_ACCENT_LT = "#E0F2FE"   # Accent background (chips, highlights)

# ── UI surface ────────────────────────────────────────────────────────────────
BG_PAGE         = "#F8FAFC"   # Page background (via st CSS injection)
BG_CARD         = "#FFFFFF"   # Card / panel background
BORDER          = "#E2E8F0"   # Card borders, dividers
BORDER_FOCUS    = "#CBD5E1"   # Focused input border

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY    = "#0F172A"
TEXT_SECONDARY  = "#475569"
TEXT_MUTED      = "#94A3B8"
TEXT_INVERSE    = "#FFFFFF"

# ── ESG pillar accents ────────────────────────────────────────────────────────
ENV_COLOR       = "#10B981"   # Environmental — green
ENV_LIGHT       = "#D1FAE5"
SOC_COLOR       = "#6366F1"   # Social — indigo
SOC_LIGHT       = "#EDE9FE"
GOV_COLOR       = "#F97316"   # Governance — orange
GOV_LIGHT       = "#FEF3C7"

PILLAR_COLORS = {
    "E": (ENV_COLOR, ENV_LIGHT),
    "S": (SOC_COLOR, SOC_LIGHT),
    "G": (GOV_COLOR, GOV_LIGHT),
}

# ── Grade colours ─────────────────────────────────────────────────────────────
GRADE_COLORS = {
    "A":  ("#059669", "#D1FAE5"),   # (text, background)
    "B+": ("#0891B2", "#CFFAFE"),
    "B":  ("#6366F1", "#EDE9FE"),
    "C":  ("#D97706", "#FEF3C7"),
    "D":  ("#DC2626", "#FEE2E2"),
}

def grade_color(grade: str) -> tuple:
    """Return (fg_hex, bg_hex) for a grade string."""
    return GRADE_COLORS.get(grade, ("#64748B", "#F1F5F9"))

# ── Status / semantic colours ─────────────────────────────────────────────────
SUCCESS         = "#059669"
SUCCESS_LIGHT   = "#D1FAE5"
WARNING         = "#D97706"
WARNING_LIGHT   = "#FEF3C7"
ERROR           = "#DC2626"
ERROR_LIGHT     = "#FEE2E2"
INFO            = "#0891B2"
INFO_LIGHT      = "#CFFAFE"
NEUTRAL         = "#64748B"
NEUTRAL_LIGHT   = "#F1F5F9"

SEMANTIC = {
    "success": (SUCCESS, SUCCESS_LIGHT),
    "warning": (WARNING, WARNING_LIGHT),
    "error":   (ERROR,   ERROR_LIGHT),
    "info":    (INFO,    INFO_LIGHT),
    "neutral": (NEUTRAL, NEUTRAL_LIGHT),
}

def semantic_color(variant: str) -> tuple:
    """Return (fg_hex, bg_hex) for a semantic variant."""
    return SEMANTIC.get(variant, SEMANTIC["neutral"])

# ── Confidence tiers ──────────────────────────────────────────────────────────
CONF_HIGH    = ("#059669", "#D1FAE5", "#6EE7B7")  # (text, bg, border) 80+
CONF_MED     = ("#0891B2", "#E0F2FE", "#7DD3FC")  # 60-79
CONF_LOW     = ("#D97706", "#FEF3C7", "#FDE68A")  # < 60 / provisional

def confidence_color(score: float, is_provisional: bool) -> tuple:
    """Return (text, bg, border) hex triple based on confidence score."""
    if is_provisional:
        return CONF_LOW
    if score >= 80:
        return CONF_HIGH
    if score >= 60:
        return CONF_MED
    return CONF_LOW

# ── Page accent map ───────────────────────────────────────────────────────────
PAGE_ACCENTS = {
    "executive_summary":    (BRAND_ACCENT,  BRAND_ACCENT_LT),
    "carbon_accounting":    (ENV_COLOR,     ENV_LIGHT),
    "esg_analytics":        (SOC_COLOR,     SOC_LIGHT),
    "data_quality":         (GOV_COLOR,     GOV_LIGHT),
    "reporting_compliance": (INFO,          INFO_LIGHT),
    "decarbonization":      ("#059669",     "#D1FAE5"),
    "governance":           ("#7C3AED",     "#EDE9FE"),
}

def page_accent(destination: str) -> tuple:
    """Return (accent_hex, light_hex) for a V8 destination."""
    return PAGE_ACCENTS.get(destination, (BRAND_ACCENT, BRAND_ACCENT_LT))
