"""
CarbonLens V7 — Design System
Primary: Light Blue (#0EA5E9) · Secondary: Slate Grey (#64748B)
Climate-tech investor aesthetic — clean, precise, data-forward.
"""

import streamlit as st


def inject_global_styles():
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
    :root {
        --cl-primary:       #0EA5E9;
        --cl-primary-dark:  #0284C7;
        --cl-primary-light: #E0F2FE;
        --cl-secondary:     #64748B;
        --cl-secondary-light: #F1F5F9;
        --cl-accent:        #06B6D4;
        --cl-accent2:       #6366F1;
        --cl-bg:            #F0F4F8;
        --cl-bg-dark:       #E2E8F0;
        --cl-card:          #FFFFFF;
        --cl-text:          #0F172A;
        --cl-muted:         #64748B;
        --cl-light:         #94A3B8;
        --cl-border:        #CBD5E1;
        --cl-border-light:  #E2E8F0;
        --cl-success:       #10B981;
        --cl-warning:       #F59E0B;
        --cl-danger:        #F43F5E;
        --cl-co2:           #F97316;
        --cl-radius:        12px;
        --cl-radius-sm:     8px;
        --cl-shadow:        0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04);
        --cl-shadow-md:     0 4px 16px rgba(15,23,42,0.08), 0 2px 4px rgba(15,23,42,0.04);
        --cl-shadow-blue:   0 4px 20px rgba(14,165,233,0.15), 0 1px 4px rgba(14,165,233,0.08);
    }

    *, *::before, *::after { box-sizing: border-box; }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background: var(--cl-bg) !important;
        color: var(--cl-text);
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, [data-testid="stDecoration"],
    [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"], [data-testid="stSidebarNav"],
    .stDeployButton { display: none !important; }

    [data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }

    /* ── Main content ── */
    section.main > div.block-container {
        padding: 1.5rem 2.5rem !important;
        max-width: 1440px !important;
    }

    /* ── Sidebar expand button ── */
    [data-testid="stExpandSidebarButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: #FFFFFF !important;
        border: 1.5px solid var(--cl-border) !important;
        border-radius: var(--cl-radius-sm) !important;
        box-shadow: var(--cl-shadow) !important;
    }
    [data-testid="stExpandSidebarButton"]:hover {
        background: var(--cl-primary-light) !important;
        border-color: var(--cl-primary) !important;
        box-shadow: var(--cl-shadow-blue) !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: var(--cl-card) !important;
        border: 1px solid var(--cl-border-light) !important;
        border-radius: var(--cl-radius) !important;
        padding: 16px 20px !important;
        box-shadow: var(--cl-shadow) !important;
        transition: box-shadow 0.2s, transform 0.15s !important;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--cl-shadow-blue) !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="stMetricLabel"] > div {
        font-size: 10px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        color: var(--cl-light) !important;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: var(--cl-text) !important;
        letter-spacing: -0.3px !important;
    }
    [data-testid="stMetricDelta"] > div {
        font-size: 11px !important;
        font-weight: 600 !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid var(--cl-border-light) !important;
        gap: 0 !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--cl-muted) !important;
        padding: 8px 18px !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -2px !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: var(--cl-primary) !important;
        border-bottom-color: var(--cl-primary) !important;
        font-weight: 600 !important;
    }

    /* ── Buttons ── */
    [data-testid="stButton"] > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        border-radius: var(--cl-radius-sm) !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stButton"] > button[kind="primary"] {
        background: var(--cl-primary) !important;
        border-color: var(--cl-primary) !important;
        color: white !important;
    }
    [data-testid="stButton"] > button[kind="primary"]:hover {
        background: var(--cl-primary-dark) !important;
        box-shadow: var(--cl-shadow-blue) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Form inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        font-family: 'Inter', sans-serif !important;
        border: 1.5px solid var(--cl-border) !important;
        border-radius: var(--cl-radius-sm) !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: var(--cl-primary) !important;
        box-shadow: 0 0 0 3px rgba(14,165,233,0.15) !important;
    }

    /* ── Select box ── */
    [data-baseweb="select"] {
        border-radius: var(--cl-radius-sm) !important;
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background: var(--cl-primary-light) !important;
        border: 2px dashed var(--cl-primary) !important;
        border-radius: var(--cl-radius) !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        border: 1px solid var(--cl-border-light) !important;
        border-radius: var(--cl-radius) !important;
        background: var(--cl-card) !important;
        box-shadow: var(--cl-shadow) !important;
    }

    /* ── Alerts ── */
    [data-testid="stAlert"] {
        border-radius: var(--cl-radius-sm) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
    }

    /* ── DataFrame ── */
    [data-testid="stDataFrame"] {
        border-radius: var(--cl-radius) !important;
        border: 1px solid var(--cl-border-light) !important;
        box-shadow: var(--cl-shadow) !important;
    }

    /* ── Plotly charts ── */
    .stPlotlyChart > div {
        border-radius: var(--cl-radius) !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--cl-border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--cl-secondary); }

    /* ── CarbonLens component classes ── */
    .cl-card {
        background: var(--cl-card);
        border: 1px solid var(--cl-border-light);
        border-radius: var(--cl-radius);
        padding: 20px;
        box-shadow: var(--cl-shadow);
        transition: box-shadow 0.2s;
    }
    .cl-card:hover { box-shadow: var(--cl-shadow-md); }

    .cl-card-header {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--cl-light);
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── Typography scale — mirrors config.settings.TYPO ──────────────────
       title=22/800  heading=15/700  body=12/400  caption=10/600
       value=22/700  label=10/700
       Used directly as utility classes, and to fix .cl-card-title /
       .cl-card-subtitle — adopted in 60+ / 55+ places across every page
       but previously had NO matching rule here, so they rendered as
       unstyled plain text. ── */
    .cl-text-title   { font-size: 22px; font-weight: 800; color: var(--cl-text); letter-spacing: -0.5px; }
    .cl-text-heading { font-size: 15px; font-weight: 700; color: var(--cl-text); }
    .cl-text-body    { font-size: 12px; font-weight: 400; color: var(--cl-muted); line-height: 1.6; }
    .cl-text-caption { font-size: 10px; font-weight: 600; color: var(--cl-light); text-transform: uppercase; letter-spacing: 0.6px; }
    .cl-text-value   { font-size: 22px; font-weight: 700; color: var(--cl-text); letter-spacing: -0.3px; }
    .cl-text-label   { font-size: 10px; font-weight: 700; color: var(--cl-light); text-transform: uppercase; letter-spacing: 0.8px; }

    .cl-card-title {
        font-size: 15px;
        font-weight: 700;
        color: var(--cl-text);
        margin-bottom: 2px;
        line-height: 1.4;
    }
    .cl-card-subtitle {
        font-size: 12px;
        font-weight: 400;
        color: var(--cl-light);
        margin-bottom: 12px;
        line-height: 1.5;
    }

    /* used once by esg_reporting.py as a print-style page wrapper */
    .cl-report-page { background: var(--cl-card); }

    .cl-stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
    }

    /* ── Company switcher chip ── */
    .cl-company-chip {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: var(--cl-radius-sm);
        border: 1.5px solid transparent;
        cursor: pointer;
        transition: all 0.12s;
        background: rgba(255,255,255,0.06);
        margin-bottom: 4px;
    }
    .cl-company-chip:hover {
        background: rgba(255,255,255,0.12);
        border-color: rgba(255,255,255,0.15);
    }
    .cl-company-chip.active {
        background: rgba(14,165,233,0.2);
        border-color: rgba(14,165,233,0.5);
    }
    .cl-company-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    /* ── Mobile responsive ── */
    @media screen and (max-width: 640px) {
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
        [data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {
            min-width: calc(50% - 8px) !important;
            flex: 0 0 calc(50% - 8px) !important;
        }
        section.main > div.block-container { padding: 0.75rem 1rem !important; }
    }
    @media screen and (max-width: 400px) {
        [data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {
            min-width: 100% !important;
            flex: 0 0 100% !important;
        }
    }

    /* ── Folium / streamlit-folium map — remove extra reserved whitespace ── */
    iframe[title="streamlit_folium.st_folium"] {
        display: block !important;
        margin-bottom: -8px !important;
    }
    div[data-testid="stCustomComponentV1"]:has(iframe[title="streamlit_folium.st_folium"]) {
        line-height: 0 !important;
        margin-bottom: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
