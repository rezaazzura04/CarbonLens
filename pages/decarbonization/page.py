"""
CarbonLens V8 — Decarbonization Planner. Phase 5-A.

Follows the reference implementation pattern exactly:
  - All service calls at TOP of render()
  - All scalars extracted before any rendering
  - Section functions receive plain Python values only
  - Zero calculations in page
  - RBAC: Analyst/Admin can create+modify; Viewer read-only

Permitted calls: state_service · decarbonization_service
"""
from __future__ import annotations
import streamlit as st

import services.state_service           as state_svc
import services.decarbonization_service as decarb_svc

from components.ui import (
    page_header, kpi_card, metric_card, info_banner,
    empty_state, divider, spacer,
)
from components.provenance_panel import provenance_panel, methodology_footnote
from components.confidence_chip  import confidence_chip
from components.theme.colors      import ENV_COLOR, SUCCESS, WARNING, ERROR
from components.theme.typography  import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, TRACKING_WIDE


# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point. All data fetching before any rendering."""

    # ── 1. Resolve organisation ───────────────────────────────────────────────
    org = state_svc.get_active_organisation()
    if not org or not org.get("company_name"):
        page_header("Decarbonization", destination="decarbonization")
        empty_state("◐", "No organisation configured",
                    "Set up an organisation profile to use the Decarbonization Planner.")
        return

    # ── 2. Fetch ComputedState for baseline ───────────────────────────────────
    di        = state_svc.get_disclosure_inputs()
    scope_inp = state_svc.get_scope_inputs()
    cs        = state_svc.get_computed_state(
        org=org, disclosure_inputs=di, scope_inputs=scope_inp, force=False
    )

    carbon      = cs.get("carbon", {})
    scope1_kg   = float(carbon.get("scope1_kg",  0))
    scope2_kg   = float(carbon.get("scope2_kg",  0))
    scope3_kg   = float(carbon.get("scope3_kg",  0))
    total_kg    = float(carbon.get("total_kg",   0))
    pln_ef      = float(carbon.get("pln_ef_used", 0.716))
    scope_src   = str(carbon.get("scope_source",  "none"))
    company     = str(org.get("company_name",    ""))
    period      = str(org.get("reporting_period",""))
    sector      = str(org.get("sector",          "Manufacturing"))

    # ── 3. Fetch decarbonization state ────────────────────────────────────────
    decarb_state    = decarb_svc.get_decarb_state()
    target          = decarb_state.get("target")
    scenarios       = decarb_state.get("scenarios",          {})
    active_sid      = decarb_state.get("active_scenario_id", "A")
    active_scenario = scenarios.get(active_sid)

    # ── 4. Compute available levers and scenario results ──────────────────────
    available_levers = decarb_svc.get_available_levers(scope1_kg, scope2_kg, scope3_kg)
    scenario_results = decarb_svc.get_all_scenario_results(scope1_kg, scope2_kg, scope3_kg, pln_ef)

    # ── 5. RBAC check ─────────────────────────────────────────────────────────
    can_edit = state_svc.check_permission("can_upload")   # analysts + admins

    # ── 6. Render page ────────────────────────────────────────────────────────
    _s1_header(company, period, scope_src, bool(target))
    _s2_baseline(total_kg, scope1_kg, scope2_kg, scope3_kg, scope_src, period)
    _s3_target_definition(target, total_kg, period, can_edit)
    _s4_scenario_builder(active_sid, active_scenario, available_levers, can_edit, total_kg)
    _s5_scenario_comparison(scenario_results, target, total_kg)
    _s6_action_plan(scenario_results, active_scenario, target)
    _s7_assumption_transparency(active_scenario, available_levers, pln_ef)
    _s8_quick_actions()
    methodology_footnote()


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_header(company: str, period: str, scope_src: str, has_target: bool) -> None:
    badge = "Target set" if has_target else "No target"
    page_header(
        title       = "Decarbonization Planner",
        subtitle    = f"{company}  ·  {period}" if period else company,
        badge       = badge,
        badge_type  = "green" if has_target else "neutral",
        destination = "decarbonization",
    )
    if scope_src == "none":
        info_banner(
            "No emission data loaded. Upload data in ESG Analytics or "
            "enter activity data in Carbon Accounting to activate scenario planning.",
            variant="warning",
        )


def _s2_baseline(
    total_kg: float, scope1_kg: float, scope2_kg: float,
    scope3_kg: float, scope_src: str, period: str,
) -> None:
    divider("Baseline Emissions")

    total_tco2e  = round(total_kg  / 1000, 2)
    scope1_tco2e = round(scope1_kg / 1000, 2)
    scope2_tco2e = round(scope2_kg / 1000, 2)
    scope3_tco2e = round(scope3_kg / 1000, 2)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Baseline Total", f"{total_tco2e:.1f}",
                 delta_label=f"tCO2e · {period}",
                 badge="Measured" if scope_src == "carbon_accounting" else "Estimated",
                 badge_type="green" if scope_src == "carbon_accounting" else "yellow")
    with c2:
        kpi_card("Scope 1", f"{scope1_tco2e:.2f}", delta_label="tCO2e")
    with c3:
        kpi_card("Scope 2", f"{scope2_tco2e:.2f}", delta_label="tCO2e")
    with c4:
        kpi_card("Scope 3", f"{scope3_tco2e:.2f}", delta_label="tCO2e")

    _label_note("Baseline", scope_src)
    spacer(8)


def _s3_target_definition(
    target: dict, baseline_kg: float, baseline_period: str, can_edit: bool,
) -> None:
    divider("Reduction Target")

    if target:
        tgt_pct = float(target.get("reduction_target_pct", 0))
        tgt_kg  = float(target.get("target_kg", 0))
        tgt_yr  = str(target.get("target_year",""))
        tgt_t   = round(tgt_kg / 1000, 2)
        remaining = round((baseline_kg - tgt_kg) / 1000, 2)

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("Reduction Target",   f"{tgt_pct:.1f}%", badge="User-provided", badge_type="blue")
        with c2:
            kpi_card("Target Emissions",   f"{tgt_t:.1f}", delta_label=f"tCO2e by {tgt_yr}")
        with c3:
            kpi_card("Required Reduction", f"{remaining:.1f}", delta_label="tCO2e to remove")

    if can_edit:
        with st.expander("✏️  Set Reduction Target", expanded=not bool(target)):
            st.caption("Define your science-based or regulatory target.")
            c1, c2, c3 = st.columns(3)
            with c1:
                tgt_year = st.selectbox(
                    "Target year",
                    [str(y) for y in range(2028, 2051)],
                    index=2,   # 2030 default
                    key="decarb_target_year",
                )
            with c2:
                tgt_pct_inp = st.number_input(
                    "Reduction target (%)", min_value=1.0, max_value=100.0,
                    value=float(target.get("reduction_target_pct", 30.0) if target else 30.0),
                    step=5.0, key="decarb_target_pct",
                )
            with c3:
                spacer(20)
                if st.button("Set Target", type="primary", key="decarb_set_target"):
                    if baseline_kg > 0:
                        decarb_svc.set_reduction_target(
                            baseline_kg, baseline_period, tgt_year, tgt_pct_inp
                        )
                        st.rerun()
                    else:
                        st.error("Cannot set target — no baseline emissions available.")
    elif not target:
        info_banner("Viewer access: Analysts and Admins can set reduction targets.", "info")
    spacer(8)


def _s4_scenario_builder(
    active_sid:       str,
    active_scenario:  dict,
    available_levers: list,
    can_edit:         bool,
    baseline_kg:      float,
) -> None:
    divider("Scenario Builder")

    col_sel, col_name = st.columns([1, 3])
    with col_sel:
        sid = st.selectbox(
            "Active scenario", ["A", "B", "C"],
            index=["A","B","C"].index(active_sid),
            key="decarb_active_sid",
        )
        if sid != active_sid:
            state = decarb_svc.get_decarb_state()
            state["active_scenario_id"] = sid
            decarb_svc.save_decarb_state(state)
            st.rerun()

    with col_name:
        scen_name = active_scenario.get("name","") if active_scenario else ""
        scen_desc = active_scenario.get("description","") if active_scenario else ""
        if can_edit:
            new_name = st.text_input(
                "Scenario name", value=scen_name or f"Scenario {active_sid}",
                key=f"decarb_name_{active_sid}",
            )
            if not active_scenario and new_name:
                if st.button(f"Create Scenario {active_sid}", key=f"create_{active_sid}"):
                    decarb_svc.create_scenario(active_sid, new_name)
                    st.rerun()
        else:
            st.markdown(f"**{scen_name or 'No scenario'}**")

    if not active_scenario:
        info_banner(f"Scenario {active_sid} not created yet. Enter a name and click Create.", "info")
        spacer(8)
        return

    if can_edit:
        spacer(4)
        st.caption("Select mitigation levers and configure reduction percentages.")
        lever_configs = list(active_scenario.get("levers", []))
        existing_ids  = {l["lever_id"] for l in lever_configs}

        col_add, col_empty = st.columns([3, 1])
        with col_add:
            lever_options = {
                l["lever_id"]: f"{'✓ ' if l['lever_id'] in existing_ids else ''}"
                               f"{l['name']}"
                               f"{' — ' + l.get('unavailable_note','') if not l['available'] else ''}"
                for l in available_levers
            }
            sel_lever = st.selectbox(
                "Add mitigation lever",
                [None] + list(lever_options.keys()),
                format_func=lambda k: "— Select lever —" if k is None else lever_options[k],
                key="decarb_lever_select",
            )
            if sel_lever and sel_lever not in existing_ids:
                lever_def = next(l for l in available_levers if l["lever_id"] == sel_lever)
                if lever_def.get("available", True):
                    if st.button(f"Add {lever_def['name']}", key=f"add_{sel_lever}"):
                        new_lever = {
                            "lever_id":             lever_def["lever_id"],
                            "name":                 lever_def["name"],
                            "reduction_pct":        lever_def["default_reduction_pct"],
                            "implementation_year":  2027,
                            "assumption_type":      "carbonlens-default",
                            "scope":                lever_def["scope"],
                        }
                        lever_configs.append(new_lever)
                        decarb_svc.update_scenario_levers(active_sid, lever_configs)
                        st.rerun()
                else:
                    info_banner(lever_def.get("unavailable_note",""), "info")

        if lever_configs:
            spacer(4)
            st.caption("Configure lever parameters:")
            updated_levers = list(lever_configs)
            levers_changed = False

            for i, lever in enumerate(lever_configs):
                lid   = lever["lever_id"]
                name  = lever["name"]
                c_pct, c_yr, c_del = st.columns([2, 1, 1])
                with c_pct:
                    new_pct = st.number_input(
                        f"{name} (%)", min_value=1.0, max_value=100.0,
                        value=float(lever["reduction_pct"]),
                        step=5.0, key=f"lever_pct_{active_sid}_{lid}",
                    )
                    if new_pct != lever["reduction_pct"]:
                        updated_levers[i] = {**lever, "reduction_pct": new_pct,
                                             "assumption_type": "user-provided"}
                        levers_changed = True
                with c_yr:
                    yr = st.number_input(
                        "Year", min_value=2024, max_value=2050,
                        value=int(lever.get("implementation_year", 2027)),
                        step=1, key=f"lever_yr_{active_sid}_{lid}",
                    )
                    if yr != lever.get("implementation_year", 2027):
                        updated_levers[i] = {**updated_levers[i], "implementation_year": yr}
                        levers_changed = True
                with c_del:
                    spacer(20)
                    if st.button("Remove", key=f"remove_{active_sid}_{lid}"):
                        updated_levers = [l for l in updated_levers if l["lever_id"] != lid]
                        decarb_svc.update_scenario_levers(active_sid, updated_levers)
                        st.rerun()

            c_save, _ = st.columns([1, 3])
            with c_save:
                if st.button("💾 Save Scenario", type="primary",
                             key=f"save_{active_sid}"):
                    if levers_changed:
                        decarb_svc.update_scenario_levers(active_sid, updated_levers)
                    decarb_svc.save_named_scenario(active_sid)
                    st.rerun()
    else:
        info_banner("Viewer access: Analysts and Admins can configure scenarios.", "info")
    spacer(8)


def _s5_scenario_comparison(
    results:    list,
    target:     dict,
    baseline_kg: float,
) -> None:
    divider("Scenario Comparison")

    if not results:
        info_banner("Create at least one scenario to see a comparison chart.", "info")
        spacer(8)
        return

    try:
        import plotly.graph_objects as go
        baseline_t  = round(baseline_kg / 1000, 2)
        target_t    = round(target["target_kg"] / 1000, 2) if target else None

        labels = ["Baseline"] + [r["scenario_name"] or r["scenario_id"] for r in results]
        values = [baseline_t] + [round(r["total_kg"] / 1000, 2) for r in results]
        colors = ["#94A3B8"] + [
            "#059669" if not r.get("above_target", True) else "#DC2626"
            for r in results
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels, y=values,
            marker_color=colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
        ))
        if target_t:
            fig.add_hline(
                y=target_t, line_dash="dot", line_color="#D97706",
                annotation_text=f"Target: {target_t:.1f} tCO2e",
                annotation_position="bottom right",
            )
        fig.update_layout(
            title       = "Scenario vs Baseline Emissions (tCO2e)",
            yaxis_title = "tCO2e",
            xaxis       = dict(showgrid=False),
            yaxis       = dict(gridcolor="#F1F5F9"),
            plot_bgcolor = "#FFFFFF", paper_bgcolor="#FFFFFF",
            margin      = dict(l=0, r=0, t=50, b=0),
            showlegend  = False, height=280,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except ImportError:
        st.caption("plotly required for comparison chart.")

    for r in results:
        red_pct = float(r.get("reduction_pct", 0))
        above   = bool(r.get("above_target", True))
        color   = "#059669" if not above else "#DC2626"
        gap_lbl = r.get("gap_label", "")
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:8px 12px;'
            f'background:#F8FAFC;border-radius:0 8px 8px 0;margin-bottom:6px;">'
            f'<span style="font-weight:{WEIGHT_BOLD};color:#0F172A;">'
            f'{r.get("scenario_name","") or r.get("scenario_id","")}</span>  '
            f'<span style="color:{color};">−{red_pct:.1f}%</span>  '
            f'<span style="font-size:{SIZE_SM};color:#64748B;">{gap_lbl}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    _label_note("Scenario comparison", "modelled")
    spacer(8)


def _s6_action_plan(results: list, active_scenario: dict, target: dict) -> None:
    divider("Action Plan")

    if not active_scenario or not active_scenario.get("levers"):
        info_banner("Add levers in the Scenario Builder to generate an action plan.", "info")
        spacer(8)
        return

    target_yr    = int(target.get("target_year", 2030)) if target else 2030
    levers       = active_scenario.get("levers", [])

    st.caption(f"**{active_scenario.get('name','')} — Implementation Timeline**")

    for lever in sorted(levers, key=lambda l: l.get("implementation_year", 2030)):
        yr    = lever.get("implementation_year", 2030)
        name  = lever.get("name","")
        pct   = float(lever.get("reduction_pct", 0))
        atype = lever.get("assumption_type","carbonlens-default")
        color = "#0891B2" if atype == "user-provided" else "#94A3B8"

        st.markdown(
            f'<div style="display:flex;gap:12px;padding:8px 0;'
            f'border-bottom:1px solid #F1F5F9;align-items:center;">'
            f'<span style="font-size:13px;font-weight:{WEIGHT_BOLD};color:{color};'
            f'min-width:48px;">{yr}</span>'
            f'<span style="font-size:{SIZE_SM};color:#0F172A;">{name}</span>'
            f'<span style="font-size:{SIZE_XS};color:#64748B;">−{pct:.0f}%</span>'
            f'<span style="font-size:{SIZE_XS};background:{"#E0F2FE" if atype=="user-provided" else "#F1F5F9"};'
            f'color:{color};padding:1px 6px;border-radius:8px;">'
            f'{"User-provided" if atype=="user-provided" else "CarbonLens default"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    spacer(8)


def _s7_assumption_transparency(
    active_scenario: dict,
    available_levers: list,
    pln_ef: float,
) -> None:
    divider("Assumption Transparency")

    prov_rows = _build_decarb_provenance_rows(active_scenario, available_levers, pln_ef)
    provenance_panel(
        title            = "Decarbonization Scenario",
        rows             = prov_rows,
        key              = "decarb_prov",
        expanded         = False,
        methodology_note = (
            "CarbonLens V8 Phase 5-A · Modelled estimates only · "
            "Not verified by a third party · "
            "Linear interpolation trajectory"
        ),
        show_download    = True,
    )

    info_banner(
        "All scenario outputs are modelled estimates. "
        "Assumption types are labelled: Measured · User-provided · "
        "CarbonLens default · Modelled estimate. "
        "Do not present modelled reductions as measured reductions "
        "in formal sustainability disclosures without independent verification.",
        variant="warning",
    )
    spacer(8)


def _s8_quick_actions() -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◉ Executive Summary", use_container_width=True, key="decarb_qa_exec"):
            state_svc.navigate_to("executive_summary"); st.rerun()
    with col2:
        if st.button("◈ Carbon Accounting", use_container_width=True, key="decarb_qa_carbon"):
            state_svc.navigate_to("carbon_accounting"); st.rerun()
    with col3:
        if st.button("◎ Reporting", use_container_width=True, key="decarb_qa_report"):
            state_svc.navigate_to("reporting_compliance"); st.rerun()
    spacer(16)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _label_note(context: str, source: str) -> None:
    """Render a small provenance label beneath a data display."""
    labels = {
        "carbon_accounting": ("Measured", "Data sourced from Carbon Accounting form"),
        "csv_estimate":      ("Estimated", "Extrapolated from total CSV emission figure"),
        "csv_scope_columns": ("CSV-derived", "Sourced from uploaded CSV scope columns"),
        "modelled":          ("Modelled estimate", "Result of scenario calculation"),
        "none":              ("No data", "Upload emission data to activate"),
    }
    badge, desc = labels.get(source, ("User-provided", ""))
    st.markdown(
        f'<div style="font-size:{SIZE_XS};color:#94A3B8;margin-top:4px;">'
        f'<span style="background:#F1F5F9;padding:1px 6px;border-radius:8px;">'
        f'{badge}</span>  {desc}</div>',
        unsafe_allow_html=True,
    )


def _build_decarb_provenance_rows(
    active_scenario: dict,
    available_levers: list,
    pln_ef: float,
) -> list:
    """Build provenance rows for the transparency panel. No arithmetic."""
    lever_map = {l["lever_id"]: l for l in available_levers}
    rows = [
        {
            "label":   "Calculation method",
            "value":   "Sequential lever application",
            "source":  "CarbonLens V8 Phase 5-A",
            "formula": "Lever N acts on emissions remaining after Levers 0…(N-1)",
            "note":    "Conservative — subsequent levers have diminishing returns",
        },
        {
            "label":   "PLN grid factor (electrification lever)",
            "value":   f"{pln_ef:.4f} kg CO₂e/kWh",
            "source":  "Kepmen ESDM No.18/2023",
            "formula": "Used for S1→S2 electrification net calculation",
            "note":    "Province-specific factor applied where province is known",
        },
        {
            "label":   "Trajectory model",
            "value":   "Linear interpolation",
            "source":  "CarbonLens V8 Phase 5-A",
            "formula": "Emissions(yr) = Baseline + (Target − Baseline) × (yr/n_years)",
            "note":    "Real pathways are non-linear — for direction indication only",
        },
    ]
    if active_scenario:
        for lever in active_scenario.get("levers", []):
            lid       = lever.get("lever_id","")
            lever_def = lever_map.get(lid, {})
            rows.append({
                "label":   lever.get("name", lid),
                "value":   f"{lever.get('reduction_pct',0):.1f}% reduction",
                "source":  lever_def.get("source", "CarbonLens default"),
                "formula": lever_def.get("unit",""),
                "note":    lever.get("assumption_type","carbonlens-default")
                           + (" · " + lever_def.get("limitation","") if lever_def.get("limitation") else ""),
            })
    return rows
