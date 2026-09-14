"""CarbonLens — Layout grid, responsive breakpoints, and global CSS shell."""
MAX_CONTENT_WIDTH = "1200px"
SIDEBAR_WIDTH     = "248px"

# Column presets (Streamlit st.columns ratios)
COLS_2_EQUAL      = [1, 1]
COLS_3_EQUAL      = [1, 1, 1]
COLS_4_EQUAL      = [1, 1, 1, 1]
COLS_1_2          = [1, 2]
COLS_2_1          = [2, 1]
COLS_1_3          = [1, 3]
COLS_3_1          = [3, 1]
COLS_1_2_1        = [1, 2, 1]   # centred content

# KPI card column presets
COLS_KPI_4        = [1, 1, 1, 1]
COLS_KPI_3        = [1, 1, 1]
COLS_KPI_2        = [1, 1]

GLOBAL_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* ── CarbonLens design tokens ────────────────────────────────────────── */
  :root {
    --primary:          #037C38;
    --primary-dark:     #0F3D2E;
    --accent:           #B7D77A;
    --bg-page:          #F5F7F2;
    --bg-card:          #FFFFFF;
    --soft-green:       #E0EFE7;
    --text-primary:     #17221C;
    --text-secondary:   #66736B;
    --text-muted:       #8A968D;
    --border:           #DDE5DE;
    --warning:          #D89A3D;
    --critical:         #C65A5A;
    --info:             #3E7C8C;
    --font-brand: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-body:  'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }

  /* ── Base typography — Inter used throughout (headings + body) ─────────── */
  /* Bulletproof baseline: a universal selector guarantees every element
     inherits Inter regardless of Streamlit's internal DOM/class structure,
     which varies across versions and can silently break a class-substring
     selector like [class*="css"] if a build's CSS-in-JS engine stops
     emitting classnames containing that literal substring. Deliberately
     NOT !important — it's a fallback default, not an override, so it
     can never fight the specific rules below it or genuine inline
     font-family choices (e.g. the monospace timestamps/values further
     down this file) the way an !important universal rule would. */
  * {
    font-family: var(--font-body), -apple-system, BlinkMacSystemFont, sans-serif;
  }
  html, body, [class*="css"], .stMarkdown, .stText, p, span, div,
  table, td, th, input, textarea, select, button, label {
    font-family: var(--font-body), sans-serif !important;
  }
  h1, h2, h3 {
    font-family: var(--font-brand), sans-serif !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
  }
  /* Bug fix: the !important rule directly above matches bare div/span/p
     tags, which — being !important — was silently overriding every
     inline style="font-family:monospace" used for timestamps and
     numeric/technical values (Governance audit trail, Data Quality,
     Reporting, provenance panels: 10 call sites). An attribute selector
     carries higher specificity than a bare-tag selector, so this reliably
     wins even though both declarations are !important — verified against
     the CSS specification's cascade rules, not just tested by eye. */
  [style*="font-family:monospace"] {
    font-family: monospace !important;
  }

  /* ── Page shell — light background, no dark surfaces anywhere ───────────── */
  .stApp { background: var(--bg-page) !important; }
  .block-container { padding-top: 28px !important; max-width: 1240px; }

  /* ── Sidebar — dark green filled surface (the one deliberate dark
     surface in the app; see components/theme/colors.py SIDEBAR_* tokens
     for the rationale) ─────────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    background: var(--primary-dark) !important;
    border-right: none !important;
  }
  /* Overrides the light-sidebar "force everything to text-primary" rule
     that predates this redesign — on a dark fill that would render every
     sidebar text node in near-black, i.e. invisible. */
  [data-testid="stSidebar"] * { color: #FFFFFF; }

  /* Native widgets inside the sidebar (the organisation switcher
     selectbox, "Set up real organisation" button) still render with
     light-surface chrome by default — restyle them to sit naturally on
     the dark fill instead of appearing as jarring white boxes. */
  [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] [data-baseweb="select"] svg { fill: #FFFFFF !important; }
  [data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: #FFFFFF !important;
  }

  /* Streamlit's native icons (expander chevrons, sidebar-collapse toggle,
     etc.) render via a Material Symbols icon font. If that font fails to
     load — offline dev environments, corporate proxies/ad-blockers that
     block Google Fonts — the browser falls back to showing the raw icon
     name as text (e.g. "keyboard_arrow_right"). Constraining every such
     icon to a small fixed box with hidden overflow means a font-load
     failure can never surface broken fallback text, in any environment —
     this is a general robustness fix, not just a sandbox workaround. */
  [data-testid="stIconMaterial"] {
    font-size: 0 !important;
    width: 16px !important; height: 16px !important;
    display: inline-block !important; overflow: hidden !important;
  }

  /* ── Buttons — flat, no gradients, subtle lift on hover only ────────────── */
  .stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: var(--font-body) !important;
    border: 1px solid var(--border) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .stButton > button:hover {
    border-color: var(--primary) !important;
    box-shadow: 0 1px 4px rgba(47,107,79,0.14);
  }
  /* Sidebar nav buttons that stay a <button> after being clicked (i.e. the
     GIS shortcut row, which never switches to the styled "active" div —
     see components/sidebar_nav.py) can otherwise retain the browser's
     default post-click focus outline, which looks like an unintended
     half-active state. Replace it with the same calm border-color used on
     hover, so a clicked-but-still-flat row never looks visually broken. */
  [data-testid="stSidebar"] .stButton > button:focus,
  [data-testid="stSidebar"] .stButton > button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 1px var(--border) !important;
    border-color: var(--border) !important;
  }
  .stButton > button[kind="primary"] {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: var(--primary-dark) !important;
    border-color: var(--primary-dark) !important;
  }

  /* ── Alerts, expanders, inputs — flat surfaces, subtle borders only ─────── */
  .stAlert { border-radius: 10px !important; }
  [data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
  }
  [data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    font-family: var(--font-body) !important;
  }
  .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
    border-radius: 8px !important;
    border-color: var(--border) !important;
  }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
  .stTabs [data-baseweb="tab"] {
    font-family: var(--font-body) !important;
    font-weight: 600;
    color: var(--text-secondary);
  }
  .stTabs [aria-selected="true"] { color: var(--primary) !important; }

  /* ── Tables — enterprise-grade: subtle separators, no card wrapping ─────── */
  [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; }

  /* No gradients anywhere: this is a documentation marker, not executable —
     every background/box-shadow declaration above is a flat colour or a
     low-opacity single-colour shadow, never linear-/radial-gradient(). */
</style>
"""

def inject_global_css() -> None:
    """Inject CarbonLens global CSS into the Streamlit page. Call once in app.py."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
