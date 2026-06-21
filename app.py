"""
CarbonLens V7 — Climate Intelligence Platform
Run: streamlit run app.py
"""

import streamlit as st
from config.settings import PAGE_CONFIG, NAVIGATION
from components.sidebar import render_sidebar
from components.styles import inject_global_styles
import utils.state as S

st.set_page_config(**PAGE_CONFIG)
inject_global_styles()

import utils.auth as auth

# ── Authentication gate ────────────────────────────────────────────────────────
if not auth.is_authenticated():
    auth.login_page()
    st.stop()

# ── Auth header bar ────────────────────────────────────────────────────────────
user = auth.current_user()
if user:
    col_sp, col_user = st.columns([8, 1])
    with col_user:
        st.markdown(auth.user_badge_html(), unsafe_allow_html=True)
        if st.button("Sign out", key="logout_btn", use_container_width=True):
            auth.logout()

S.init()

active_page = render_sidebar(NAVIGATION)

PAGE_MAP = {
    "profile":           "_pages.profile",
    "dashboard":         "_pages.dashboard",
    "esg_analytics":     "_pages.esg_analytics",
    "ai_consultant":     "_pages.ai_consultant",
    "scenario_sim":      "_pages.scenario_sim",
    "ai_prediction":     "_pages.ai_prediction",
    "carbon_accounting": "_pages.carbon_accounting",
    "gis_intelligence":  "_pages.gis_intelligence",
    "benchmarking":      "_pages.benchmarking",
    "esg_reporting":     "_pages.esg_reporting",
    "target_tracker":    "_pages.target_tracker",
    "data_export":       "_pages.data_export",
    "carbon_credit":     "_pages.carbon_credit",
    "pojk_compliance":    "_pages.pojk_compliance",
    "alerts":             "_pages.alerts",
    "supplier_scorecard": "_pages.supplier_scorecard",
    "historical":         "_pages.historical",
    "gri_gap":            "_pages.gri_gap",
    "consolidation":      "_pages.consolidation",
    "user_management":    "_pages.user_management",
}

import importlib
mod = importlib.import_module(PAGE_MAP.get(active_page, "_pages.profile"))
mod.render()
