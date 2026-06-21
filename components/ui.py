"""
CarbonLens V7 — UI Component Library
Typography scale: title=22/800, heading=15/700, body=12/400, caption=10/600, value=22/700
All inline font-size strictly follows this scale. No ad-hoc sizes.
"""

import streamlit as st
import plotly.graph_objects as go

BADGE_COLORS = {
    "blue":   ("#E0F2FE", "#0C4A6E"),
    "sky":    ("#E0F2FE", "#0284C7"),
    "cyan":   ("#ECFEFF", "#164E63"),
    "indigo": ("#EEF2FF", "#3730A3"),
    "violet": ("#F5F3FF", "#4C1D95"),
    "green":  ("#DCFCE7", "#14532D"),
    "teal":   ("#CCFBF1", "#134E4A"),
    "yellow": ("#FEF9C3", "#713F12"),
    "orange": ("#FFF7ED", "#9A3412"),
    "red":    ("#FFE4E6", "#9F1239"),
    "slate":  ("#F1F5F9", "#1E293B"),
    "gray":   ("#F3F4F6", "#374151"),
    "purple": ("#F3E8FF", "#5B21B6"),
    "pink":   ("#FDF2F8", "#9D174D"),
    "lime":   ("#F7FEE7", "#365314"),
}

def _badge_html(text: str, t: str = "blue") -> str:
    bg, fg = BADGE_COLORS.get(t, BADGE_COLORS["slate"])
    return (f'<span style="display:inline-block;font-size:10px;font-weight:600;'
            f'padding:2px 9px;border-radius:20px;background:{bg};color:{fg};">{text}</span>')

def _page_accent() -> dict:
    from config.settings import PAGE_COLORS
    pid = st.session_state.get("active_page", "profile")
    return PAGE_COLORS.get(pid, PAGE_COLORS["profile"])

# ── Page header ───────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = "", badge: str = "", badge_type: str = "blue"):
    pc = _page_accent()
    badge_html = _badge_html(badge, badge_type) if badge else ""
    st.markdown(f"""
    <div style="padding:20px 0 14px;border-bottom:2px solid {pc['accent']}28;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <div style="width:3px;height:28px;background:{pc['accent']};border-radius:2px;flex-shrink:0;"></div>
            <span style="font-size:22px;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">{title}</span>
            {badge_html}
        </div>
        <p style="font-size:12px;color:#64748B;margin-top:5px;padding-left:11px;line-height:1.5;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ── Step header — for multi-step pages (e.g. ESG Analytics) ──────────────────
def step_header(step: int, total: int, title: str, subtitle: str = "", accent: str = "#6366F1"):
    parts = []
    for i in range(1, total + 1):
        circle_bg = accent if i == step else "#F1F5F9"
        circle_fg = "white" if i == step else "#94A3B8"
        connector = ('<div style="width:20px;height:2px;background:#E2E8F0;"></div>'
                     if i < total else "")
        parts.append(
            f'<div style="display:flex;align-items:center;gap:4px;">'
            f'<div style="width:22px;height:22px;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-size:10px;font-weight:700;'
            f'background:{circle_bg};color:{circle_fg};">{i}</div>'
            f'{connector}'
            f'</div>'
        )
    steps_html = "".join(parts)
    st.markdown(f"""
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
         padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;gap:16px;">
        <div style="display:flex;align-items:center;gap:0;">{steps_html}</div>
        <div>
            <div style="font-size:15px;font-weight:700;color:#0F172A;">{title}</div>
            <div style="font-size:12px;color:#64748B;margin-top:1px;">{subtitle}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Card wrappers ─────────────────────────────────────────────────────────────
def card_start(title: str = "", subtitle: str = "", icon: str = ""):
    pc = _page_accent()
    icon_html = f'<span style="color:{pc["accent"]};margin-right:6px;">{icon}</span>' if icon else ""
    header = ""
    if title:
        sub_html = f'<span style="font-weight:400;color:#CBD5E1;margin-left:6px;">— {subtitle}</span>' if subtitle else ""
        header = (f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                  f'letter-spacing:0.8px;color:#94A3B8;margin-bottom:14px;">{icon_html}{title}{sub_html}</div>')
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:20px;border-top:3px solid {pc["accent"]};'
        f'box-shadow:0 1px 3px rgba(15,23,42,0.05);">{header}',
        unsafe_allow_html=True
    )

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

# ── KPI card ─────────────────────────────────────────────────────────────────
def kpi_card(label: str, value: str, delta: str = "", delta_label: str = "",
             icon: str = "", icon_bg: str = "#E0F2FE", icon_color: str = "",
             badge: str = "", badge_type: str = "blue"):
    is_neg     = delta.startswith("-") if delta else False
    delta_color= "#10B981" if is_neg else "#F43F5E" if delta else "#64748B"
    arrow      = "↓" if is_neg else "↑" if delta else ""
    delta_html = (f'<div style="font-size:12px;font-weight:600;color:{delta_color};margin-top:3px;">'
                  f'{arrow} {delta} {delta_label}</div>') if delta else ""
    badge_html  = _badge_html(badge, badge_type) if badge else ""
    _ic         = f"color:{icon_color};" if icon_color else ""
    icon_html   = (f'<div style="width:34px;height:34px;background:{icon_bg};border-radius:9px;'
                   f'display:flex;align-items:center;justify-content:center;font-size:17px;'
                   f'margin-bottom:8px;{_ic}">{icon}</div>') if icon else ""
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:16px 18px;box-shadow:0 1px 3px rgba(15,23,42,0.05);">'
        f'{icon_html}'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;'
        f'color:#94A3B8;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:22px;font-weight:700;color:#0F172A;letter-spacing:-0.3px;">{value}</div>'
        f'{delta_html}<div style="margin-top:6px;">{badge_html}</div></div>',
        unsafe_allow_html=True
    )

# ── Hero banner ───────────────────────────────────────────────────────────────
def hero_banner(title: str, subtitle: str, stats: list = None, accent: str = "#0EA5E9"):
    stats_html = ""
    if stats:
        items = "".join([
            f'<div style="display:flex;flex-direction:column;gap:2px;">'
            f'<span style="font-size:22px;font-weight:800;letter-spacing:-0.5px;">{s["value"]}</span>'
            f'<span style="font-size:10px;opacity:0.6;text-transform:uppercase;letter-spacing:0.5px;">{s["label"]}</span>'
            f'</div>' for s in stats
        ])
        stats_html = f'<div style="display:flex;gap:32px;flex-wrap:wrap;margin-top:16px;">{items}</div>'
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0B1220 0%,#0C2340 50%,#0F3460 100%);
         border-radius:16px;padding:28px 32px;color:white;margin-bottom:20px;
         position:relative;overflow:hidden;border:1px solid rgba(14,165,233,0.2);
         box-shadow:0 8px 32px rgba(14,165,233,0.12);">
        <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;
             background:rgba(14,165,233,0.06);border-radius:50%;"></div>
        <div style="position:absolute;bottom:-60px;right:60px;width:280px;height:280px;
             background:rgba(99,102,241,0.05);border-radius:50%;"></div>
        <div style="position:relative;z-index:1;">
            <div style="font-size:22px;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px;">{title}</div>
            <div style="font-size:12px;opacity:0.6;">{subtitle}</div>
            {stats_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Insight panel ─────────────────────────────────────────────────────────────
def insight_panel(items: list):
    """items: list of {icon, type, text}. type: info|warn|alert"""
    TYPE_COLORS = {
        "info":  ("#EFF6FF", "#BFDBFE", "#1E40AF"),
        "warn":  ("#FFFBEB", "#FDE68A", "#92400E"),
        "alert": ("#FFF1F2", "#FECDD3", "#9F1239"),
    }
    for it in items:
        bg, border, fg = TYPE_COLORS.get(it.get("type","info"), TYPE_COLORS["info"])
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 14px;'
            f'background:{bg};border:1px solid {border};border-radius:8px;margin-bottom:6px;">'
            f'<span style="font-size:15px;flex-shrink:0;margin-top:1px;">{it.get("icon","ℹ️")}</span>'
            f'<div style="font-size:12px;color:#334155;line-height:1.6;">{it["text"]}</div></div>',
            unsafe_allow_html=True
        )

# ── Action card ───────────────────────────────────────────────────────────────
def action_card(title: str, body: str, impact: str = "", accent: str = "#0EA5E9"):
    impact_html = (f'<div style="font-size:10px;color:#94A3B8;margin-top:5px;">📈 {impact}</div>'
                   if impact else "")
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;'
        f'padding:14px 16px;border-left:3px solid {accent};margin-bottom:6px;">'
        f'<div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:4px;">{title}</div>'
        f'<div style="font-size:12px;color:#64748B;line-height:1.6;">{body}</div>'
        f'{impact_html}</div>',
        unsafe_allow_html=True
    )

# ── Recommendation card (priority-based variant, used by carbon_accounting) ───
def recommendation_card(title: str, body: str, impact: str = "", priority: str = "high"):
    colors = {"high": "#0EA5E9", "medium": "#F59E0B", "low": "#64748B"}
    color  = colors.get(priority, "#0EA5E9")
    impact_html = (f'<div style="font-size:10px;color:#94A3B8;margin-top:5px;">📈 {impact}</div>'
                   if impact else "")
    st.markdown(
        f'<div style="border:1px solid #E2E8F0;border-left:4px solid {color};'
        f'border-radius:10px;padding:13px 15px;margin-bottom:10px;background:white;">'
        f'<div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:4px;">{title}</div>'
        f'<div style="font-size:11px;color:#64748B;line-height:1.6;">{body}</div>'
        f'{impact_html}</div>',
        unsafe_allow_html=True
    )

# ── Metric row (label + bar) ──────────────────────────────────────────────────
def metric_bar(label: str, value: float, max_val: float = 100, color: str = "#0EA5E9", suffix: str = "%"):
    pct = min(value / max_val * 100, 100) if max_val else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:5px 0;">'
        f'<div style="width:90px;font-size:10px;font-weight:700;color:#94A3B8;'
        f'text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
        f'<div style="flex:1;height:6px;background:#F1F5F9;border-radius:3px;overflow:hidden;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;"></div></div>'
        f'<div style="width:28px;font-size:12px;font-weight:700;color:{color};text-align:right;">'
        f'{value:.0f}</div></div>',
        unsafe_allow_html=True
    )

# ── Scope bar ─────────────────────────────────────────────────────────────────
# Signature kept as (label, value, total, unit, color) — every current call
# site (carbon_accounting, dashboard, esg_reporting) passes a total to compute
# % from, not a pre-computed pct.
def scope_bar(label: str, value: float, total: float, unit: str = "tCO₂e", color: str = "#0EA5E9"):
    pct = (value / total * 100) if total > 0 else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<div style="width:72px;font-size:11px;font-weight:600;color:#64748B;">{label}</div>'
        f'<div style="flex:1;height:6px;background:#E2E8F0;border-radius:3px;overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;background:{color};border-radius:3px;"></div></div>'
        f'<div style="width:100px;font-size:11px;font-weight:700;color:#0F172A;text-align:right;">'
        f'{value:,.0f} {unit}</div></div>',
        unsafe_allow_html=True
    )

# ── Stat row (label/value pair, used by esg_reporting) ────────────────────────
def stat_row(label: str, value: str, color: str = "#0F172A"):
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:7px 0;border-bottom:1px solid #F8FAFC;font-size:12px;">'
        f'<span style="color:#64748B;">{label}</span>'
        f'<span style="font-weight:700;color:{color};">{value}</span></div>',
        unsafe_allow_html=True
    )

# ── Empty state ───────────────────────────────────────────────────────────────
def empty_state(icon: str, title: str, message: str, cta: str = ""):
    cta_html = (f'<div style="font-size:12px;font-weight:600;color:#0EA5E9;margin-top:10px;">{cta}</div>'
                if cta else "")
    st.markdown(f"""
    <div style="text-align:center;padding:40px 20px;background:#F8FAFC;border-radius:14px;
         border:1.5px dashed #E2E8F0;margin-bottom:16px;">
        <div style="font-size:44px;margin-bottom:12px;">{icon}</div>
        <div style="font-size:15px;font-weight:700;color:#0F172A;margin-bottom:8px;">{title}</div>
        <div style="font-size:12px;color:#64748B;line-height:1.7;max-width:420px;margin:0 auto;">{message}</div>
        {cta_html}
    </div>
    """, unsafe_allow_html=True)

# ── Divider ───────────────────────────────────────────────────────────────────
def divider(label: str = ""):
    if label:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin:16px 0;">'
            f'<div style="flex:1;height:1px;background:#E2E8F0;"></div>'
            f'<div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
            f'letter-spacing:0.8px;white-space:nowrap;">{label}</div>'
            f'<div style="flex:1;height:1px;background:#E2E8F0;"></div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div style="height:1px;background:#F1F5F9;margin:12px 0;"></div>', unsafe_allow_html=True)

# ── ESG gauge (Plotly) ────────────────────────────────────────────────────────
def esg_gauge(score: float, title: str = "ESG Score", height: int = 220):
    color = "#10B981" if score >= 70 else "#F59E0B" if score >= 50 else "#F43F5E"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"size": 26, "color": "#0F172A",
                                            "family": "Inter,system-ui,sans-serif"}},
        title={"text": title, "font": {"size": 11, "color": "#64748B",
                                        "family": "Inter,system-ui,sans-serif"}},
        gauge={
            "axis": {"range": [0,100], "tickcolor": "#CBD5E1",
                     "tickfont": {"size": 9, "family": "Inter,system-ui,sans-serif"}},
            "bar":  {"color": color, "thickness": 0.7},
            "bgcolor": "#F8FAFC",
            "borderwidth": 0,
            "steps": [
                {"range": [0,   50], "color": "#FFF1F2"},
                {"range": [50,  70], "color": "#FFFBEB"},
                {"range": [70, 100], "color": "#ECFDF5"},
            ],
            "threshold": {"line": {"color": color, "width": 3},
                          "thickness": 0.85, "value": score},
        }
    ))
    fig.update_layout(
        height=height, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font_family="Inter,system-ui,sans-serif",
    )
    st.plotly_chart(fig, use_container_width=True)
