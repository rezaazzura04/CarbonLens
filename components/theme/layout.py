"""CarbonLens V8 — Layout grid and responsive breakpoint constants."""
MAX_CONTENT_WIDTH = "1200px"
SIDEBAR_WIDTH     = "240px"

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
  /* CarbonLens V8 global CSS injection */
  :root {
    --text-primary:   #0F172A;
    --text-secondary: #475569;
    --text-muted:     #94A3B8;
    --bg-card:        #FFFFFF;
    --border:         #E2E8F0;
    --accent:         #0EA5E9;
  }
  .block-container { padding-top: 24px !important; }
  [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
  .stButton > button { border-radius: 8px !important; font-weight: 600 !important; }
  .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(14,165,233,0.15); }
  h1, h2, h3 { color: #0F172A !important; }
  .stAlert { border-radius: 10px !important; }
  [data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 700 !important; }
</style>
"""

def inject_global_css() -> None:
    """Inject CarbonLens V8 global CSS into the Streamlit page. Call once in app.py."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
