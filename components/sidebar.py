"""
CarbonLens V7 — Sidebar
4-group navigation: Core / Analysis / Compliance / Reports / Admin
Clear visual grouping with group badges, core vs advanced indicators.
"""

import streamlit as st
from config.settings import PAGE_COLORS, NAVIGATION, MAX_COMPANIES
import utils.state as S

_SLOT_COLORS = ["#0EA5E9","#6366F1","#10B981","#F97316","#8B5CF6"]

GROUP_META = {
    "Core":       {"color": "#0EA5E9", "desc": "Start here"},
    "Analysis":   {"color": "#8B5CF6", "desc": "Deep dive"},
    "Compliance": {"color": "#10B981", "desc": "Regulatory"},
    "Reports":    {"color": "#F97316", "desc": "Outputs"},
    "Admin":      {"color": "#64748B", "desc": "Settings"},
}

def _hex_to_rgb(h: str) -> str:
    h = h.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}" if len(h)==6 else "14,165,233"

def _build_css(active_id: str) -> str:
    pc = PAGE_COLORS.get(active_id, PAGE_COLORS["profile"])
    rgb = _hex_to_rgb(pc["accent"])
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

section[data-testid="stSidebar"] {{
    background:#FFFFFF !important;
    border-right:1.5px solid #E2E8F0 !important;
    box-shadow:2px 0 20px rgba(14,165,233,0.06) !important;
    font-family:'Inter',sans-serif !important;
}}
section[data-testid="stSidebar"] > div {{ padding:0 !important; }}
section[data-testid="stSidebar"] * {{ font-family:'Inter',sans-serif !important; }}

/* ── Nav buttons base ── */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {{
    width:calc(100% - 16px) !important;
    padding:8px 14px !important;
    font-size:12px !important;
    font-weight:500 !important;
    text-align:left !important;
    justify-content:flex-start !important;
    border-radius:8px !important;
    border:1.5px solid transparent !important;
    background:transparent !important;
    color:#64748B !important;
    margin:1px 8px !important;
    letter-spacing:0.1px !important;
    box-shadow:none !important;
    transition:all 0.1s ease !important;
    line-height:1.3 !important;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
    background:#F0F9FF !important;
    color:#0284C7 !important;
    border-color:#BAE6FD !important;
}}

/* ── Active button ── */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {{
    background:{pc['accent']} !important;
    color:#FFFFFF !important;
    border-color:{pc['accent']} !important;
    font-weight:700 !important;
    box-shadow:0 2px 8px rgba({rgb},0.30) !important;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {{
    filter:brightness(1.05) !important;
    box-shadow:0 4px 12px rgba({rgb},0.40) !important;
}}

/* ── Company switcher ── */
section[data-testid="stSidebar"] .cl-co-active > div > button {{
    background:#EFF6FF !important; color:#0284C7 !important;
    border:1.5px solid #BFDBFE !important; font-weight:700 !important;
}}
section[data-testid="stSidebar"] .cl-co-inactive > div > button {{
    background:#F8FAFC !important; color:#94A3B8 !important;
    border:1.5px solid #E2E8F0 !important; font-size:11px !important;
}}
section[data-testid="stSidebar"] .cl-co-inactive > div > button:hover {{
    background:#EFF6FF !important; color:#0EA5E9 !important; border-color:#BAE6FD !important;
}}
section[data-testid="stSidebar"] .cl-co-add > div > button {{
    background:transparent !important; color:#94A3B8 !important;
    border:1.5px dashed #CBD5E1 !important; font-size:11px !important;
}}
section[data-testid="stSidebar"] .cl-co-add > div > button:hover {{
    background:#EFF6FF !important; color:#0EA5E9 !important;
    border-color:#0EA5E9 !important; border-style:solid !important;
}}

/* ── Group header (now a clickable accordion toggle) ── */
.cl-nav-group-wrap {{
    padding:14px 16px 3px;
    display:flex; align-items:center; gap:7px;
}}
.cl-nav-group-dot {{
    width:5px; height:5px; border-radius:50%; flex-shrink:0;
}}
.cl-nav-group-label {{
    font-size:9px; font-weight:700; text-transform:uppercase;
    letter-spacing:1.4px; color:#CBD5E1;
}}
.cl-nav-group-desc {{
    font-size:9px; color:#E2E8F0; margin-left:auto;
    font-weight:500; letter-spacing:0.3px;
}}

.cl-nav-group-btn {{ margin-top:6px; }}
.cl-nav-group-btn > div > button {{
    width:calc(100% - 16px) !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:6px 14px !important;
    margin:0 8px !important;
    font-size:9px !important;
    font-weight:700 !important;
    text-transform:uppercase !important;
    letter-spacing:1.4px !important;
    color:#94A3B8 !important;
    text-align:left !important;
    justify-content:flex-start !important;
    border-radius:6px !important;
}}
.cl-nav-group-btn > div > button:hover {{
    background:#F8FAFC !important;
    color:#475569 !important;
}}
.cl-nav-group-btn-active > div > button {{ color:#0F172A !important; }}

.cl-divider {{ height:1px; background:#F1F5F9; margin:4px 0; }}

[data-testid="stExpandSidebarButton"] {{
    display:flex !important; visibility:visible !important;
    background:#FFFFFF !important; border:1.5px solid #CBD5E1 !important;
    border-radius:8px !important; box-shadow:0 2px 6px rgba(14,165,233,0.08) !important;
}}
[data-testid="stExpandSidebarButton"]:hover {{
    background:#EFF6FF !important; border-color:#0EA5E9 !important;
}}
</style>
"""

def render_sidebar(navigation: list) -> str:
    S.init()
    if "active_page" not in st.session_state:
        st.session_state.active_page = "profile"

    active_id   = st.session_state.active_page
    active_slot = S.get_active_slot()
    companies   = S.get_company_summary()
    has_data    = S.get("uploaded_df") is not None
    company     = S.get("company_name", "")
    esg_grade   = S.get("esg_grade", "—")
    esg_score   = S.get("esg_score", 0)
    pc          = PAGE_COLORS.get(active_id, PAGE_COLORS["profile"])

    # ── Gated pages (need data) ───────────────────────────────────────────────
    gated = {"dashboard","ai_prediction","esg_reporting","ai_consultant",
             "scenario_sim","benchmarking","target_tracker","data_export"}

    with st.sidebar:
        st.markdown(_build_css(active_id), unsafe_allow_html=True)

        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="padding:18px 16px 14px;border-bottom:1.5px solid #F1F5F9;">
            <div style="display:flex;align-items:center;gap:11px;">
                <div style="width:38px;height:38px;flex-shrink:0;
                     background:linear-gradient(135deg,#0284C7,{pc['accent']});
                     border-radius:11px;display:flex;align-items:center;justify-content:center;
                     font-size:20px;box-shadow:0 3px 12px rgba(14,165,233,0.25);">🌊</div>
                <div>
                    <div style="font-size:15px;font-weight:800;color:#0F172A;letter-spacing:-0.4px;">
                        CarbonLens</div>
                    <div style="font-size:9px;color:#94A3B8;letter-spacing:1.4px;
                         text-transform:uppercase;font-weight:600;">V7 · Climate Intelligence</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Company switcher — collapsible ───────────────────────────────────
        any_setup = any(co["setup"] for co in companies)
        if "org_panel_open" not in st.session_state:
            st.session_state["org_panel_open"] = any_setup  # collapsed by default kalau kosong semua

        org_open    = st.session_state["org_panel_open"]
        org_chevron = "▾" if org_open else "▸"
        active_co   = next((co for co in companies if co["slot"] == active_slot and co["setup"]), None)
        org_summary = f"  ·  {active_co['name'][:18]}" if active_co else "  ·  No org"

        st.markdown('<div class="cl-nav-group-btn">', unsafe_allow_html=True)
        if st.button(f"{org_chevron}  Organizations{org_summary}", key="org_panel_toggle",
                     use_container_width=True):
            st.session_state["org_panel_open"] = not org_open
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if org_open:
            for co in companies:
                slot      = co["slot"]
                is_active = (slot == active_slot)
                if co["setup"]:
                    grade_str = f" · {co['grade']}" if co["grade"] != "—" else ""
                    label     = f"{'●' if is_active else '○'}  {co['name'][:20]}{'…' if len(co['name'])>20 else ''}{grade_str}"
                    wrap_cls  = "cl-co-active" if is_active else "cl-co-inactive"
                else:
                    label    = f"＋  Add Organization {slot+1}"
                    wrap_cls = "cl-co-add"
                st.markdown(f'<div class="{wrap_cls}">', unsafe_allow_html=True)
                if st.button(label, key=f"co_switch_{slot}", use_container_width=True):
                    S.set_active_slot(slot)
                    st.session_state.active_page = "profile"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # ── Data status pill ──────────────────────────────────────────────────
        if has_data and company:
            score_color = "#10B981" if esg_score >= 70 else "#F59E0B" if esg_score >= 50 else "#F43F5E"
            st.markdown(f"""
            <div style="margin:8px 12px;background:#F0F9FF;border:1.5px solid #BAE6FD;
                 border-radius:10px;padding:8px 12px;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:7px;height:7px;background:#10B981;border-radius:50%;
                             box-shadow:0 0 0 2px rgba(16,185,129,0.2);"></div>
                        <span style="font-size:10px;font-weight:700;color:#0284C7;">Data Active</span>
                    </div>
                    <div style="background:{score_color};color:white;font-size:9px;font-weight:800;
                         padding:2px 7px;border-radius:20px;">{esg_grade}</div>
                </div>
                <div style="font-size:10px;color:#64748B;margin-top:2px;overflow:hidden;
                     text-overflow:ellipsis;white-space:nowrap;">{company}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="margin:8px 12px;background:#F8FAFC;border:1.5px solid #E2E8F0;
                 border-radius:10px;padding:8px 12px;display:flex;align-items:center;gap:8px;">
                <div style="width:7px;height:7px;background:#CBD5E1;border-radius:50%;"></div>
                <div>
                    <div style="font-size:10px;font-weight:600;color:#94A3B8;">No data uploaded</div>
                    <div style="font-size:9px;color:#CBD5E1;">Upload in ESG Analytics →</div>
                </div>
            </div>""", unsafe_allow_html=True)

        # ── Session persistence warning ──────────────────────────────────────
        st.markdown("""
        <div style="margin:6px 12px 2px;background:#FFFBEB;border:1px solid #FDE68A;
             border-radius:8px;padding:7px 10px;">
            <div style="font-size:9px;font-weight:700;color:#92400E;margin-bottom:2px;">
                ⚠️ Session-based storage
            </div>
            <div style="font-size:9px;color:#78350F;line-height:1.5;">
                Data resets on browser close or server restart.
                Download your results (Data Export) before closing.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="cl-divider"></div>', unsafe_allow_html=True)

        # ── Navigation — collapsible groups (accordion) ─────────────────────────
        # Group items while preserving first-seen order, so NAVIGATION stays the
        # single source of truth for both grouping and display order.
        groups_order: list = []
        items_by_group: dict = {}
        for item in navigation:
            g = item.get("group", "")
            if g not in items_by_group:
                items_by_group[g] = []
                groups_order.append(g)
            items_by_group[g].append(item)

        active_group = next((g for g in groups_order if any(
            it["id"] == active_id for it in items_by_group[g])), groups_order[0] if groups_order else "")

        # The group containing the active page always wins on load / after a
        # page switch, so the current page can never end up hidden inside a
        # collapsed group.
        if (st.session_state.get("nav_expanded_group") != active_group
                and st.session_state.get("_nav_last_active_id") != active_id):
            st.session_state["nav_expanded_group"] = active_group
        st.session_state["_nav_last_active_id"] = active_id
        expanded_group = st.session_state.get("nav_expanded_group", active_group)

        for group in groups_order:
            gm    = GROUP_META.get(group, {"color": "#94A3B8", "desc": ""})
            items = items_by_group[group]
            is_open = (group == expanded_group)
            chevron = "▾" if is_open else "▸"

            btn_cls = "cl-nav-group-btn-active" if is_open else ""
            st.markdown(f'<div class="cl-nav-group-btn {btn_cls}">', unsafe_allow_html=True)
            if st.button(f"{chevron}  {group}  ·  {gm['desc']}", key=f"navgroup_{group}",
                         use_container_width=True):
                st.session_state["nav_expanded_group"] = group
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            if not is_open:
                continue

            for item in items:
                pid    = item["id"]
                is_act = (active_id == pid)
                locked = pid in gated and not has_data and not is_act
                label  = f"{item['icon']}  {item['label']}" + (" 🔒" if locked else "")

                if st.button(label, key=f"nav_{pid}", use_container_width=True,
                             type="primary" if is_act else "secondary"):
                    st.session_state.active_page = pid
                    st.rerun()

        # ── Footer ────────────────────────────────────────────────────────────
        st.markdown('<div class="cl-divider" style="margin-top:8px;"></div>', unsafe_allow_html=True)
        org     = company if company else "No organization"
        initial = org[0].upper()
        slot_c  = _SLOT_COLORS[active_slot % len(_SLOT_COLORS)]
        sector  = S.get("sector", "—")

        st.markdown(f"""
        <div style="padding:8px 12px 16px;">
            <div style="display:flex;align-items:center;gap:9px;margin-bottom:6px;">
                <div style="width:30px;height:30px;background:{slot_c};border-radius:50%;
                     display:flex;align-items:center;justify-content:center;
                     font-size:12px;font-weight:800;color:white;flex-shrink:0;">{initial}</div>
                <div style="overflow:hidden;">
                    <div style="font-size:11px;font-weight:600;color:#0F172A;white-space:nowrap;
                         overflow:hidden;text-overflow:ellipsis;">{org}</div>
                    <div style="font-size:9px;color:#94A3B8;">Slot {active_slot+1} · {sector}</div>
                </div>
            </div>
            <div style="font-size:8px;color:#CBD5E1;text-align:center;letter-spacing:0.5px;">
                CARBONLENS V7 · CLIMATE INTELLIGENCE
            </div>
        </div>
        """, unsafe_allow_html=True)

    return active_id
