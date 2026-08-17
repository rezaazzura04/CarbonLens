"""
CarbonLens V8 — Organisation Setup (Onboarding) page.
Accessible via "Set Up My Organisation" — not a permanent sidebar destination.

Follows V8 architecture: pages → state_service → repository.
No calculations. No direct repository access.
"""
from __future__ import annotations
import streamlit as st

import services.state_service as state_svc

from components.ui import (
    page_header, info_banner, divider, spacer, empty_state,
)
from components.theme.typography import SIZE_SM, SIZE_XS, WEIGHT_BOLD


SECTORS = [
    "Manufacturing", "Energy & Utilities", "Transportation & Logistics",
    "Construction & Real Estate", "Agriculture & Food", "Healthcare",
    "Financial Services", "Retail & Consumer Goods", "Technology & ICT",
    "Education & Research", "Hospitality & Tourism", "Other Services",
]

PROVINCES = [
    "Aceh","Bali","Bangka Belitung","Banten","Bengkulu","DI Yogyakarta",
    "DKI Jakarta","Gorontalo","Jambi","Jawa Barat","Jawa Tengah","Jawa Timur",
    "Kalimantan Barat","Kalimantan Selatan","Kalimantan Tengah",
    "Kalimantan Timur","Kalimantan Utara","Kepulauan Riau",
    "Lampung","Maluku","Maluku Utara","Nusa Tenggara Barat",
    "Nusa Tenggara Timur","Papua","Papua Barat","Riau",
    "Sulawesi Barat","Sulawesi Selatan","Sulawesi Tengah",
    "Sulawesi Tenggara","Sulawesi Utara","Sumatera Barat",
    "Sumatera Selatan","Sumatera Utara",
]

PERIODS = ["2020","2021","2022","2023","2024","2025"]


def render() -> None:
    """Render the Organisation Setup wizard."""
    page_header(
        title       = "Organisation Setup",
        subtitle    = "Set up your organisation profile to begin ESG and carbon analysis",
        badge       = "Setup Required",
        badge_type  = "blue",
    )

    # Step indicator
    _step_indicator()

    # Check which step we're on
    step = st.session_state.get("onboarding_step", 1)

    if step == 1:
        _step1_profile()
    elif step == 2:
        _step2_data_upload()
    elif step == 3:
        _step3_complete()


def _step_indicator() -> None:
    steps = ["1. Organisation Profile", "2. Upload Data", "3. Complete"]
    step  = st.session_state.get("onboarding_step", 1)
    cols  = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, steps), 1):
        with col:
            active = i == step
            done   = i < step
            color  = "#059669" if done else ("#0EA5E9" if active else "#94A3B8")
            bg     = "#D1FAE5" if done else ("#E0F2FE" if active else "#F1F5F9")
            st.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:8px;'
                f'text-align:center;font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                f'color:{color};">{"✓ " if done else ""}{label}</div>',
                unsafe_allow_html=True,
            )
    spacer(16)


def _step1_profile() -> None:
    """Step 1: Collect organisation profile."""
    divider("Organisation Profile")
    st.caption("All fields are required to proceed.")

    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input(
            "Organisation / Company Name *",
            value     = st.session_state.get("ob_company",""),
            key       = "ob_company_input",
            placeholder = "e.g. PT Sinar Energi Nusantara",
        )
        sector = st.selectbox(
            "Industry Sector *",
            SECTORS,
            index = SECTORS.index(st.session_state.get("ob_sector", "Manufacturing")),
            key   = "ob_sector_select",
        )
        reporting_period = st.selectbox(
            "Reporting Period (Year) *",
            PERIODS,
            index = PERIODS.index(st.session_state.get("ob_period", "2025")),
            key   = "ob_period_select",
        )

    with col2:
        province = st.selectbox(
            "Province (for PLN grid factor) *",
            PROVINCES,
            index = PROVINCES.index(st.session_state.get("ob_province", "Jawa Timur")),
            key   = "ob_province_select",
        )
        area_m2 = st.number_input(
            "Floor / Site Area (m²) *",
            min_value = 1.0, max_value = 10_000_000.0,
            value     = float(st.session_state.get("ob_area", 5000.0)),
            step      = 100.0, key="ob_area_input",
        )
        employees = st.number_input(
            "Number of Employees *",
            min_value = 1, max_value = 1_000_000,
            value     = int(st.session_state.get("ob_employees", 100)),
            step      = 10, key="ob_employees_input",
        )

    spacer(8)
    _, btn_col = st.columns([3, 1])
    with btn_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="ob_next1"):
            if not company_name or not company_name.strip():
                st.error("Organisation name is required.")
                return
            # Save to session state for step 2
            st.session_state["ob_company"]   = company_name.strip()
            st.session_state["ob_sector"]    = sector
            st.session_state["ob_period"]    = reporting_period
            st.session_state["ob_province"]  = province
            st.session_state["ob_area"]      = area_m2
            st.session_state["ob_employees"] = employees
            st.session_state["onboarding_step"] = 2
            st.rerun()


def _step2_data_upload() -> None:
    """Step 2: Upload emission CSV."""
    divider("Upload Emission Data")
    st.caption(
        "Upload a CSV containing monthly emission data. "
        "Required column: **Emission** (kg CO₂e). "
        "Optional: Energy, Waste, Water. "
        "You can also skip this step and upload later."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV", type=["csv"], key="ob_csv_upload"
    )

    if uploaded_file:
        try:
            from services.validation_service import validate_upload
            df, result = validate_upload(
                uploaded_file.getvalue(), uploaded_file.name
            )
            status = result.get("status","Fail")
            if status == "Pass":
                info_banner("✓  Data validated successfully.", "success")
                st.session_state["ob_df"]         = df
                st.session_state["ob_val_result"] = result
            elif status == "Warning":
                info_banner(
                    "Data accepted with warnings: " + "; ".join(result.get("warnings",[])),
                    "warning",
                )
                st.session_state["ob_df"]         = df
                st.session_state["ob_val_result"] = result
            else:
                for err in result.get("errors", []):
                    st.error(err)
                st.session_state.pop("ob_df", None)
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

    spacer(8)
    col_back, col_skip, col_next = st.columns([1, 1, 1])

    with col_back:
        if st.button("← Back", key="ob_back2"):
            st.session_state["onboarding_step"] = 1
            st.rerun()

    with col_skip:
        if st.button("Skip — Upload Later", key="ob_skip_upload"):
            st.session_state.pop("ob_df", None)
            st.session_state.pop("ob_val_result", None)
            _complete_setup(with_data=False)

    with col_next:
        has_data = "ob_df" in st.session_state
        if st.button(
            "Complete Setup →" if has_data else "Continue Without Data →",
            type="primary", use_container_width=True, key="ob_complete",
        ):
            _complete_setup(with_data=has_data)


def _complete_setup(with_data: bool) -> None:
    """Build the org dict, call complete_onboarding, advance to step 3."""
    org_data = {
        "org_id":           f"org-{st.session_state.get('ob_company','x').replace(' ','-')[:30]}",
        "company_name":     st.session_state.get("ob_company",  ""),
        "sector":           st.session_state.get("ob_sector",   "Manufacturing"),
        "reporting_period": st.session_state.get("ob_period",   "2025"),
        "province":         st.session_state.get("ob_province", "Jawa Timur"),
        "area_m2":          float(st.session_state.get("ob_area",    5000.0)),
        "employees":        int(st.session_state.get("ob_employees", 100)),
        "renew_pct":        0.0,
        "recycle_pct":      0.0,
        "certifications":   [],
        "is_demo":          False,
    }

    df         = st.session_state.pop("ob_df", None)
    val_result = st.session_state.pop("ob_val_result", None)

    state_svc.complete_onboarding(org_data, df, val_result)

    st.session_state["onboarding_step"] = 3
    st.rerun()


def _step3_complete() -> None:
    """Step 3: Setup complete — navigate to Executive Summary."""
    company = st.session_state.get("ob_company", "your organisation")
    st.markdown(
        f'<div style="text-align:center;padding:40px 20px;">'
        f'<div style="font-size:48px;margin-bottom:16px;">✓</div>'
        f'<div style="font-size:20px;font-weight:800;color:#059669;">'
        f'Setup Complete!</div>'
        f'<div style="font-size:14px;color:#475569;margin-top:8px;">'
        f'{company} is now configured.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    spacer(16)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("Go to Executive Summary →", type="primary",
                     use_container_width=True, key="ob_go_exec"):
            # Clean up onboarding step
            for k in ["onboarding_step","ob_company","ob_sector","ob_period",
                       "ob_province","ob_area","ob_employees"]:
                st.session_state.pop(k, None)
            state_svc.navigate_to("executive_summary")
            st.rerun()
