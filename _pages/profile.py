"""
CarbonLens V7 — Profile / Landing Page
SaaS-style product homepage introducing the platform
"""

import streamlit as st
import utils.state as S
from components.styles import inject_global_styles
from config.settings import INDUSTRY_BENCHMARKS


def render():
    S.init()

    # ── Organization setup (merged from onboarding) ────────────────────────
    company_name = S.get("company_name", "")
    is_setup     = bool(company_name and company_name.strip()
                        and company_name not in ("", "My Organization"))

    if not is_setup:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0B1220,#1a5c38);border-radius:14px;
             padding:22px 28px;color:white;margin-bottom:20px;display:flex;
             align-items:center;gap:16px;">
            <div style="font-size:32px;flex-shrink:0;">👋</div>
            <div>
                <div style="font-size:17px;font-weight:800;margin-bottom:3px;">
                    Welcome to CarbonLens — set up your organization first</div>
                <div style="font-size:12px;opacity:0.75;line-height:1.6;">
                    Takes 60 seconds. Your profile personalizes every module —
                    dashboards, reports, benchmarks, and PDF exports will all use your company details.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("◈  Organization Profile" + (" · ✅ Configured" if is_setup else " · ⚠️ Setup required"), expanded=not is_setup):
        with st.form("org_profile_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                new_name = st.text_input("Organization Name *",
                    value=S.get("company_name",""),
                    placeholder="e.g. PT Pupuk Indonesia")
            with c2:
                sectors = list(INDUSTRY_BENCHMARKS.keys())
                cur_sec = S.get("sector", sectors[0])
                sec_idx = sectors.index(cur_sec) if cur_sec in sectors else 0
                new_sector = st.selectbox("Industry Sector *", sectors, index=sec_idx)
            with c3:
                new_area = st.number_input("Building Area (m²) *",
                    min_value=100.0, value=float(S.get("area_m2", 5000)),
                    step=100.0)

            c4, c5, c6 = st.columns(3, gap="medium")
            with c4:
                new_emp = st.number_input("Employees",
                    min_value=1, value=int(S.get("employees", 200)), step=10)
            with c5:
                new_renew = st.slider("Renewable Energy %", 0, 100,
                    value=int(S.get("renew_pct", 5)))
            with c6:
                new_recycle = st.slider("Recycling Rate %", 0, 100,
                    value=int(S.get("recycle_pct", 15)))

            st.markdown("""
            <div style="font-size:10px;font-weight:700;color:#0EA5E9;
                        margin:12px 0 6px;text-transform:uppercase;letter-spacing:0.5px;">
                📍 Facility Location (optional — enables GEE satellite analysis)
            </div>
            <div style="font-size:10px;color:#94A3B8;margin-bottom:8px;">
                Provide your facility's coordinates to unlock real Sentinel-2 NDVI,
                carbon stock, and deforestation analysis in GIS Intelligence.
                Without this, GIS shows province-level estimates only.
            </div>
            """, unsafe_allow_html=True)

            c7, c8, c9 = st.columns(3, gap="medium")
            with c7:
                _cur_lat = S.get("facility_lat")
                new_lat = st.number_input("Latitude",
                    min_value=-11.0, max_value=6.5,
                    value=float(_cur_lat) if _cur_lat is not None else 0.0,
                    step=0.0001, format="%.4f",
                    help="e.g. -6.2088 for Jakarta. Indonesia range: -11.0 to 6.5")
            with c8:
                _cur_lon = S.get("facility_lon")
                new_lon = st.number_input("Longitude",
                    min_value=95.0, max_value=141.0,
                    value=float(_cur_lon) if (_cur_lon is not None and 95.0 <= float(_cur_lon) <= 141.0) else 107.0,
                    step=0.0001, format="%.4f",
                    help="e.g. 106.8456 for Jakarta. Indonesia range: 95.0 to 141.0")
            with c9:
                new_buffer = st.number_input("Analysis radius (km)",
                    min_value=0.5, max_value=20.0,
                    value=float(S.get("facility_buffer_km", 2.0)), step=0.5,
                    help="Area around the coordinate point analyzed for NDVI/carbon stock")

            new_land_use = st.text_input(
                "Land use history (optional)",
                value=S.get("facility_land_use_history", ""),
                placeholder="e.g. Converted from oil palm plantation in 2018",
                help="If the facility site has a known land-use change history, "
                     "this connects GEE deforestation data to Scope 3 land-use emissions.",
            )

            # ── Social Indicators (GRI 401/403/404/405) ─────────────────────
            st.markdown("""
            <div style="font-size:10px;font-weight:700;color:#10B981;
                        margin:14px 0 6px;text-transform:uppercase;letter-spacing:0.5px;">
                👥 Social Indicators (GRI 401 / 403 / 404 / 405)
            </div>
            <div style="font-size:10px;color:#94A3B8;margin-bottom:8px;">
                Optional but recommended — improves ESG Social pillar accuracy.
                Leave at default if unknown; defaults use sector-neutral assumptions.
            </div>
            """, unsafe_allow_html=True)

            sc1, sc2, sc3, sc4 = st.columns(4, gap="medium")
            with sc1:
                _wr = S.get("water_recycled_pct", 0.0)
                new_water_recycled = st.slider("Water Recycled/Reused %", 0, 100,
                    value=int(_wr or 0),
                    help="GRI 303-3 — % of water withdrawn that is recycled or reused")
            with sc2:
                _to = S.get("employee_turnover_pct")
                new_turnover = st.number_input("Employee Turnover % /yr",
                    min_value=0.0, max_value=100.0, step=0.5,
                    value=float(_to) if _to is not None else 15.0,
                    help="GRI 401-1 — annual employee turnover rate. Lower is better.")
            with sc3:
                _th = S.get("training_hours_per_employee")
                new_training = st.number_input("Training Hours/Employee/yr",
                    min_value=0.0, step=1.0,
                    value=float(_th) if _th is not None else 8.0,
                    help="GRI 404-1 — average training hours per employee per year")
            with sc4:
                _ir = S.get("injury_rate")
                new_injury = st.number_input("Injury Rate (per 200k hrs)",
                    min_value=0.0, step=0.1,
                    value=float(_ir) if _ir is not None else 3.0,
                    help="GRI 403-9 — recordable workplace injuries per 200,000 hours worked")

            sc5, sc6 = st.columns(2, gap="medium")
            with sc5:
                _wwf = S.get("women_workforce_pct")
                new_women_wf = st.slider("Women in Workforce %", 0, 100,
                    value=int(_wwf) if _wwf is not None else 30,
                    help="GRI 405-1 — % of total workforce that is female")
            with sc6:
                _wmg = S.get("women_management_pct")
                new_women_mg = st.slider("Women in Management %", 0, 100,
                    value=int(_wmg) if _wmg is not None else 20,
                    help="GRI 405-1 — % of management positions held by women")

            # ── Governance Indicators (GRI 2-9 to 2-24, 205) ─────────────────
            st.markdown("""
            <div style="font-size:10px;font-weight:700;color:#8B5CF6;
                        margin:14px 0 6px;text-transform:uppercase;letter-spacing:0.5px;">
                ⚖️ Governance Indicators (GRI 2-9 to 2-24, 205)
            </div>
            <div style="font-size:10px;color:#94A3B8;margin-bottom:8px;">
                Board structure and ethics policies — feeds the Governance pillar.
            </div>
            """, unsafe_allow_html=True)

            gv1, gv2, gv3 = st.columns(3, gap="medium")
            with gv1:
                _bi = S.get("board_independence_pct")
                new_board_indep = st.slider("Board Independence %", 0, 100,
                    value=int(_bi) if _bi is not None else 30,
                    help="GRI 2-9/2-10 — % of board members who are independent directors")
            with gv2:
                _wb = S.get("women_board_pct")
                new_women_board = st.slider("Women on Board %", 0, 100,
                    value=int(_wb) if _wb is not None else 15,
                    help="GRI 405-1 — % of board seats held by women")
            with gv3:
                _act = S.get("anti_corruption_training_pct")
                new_anticorr = st.slider("Anti-Corruption Training %", 0, 100,
                    value=int(_act) if _act is not None else 0,
                    help="GRI 205-2 — % of employees trained on anti-corruption policies")

            gv4, gv5 = st.columns(2, gap="medium")
            with gv4:
                new_coc = st.checkbox("Has Code of Conduct (GRI 2-23)",
                    value=bool(S.get("has_code_of_conduct") or False))
            with gv5:
                new_whistle = st.checkbox("Has Whistleblower Policy (GRI 2-24)",
                    value=bool(S.get("has_whistleblower_policy") or False))

            submitted = st.form_submit_button(
                "✓  Save Profile" if is_setup else "✓  Save & Start Using CarbonLens",
                type="primary", use_container_width=True)

            if submitted:
                if not new_name.strip():
                    st.error("Organization name is required.")
                else:
                    S.set_company_profile(
                        name           = new_name.strip(),
                        sector         = new_sector,
                        area_m2        = float(new_area),
                        employees      = int(new_emp),
                        renew_pct      = int(new_renew),
                        recycle_pct    = int(new_recycle),
                        certifications = [],
                    )
                    # Facility coordinates — only store if user entered non-zero values
                    if new_lat != 0.0 or new_lon != 0.0:
                        S.set("facility_lat", float(new_lat))
                        S.set("facility_lon", float(new_lon))
                    S.set("facility_buffer_km", float(new_buffer))
                    S.set("facility_land_use_history", new_land_use.strip())

                    # Social indicators (GRI 401/403/404/405)
                    S.set("water_recycled_pct",          float(new_water_recycled))
                    S.set("employee_turnover_pct",       float(new_turnover))
                    S.set("training_hours_per_employee", float(new_training))
                    S.set("injury_rate",                 float(new_injury))
                    S.set("women_workforce_pct",         float(new_women_wf))
                    S.set("women_management_pct",        float(new_women_mg))

                    # Governance indicators (GRI 2-9 to 2-24, 205)
                    S.set("board_independence_pct",       float(new_board_indep))
                    S.set("women_board_pct",              float(new_women_board))
                    S.set("anti_corruption_training_pct", float(new_anticorr))
                    S.set("has_code_of_conduct",          bool(new_coc))
                    S.set("has_whistleblower_policy",     bool(new_whistle))

                    S.set("onboarding_done", True)
                    # Recompute canonical ESG with the new inputs
                    from utils.state import compute_canonical_esg
                    with st.spinner("🔄 Computing ESG score..."):
                        compute_canonical_esg(force=True)
                    st.success(f"✅ Profile saved for **{new_name}**.")
                    st.rerun()

    if not is_setup:
        col_skip, _ = st.columns([1, 3])
        with col_skip:
            if st.button("Skip for now →", key="skip_setup"):
                S.set("company_name", "My Organization")
                S.set("sector",       "Manufacturing")
                S.set("area_m2",      5000.0)
                S.set("employees",    200)
                S.set("renew_pct",    5)
                S.set("recycle_pct",  15)
                S.set("onboarding_done", True)
                st.rerun()


    # ── Emission Factor Manager ─────────────────────────────────────────────
    if is_setup:
        from config.settings import EMISSION_FACTORS
        import datetime as _dt

        active_ef  = S.get_emission_factors()
        ef_source  = S.get("emission_factors_source") or "PLN RUPTL 2023 / Kepmen ESDM 18/2023 (default)"
        ef_updated = S.get("emission_factors_updated") or ""
        is_custom  = S.get("emission_factors") is not None

        with st.expander(
            f"⚡  Emission Factors  ·  Source: {ef_source}"
            + (f"  ·  Updated {ef_updated}" if ef_updated else ""),
            expanded=False
        ):
            st.markdown("""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                 padding:12px 16px;font-size:12px;color:#1E40AF;margin-bottom:14px;">
                <strong>Why this matters:</strong> Grid electricity emission factor (kg CO₂e/kWh)
                changes whenever the government updates the national grid factor
                (currently 0.7160 per Kepmen ESDM No.18/2023, regional subsystem factors also apply
                in Carbon Accounting). When a new Kepmen / RUPTL is published, update the value here —
                Scope 1/2 calculations across Carbon Accounting, Dashboard, Scenario Simulator,
                Data Export, and POJK 51 will all use the new number consistently.
            </div>
            """, unsafe_allow_html=True)

            ef_c1, ef_c2 = st.columns(2, gap="medium")
            with ef_c1:
                new_elec = st.number_input(
                    "Grid electricity (national avg) — kg CO₂e/kWh",
                    min_value=0.01, max_value=2.0, step=0.0001, format="%.4f",
                    value=float(active_ef["electricity_kgco2_per_kwh"]),
                    help="National average. Default 0.7160 = Kepmen ESDM No.18/2023.",
                    key="ef_electricity",
                )
                new_diesel = st.number_input(
                    "Diesel — kg CO₂e/liter",
                    min_value=0.01, max_value=5.0, step=0.01,
                    value=float(active_ef["diesel_kgco2_per_liter"]),
                    key="ef_diesel",
                )
                new_petrol = st.number_input(
                    "Petrol — kg CO₂e/liter",
                    min_value=0.01, max_value=5.0, step=0.01,
                    value=float(active_ef["petrol_kgco2_per_liter"]),
                    key="ef_petrol",
                )
            with ef_c2:
                new_lpg = st.number_input(
                    "LPG — kg CO₂e/kg",
                    min_value=0.01, max_value=5.0, step=0.01,
                    value=float(active_ef["lpg_kgco2_per_kg"]),
                    key="ef_lpg",
                )
                new_gas = st.number_input(
                    "Natural gas — kg CO₂e/m³",
                    min_value=0.01, max_value=5.0, step=0.01,
                    value=float(active_ef["natural_gas_kgco2_per_m3"]),
                    key="ef_natgas",
                )
                source_label = st.text_input(
                    "Source label",
                    value=ef_source if is_custom else "Kepmen ESDM 2026",
                    placeholder="e.g. Kepmen ESDM 2026, IESR 2026",
                    key="ef_source_label",
                )

            st.caption(
                "ℹ️ Regional PLN subsystem factors (Jawa-Bali, Sumatera, Kalimantan, Sulawesi) "
                "are set separately and used automatically in Carbon Accounting based on province selection. "
                "The value above is the national average override applied when no province is selected, "
                "or when Scenario Simulator / Data Export need a single reference factor."
            )

            col_save, col_reset, col_status = st.columns([1, 1, 2], gap="small")
            with col_save:
                if st.button("💾  Save Factors", type="primary", use_container_width=True, key="ef_save"):
                    new_factors = {
                        "electricity_kgco2_per_kwh": new_elec,
                        "diesel_kgco2_per_liter":    new_diesel,
                        "petrol_kgco2_per_liter":    new_petrol,
                        "lpg_kgco2_per_kg":          new_lpg,
                        "natural_gas_kgco2_per_m3":  new_gas,
                    }
                    S.save_emission_factors(
                        new_factors,
                        source=source_label.strip() or "Custom",
                        updated_at=_dt.date.today().isoformat(),
                    )
                    st.success(f"✅ Emission factors updated — source: {source_label}")
                    st.rerun()
            with col_reset:
                if is_custom:
                    if st.button("↺  Reset to Default", use_container_width=True, key="ef_reset"):
                        S.reset_emission_factors()
                        st.success("✅ Reverted to platform defaults (Kepmen ESDM 18/2023).")
                        st.rerun()
            with col_status:
                if is_custom:
                    st.markdown(
                        '<div style="font-size:10px;color:#10B981;padding-top:8px;">'
                        '✅ Custom factors active — used in Carbon Accounting, Scenario Simulator, '
                        'Data Export, and POJK 51.</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="font-size:10px;color:#94A3B8;padding-top:8px;">'
                        f'Using platform default ({EMISSION_FACTORS["electricity_kgco2_per_kwh"]} kg CO₂e/kWh national avg).</div>',
                        unsafe_allow_html=True
                    )

    st.markdown("<div style=\'height:8px\'></div>", unsafe_allow_html=True)
    # ── End of organization setup ───────────────────────────────────────────



    # ── Hero Section ───────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #6277A1 0%, #0EA5E9 40%, #06B6D4 80%, #06B6D4 100%);
        border-radius: 20px;
        padding: 60px 48px 52px;
        color: white;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    ">
        <div style="position:absolute;top:-60px;right:-60px;width:300px;height:300px;
                    background:rgba(255,255,255,0.04);border-radius:50%;"></div>
        <div style="position:absolute;bottom:-80px;right:120px;width:400px;height:400px;
                    background:rgba(255,255,255,0.025);border-radius:50%;"></div>
        <div style="position:relative;z-index:1;">
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;">
                <div style="
                    width:56px;height:56px;
                    background:rgba(255,255,255,0.15);
                    backdrop-filter:blur(10px);
                    border:1px solid rgba(255,255,255,0.2);
                    border-radius:16px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:28px;
                ">🌿</div>
                <div>
                    <div style="font-size:10px;font-weight:600;letter-spacing:2px;
                                text-transform:uppercase;opacity:0.6;margin-bottom:2px;">Climate Intelligence Platform</div>
                    <div style="font-size:40px;font-weight:900;letter-spacing:-1.5px;line-height:1;">CarbonLens</div>
                </div>
            </div>
            <div style="font-size:22px;font-weight:300;letter-spacing:2px;opacity:0.85;margin-bottom:12px;">
                Measure &nbsp;·&nbsp; Analyze &nbsp;·&nbsp; Decarbonize
            </div>
            <div style="font-size:12px;opacity:0.65;max-width:560px;line-height:1.7;margin-bottom:28px;">
                The enterprise ESG intelligence platform built for organizations that are serious about
                their sustainability journey. From carbon accounting to AI-powered forecasting — all in one place.
            </div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;">
                <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
                            border-radius:10px;padding:10px 20px;font-size:15px;font-weight:600;">
                    🇮🇩 &nbsp; Built for Indonesian Organizations
                </div>
                <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
                            border-radius:10px;padding:10px 20px;font-size:15px;font-weight:600;">
                    📋 &nbsp; GRI · TCFD · ISSB Ready
                </div>
                <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
                            border-radius:10px;padding:10px 20px;font-size:15px;font-weight:600;">
                    🤖 &nbsp; AI-Powered Forecasting
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Mission Statement ──────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:32px 20px 24px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;
                    color:#06B6D4;margin-bottom:10px;">Our Mission</div>
        <div style="font-size:24px;font-weight:800;color:#1F2937;letter-spacing:-0.5px;
                    max-width:720px;margin:0 auto;line-height:1.4;">
            Help organizations understand, measure, monitor, forecast,<br>
            and report their sustainability performance.
        </div>
        <div style="font-size:12px;color:#6B7280;margin-top:14px;max-width:560px;margin-left:auto;margin-right:auto;line-height:1.7;">
            CarbonLens transforms raw ESG data into actionable intelligence — giving sustainability teams,
            executives, and ESG consultants a single source of truth.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Why ESG Intelligence ───────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        st.markdown("""
        <div class="cl-card" style="height:100%;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                        color:#06B6D4;margin-bottom:16px;">Why ESG Intelligence?</div>
            <div style="display:flex;flex-direction:column;gap:14px;">
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="font-size:20px;flex-shrink:0;">📊</div>
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:3px;">Regulatory Pressure</div>
                        <div style="font-size:12px;color:#6B7280;line-height:1.6;">Indonesia's POJK 51 and global TCFD mandates require organizations to disclose climate-related risks and ESG performance.</div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="font-size:20px;flex-shrink:0;">💰</div>
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:3px;">Investor Expectations</div>
                        <div style="font-size:12px;color:#6B7280;line-height:1.6;">Over 90% of institutional investors now consider ESG factors — strong ESG scores improve access to green finance and lower capital cost.</div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="font-size:20px;flex-shrink:0;">🌍</div>
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:3px;">Climate Commitments</div>
                        <div style="font-size:12px;color:#6B7280;line-height:1.6;">Indonesia's NDC targets a 31.9% emission reduction by 2030. Organizations must align operations with national decarbonization pathways.</div>
                    </div>
                </div>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="font-size:20px;flex-shrink:0;">⚡</div>
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:3px;">Operational Efficiency</div>
                        <div style="font-size:12px;color:#6B7280;line-height:1.6;">Organizations that actively monitor ESG metrics identify 15–25% cost reduction opportunities in energy, water, and waste management.</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown("""
        <div class="cl-card" style="height:100%;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                        color:#06B6D4;margin-bottom:16px;">What is CarbonLens?</div>
            <div style="font-size:12px;color:#374151;line-height:1.8;margin-bottom:16px;">
                CarbonLens is an integrated ESG intelligence platform that brings together
                <strong>carbon accounting, environmental analytics, AI forecasting, geospatial intelligence,
                and automated reporting</strong> into a single cohesive workflow.
            </div>
            <div style="font-size:12px;color:#374151;line-height:1.8;margin-bottom:20px;">
                Unlike spreadsheet-based approaches, CarbonLens connects your raw ESG data to
                intelligent insights — automatically computing scores, detecting risks, forecasting
                trends, and generating consulting-grade reports.
            </div>
            <div style="background:#E0F2FE;border-radius:12px;padding:16px 20px;">
                <div style="font-size:12px;font-weight:700;color:#0C4A6E;margin-bottom:10px;">Platform Highlights</div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; One-click ESG dataset upload</div>
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; Automatic GHG scope calculation</div>
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; AI-powered 12-month forecasting</div>
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; Executive narrative generation</div>
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; GRI / TCFD / ISSB report export</div>
                    <div style="font-size:12px;color:#1F2937;">✅ &nbsp; Mangrove & blue carbon GIS layer</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Core Features Cards ────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;margin-bottom:20px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;
                    color:#06B6D4;margin-bottom:8px;">Core Modules</div>
        <div style="font-size:20px;font-weight:800;color:#1F2937;letter-spacing:-0.3px;">
            Five integrated intelligence engines
        </div>
    </div>
    """, unsafe_allow_html=True)

    features = [
        {
            "icon": "◉", "color": "#06B6D4", "bg": "#E0F2FE",
            "title": "ESG Analytics",
            "desc": "The core data engine. Upload your ESG dataset and instantly receive environmental performance analysis, ESG scoring, benchmark comparison, data quality assessment, and AI-generated executive insights.",
            "tags": ["Environmental Analysis", "ESG Scoring", "Benchmarking", "Data Quality"],
        },
        {
            "icon": "◎", "color": "#3B82F6", "bg": "#EFF6FF",
            "title": "AI Predictions",
            "desc": "Machine learning forecasting engine that projects emission trends, energy consumption, water use, and waste generation up to 12 months ahead with confidence intervals and risk classification.",
            "tags": ["12-Month Forecast", "Risk Assessment", "Trend Analysis", "Scenario Planning"],
        },
        {
            "icon": "◍", "color": "#F59E0B", "bg": "#FFFBEB",
            "title": "Carbon Accounting",
            "desc": "GHG Protocol-compliant emission calculator covering Scope 1 direct combustion, Scope 2 purchased electricity, and Scope 3 value chain emissions with reduction opportunity analysis.",
            "tags": ["GHG Protocol", "Scope 1·2·3", "ISO 14064", "Reduction Plans"],
        },
        {
            "icon": "▣", "color": "#8B5CF6", "bg": "#F5F3FF",
            "title": "GIS Intelligence",
            "desc": "Geospatial carbon monitoring platform integrating mangrove carbon stock analysis, blue carbon assessment, environmental risk layers, and biodiversity index mapping for nature-based solutions.",
            "tags": ["Carbon Mapping", "Mangrove Analysis", "Blue Carbon", "Risk Layers"],
        },
        {
            "icon": "▤", "color": "#EF4444", "bg": "#FEF2F2",
            "title": "ESG Reporting",
            "desc": "Automated generation of consulting-grade ESG reports aligned with GRI Standards, TCFD recommendations, and ISSB frameworks — exportable as PDF with executive narrative and recommendations.",
            "tags": ["GRI Standards", "TCFD", "ISSB", "PDF Export"],
        },
    ]

    # Feature cards — responsive CSS grid (wraps to 1 col on mobile, 2 on tablet, 3 on desktop)
    # Built via list + join (not nested f-strings) to avoid brace-escaping bugs
    # that previously caused raw HTML to leak onto the page.
    card_parts = []
    for feat in features:
        tags_html = "".join(
            '<span style="background:#F3F4F6;color:#374151;border-radius:20px;'
            'padding:3px 9px;font-size:10px;font-weight:600;margin-right:4px;">'
            + t + '</span>'
            for t in feat["tags"]
        )
        card = (
            '<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;'
            'padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">'
            '<div style="width:44px;height:44px;background:' + feat["bg"] + ';border-radius:12px;'
            'display:flex;align-items:center;justify-content:center;font-size:22px;'
            'margin-bottom:14px;">' + feat["icon"] + '</div>'
            '<div style="font-size:15px;font-weight:800;color:#1F2937;margin-bottom:8px;">'
            + feat["title"] + '</div>'
            '<div style="font-size:12px;color:#6B7280;line-height:1.7;margin-bottom:14px;">'
            + feat["desc"] + '</div>'
            '<div style="display:flex;flex-wrap:wrap;gap:6px;">' + tags_html + '</div>'
            '</div>'
        )
        card_parts.append(card)

    cards_html = "".join(card_parts)
    grid_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));'
        'gap:16px;margin-bottom:8px;">' + cards_html + '</div>'
    )
    st.markdown(grid_html, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ── Platform Workflow ──────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;margin-bottom:24px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;
                    color:#06B6D4;margin-bottom:8px;">How It Works</div>
        <div style="font-size:20px;font-weight:800;color:#1F2937;letter-spacing:-0.3px;">
            Five steps to ESG intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    steps = [
        {"num": "01", "title": "Upload ESG Dataset",       "desc": "Upload your CSV with emission, energy, water, and waste data via ESG Analytics.", "icon": "📂"},
        {"num": "02", "title": "Analyze ESG Performance",  "desc": "Get instant ESG scoring, benchmark comparison, data quality assessment, and insights.", "icon": "📊"},
        {"num": "03", "title": "Generate AI Predictions",  "desc": "Forecasting engine projects trends up to 12 months with risk classification.", "icon": "🤖"},
        {"num": "04", "title": "Calculate Carbon Emissions","desc": "Compute Scope 1, 2 & 3 emissions with GHG Protocol-compliant methodology.", "icon": "⚖️"},
        {"num": "05", "title": "Create ESG Report",        "desc": "Generate a consulting-grade PDF report aligned with GRI, TCFD, and ISSB frameworks.", "icon": "📄"},
    ]

    # Steps juga pakai CSS grid — wraps ke 2-3 col di mobile, 5 di desktop
    # Built via list + join (not nested f-strings) to avoid HTML-leak bugs.
    step_parts = []
    for step in steps:
        step_card = (
            '<div style="text-align:center;padding:16px 12px;background:white;'
            'border:1px solid #E2E8F0;border-radius:12px;">'
            '<div style="font-size:28px;margin-bottom:10px;">' + step["icon"] + '</div>'
            '<div style="display:inline-block;background:#06B6D4;color:white;font-size:10px;'
            'font-weight:800;letter-spacing:0.5px;padding:3px 10px;border-radius:20px;'
            'margin-bottom:10px;">STEP ' + step["num"] + '</div>'
            '<div style="font-size:14px;font-weight:700;color:#1F2937;margin-bottom:6px;line-height:1.3;">'
            + step["title"] + '</div>'
            '<div style="font-size:11px;color:#6B7280;line-height:1.6;">' + step["desc"] + '</div>'
            '</div>'
        )
        step_parts.append(step_card)

    steps_html = "".join(step_parts)
    steps_grid_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;">'
        + steps_html + '</div>'
    )
    st.markdown(steps_grid_html, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ── Key Benefits ───────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background:linear-gradient(135deg,#E0F2FE,#E8FAF0);
        border:1px solid #BAE6FD;
        border-radius:16px;
        padding:32px 36px;
        margin-bottom:28px;
    ">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;
                    color:#06B6D4;margin-bottom:8px;text-align:center;">Key Benefits</div>
        <div style="font-size:19px;font-weight:800;color:#1F2937;text-align:center;margin-bottom:24px;">
            Why organizations choose CarbonLens
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;">
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">⚡</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">Instant Analysis</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">Upload data once, get ESG scores, forecasts, and reports in seconds — no manual calculation needed.</div>
            </div>
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">🔗</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">Connected Modules</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">All modules share the same dataset — upload once, access everywhere with zero re-entry.</div>
            </div>
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">📋</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">Compliance Ready</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">Reports aligned with GRI Standards, TCFD, ISSB S1/S2, and Indonesia's POJK 51 requirements.</div>
            </div>
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">🤖</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">AI-Driven Insights</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">Machine learning forecasting and NLP narrative generation deliver consultant-quality interpretation automatically.</div>
            </div>
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">🗺️</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">Spatial Intelligence</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">GIS-based carbon mapping including mangrove stocks and blue carbon for nature-based solution planning.</div>
            </div>
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                <div style="font-size:24px;margin-bottom:10px;">🎯</div>
                <div style="font-size:15px;font-weight:700;color:#1F2937;margin-bottom:6px;">Executive Ready</div>
                <div style="font-size:12px;color:#6B7280;line-height:1.6;">Dashboard designed for C-suite communication — clear KPIs, visual narratives, and actionable recommendations.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:16px 0 32px;">
        <div style="font-size:18px;font-weight:800;color:#1F2937;margin-bottom:8px;">
            Ready to start your ESG journey?
        </div>
        <div style="font-size:12px;color:#6B7280;margin-bottom:20px;">
            Navigate to <strong>ESG Analytics</strong> in the sidebar to upload your dataset and begin.
        </div>
        <div style="font-size:10px;color:#9CA3AF;margin-top:12px;">
            CarbonLens V7 · Built with Streamlit · Python
        </div>
    </div>
    """, unsafe_allow_html=True)
        
    if st.button("◉  Start with ESG Analytics →", type="primary", key="home_goto_esg"):
        st.session_state.active_page = "esg_analytics"
        st.rerun()
