"""
CarbonLens — Design colour palette.
Single source of truth for every colour used across components.

Brand system (light-first page canvas; a single deliberate dark-green
surface is used for the sidebar as a brand choice, not OS-dark-mode
theming — the app still ignores the OS/browser light-dark preference
entirely, per the original "no dark UI" requirement):
  Primary        #037C38   Primary Dark   #0F3D2E
  Accent         #B7D77A   Background     #F5F7F2
  Surface        #FFFFFF   Soft Green     #E0EFE7
  Primary Text   #17221C   Secondary Text #66736B
  Border         #DDE5DE   Warning        #D89A3D
  Critical       #C65A5A   Information    #3E7C8C (restrained teal)

Every name below is preserved from the previous palette so no import
breaks — only the underlying hex VALUES changed for the brand redesign.
"""

# ── Core brand ────────────────────────────────────────────────────────────────
BRAND_DARK      = "#17221C"   # Page titles, primary text
BRAND_ACCENT    = "#037C38"   # Primary CTA, active nav, default KPI accent
BRAND_ACCENT_LT = "#E0EFE7"   # Accent background (chips, highlights)
BRAND_PRIMARY_DARK = "#0F3D2E"
BRAND_LIME      = "#B7D77A"   # Secondary accent — used sparingly (never as a base UI color)
ACCENT_ORANGE   = "#F47C2B"   # Decorative highlight accent (notification dot, chart highlight
                              # segment) — distinct from WARNING below: not every orange use is
                              # a semantic "needs attention" state, so this is kept separate
                              # rather than overloading WARNING for purely decorative accents.

# ── Sidebar (dark surface) ──────────────────────────────────────────────────
# The ONLY dark-filled surface in the app. Light-on-dark equivalents of the
# TEXT_PRIMARY/TEXT_MUTED/BORDER tokens below, used exclusively inside
# components/sidebar_nav.py — never reference these outside the sidebar,
# since every other surface in CarbonLens is light per the brand rule above.
SIDEBAR_BG          = BRAND_PRIMARY_DARK
SIDEBAR_ACTIVE_BG   = "#1B5A43"   # Lighter than SIDEBAR_BG so the active pill visibly lifts off it
SIDEBAR_TEXT        = "#FFFFFF"
SIDEBAR_TEXT_MUTED  = "#9FC2AE"   # Muted light green — kept >= 4.5:1 contrast against SIDEBAR_BG
SIDEBAR_BORDER      = "rgba(255,255,255,0.14)"


# ── UI surface ────────────────────────────────────────────────────────────────
BG_PAGE         = "#F5F7F2"   # Page background (via st CSS injection)
BG_CARD         = "#FFFFFF"   # Card / panel background
BORDER          = "#DDE5DE"   # Card borders, dividers
BORDER_FOCUS    = "#B7D77A"   # Focused input border

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY    = "#17221C"
TEXT_SECONDARY  = "#66736B"
TEXT_MUTED      = "#8A968D"
TEXT_INVERSE    = "#FFFFFF"

# ── ESG pillar accents ────────────────────────────────────────────────────────
# E = the core brand green (environmental IS the brand identity here).
# S = the restrained information teal (visually distinct from green/lime).
# G = the deeper primary-dark shade (conveys authority, stays in-family).
ENV_COLOR       = "#037C38"   # Environmental
ENV_LIGHT       = "#E0EFE7"
SOC_COLOR       = "#3E7C8C"   # Social
SOC_LIGHT       = "#E3EEF0"
GOV_COLOR       = "#0F3D2E"   # Governance
GOV_LIGHT       = "#DDE7E1"

PILLAR_COLORS = {
    "E": (ENV_COLOR, ENV_LIGHT),
    "S": (SOC_COLOR, SOC_LIGHT),
    "G": (GOV_COLOR, GOV_LIGHT),
}

# ── Grade colours ─────────────────────────────────────────────────────────────
GRADE_COLORS = {
    "A":  ("#037C38", "#E0EFE7"),   # (text, background)
    "B+": ("#3E7C8C", "#E3EEF0"),
    "B":  ("#6E9B7F", "#EDF3EA"),
    "C":  ("#D89A3D", "#FBF1DF"),
    "D":  ("#C65A5A", "#FBE8E6"),
}

def grade_color(grade: str) -> tuple:
    """Return (fg_hex, bg_hex) for a grade string."""
    return GRADE_COLORS.get(grade, ("#66736B", "#F0F2EE"))

# ── Status / semantic colours ─────────────────────────────────────────────────
SUCCESS         = "#037C38"
SUCCESS_LIGHT   = "#E0EFE7"
WARNING         = "#D89A3D"
WARNING_LIGHT   = "#FBF1DF"
ERROR           = "#C65A5A"
ERROR_LIGHT     = "#FBE8E6"
INFO            = "#3E7C8C"
INFO_LIGHT      = "#E3EEF0"
NEUTRAL         = "#66736B"
NEUTRAL_LIGHT   = "#F0F2EE"

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
CONF_HIGH    = ("#037C38", "#E0EFE7", "#B7D77A")  # (text, bg, border) 80+
CONF_MED     = ("#3E7C8C", "#E3EEF0", "#9CC3CC")  # 60-79
CONF_LOW     = ("#D89A3D", "#FBF1DF", "#EBC684")  # < 60 / provisional

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
    "data_quality":         (WARNING,       WARNING_LIGHT),
    "reporting_compliance": (INFO,          INFO_LIGHT),
    "decarbonization":      (BRAND_ACCENT,  BRAND_ACCENT_LT),
    "governance":           (GOV_COLOR,     GOV_LIGHT),
}

def page_accent(destination: str) -> tuple:
    """Return (accent_hex, light_hex) for a destination."""
    return PAGE_ACCENTS.get(destination, (BRAND_ACCENT, BRAND_ACCENT_LT))

# ── Chart series palette (see brief "Chart System") ───────────────────────────
CHART_PRIMARY   = "#037C38"
CHART_SECONDARY = "#6E9B7F"
CHART_ACCENT    = "#B7D77A"
CHART_NEUTRAL   = "#AAB5AE"
CHART_WARNING   = "#D89A3D"
CHART_CRITICAL  = "#C65A5A"
CHART_INFO      = "#3E7C8C"
CHART_SERIES = [CHART_PRIMARY, CHART_INFO, CHART_ACCENT, CHART_SECONDARY, CHART_WARNING]
