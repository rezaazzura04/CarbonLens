"""
CarbonLens V7 — Carbon Accounting
GHG Protocol · Scope 1, 2, and 12 Scope 3 categories
Multiple intensity normalizations: per m², per employee, per Rp miliar
"""

import streamlit as st
import utils.state as S
from utils.state import set_scope_results
from components.ui import page_header, kpi_card, scope_bar, recommendation_card
from utils.charts import scope_donut, benchmark_bar
from utils.calculations import (
    calculate_scope1, calculate_scope2, calculate_scope3,
    calculate_total_emission, calculate_intensity,
    calculate_esg_score, get_benchmark, benchmark_gap,
    emission_category, SCOPE3_CATS,
)
from config.settings import COLORS, INDUSTRY_BENCHMARKS, PLN_GRID_SUBSYSTEM


# ─────────────────────────────────────────────────────────────────────────────
# INTENSITY DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def _intensity_card(label: str, value: float, unit: str, bench: float,
                    bench_unit: str, color: str):
    above = value > bench
    gap   = ((value - bench) / max(bench, 1)) * 100
    st.markdown(f"""
    <div style="border:1px solid {'#FEE2E2' if above else '#DCFCE7'};
                border-top:4px solid {'#EF4444' if above else '#10B981'};
                border-radius:10px;padding:14px 16px;background:white;text-align:center;">
        <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.8px;color:#9CA3AF;margin-bottom:6px;">{label}</div>
        <div style="font-size:26px;font-weight:800;color:#111827;letter-spacing:-0.5px;line-height:1;">
            {value:.2f}</div>
        <div style="font-size:10px;color:#6B7280;margin-bottom:8px;">{unit}</div>
        <div style="height:5px;background:#F3F4F6;border-radius:3px;overflow:hidden;margin-bottom:6px;">
            <div style="width:{min(value/max(bench,1)*100,100):.0f}%;height:100%;
                        background:{'#EF4444' if above else '#10B981'};border-radius:3px;"></div>
        </div>
        <div style="font-size:10px;font-weight:600;color:{'#EF4444' if above else '#10B981'};">
            {gap:+.0f}% vs benchmark ({bench_unit})</div>
    </div>
    """, unsafe_allow_html=True)


def render():
    S.init()

    page_header(
        title="Carbon Accounting",
        subtitle="GHG Protocol · ISO 14064-1 · Scope 1 · Scope 2 · 12 Scope 3 categories · Multiple intensity metrics",
        badge="ISO 14064 Ready",
        badge_type="blue",
    )

    sector   = S.get("sector",   "Manufacturing")
    area_m2  = float(S.get("area_m2", 5000.0))
    employees= int(S.get("employees", 100))
    company  = S.get("company_name", "Your Organization")

    left, right = st.columns([1, 1.65], gap="large")

    # ── LEFT: Input forms ────────────────────────────────────────────────────
    with left:

        # Scope 1
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🔥 Scope 1 — Direct Emissions</div>
            <div class="cl-card-subtitle">On-site combustion · Owned vehicles · Stationary sources</div>
        """, unsafe_allow_html=True)
        diesel  = st.number_input("Diesel (liters/yr)",      0.0, step=10.0,  key="s1_diesel",  help="Generators, boilers, company vehicles")
        petrol  = st.number_input("Petrol (liters/yr)",      0.0, step=10.0,  key="s1_petrol")
        lpg     = st.number_input("LPG (kg/yr)",             0.0, step=1.0,   key="s1_lpg")
        nat_gas = st.number_input("Natural Gas (m³/yr)",     0.0, step=1.0,   key="s1_natgas")


        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Scope 2
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">⚡ Scope 2 — Purchased Electricity</div>
            <div class="cl-card-subtitle">Grid electricity · EF = 0.85 kg CO₂e/kWh (PLN Indonesia 2023)</div>
        """, unsafe_allow_html=True)
        electricity = st.number_input("Grid electricity (kWh/yr)", 0.0, step=100.0, key="s2_elec")
        province_opts = ["(National average)"] + sorted(PLN_GRID_SUBSYSTEM.keys())
        province_sel  = st.selectbox(
            "PLN Grid Region (optional)",
            province_opts, key="s2_province",
            help="Select your province to use the PLN regional subsystem emission factor (Kepmen ESDM 18/2023). Defaults to national average 0.7160 kg CO₂e/kWh.",
        )
        _prov = province_sel if province_sel != "(National average)" else ""
        S.set("province", _prov)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Scope 3 — 12 categories
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🌐 Scope 3 — 12 GHG Protocol Categories</div>
            <div class="cl-card-subtitle">Activity-based · Peer-reviewed emission factors · Enter 0 for unreported categories</div>
        """, unsafe_allow_html=True)

        with st.expander("ℹ️ About Scope 3 & emission factors", expanded=False):
            st.markdown("""
            Scope 3 covers **indirect value chain emissions** per GHG Protocol.
            CarbonLens covers the **12 most material categories** for organizations in Indonesia.

            | Source | Emission Factor | Reference |
            |--------|----------------|-----------|
            | USEEIO v2.0 | Spend-based IO | EPA, 2023 |
            | DEFRA 2023  | Air travel, T&D | UK BEIS, 2023 |
            | GLEC v3     | Freight transport | ITF/SmartFreight, 2023 |
            | IPCC 2006   | Waste disposal | IPCC, 2006 |
            | MEMR 2023   | Indonesia grid EF | Ministry of Energy, 2023 |
            | IPCC AR6    | Commuting modes | IPCC, 2022 |
            """)

        s3_inputs = {}

        # Group categories into logical sections
        groups = {
            "🏭 Upstream (Cats. 1–4)": [
                "cat1_purchased_goods_usd",
                "cat2_capital_goods_usd",
                "cat3_fuel_energy_kwh",
                "cat4_upstream_transport_tkm",
            ],
            "🗑️ Operations (Cat. 5)": [
                "cat5_waste_landfill_tonne",
            ],
            "✈️ People & Travel (Cats. 6–7)": [
                "cat6_business_travel_km",
                "cat7_employee_commute_km",
            ],
            "🏢 Leased & Downstream (Cats. 8–9, 11–13)": [
                "cat8_upstream_leased_kwh",
                "cat9_downstream_transport_tkm",
                "cat11_use_of_sold_products_kwh",
                "cat12_eol_waste_tonne",
                "cat13_downstream_leased_kwh",
            ],
        }

        for grp_label, keys in groups.items():
            st.markdown(f"<div style='font-size:11px;font-weight:700;color:#0EA5E9;margin:12px 0 6px;'>{grp_label}</div>",
                        unsafe_allow_html=True)
            for key in keys:
                label, unit, ef, source = SCOPE3_CATS[key]
                short_label = label.split("—")[1].strip() if "—" in label else label
                val = st.number_input(
                    f"{short_label} ({unit})",
                    min_value=0.0, step=1.0, key=f"s3_{key}",
                    help=f"EF: {ef} kg CO₂e/{unit.split('/')[0]} · {source[:60]}...",
                )
                s3_inputs[key] = val
                S.set(f"s3_{key}", val)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Building settings
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">🏢 Building & Revenue Settings</div>
            <div class="cl-card-subtitle">Used for intensity normalization — pre-filled from organization profile</div>
        """, unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            area_input  = st.number_input("Floor area (m²)", 1.0, value=area_m2, step=50.0, key="ca_area")
            emp_input   = st.number_input("Employees",        1,   value=employees, step=5,  key="ca_emp")
        with c2:
            revenue_rp  = st.number_input("Annual Revenue (Rp miliar)", 0.0, step=1.0, key="ca_revenue",
                                           help="Used for revenue-intensity: kg CO₂e / Rp miliar")
            sector_input= st.selectbox("Sector", list(INDUSTRY_BENCHMARKS.keys()),
                                        index=list(INDUSTRY_BENCHMARKS.keys()).index(sector)
                                              if sector in INDUSTRY_BENCHMARKS else 0, key="ca_sector")
        S.set("area_m2",   float(area_input))
        S.set("employees", int(emp_input))
        S.set("sector",    sector_input)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── CALCULATIONS ─────────────────────────────────────────────────────────
    _custom_ef = S.get("emission_factors")
    s1  = calculate_scope1(diesel, petrol, lpg, nat_gas, ef=_custom_ef)
    _province = S.get("province", "")
    s2  = calculate_scope2(electricity, province=_province, ef=_custom_ef)
    _cat1_override = S.get("scope3_cat1_override_tco2e")
    _cat1_source    = S.get("scope3_cat1_source", "")
    s3  = calculate_scope3(cat1_override_tco2e=_cat1_override, cat1_override_source=_cat1_source, **s3_inputs)

    total_kg   = calculate_total_emission(s1["total"], s2["total"], s3["total"])


    # ── GHG Inventory Download (uses computed s1/s2/s3) ──────────────────
    import pandas as _pd
    inv_rows = [
        {"Scope": "Scope 1",  "Category": "Direct combustion",    "kg_CO2e": round(s1["total"],2), "tCO2e": round(s1["total"]/1000,4)},
        {"Scope": "Scope 2",  "Category": "Purchased electricity", "kg_CO2e": round(s2["total"],2), "tCO2e": round(s2["total"]/1000,4)},
    ]
    for cat_key, cat_data in s3.get("breakdown",{}).items():
        kg = cat_data["kg_co2e"] if isinstance(cat_data, dict) else cat_data
        label = cat_data.get("label", cat_key) if isinstance(cat_data, dict) else cat_key
        inv_rows.append({"Scope":"Scope 3","Category":label,"kg_CO2e":round(kg,2),"tCO2e":round(kg/1000,4)})
    inv_rows.append({"Scope":"TOTAL","Category":"All scopes","kg_CO2e":round(total_kg,2),"tCO2e":round(total_kg/1000,4)})
    inv_df = _pd.DataFrame(inv_rows)
    dl_col, _ = st.columns([1, 3])
    with dl_col:
        st.download_button(
            "⬇️  Download GHG Inventory CSV",
            data=inv_df.to_csv(index=False).encode(),
            file_name=f"carbonlens_ghg_inventory_{_pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Scope 1, 2 & 3 breakdown for audit trail",
        )

    total_tco2 = total_kg / 1000
    bench      = get_benchmark(sector_input)

    # Intensity normalizations
    intens_m2  = (total_kg / max(float(area_input), 1))                  # kg/m²
    intens_emp = (total_kg / max(float(emp_input), 1))                   # kg/employee
    intens_rev = (total_kg / max(float(revenue_rp), 0.001))              # kg/Rp miliar (if entered)

    # ── Persist scope totals to shared state FIRST (used by canonical ESG calc) ──
    rev_input = float(st.session_state.get("ca_revenue", 0.0))
    set_scope_results(
        scope1_kg  = s1["total"],
        scope2_kg  = s2["total"],
        scope3_kg  = s3["total"],
        area_m2    = float(area_input),
        employees  = int(emp_input),
        revenue_rp = rev_input,
    )

    # ESG score — canonical, single source of truth (uses scope results above)
    from utils.state import compute_canonical_esg
    with st.spinner("🔄 Recalculating ESG score..."):
        esg  = compute_canonical_esg(force=True)
    gap  = benchmark_gap(intens_m2, bench)

    # ── RIGHT: Results ───────────────────────────────────────────────────────
    with right:

        # Summary KPIs
        k1, k2, k3, k4 = st.columns(4, gap="small")
        with k1:
            kpi_card("Scope 1", f"{s1['total']/1000:.2f}",
                     badge="tCO₂e", badge_type="gray",
                     delta=f"{s1['total']/max(total_kg,1)*100:.0f}% of total",
                     icon="🔥", icon_bg="#FEE2E2")
        with k2:
            kpi_card("Scope 2", f"{s2['total']/1000:.2f}",
                     badge="tCO₂e", badge_type="gray",
                     delta=f"{s2['total']/max(total_kg,1)*100:.0f}% of total",
                     icon="⚡", icon_bg="#FFF7ED")
        with k3:
            s3_disp = f"{s3['total']/1000:.2f}" if s3["has_data"] else "—"
            kpi_card("Scope 3", s3_disp,
                     badge=f"{s3['n_categories']}/12 cats" if s3["has_data"] else "Enter data",
                     badge_type="teal" if s3["has_data"] else "yellow",
                     delta=f"{s3['completeness']}% coverage",
                     icon="🌐", icon_bg="#ECFEFF")
        with k4:
            kpi_card("Total GHG", f"{total_tco2:.2f}",
                     badge="tCO₂e/year", badge_type="gray",
                     delta=f"Grade {esg['grade']} · {esg['score']}/100",
                     icon="☁️", icon_bg="#F9FAFB")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # ── Intensity normalization toggle ────────────────────────────────────
        st.markdown("""
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                    color:#0EA5E9;margin-bottom:10px;">📏 Intensity Normalization</div>
        """, unsafe_allow_html=True)

        norm_mode = st.radio(
            "", ["Per m² (Area)", "Per Employee", "Per Rp Miliar Revenue", "Show All"],
            horizontal=True, key="norm_mode", label_visibility="collapsed",
        )

        if norm_mode == "Show All":
            ia, ib, ic = st.columns(3, gap="medium")
            with ia:
                _intensity_card("Per m² (Area)", intens_m2, "kg CO₂e/m²",
                                bench, f"{bench} kg/m²", COLORS["primary"])
            with ib:
                bench_emp = bench * float(area_input) / max(float(emp_input), 1)
                _intensity_card("Per Employee", intens_emp, "kg CO₂e/emp",
                                bench_emp, f"{bench_emp:.0f} kg/emp", COLORS["warning"])
            with ic:
                if revenue_rp > 0:
                    bench_rev = bench * float(area_input) / max(float(revenue_rp), 0.001)
                    _intensity_card("Per Rp Miliar", intens_rev, "kg CO₂e/Rp M",
                                    bench_rev, f"{bench_rev:.0f} kg/RpM", COLORS["info"])
                else:
                    st.markdown("""
                    <div style="border:1px solid #E5E7EB;border-radius:10px;padding:14px 16px;
                                background:#F9FAFB;text-align:center;font-size:12px;color:#9CA3AF;">
                        Enter annual revenue<br>to see revenue intensity</div>
                    """, unsafe_allow_html=True)

        elif norm_mode == "Per m² (Area)":
            col_i, _ = st.columns([1, 2])
            with col_i:
                _intensity_card("Carbon Intensity (Area)", intens_m2, "kg CO₂e/m²",
                                bench, f"{bench} kg/m²", COLORS["primary"])

        elif norm_mode == "Per Employee":
            col_i, _ = st.columns([1, 2])
            bench_emp = bench * float(area_input) / max(float(emp_input), 1)
            with col_i:
                _intensity_card("Carbon Intensity (Employee)", intens_emp, "kg CO₂e/employee",
                                bench_emp, f"{bench_emp:.0f} kg/emp", COLORS["warning"])

        elif norm_mode == "Per Rp Miliar Revenue":
            if revenue_rp > 0:
                col_i, _ = st.columns([1, 2])
                bench_rev = bench * float(area_input) / max(float(revenue_rp), 0.001)
                with col_i:
                    _intensity_card("Carbon Intensity (Revenue)", intens_rev, "kg CO₂e/Rp miliar",
                                    bench_rev, f"{bench_rev:.0f} kg/RpM", COLORS["info"])
            else:
                st.info("Enter Annual Revenue (Rp miliar) in the settings panel to see revenue-based intensity.")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # Charts row
        ch1, ch2 = st.columns(2, gap="medium")
        with ch1:
            st.markdown("""
            <div class="cl-card">
                <div class="cl-card-title">⬡ GHG Scope Breakdown</div>
                <div class="cl-card-subtitle">Scope 1, 2 & 3 · tCO₂e</div>
            """, unsafe_allow_html=True)
            fig = scope_donut(round(s1["total"]/1000,2), round(s2["total"]/1000,2),
                              round(s3["total"]/1000,2), height=220)
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception as _chart_err:
                st.warning(f"⚠️ Chart unavailable — {_chart_err}")
            scope_bar("Scope 1", s1["total"]/1000, total_tco2, color=COLORS["danger"])
            scope_bar("Scope 2", s2["total"]/1000, total_tco2, color=COLORS["warning"])
            scope_bar("Scope 3", s3["total"]/1000, total_tco2, color=COLORS["info"])
            st.markdown("</div>", unsafe_allow_html=True)

        with ch2:
            st.markdown("""
            <div class="cl-card">
                <div class="cl-card-title">📊 Benchmark Comparison</div>
                <div class="cl-card-subtitle">Carbon intensity vs sector · kg CO₂e/m²</div>
            """, unsafe_allow_html=True)
            fig2 = benchmark_bar(intens_m2, bench, sector_input, height=220)
            try:
                st.plotly_chart(fig2, use_container_width=True)
            except Exception as _chart_err:
                st.warning(f"⚠️ Chart unavailable — {_chart_err}")
            st.markdown("</div>", unsafe_allow_html=True)

        # Scope 3 breakdown table
        if s3["has_data"]:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div class="cl-card">
                <div class="cl-card-title">🌐 Scope 3 Category Breakdown</div>
                <div class="cl-card-subtitle">Activity-based calculation · Full emission factor provenance</div>
            """, unsafe_allow_html=True)

            total_s3 = s3["total"]
            for key, cat in s3["breakdown"].items():
                pct = cat["kg_co2e"] / max(total_s3, 1) * 100
                st.markdown(f"""
                <div style="padding:9px 0;border-bottom:1px solid #F3F4F6;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div style="flex:1;">
                            <div style="font-size:12px;font-weight:600;color:#374151;">{cat['label']}</div>
                            <div style="font-size:10px;color:#9CA3AF;margin-top:2px;">
                                {cat['activity']:,.1f} {cat['unit']} × {cat['ef']} kg CO₂e/{cat['unit'].split('/')[0]}
                            </div>
                            <div style="font-size:9px;color:#D1D5DB;margin-top:1px;">📚 {cat['source'][:70]}...</div>
                        </div>
                        <div style="text-align:right;flex-shrink:0;margin-left:12px;">
                            <div style="font-size:13px;font-weight:800;color:#111827;">{cat['kg_co2e']/1000:.3f} tCO₂e</div>
                            <div style="font-size:10px;color:#9CA3AF;">{pct:.1f}%</div>
                        </div>
                    </div>
                    <div style="height:4px;background:#F3F4F6;border-radius:2px;margin-top:6px;overflow:hidden;">
                        <div style="width:{pct:.0f}%;height:100%;background:#06B6D4;border-radius:2px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            missing = len(SCOPE3_CATS) - s3["n_categories"]
            if missing > 0:
                st.markdown(f"""
                <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
                            padding:9px 12px;margin-top:10px;font-size:11px;color:#92400E;">
                    ⚠️ <strong>{missing} of 12 categories unreported.</strong>
                    GHG Protocol recommends disclosing all material categories.
                    Current Scope 3 coverage: <strong>{s3['completeness']}%</strong>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Recommendations
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">💡 Priority Reduction Actions</div>
            <div class="cl-card-subtitle">Derived from your emission profile · Ranked by tCO₂e impact</div>
        """, unsafe_allow_html=True)
        if s2["total"] >= s1["total"]:
            recommendation_card(
                "Renewable Energy (Scope 2)",
                f"Electricity is your largest source ({s2['total']/max(total_kg,1)*100:.0f}%). "
                f"30% solar PPA saves ~{s2['total']*0.30*0.85/1000:.1f} tCO₂e/yr "
                f"and improves intensity by {s2['total']*0.30*0.85/max(float(area_input),1):.1f} kg/m².",
                impact=f"−{s2['total']*0.30*0.85/1000:.1f} tCO₂e/yr",
                priority="high",
            )
        if s1["total"] > 0:
            recommendation_card(
                "Fleet Electrification (Scope 1)",
                f"Direct combustion contributes {s1['total']/max(total_kg,1)*100:.0f}% of GHG. "
                f"30% EV fleet switch eliminates ~{s1['total']*0.22/1000:.2f} tCO₂e/yr.",
                impact=f"−{s1['total']*0.22/1000:.2f} tCO₂e/yr",
                priority="high",
            )
        if not s3["has_data"]:
            recommendation_card(
                "Complete Scope 3 Inventory",
                "0 of 12 Scope 3 categories reported. Scope 3 is typically 65–85% of total footprint. "
                "Enter activity data above to unlock full GHG Protocol compliance.",
                impact="Governance +8–12 pts",
                priority="medium",
            )
        elif s3["n_categories"] < 6:
            recommendation_card(
                "Expand Scope 3 Coverage",
                f"Only {s3['n_categories']} of 12 categories reported ({s3['completeness']}% coverage). "
                "Investors and ESG raters (MSCI, Sustainalytics) require ≥8 categories for full disclosure.",
                impact="Governance + credibility",
                priority="medium",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── GRI 301-1/301-2 — Materials Used by Weight/Volume ────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    _materials_relevant_sectors = {"Manufacturing", "Industrial", "Construction",
                                    "Food & Beverage", "Packaging", "Textile"}
    _is_materials_relevant = sector_input in _materials_relevant_sectors

    _mat_label = "🧱 Materials Used (GRI 301-1 / 301-2)"
    _mat_expanded = _is_materials_relevant

    with st.expander(_mat_label +
                      (" — recommended for your sector" if _is_materials_relevant else " — optional"),
                      expanded=_mat_expanded):
        st.markdown("""
        <div style="font-size:11px;color:#94A3B8;margin-bottom:10px;line-height:1.6;">
            Record raw materials used in production/operations by weight or volume.
            Satisfies <strong>GRI 301-1</strong> (total materials used) and upgrades
            <strong>GRI 301-2</strong> (recycled input %) from an org-wide estimate to
            material-specific disclosure. Most relevant for manufacturing, construction,
            packaging, F&B, and textile sectors — but any organization can report this.
        </div>
        """, unsafe_allow_html=True)

        import pandas as _mpd

        if "materials_table" not in st.session_state:
            existing = S.get("materials_table")
            st.session_state["materials_table"] = (
                _mpd.DataFrame(existing) if existing else
                _mpd.DataFrame([
                    {"Material": "", "Quantity (tonnes)": 0.0, "Renewable/Recycled?": False,
                     "Recycled Content (%)": 0.0, "Notes": ""}
                ])
            )

        edited_materials = st.data_editor(
            st.session_state["materials_table"],
            num_rows="dynamic",
            use_container_width=True,
            key="materials_editor",
            column_config={
                "Material": st.column_config.TextColumn(
                    "Material", width="medium",
                    help="e.g. Steel, Plastic resin (PET), Cardboard, Cement, Cotton fabric"),
                "Quantity (tonnes)": st.column_config.NumberColumn(
                    "Quantity (tonnes)", min_value=0.0, step=0.1, format="%.2f"),
                "Renewable/Recycled?": st.column_config.CheckboxColumn(
                    "Renewable/Recycled Input?",
                    help="Check if this material is a renewable resource or recycled input"),
                "Recycled Content (%)": st.column_config.NumberColumn(
                    "Recycled Content (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.0f"),
                "Notes": st.column_config.TextColumn("Notes", width="large"),
            },
        )
        st.session_state["materials_table"] = edited_materials
        S.set("materials_table", edited_materials.to_dict("records"))

        # Summary metrics
        _valid_rows = edited_materials[edited_materials["Material"].astype(str).str.strip() != ""]
        if not _valid_rows.empty:
            _total_mat = _valid_rows["Quantity (tonnes)"].sum()
            _recycled_mat = (_valid_rows["Quantity (tonnes)"] *
                             _valid_rows["Recycled Content (%)"] / 100).sum()
            _recycled_share = (_recycled_mat / _total_mat * 100) if _total_mat > 0 else 0.0
            _renewable_count = int(_valid_rows["Renewable/Recycled?"].sum())

            m1, m2, m3 = st.columns(3, gap="medium")
            with m1:
                kpi_card("Total Materials", f"{_total_mat:,.1f}",
                         badge="tonnes/year", badge_type="gray",
                         icon="🧱", icon_bg="#F1F5F9")
            with m2:
                kpi_card("Recycled Content", f"{_recycled_share:.0f}%",
                         badge=f"{_recycled_mat:,.1f} t recycled", badge_type="green",
                         icon="♻️", icon_bg="#DCFCE7")
            with m3:
                kpi_card("Renewable/Recycled Inputs", f"{_renewable_count}",
                         badge=f"of {len(_valid_rows)} materials", badge_type="teal",
                         icon="🌱", icon_bg="#ECFEFF")

            st.markdown(f"""
            <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;
                        padding:10px 14px;margin-top:8px;font-size:11px;color:#14532D;">
                ✅ <strong>GRI 301-1 satisfied</strong>: {len(_valid_rows)} material type(s)
                tracked, {_total_mat:,.1f} tonnes total.
                {"<strong>GRI 301-2 upgraded</strong> to material-specific disclosure (" + f"{_recycled_share:.0f}% recycled content)." if _recycled_mat > 0 else "Add recycled content % to satisfy GRI 301-2 with material-level detail."}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
                        padding:10px 14px;margin-top:4px;font-size:11px;color:#92400E;">
                ⚠️ No materials recorded yet. Add at least one row above to satisfy GRI 301-1.
            </div>
            """, unsafe_allow_html=True)

