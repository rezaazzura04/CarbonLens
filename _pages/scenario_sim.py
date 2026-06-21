"""
CarbonLens V7 — Scenario Simulation Center
Interactive sustainability planning: sliders → real-time ESG + emission projections
"""

import streamlit as st
import pandas as pd
import json
import datetime
import utils.state as S
import plotly.graph_objects as go
import numpy as np
from components.ui import page_header, kpi_card, insight_panel
from utils.calculations import (
    dataset_overview, calculate_esg_score, get_benchmark,
    annual_projection, generate_demo_data, NumpyEncoder,
)
from config.settings import COLORS, PLOTLY_THEME as T


def _recalc(total_em, area_m2, sector,
            renew_pct, eff_pct, waste_red, water_con, fleet_ev, ef=None):
    """Re-compute projected emissions and ESG from scenario sliders."""
    from config.settings import EMISSION_FACTORS
    grid_ef = (ef or EMISSION_FACTORS)["electricity_kgco2_per_kwh"]
    # Each lever reduces a portion of total
    renewable_saving = total_em * 0.436 * (renew_pct / 100) * grid_ef   # Scope 2 reduction
    efficiency_saving= total_em * 0.436 * (eff_pct  / 100) * 0.12    # Energy efficiency % off scope2
    waste_saving     = total_em * 0.05  * (waste_red / 100)           # Waste / scope 3 portion
    water_saving     = total_em * 0.02  * (water_con / 100)
    fleet_saving     = total_em * 0.15  * (fleet_ev  / 100) * 0.72   # Direct combustion EV substitution

    total_saving   = renewable_saving + efficiency_saving + waste_saving + water_saving + fleet_saving
    projected_em   = max(total_em - total_saving, total_em * 0.05)
    reduction_pct  = (total_saving / total_em * 100) if total_em > 0 else 0

    # ── ESG: baseline from canonical (real S/G data), projected varies E pillar ──
    from utils.state import compute_canonical_esg
    import streamlit as _st
    canonical = compute_canonical_esg()
    _comp        = _st.session_state.get("completeness", 94)
    _recycle_pct = float(_st.session_state.get("recycle_pct", 20))
    _cur_renew   = float(_st.session_state.get("renew_pct", 5))

    new_intensity  = (projected_em * 1000 / area_m2) if area_m2 > 0 else 50
    cur_intensity  = (total_em * 1000 / area_m2) if area_m2 > 0 else 50

    # Projected renewable % = current + the renewable lever applied in this scenario
    _proj_renew = min(100.0, _cur_renew + renew_pct)

    new_esg = calculate_esg_score(
        new_intensity, _comp, _proj_renew, _recycle_pct,
        water_recycled_pct           = _st.session_state.get("water_recycled_pct", 0) or 0,
        employee_turnover_pct        = _st.session_state.get("employee_turnover_pct"),
        training_hours_per_employee  = _st.session_state.get("training_hours_per_employee"),
        women_workforce_pct          = _st.session_state.get("women_workforce_pct"),
        women_management_pct         = _st.session_state.get("women_management_pct"),
        injury_rate                  = _st.session_state.get("injury_rate"),
        board_independence_pct       = _st.session_state.get("board_independence_pct"),
        women_board_pct              = _st.session_state.get("women_board_pct"),
        has_code_of_conduct          = _st.session_state.get("has_code_of_conduct"),
        has_whistleblower_policy     = _st.session_state.get("has_whistleblower_policy"),
        anti_corruption_training_pct = _st.session_state.get("anti_corruption_training_pct"),
        certifications_count         = len(_st.session_state.get("certifications") or []),
    )
    cur_esg = canonical  # canonical baseline — single source of truth

    # Cost estimation (rough $)
    cost_renew   = total_em * 0.436 * (renew_pct/100) * 85  * 1    # ~$85/MWh PPA premium
    cost_eff     = total_em * 0.436 * (eff_pct /100) * 12000 * 0.001  # audit + retrofit
    cost_fleet   = total_em * 0.15  * (fleet_ev/100) * 35           # EV premium

    total_cost   = cost_renew + cost_eff + cost_fleet
    cost_per_tco2= (total_cost / max(total_saving, 1))

    return {
        "cur_em":        total_em,
        "proj_em":       round(projected_em, 1),
        "saving":        round(total_saving, 1),
        "reduction_pct": round(reduction_pct, 1),
        "cur_score":     cur_esg["score"],
        "proj_score":    new_esg["score"],
        "cur_grade":     cur_esg["grade"],
        "proj_grade":    new_esg["grade"],
        "proj_label":    new_esg["label"],
        "cost_estimate": round(total_cost),
        "cost_per_tco2": round(cost_per_tco2, 1),
        "savings_breakdown": {
            "Renewable Energy":  round(renewable_saving, 1),
            "Energy Efficiency": round(efficiency_saving, 1),
            "Fleet Electrification": round(fleet_saving, 1),
            "Waste Reduction":   round(waste_saving, 1),
            "Water Conservation":round(water_saving, 1),
        },
    }


def _waterfall(result: dict) -> go.Figure:
    labels = ["Current"] + list(result["savings_breakdown"].keys()) + ["Projected"]
    values = [result["cur_em"]]
    for v in result["savings_breakdown"].values():
        values.append(-v)
    values.append(result["proj_em"])

    colors_wf = (
        ["#6B7280"] +
        ["#06B6D4"] * len(result["savings_breakdown"]) +
        ["#0EA5E9"]
    )

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + ["relative"] * len(result["savings_breakdown"]) + ["total"],
        x=labels,
        y=values,
        connector=dict(line=dict(color="#E5E7EB", width=1, dash="dot")),
        decreasing=dict(marker_color="#06B6D4"),
        increasing= dict(marker_color="#EF4444"),
        totals=     dict(marker_color="#0EA5E9"),
        text=[f"{abs(v):,.0f}" for v in values],
        textposition="outside",
        textfont=dict(size=11, family=T["font_family"]),
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} tCO₂e<extra></extra>",
    ))
    fig.update_layout(
        height=300, margin=dict(l=0,r=0,t=20,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F3F4F6", title="tCO₂e"),
        xaxis=dict(showgrid=False),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        showlegend=False,
    )
    return fig


def _score_gauge_pair(cur, proj) -> go.Figure:
    fig = go.Figure()

    for val, name, color in [(cur,"Current","#6B7280"),(proj,"Projected","#06B6D4")]:
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title=dict(text=name, font=dict(size=12, color=color, family=T["font_family"])),
            number=dict(suffix="/100", font=dict(size=20, color="#111827", family=T["font_family"])),
            gauge=dict(
                axis=dict(range=[0,100], tickfont=dict(size=9, family=T["font_family"])),
                bar=dict(color=color, thickness=0.22),
                bgcolor="rgba(0,0,0,0)",
                steps=[
                    dict(range=[0,40],  color="#FEE2E2"),
                    dict(range=[40,70], color="#FEF3C7"),
                    dict(range=[70,100],color="#DCFCE7"),
                ],
            ),
            domain=dict(x=[0, 0.48] if name == "Current" else [0.52, 1.0], y=[0, 1]),
        ))
    fig.update_layout(
        height=200, margin=dict(l=10,r=10,t=30,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=T["font_family"]),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TIER 4 · Predictive Decarbonization Simulator — target → auto action plan
# ─────────────────────────────────────────────────────────────────────────────

_LEVER_META = {
    "renew": {
        "label": "Renewable Energy Adoption", "icon": "☀️", "max_pct": 100, "sim_key": "sim_renew",
        "action": "Procure renewables via rooftop solar PV, PPA with an IPP, or REC purchase",
        "lead_time": "6–18 months", "phase": "Phase 3 · Strategic (ongoing to target year)",
    },
    "eff": {
        "label": "Energy Efficiency Programme", "icon": "🏭", "max_pct": 50, "sim_key": "sim_eff",
        "action": "ISO 50001 energy audit, LED retrofit, HVAC/motor optimization",
        "lead_time": "3–9 months", "phase": "Phase 2 · Mid-term (Year 1–3)",
    },
    "fleet": {
        "label": "Fleet Electrification", "icon": "🚗", "max_pct": 100, "sim_key": "sim_fleet",
        "action": "Phase fossil fleet to EV, starting with light-duty / passenger vehicles",
        "lead_time": "12–24 months (phased)", "phase": "Phase 2 · Mid-term (Year 1–2)",
    },
    "waste": {
        "label": "Waste Reduction Programme", "icon": "♻️", "max_pct": 100, "sim_key": "sim_waste",
        "action": "Source segregation, composting, recycling partnerships, zero-landfill push",
        "lead_time": "3–6 months", "phase": "Phase 1 · Quick win (Year 1)",
    },
    "water": {
        "label": "Water Conservation", "icon": "💧", "max_pct": 100, "sim_key": "sim_water",
        "action": "Greywater recycling, leak detection, low-flow fixtures",
        "lead_time": "3–6 months", "phase": "Phase 1 · Quick win (Year 1)",
    },
}

# Indicative 2026 voluntary carbon market reference ranges (USD/tCO2e) — varies
# heavily by registry, vintage & quality rating; confirm live pricing before committing.
CREDIT_PROJECT_TYPES = {
    "Blue Carbon (Mangrove/Coastal — VCS VM0007)": {
        "low": 10, "high": 25,
        "note": "Highest Indonesia relevance — aligned with the Marine & Blue Carbon priority sector under Perpres 110/2025",
    },
    "REDD+ / Forest Conservation": {
        "low": 5, "high": 15,
        "note": "Most common Indonesia project type — quality varies widely; check ICVCM Core Carbon Principle (CCP) status",
    },
    "Nature-based Removal (Afforestation/ARR)": {
        "low": 15, "high": 35,
        "note": "Durable sequestration, higher integrity premium",
    },
    "Renewable Energy (Grid-connected)": {
        "low": 2, "high": 6,
        "note": "Lowest cost, but additionality is increasingly questioned — many corporate buyers now avoid for net-zero claims",
    },
    "Community Energy / Cookstoves": {
        "low": 5, "high": 12,
        "note": "Strong co-benefits (health, livelihoods) — a Gold Standard specialty",
    },
}


def _lever_saving_at(lever, pct, total_em, grid_ef):
    """tCO2e saved by one lever at `pct` — mirrors _recalc()'s per-lever terms exactly,
    so the action plan always reconciles with the manual simulator above."""
    if lever == "renew": return total_em * 0.436 * (pct / 100) * grid_ef
    if lever == "eff":   return total_em * 0.436 * (pct / 100) * 0.12
    if lever == "fleet": return total_em * 0.15  * (pct / 100) * 0.72
    if lever == "waste": return total_em * 0.05  * (pct / 100)
    if lever == "water": return total_em * 0.02  * (pct / 100)
    return 0.0


def _lever_cost_at(lever, pct, total_em):
    """Rough USD capex — mirrors _recalc()'s cost model (waste/water ≈ $0 capex,
    treated as low-cost operational/behavioral programmes, same as the manual simulator)."""
    if lever == "renew": return total_em * 0.436 * (pct / 100) * 85
    if lever == "eff":   return total_em * 0.436 * (pct / 100) * 12000 * 0.001
    if lever == "fleet": return total_em * 0.15  * (pct / 100) * 35
    return 0.0


def _generate_action_plan(total_em, target_pct, grid_ef, target_year, current_year):
    """
    Reverse-engineer the lowest-cost lever combination that reaches `target_pct`
    emission reduction. Each lever's saving is linear & independent of the others
    (confirmed against _recalc()'s formulas), so cheapest-$/tCO2e-first allocation
    up to each lever's own UI bound is the exact cost-minimizing solution — not a
    heuristic. Whatever the levers cannot close becomes the residual offset gap.
    """
    total_em = max(float(total_em or 0), 0.0)
    target_saving = max(total_em * (target_pct / 100), 0.0)

    ranking = []
    for lever, meta in _LEVER_META.items():
        max_pct  = meta["max_pct"]
        ref_em   = total_em if total_em > 0 else 1.0          # scale-invariant ranking only
        max_save = _lever_saving_at(lever, max_pct, ref_em, grid_ef)
        max_cost = _lever_cost_at(lever, max_pct, ref_em)
        cost_per_tco2 = (max_cost / max_save) if max_save > 0 else float("inf")
        ranking.append((cost_per_tco2, lever))
    ranking.sort(key=lambda x: x[0])
    order = [lever for _, lever in ranking]

    remaining = target_saving
    rec_pct   = {}
    for lever in order:
        meta     = _LEVER_META[lever]
        max_pct  = meta["max_pct"]
        max_save = _lever_saving_at(lever, max_pct, total_em, grid_ef)
        if max_save <= 0 or remaining <= 0:
            rec_pct[lever] = 0
            continue
        take    = min(remaining, max_save)
        pct_raw = (take / max_save) * max_pct
        pct     = min(max_pct, max(0, round(pct_raw / 5) * 5))   # snap to slider step
        rec_pct[lever] = int(pct)
        remaining -= _lever_saving_at(lever, pct, total_em, grid_ef)

    achieved_saving = sum(_lever_saving_at(l, rec_pct[l], total_em, grid_ef) for l in order)
    achieved_cost   = sum(_lever_cost_at(l, rec_pct[l], total_em) for l in order)
    residual_gap    = max(target_saving - achieved_saving, 0.0)

    return {
        "target_saving":   round(target_saving, 1),
        "achieved_saving": round(achieved_saving, 1),
        "achieved_cost":   round(achieved_cost),
        "residual_gap":    round(residual_gap, 1),
        "rec_pct":         rec_pct,
        "order":           order,
        "years_to_target": max(target_year - current_year, 1),
    }


def _glide_path_chart(total_em, target_pct, current_year, target_year, achievable_pct) -> go.Figure:
    years = list(range(current_year, target_year + 1))
    n = len(years)
    target_level     = total_em * (1 - target_pct / 100)
    achievable_level = total_em * (1 - achievable_pct / 100)
    pathway = ([total_em + (target_level - total_em) * (i / (n - 1)) for i in range(n)]
               if n > 1 else [total_em])
    bau     = [total_em] * n

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=bau, name="Business-as-usual", mode="lines",
        line=dict(color="#CBD5E1", width=1.5, dash="dot"), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=pathway, name="Target pathway", mode="lines+markers",
        line=dict(color="#0EA5E9", width=2.5), marker=dict(size=5, color="#0EA5E9"),
        fill="tonexty", fillcolor="rgba(14,165,233,0.07)",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} tCO₂e<extra></extra>",
    ))
    fig.add_hline(
        y=achievable_level, line_dash="dash", line_color="#10B981", line_width=1.5,
        annotation_text=f" Achievable via levers ({achievable_pct:.0f}%)",
        annotation_font=dict(size=10, color="#10B981", family=T["font_family"]),
        annotation_position="bottom right",
    )

    span  = max(target_year - current_year, 1)
    dtick = 1 if span <= 10 else (5 if span <= 25 else 10)

    fig.update_layout(
        height=280, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#F3F4F6", title="tCO₂e/yr"),
        xaxis=dict(showgrid=False, dtick=dtick),
        font=dict(family=T["font_family"], size=11, color=T["font_color"]),
        legend=dict(orientation="h", y=1.15, font=dict(size=10, family=T["font_family"])),
    )
    return fig


def _apply_levers_callback(renew, eff, fleet, waste, water):
    """on_click callback — safe to mutate widget-bound session_state here because
    callbacks run BEFORE the script body (and its widgets) execute on the rerun.
    Assigning directly inside an `if st.button(...):` block raises
    StreamlitAPIException once the same-keyed widget has already rendered earlier
    in that run, which is what the original BAU/2030 Plan/Net Zero presets did."""
    st.session_state["sim_renew"] = renew
    st.session_state["sim_eff"]   = eff
    st.session_state["sim_fleet"] = fleet
    st.session_state["sim_waste"] = waste
    st.session_state["sim_water"] = water


def _apply_plan_callback(rec_pct: dict):
    for _lever, _meta in _LEVER_META.items():
        st.session_state[_meta["sim_key"]] = int(rec_pct.get(_lever, 0))
    st.session_state["_plan_applied_flag"] = True


def _set_plan_target_callback(year, pct):
    st.session_state["plan_target_year"] = year
    st.session_state["plan_target_pct"]  = pct


def _sync_offset_callback(value):
    st.session_state["credit_offset_vol"] = value


def render():
    S.init()

    page_header(
        title="Scenario Simulation Center",
        subtitle="Interactive sustainability planning · Adjust levers → see projected ESG score & emission reductions in real time",
        badge="Planning Tool",
        badge_type="purple",
    )

    has_data = S.get("uploaded_df") is not None
    df       = S.get("uploaded_df") if has_data else generate_demo_data()
    ov       = dataset_overview(df)
    total_em = ov.get("total", 0)

    if not has_data:
        st.info("📌 Using demo data. Upload your dataset in ESG Analytics for real projections.")

    sector  = S.get("sector", "Manufacturing")
    area_m2 = float(S.get("area_m2", 5000))

    # ── Lever Controls ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:14px;">⧖ Adjust Sustainability Levers</div>
    """, unsafe_allow_html=True)

    lev_l, lev_r = st.columns(2, gap="large")

    with lev_l:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">⚡ Energy & Renewables</div>
            <div class="cl-card-subtitle">Scope 1 & 2 emission drivers</div>
        """, unsafe_allow_html=True)

        renew_pct = st.slider("☀️ Renewable Energy Adoption", 0, 100, 20, 5,
                              key="sim_renew", help="% of electricity from renewables")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;margin-bottom:12px;'>Target: 100% by 2030 · Current: {renew_pct}%</div>", unsafe_allow_html=True)

        eff_pct   = st.slider("🏭 Energy Efficiency Programme", 0, 50, 10, 5,
                              key="sim_eff", help="% reduction via ISO 50001 / LED / HVAC")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;margin-bottom:12px;'>Typical range: 8–15% savings</div>", unsafe_allow_html=True)

        fleet_ev  = st.slider("🚗 Fleet Electrification", 0, 100, 10, 5,
                              key="sim_fleet", help="% of fossil fuel fleet replaced with EVs")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;'>Reduces direct combustion (Scope 1)</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with lev_r:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">💧 Resources & Waste</div>
            <div class="cl-card-subtitle">Scope 3 & operational efficiency</div>
        """, unsafe_allow_html=True)

        waste_red = st.slider("♻️ Waste Reduction Programme", 0, 100, 20, 5,
                              key="sim_waste", help="% reduction in total waste generation")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;margin-bottom:12px;'>Zero-landfill target: 100%</div>", unsafe_allow_html=True)

        water_con = st.slider("💧 Water Conservation", 0, 100, 10, 5,
                              key="sim_water", help="% reduction in water consumption")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;margin-bottom:12px;'>Industry target: 20% by 2028</div>", unsafe_allow_html=True)

        # Scenario presets
        st.markdown("<div style='margin-top:12px;font-size:10px;font-weight:700;color:#6B7280;margin-bottom:8px;'>SCENARIO PRESETS</div>", unsafe_allow_html=True)
        sc_c1, sc_c2, sc_c3 = st.columns(3)
        with sc_c1:
            st.button("📋 BAU", use_container_width=True, key="preset_bau", help="Business As Usual",
                      on_click=_apply_levers_callback, args=(5, 3, 0, 5, 3))
        with sc_c2:
            st.button("🌱 2030 Plan", use_container_width=True, key="preset_2030", help="Paris-aligned 2030 target",
                      on_click=_apply_levers_callback, args=(60, 20, 40, 50, 25))
        with sc_c3:
            st.button("⚡ Net Zero", use_container_width=True, key="preset_nz", help="Aggressive net-zero path",
                      on_click=_apply_levers_callback, args=(100, 35, 90, 80, 50))
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Calculate ───────────────────────────────────────────────────────────
    result = _recalc(
        total_em, area_m2, sector,
        st.session_state.get("sim_renew", 20),
        st.session_state.get("sim_eff",   10),
        st.session_state.get("sim_waste", 20),
        st.session_state.get("sim_water", 10),
        st.session_state.get("sim_fleet", 10),
        ef=S.get_emission_factors(),
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Results ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:14px;">📊 Simulation Results</div>
    """, unsafe_allow_html=True)

    r1, r2, r3, r4, r5 = st.columns(5, gap="medium")
    with r1:
        kpi_card("Current Emissions", f"{result['cur_em']:,.0f}",
                 badge="tCO₂e baseline", badge_type="gray", icon="📍", icon_bg="#F3F4F6")
    with r2:
        kpi_card("Projected Emissions", f"{result['proj_em']:,.0f}",
                 badge=f"−{result['reduction_pct']:.0f}%", badge_type="green",
                 icon="📉", icon_bg="#DCFCE7")
    with r3:
        kpi_card("Emission Reduction", f"{result['saving']:,.0f}",
                 badge="tCO₂e saved", badge_type="green",
                 icon="✅", icon_bg="#E0F2FE")
    with r4:
        score_delta = result["proj_score"] - result["cur_score"]
        kpi_card("ESG Score Change",
                 f"{result['cur_score']} → {result['proj_score']}",
                 badge=f"+{score_delta} points" if score_delta >= 0 else f"{score_delta} pts",
                 badge_type="green" if score_delta >= 0 else "red",
                 icon="🎯", icon_bg="#E0F2FE")
    with r5:
        kpi_card("Investment Estimate",
                 f"${result['cost_estimate']:,}",
                 badge=f"${result['cost_per_tco2']}/tCO₂e", badge_type="teal",
                 icon="💰", icon_bg="#CFFAFE")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Charts ──────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="medium")

    with ch1:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📉 Emission Reduction Waterfall</div>
            <div class="cl-card-subtitle">Contribution of each lever to total reduction · tCO₂e</div>
        """, unsafe_allow_html=True)
        try:
            st.plotly_chart(_waterfall(result), use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    with ch2:
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">🎯 ESG Score: Current vs Projected</div>
            <div class="cl-card-subtitle">{result['cur_grade']} → {result['proj_grade']} · {result['proj_label']}</div>
        """, unsafe_allow_html=True)
        try:
            st.plotly_chart(_score_gauge_pair(result["cur_score"], result["proj_score"]), use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")

        # Breakdown table
        st.markdown("<div style='margin-top:8px;'>", unsafe_allow_html=True)
        for lever, saving in result["savings_breakdown"].items():
            if saving > 0:
                pct = saving / max(result["saving"], 1) * 100
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:5px 0;
                            border-bottom:1px solid #F9FAFB;font-size:12px;">
                    <span style="color:#6B7280;">{lever}</span>
                    <span style="font-weight:700;color:#0EA5E9;">{saving:,.0f} tCO₂e · {pct:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Narrative ───────────────────────────────────────────────────────────
    top_lever = max(result["savings_breakdown"], key=result["savings_breakdown"].get)
    top_saving= result["savings_breakdown"][top_lever]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#E0F2FE,#ECFEFF);border:1.5px solid #86EFAC;
                border-radius:12px;padding:18px 22px;margin-top:8px;">
        <div style="font-size:10px;font-weight:700;color:#0C4A6E;margin-bottom:8px;">🤖 Simulation Interpretation</div>
        <div style="font-size:12px;color:#374151;line-height:1.8;">
            With the selected interventions, annual emissions would decrease from
            <strong>{result['cur_em']:,.0f} to {result['proj_em']:,.0f} tCO₂e
            (−{result['reduction_pct']:.0f}%)</strong>.
            The most impactful lever is <strong>{top_lever}</strong>,
            contributing <strong>{top_saving:,.0f} tCO₂e</strong> in annual savings.
            ESG score would improve from <strong>Grade {result['cur_grade']} to Grade {result['proj_grade']}</strong>,
            {'unlocking access to green finance and ESG-linked bonds.' if result['proj_score'] >= 75 else 'approaching the Grade A threshold required for premium ESG ratings.'}
            Estimated implementation cost: <strong>${result['cost_estimate']:,}</strong>
            ({f"${result['cost_per_tco2']}/tCO₂e" if result['cost_per_tco2'] > 0 else "N/A"} abatement cost).
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 4 · TARGET-BASED DECARBONIZATION PLANNER  (auto action plan + cost)
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:4px;">🎯 Target-Based Decarbonization Planner</div>
    <div style="font-size:12px;color:#94A3B8;margin-bottom:14px;">
        Set a target year &amp; reduction goal — the engine reverse-engineers the lowest-cost lever mix to get there</div>
    """, unsafe_allow_html=True)

    cur_year    = datetime.datetime.now().year
    grid_ef_now = S.get_emission_factors().get("electricity_kgco2_per_kwh", 0.716)

    plan_l, plan_r = st.columns([1, 1.5], gap="large")

    with plan_l:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">⏱️ Target Configuration</div>
            <div class="cl-card-subtitle">Define the goal — the system handles the "how"</div>
        """, unsafe_allow_html=True)

        target_year = st.slider("Target Year", cur_year + 1, cur_year + 35, cur_year + 4, 1,
                                 key="plan_target_year")
        target_reduction_pct = st.slider("Target Emission Reduction (%)", 0, 100, 40, 5,
                                          key="plan_target_pct",
                                          help="vs. current baseline annual emissions")

        st.markdown("<div style='font-size:10px;font-weight:700;color:#6B7280;margin:10px 0 6px;'>"
                    "QUICK REFERENCE TARGETS</div>", unsafe_allow_html=True)
        qp1, qp2, qp3 = st.columns(3)
        with qp1:
            st.button("🇮🇩 NDC 2030", use_container_width=True, key="preset_ndc",
                      help="Indonesia's 2022 Enhanced NDC — unconditional 2030 target",
                      on_click=_set_plan_target_callback, args=(max(2030, cur_year + 1), 32))
        with qp2:
            st.button("🌍 Net Zero 2060", use_container_width=True, key="preset_nz60",
                      help="Indonesia's national net-zero pathway (LTS-LCCR 2050)",
                      on_click=_set_plan_target_callback, args=(2060, 90))
        with qp3:
            st.button("⚡ 5-Year Push", use_container_width=True, key="preset_5yr",
                      help="Aggressive near-term decarbonization",
                      on_click=_set_plan_target_callback, args=(cur_year + 5, 60))
        st.markdown("""
        <div style="font-size:10px;color:#CBD5E1;margin-top:8px;line-height:1.5;">
            🇮🇩 reference only — Indonesia's Second NDC (Oct 2025) moved to an absolute 2035 emissions
            target; the 2030 figure above still reflects the operative 2022 Enhanced NDC (−31.89% unconditional).
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    plan = _generate_action_plan(total_em, target_reduction_pct, grid_ef_now, target_year, cur_year)
    achievable_pct = (plan["achieved_saving"] / total_em * 100) if total_em > 0 else 0.0

    with plan_r:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📈 Glide Path to Target</div>
            <div class="cl-card-subtitle">Linear pathway vs. business-as-usual</div>
        """, unsafe_allow_html=True)
        try:
            st.plotly_chart(
                _glide_path_chart(total_em, target_reduction_pct, cur_year, target_year, achievable_pct),
                use_container_width=True)
        except Exception as _chart_err:
            st.warning(f"⚠️ Chart unavailable — {_chart_err}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    pk1, pk2, pk3, pk4 = st.columns(4, gap="medium")
    with pk1:
        kpi_card("Target Reduction", f"{target_reduction_pct}%",
                 badge=f"by {target_year}", badge_type="blue", icon="🎯", icon_bg="#E0F2FE")
    with pk2:
        kpi_card("Achievable via Levers", f"{achievable_pct:.0f}%",
                 badge=f"{plan['achieved_saving']:,.0f} tCO₂e", badge_type="green",
                 icon="🛠️", icon_bg="#DCFCE7")
    with pk3:
        gap_val   = plan["residual_gap"]
        gap_label = "No gap" if gap_val <= 0.5 else f"{gap_val:,.0f} tCO₂e/yr"
        kpi_card("Residual Gap", gap_label,
                 badge="needs offsetting" if gap_val > 0.5 else "fully internal",
                 badge_type="red" if gap_val > 0.5 else "green",
                 icon="🌍", icon_bg="#FFE4E6" if gap_val > 0.5 else "#DCFCE7")
    with pk4:
        kpi_card("Estimated Capex", f"${plan['achieved_cost']:,}",
                 badge=f"by {target_year}", badge_type="teal", icon="💰", icon_bg="#CFFAFE")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="cl-card">
        <div class="cl-card-title">📋 Auto-Generated Action Plan</div>
        <div class="cl-card-subtitle">Ranked by abatement cost ($/tCO₂e) — cheapest, fastest levers first</div>
    """, unsafe_allow_html=True)

    any_action = False
    for lever in plan["order"]:
        pct = plan["rec_pct"].get(lever, 0)
        if pct <= 0:
            continue
        any_action = True
        meta     = _LEVER_META[lever]
        saving   = _lever_saving_at(lever, pct, total_em, grid_ef_now)
        cost     = _lever_cost_at(lever, pct, total_em)
        cost_str = f"${cost:,.0f}" if cost > 0 else "Low / operational cost"
        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #F1F5F9;">
            <div style="font-size:20px;flex-shrink:0;width:30px;">{meta['icon']}</div>
            <div style="flex:1;">
                <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px;">
                    <span style="font-size:12px;font-weight:700;color:#0F172A;">{meta['label']} → {pct}%</span>
                    <span style="font-size:10px;font-weight:700;color:#0EA5E9;">{saving:,.0f} tCO₂e/yr · {cost_str}</span>
                </div>
                <div style="font-size:12px;color:#64748B;margin-top:3px;">{meta['action']}</div>
                <div style="font-size:10px;color:#94A3B8;margin-top:3px;">{meta['phase']} · Lead time: {meta['lead_time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if not any_action:
        st.markdown('<div style="font-size:12px;color:#94A3B8;padding:8px 0;">'
                    'Set a target reduction above 0% to generate an action plan.</div>',
                    unsafe_allow_html=True)

    if plan["residual_gap"] > 0.5:
        st.markdown(f"""
        <div style="margin-top:10px;background:#FFF7ED;border:1.5px solid #FED7AA;border-radius:10px;
             padding:12px 14px;font-size:12px;color:#7C2D12;line-height:1.6;">
            ⚠️ Internal levers max out at <strong>{achievable_pct:.0f}%</strong> reduction — short of your
            <strong>{target_reduction_pct}%</strong> target by <strong>{plan['residual_gap']:,.0f} tCO₂e/yr</strong>.
            Expected for ambitious targets — see <strong>Carbon Credit &amp; Offset Requirement</strong> below
            to close the remaining gap.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin-top:10px;background:#ECFDF5;border:1.5px solid #A7F3D0;border-radius:10px;
             padding:12px 14px;font-size:12px;color:#064E3B;">
            ✅ This target is fully achievable through internal decarbonization levers — no offsetting required.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    ap1, _ap2 = st.columns([1, 3])
    with ap1:
        st.button("✅ Apply Plan to Simulator", type="primary", use_container_width=True, key="apply_plan_btn",
                  on_click=_apply_plan_callback, args=(plan["rec_pct"],))
    if st.session_state.pop("_plan_applied_flag", False):
        st.toast("Action plan applied — scroll up to see the updated simulator ☝️", icon="✅")

    # ═══════════════════════════════════════════════════════════════════════
    # TIER 4 · CARBON CREDIT & OFFSET REQUIREMENT
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:4px;">🌍 Carbon Credit &amp; Offset Requirement</div>
    <div style="font-size:12px;color:#94A3B8;margin-bottom:14px;">
        Estimate offset volume &amp; cost for the gap internal levers cannot eliminate</div>
    """, unsafe_allow_html=True)

    gap_default = max(plan["residual_gap"], 0.0)

    cc1, cc2 = st.columns([1, 1.5], gap="large")
    with cc1:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🧮 Offset Calculator</div>
        """, unsafe_allow_html=True)

        offset_vol = st.number_input("Offset volume (tCO₂e/yr)", min_value=0.0,
                                      value=float(gap_default), step=50.0, key="credit_offset_vol")
        st.markdown(f"<div style='font-size:10px;color:#9CA3AF;margin-top:-8px;margin-bottom:10px;'>"
                    f"Auto-filled from the residual gap above ({gap_default:,.0f} tCO₂e/yr) — adjust freely</div>",
                    unsafe_allow_html=True)
        st.button("🔄 Sync to residual gap", key="sync_gap_btn", use_container_width=True,
                  on_click=_sync_offset_callback, args=(gap_default,))

        project_type = st.selectbox("Credit / project type", list(CREDIT_PROJECT_TYPES.keys()),
                                     key="credit_project_type")
        credit_info = CREDIT_PROJECT_TYPES[project_type]
        st.markdown(f"<div style='font-size:10px;color:#94A3B8;margin-top:-6px;'>{credit_info['note']}</div>",
                    unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    cost_low  = offset_vol * credit_info["low"]
    cost_high = offset_vol * credit_info["high"]

    with cc2:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">💵 Offset Cost Estimate</div>
            <div class="cl-card-subtitle">Indicative 2026 voluntary carbon market range — varies by registry, vintage &amp; quality rating</div>
        """, unsafe_allow_html=True)

        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            kpi_card("Offset Needed", f"{offset_vol:,.0f}", badge="tCO₂e/yr", badge_type="gray",
                     icon="🌍", icon_bg="#F3F4F6")
        with oc2:
            kpi_card("Price Range", f"${credit_info['low']}–{credit_info['high']}", badge="per tCO₂e",
                     badge_type="blue", icon="🏷️", icon_bg="#E0F2FE")
        with oc3:
            kpi_card("Annual Cost", f"${cost_low:,.0f}–{cost_high:,.0f}", badge="USD/yr", badge_type="teal",
                     icon="💵", icon_bg="#CFFAFE")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    rl1, rl2, rl3 = st.columns(3, gap="medium")
    with rl1:
        st.markdown("""
        <div class="cl-card" style="text-align:center;">
            <div style="font-size:26px;margin-bottom:6px;">🥇</div>
            <div style="font-size:12px;font-weight:700;color:#0F172A;">Gold Standard</div>
            <div style="font-size:10px;color:#64748B;margin:4px 0 10px;">Co-benefit-focused VER credits · Indonesia MRA since May 2025</div>
        """, unsafe_allow_html=True)
        st.link_button("🔗 Browse Marketplace", "https://marketplace.goldstandard.org/", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with rl2:
        st.markdown("""
        <div class="cl-card" style="text-align:center;">
            <div style="font-size:26px;margin-bottom:6px;">🌳</div>
            <div style="font-size:12px;font-weight:700;color:#0F172A;">Verra (VCS)</div>
            <div style="font-size:10px;color:#64748B;margin:4px 0 10px;">Largest registry, incl. VM0007 REDD+/blue carbon · Indonesia MRA since Oct 2025</div>
        """, unsafe_allow_html=True)
        st.link_button("🔗 Browse VCS Registry", "https://registry.verra.org/", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with rl3:
        st.markdown("""
        <div class="cl-card" style="text-align:center;">
            <div style="font-size:26px;margin-bottom:6px;">🇮🇩</div>
            <div style="font-size:12px;font-weight:700;color:#0F172A;">IDXCarbon</div>
            <div style="font-size:10px;color:#64748B;margin:4px 0 10px;">Indonesia's domestic exchange (PTBAE-PU / SPE-GRK), OJK-regulated</div>
        """, unsafe_allow_html=True)
        st.link_button("🔗 Visit IDXCarbon", "https://www.idxcarbon.co.id/", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    _gis_result = st.session_state.get("gis_result")
    _gis_tip = []
    if _gis_result and _gis_result.get("redd_eligible_ha", 0) > 0:
        _gis_tip.append({
            "text": (f"<strong>Internal credit source identified:</strong> your GIS Intelligence module flagged "
                     f"<strong>{_gis_result['redd_eligible_ha']:,.0f} ha</strong> of REDD+/blue-carbon-eligible "
                     f"mangrove area. Open <strong>GIS Intelligence</strong> for the site-specific carbon stock "
                     f"analysis before sizing a self-developed credit project."),
            "type": "info", "icon": "🌊",
        })

    insight_panel(_gis_tip + [
        {
            "text": ("<strong>Regulatory context (Indonesia, 2026):</strong> domestic carbon trading now runs under "
                     "<strong>Perpres 110/2025</strong> (replacing Perpres 98/2021), migrating the national registry "
                     "from SRN-PPI to <strong>SRUK</strong> and decoupling voluntary credit sales from the NDC "
                     "accounting cycle — existing systems must align by 10 Oct 2026."),
            "type": "info", "icon": "📋",
        },
        {
            "text": ("<strong>Use with care:</strong> offsets should only cover the residual gap after internal "
                     "abatement (SBTi's Net-Zero Standard expects ≥90–95% real reduction first). Treat the price "
                     "range above as directional — confirm live pricing and Core Carbon Principle (CCP) status on "
                     "the registry before committing."),
            "type": "warn", "icon": "⚠️",
        },
    ])

    # ── Export Section ──────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                color:#0EA5E9;margin-bottom:12px;">📤 Export Simulation Results</div>
    """, unsafe_allow_html=True)

    exp1, exp2, exp3, exp4 = st.columns(4, gap="medium")

    # Build export data
    sim_summary = {
        "simulation_date":    datetime.datetime.now().isoformat(),
        "company":            st.session_state.get("company_name", "Organization"),
        "sector":             sector,
        "baseline_emissions_tco2e": result["cur_em"],
        "projected_emissions_tco2e": result["proj_em"],
        "total_reduction_tco2e":    result["saving"],
        "reduction_percent":        result["reduction_pct"],
        "current_esg_score":        result["cur_score"],
        "projected_esg_score":      result["proj_score"],
        "current_grade":            result["cur_grade"],
        "projected_grade":          result["proj_grade"],
        "investment_estimate_usd":  result["cost_estimate"],
        "cost_per_tco2_usd":        result["cost_per_tco2"],
        "levers": {
            "renewable_energy_pct":    st.session_state.get("sim_renew", 20),
            "energy_efficiency_pct":   st.session_state.get("sim_eff", 10),
            "fleet_electrification_pct": st.session_state.get("sim_fleet", 10),
            "waste_reduction_pct":     st.session_state.get("sim_waste", 20),
            "water_conservation_pct":  st.session_state.get("sim_water", 10),
        },
        "savings_breakdown_tco2e": result["savings_breakdown"],
    }

    breakdown_rows = [
        {"Lever": k, "Reduction (tCO₂e)": v,
         "Share (%)": round(v / max(result["saving"], 1) * 100, 1),
         "Abatement Cost ($/tCO₂e)": round(result["cost_per_tco2"], 1)}
        for k, v in result["savings_breakdown"].items() if v > 0
    ]
    breakdown_rows.append({
        "Lever": "TOTAL",
        "Reduction (tCO₂e)": result["saving"],
        "Share (%)": 100.0,
        "Abatement Cost ($/tCO₂e)": round(result["cost_per_tco2"], 1),
    })
    breakdown_df = pd.DataFrame(breakdown_rows)

    scorecard_df = pd.DataFrame([{
        "Metric": "Baseline Emissions (tCO₂e)",    "Current": f"{result['cur_em']:,.0f}", "Projected": f"{result['proj_em']:,.0f}"},
        {"Metric": "ESG Score",                     "Current": f"{result['cur_score']}/100", "Projected": f"{result['proj_score']}/100"},
        {"Metric": "ESG Grade",                     "Current": result["cur_grade"], "Projected": result["proj_grade"]},
        {"Metric": "Emission Reduction",            "Current": "—", "Projected": f"−{result['reduction_pct']:.0f}%"},
        {"Metric": "Investment Estimate (USD)",     "Current": "—", "Projected": f"${result['cost_estimate']:,}"},
        {"Metric": "Cost per tCO₂e (USD)",          "Current": "—", "Projected": f"${result['cost_per_tco2']}"},
    ])

    with exp1:
        st.markdown("""
        <div class="cl-card" style="text-align:center;padding:18px 14px;">
            <div style="font-size:28px;margin-bottom:8px;">📊</div>
            <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:4px;">
                Lever Breakdown CSV</div>
            <div style="font-size:10px;color:#6B7280;margin-bottom:12px;">
                Per-lever reduction & cost</div>
        """, unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download CSV",
            data=breakdown_df.to_csv(index=False),
            file_name=f"CarbonLens_Simulation_Breakdown.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
            key="sim_dl_csv",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with exp2:
        st.markdown("""
        <div class="cl-card" style="text-align:center;padding:18px 14px;">
            <div style="font-size:28px;margin-bottom:8px;">🎯</div>
            <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:4px;">
                ESG Scorecard CSV</div>
            <div style="font-size:10px;color:#6B7280;margin-bottom:12px;">
                Current vs projected KPIs</div>
        """, unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download CSV",
            data=scorecard_df.to_csv(index=False),
            file_name=f"CarbonLens_Simulation_Scorecard.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
            key="sim_dl_scorecard",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with exp3:
        st.markdown("""
        <div class="cl-card" style="text-align:center;padding:18px 14px;">
            <div style="font-size:28px;margin-bottom:8px;">🔗</div>
            <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:4px;">
                Full Simulation JSON</div>
            <div style="font-size:10px;color:#6B7280;margin-bottom:12px;">
                Complete results · API-ready</div>
        """, unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(sim_summary, indent=2, cls=NumpyEncoder),
            file_name=f"CarbonLens_Simulation.json",
            mime="application/json",
            use_container_width=True,
            type="primary",
            key="sim_dl_json",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with exp4:
        st.markdown("""
        <div class="cl-card" style="text-align:center;padding:18px 14px;">
            <div style="font-size:28px;margin-bottom:8px;">🎯</div>
            <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:4px;">
                Action Plan + Offset JSON</div>
            <div style="font-size:10px;color:#6B7280;margin-bottom:12px;">
                Target plan, levers &amp; credit estimate</div>
        """, unsafe_allow_html=True)
        # Save residual gap for Carbon Credit Center
        if plan.get("residual_gap", 0) > 0:
            S.set("sim_residual_gap_tco2e", round(float(plan["residual_gap"]), 2))
        plan_export = {
            "target_year":               target_year,
            "target_reduction_pct":      target_reduction_pct,
            "achievable_reduction_pct":  round(achievable_pct, 1),
            "achievable_saving_tco2e":   plan["achieved_saving"],
            "residual_gap_tco2e":        plan["residual_gap"],
            "recommended_levers_pct":    plan["rec_pct"],
            "lever_priority_order":      plan["order"],
            "estimated_capex_usd":       plan["achieved_cost"],
            "offset_project_type":       project_type,
            "offset_volume_tco2e":       offset_vol,
            "offset_cost_usd_range":     [round(cost_low), round(cost_high)],
            "registries": {
                "gold_standard_marketplace": "https://marketplace.goldstandard.org/",
                "verra_vcs_registry":        "https://registry.verra.org/",
                "idx_carbon_indonesia":      "https://www.idxcarbon.co.id/",
            },
        }
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(plan_export, indent=2, cls=NumpyEncoder),
            file_name="CarbonLens_ActionPlan_Offset.json",
            mime="application/json",
            use_container_width=True,
            type="primary",
            key="sim_dl_plan_json",
        )
        st.markdown("</div>", unsafe_allow_html=True)
