"""
CarbonLens — Organisation Setup (Onboarding) page.
Accessible via "Set Up My Organisation" — not a permanent sidebar destination.

Follows the layered architecture: pages → state_service → repository.
No calculations. No direct repository access. No direct st.session_state
access — all wizard scratch state goes through state_svc.*_onboarding_*
helpers, which own it in repository/session_repo.py (Phase 5-B Fix: onboarding
architecture violation). Streamlit widget `key=` bindings remain — those are
Streamlit's own internal widget-state mechanism, not direct session_state
reads/writes by this page.
"""
from __future__ import annotations
import html
import streamlit as st
from components.compat import width_stretch_kwargs

import services.state_service as state_svc

from components.ui import (
    page_header, info_banner, divider, spacer, empty_state,
)
from components.theme.typography import SIZE_SM, SIZE_XS, WEIGHT_BOLD
from components.theme.icons import icon


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

    # RBAC (Fix F-06): setting up / editing an organisation profile requires
    # can_upload (the same permission required to bring in emission data —
    # both are "bring real organisational data into the platform" actions).
    # This intentionally does NOT require can_edit_profile (admin-only),
    # because the local single-user identity used in this login-free build
    # is an "analyst", not an "admin" — gating on can_edit_profile would
    # lock the only supported flow (local real-organisation setup) out
    # entirely. RBAC is retained as reusable infrastructure for a future
    # authenticated deployment, but no login gate exists in this build.
    if not state_svc.check_permission("can_upload"):
        empty_state(
            "lock", "Organisation setup is restricted",
            "Your account role does not have permission to create or edit an "
            "organisation profile. Contact an administrator or analyst.",
        )
        return

    # Step indicator
    _step_indicator()

    step = state_svc.get_onboarding_step()

    if step == 1:
        _step1_profile()
    elif step == 2:
        _step2_data_upload()
    elif step == 3:
        _step3_complete()


def _step_indicator() -> None:
    steps = ["1. Organisation Profile", "2. Upload Data", "3. Complete"]
    step  = state_svc.get_onboarding_step()
    cols  = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, steps), 1):
        with col:
            active = i == step
            done   = i < step
            color  = "#037C38" if done else ("#3E7C8C" if active else "#8A968D")
            bg     = "#E0EFE7" if done else ("#E3EEF0" if active else "#F0F2EE")
            prefix = f'{icon("check", size=11, color=color)} ' if done else ""
            st.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:8px;'
                f'text-align:center;font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
                f'color:{color};display:flex;align-items:center;justify-content:center;gap:4px;">'
                f'{prefix}<span>{label}</span></div>',
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
            value     = state_svc.get_onboarding_field("company", ""),
            key       = "ob_company_input",
            placeholder = "e.g. PT Sinar Energi Nusantara",
        )
        sector = st.selectbox(
            "Industry Sector *",
            SECTORS,
            index = SECTORS.index(state_svc.get_onboarding_field("sector", "Manufacturing")),
            key   = "ob_sector_select",
        )
        reporting_period = st.selectbox(
            "Reporting Period (Year) *",
            PERIODS,
            index = PERIODS.index(state_svc.get_onboarding_field("period", "2025")),
            key   = "ob_period_select",
        )

    with col2:
        province = st.selectbox(
            "Province (for PLN grid factor) *",
            PROVINCES,
            index = PROVINCES.index(state_svc.get_onboarding_field("province", "Jawa Timur")),
            key   = "ob_province_select",
        )
        area_m2 = st.number_input(
            "Floor / Site Area (m²) *",
            min_value = 1.0, max_value = 10_000_000.0,
            value     = float(state_svc.get_onboarding_field("area", 5000.0)),
            step      = 100.0, key="ob_area_input",
        )
        employees = st.number_input(
            "Number of Employees *",
            min_value = 1, max_value = 1_000_000,
            value     = int(state_svc.get_onboarding_field("employees", 100)),
            step      = 10, key="ob_employees_input",
        )

    spacer(8)
    _, btn_col = st.columns([3, 1])
    with btn_col:
        if st.button("Continue →", type="primary", **width_stretch_kwargs(), key="ob_next1"):
            if not company_name or not company_name.strip():
                st.error("Organisation name is required.")
                return
            # Save to onboarding-wizard scratch state for step 2
            state_svc.set_onboarding_field("company",   company_name.strip())
            state_svc.set_onboarding_field("sector",    sector)
            state_svc.set_onboarding_field("period",    reporting_period)
            state_svc.set_onboarding_field("province",  province)
            state_svc.set_onboarding_field("area",      area_m2)
            state_svc.set_onboarding_field("employees", employees)
            state_svc.set_onboarding_step(2)
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
                info_banner("Data validated successfully.", "success")
                state_svc.set_onboarding_field("df",         df)
                state_svc.set_onboarding_field("val_result", result)
            elif status == "Warning":
                info_banner(
                    "Data accepted with warnings: " + "; ".join(result.get("warnings",[])),
                    "warning",
                )
                state_svc.set_onboarding_field("df",         df)
                state_svc.set_onboarding_field("val_result", result)
            else:
                for err in result.get("errors", []):
                    st.error(err)
                state_svc.pop_onboarding_field("df")
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

    spacer(8)
    col_back, col_skip, col_next = st.columns([1, 1, 1])

    with col_back:
        if st.button("← Back", key="ob_back2"):
            state_svc.set_onboarding_step(1)
            st.rerun()

    with col_skip:
        if st.button("Skip — Upload Later", key="ob_skip_upload"):
            state_svc.pop_onboarding_field("df")
            state_svc.pop_onboarding_field("val_result")
            _complete_setup(with_data=False)

    with col_next:
        has_data = state_svc.get_onboarding_field("df") is not None
        if st.button(
            "Complete Setup →" if has_data else "Continue Without Data →",
            type="primary", **width_stretch_kwargs(), key="ob_complete",
        ):
            _complete_setup(with_data=has_data)


def _complete_setup(with_data: bool) -> None:
    """Build the org dict, call complete_onboarding against the ACTIVE
    slot, advance to step 3. org_id is intentionally NOT set here — the
    service layer assigns a collision-safe identity (Phase 5-B Fix F-02)."""
    org_data = {
        "company_name":     state_svc.get_onboarding_field("company",  ""),
        "sector":           state_svc.get_onboarding_field("sector",   "Manufacturing"),
        "reporting_period": state_svc.get_onboarding_field("period",   "2025"),
        "province":         state_svc.get_onboarding_field("province", "Jawa Timur"),
        "area_m2":          float(state_svc.get_onboarding_field("area",    5000.0)),
        "employees":        int(state_svc.get_onboarding_field("employees", 100)),
        "renew_pct":        0.0,
        "recycle_pct":      0.0,
        "certifications":   [],
        "is_demo":          False,
    }

    df         = state_svc.pop_onboarding_field("df")
    val_result = state_svc.pop_onboarding_field("val_result")

    # Fix F-01: the organisation MUST be written to the slot the user is
    # actually looking at (the active slot from the sidebar org switcher),
    # never a hardcoded slot. Without this, switching to an empty slot and
    # completing setup silently overwrote slot 0 instead.
    active_slot = state_svc.get_active_slot()
    result = state_svc.complete_onboarding(org_data, df, val_result, slot=active_slot)

    # Fix F-08: don't claim success if disk persistence actually failed.
    state_svc.set_onboarding_field("last_result_persisted", bool(result.get("_persisted", True)))
    state_svc.set_onboarding_step(3)
    st.rerun()


def _step3_complete() -> None:
    """Step 3: Setup complete — navigate to Executive Summary."""
    # company is user-entered free text (onboarding step 1) — escape before
    # it reaches unsafe_allow_html, same trust boundary as components/ui.py.
    company   = html.escape(state_svc.get_onboarding_field("company", "your organisation"))
    persisted = state_svc.get_onboarding_field("last_result_persisted", True)

    if persisted:
        st.markdown(
            f'<div style="text-align:center;padding:40px 20px;">'
            f'<div style="margin-bottom:16px;display:flex;justify-content:center;">'
            f'{icon("check_circle", size=40, color="#037C38", stroke_width=1.5)}</div>'
            f'<div style="font-size:20px;font-weight:800;color:#037C38;">'
            f'Setup Complete!</div>'
            f'<div style="font-size:14px;color:#66736B;margin-top:8px;">'
            f'{company} is now configured.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="text-align:center;padding:40px 20px;">'
            f'<div style="margin-bottom:16px;display:flex;justify-content:center;">'
            f'{icon("alert_triangle", size=40, color="#D89A3D", stroke_width=1.5)}</div>'
            f'<div style="font-size:20px;font-weight:800;color:#D89A3D;">'
            f'Setup completed for this session</div>'
            f'<div style="font-size:14px;color:#66736B;margin-top:8px;">'
            f'{company} is ready to use right now, but it could not be saved to disk '
            f'(check storage permissions). It will be lost if the app restarts — '
            f'try again, or export your data once available.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(16)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("Go to Executive Summary →", type="primary",
                     **width_stretch_kwargs(), key="ob_go_exec"):
            state_svc.clear_onboarding_fields()
            state_svc.navigate_to("executive_summary")
            st.rerun()
