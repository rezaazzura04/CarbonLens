"""CarbonLens — Audit event table component."""
from __future__ import annotations
import streamlit as st
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, WEIGHT_BOLD, FONT_BODY
from components.theme.colors import BORDER, TEXT_MUTED, TEXT_PRIMARY, BRAND_ACCENT
from components.theme.icons import icon


EVENT_ICONS = {
    "user_login":              "lock",
    "user_logout":              "lock",
    "role_change":              "refresh",
    "user_created":              "users",
    "user_deleted":              "x_circle",
    "data_uploaded":              "upload",
    "carbon_recalculated":     "flask",
    "esg_score_recalculated":  "esg",
    "dq_score_recalculated":   "search",
    "report_exported":         "file_check",
    "pdf_generated":           "file_check",
    "quality_flag_actioned":   "alert_triangle",
    "onboarding_completed":    "check_circle",
    "scenario_created":        "decarbonization",
    "scenario_modified":       "edit",
    "scenario_saved":          "save",
    "gis_query_run":           "gis",
}


def audit_table(
    events:       list,
    show_filters: bool = True,
    max_rows:     int  = 50,
) -> None:
    """
    Render a filterable audit trail table.

    Parameters
    ----------
    events      : list of AuditEvent dicts — pre-fetched by caller.
    show_filters: Whether to render type/search filter controls.
    max_rows    : Maximum rows to display.
    """
    if not events:
        st.info("No audit events recorded yet. Actions like uploading data and "
                "generating reports will appear here.")
        return

    filtered = events

    if show_filters:
        col_type, col_search = st.columns([1, 2])
        with col_type:
            all_types = sorted({e.get("event_type", "") for e in events})
            sel_type  = st.selectbox(
                "Event type", ["All"] + all_types, key="audit_type_filter"
            )
        with col_search:
            search = st.text_input("Search summary", key="audit_search",
                                   placeholder="Filter by summary text…")

        if sel_type != "All":
            filtered = [e for e in filtered if e.get("event_type") == sel_type]
        if search:
            filtered = [e for e in filtered
                        if search.lower() in e.get("summary", "").lower()]

    st.markdown(
        f'<div style="display:grid;grid-template-columns:90px 130px 1fr 80px;'
        f'gap:4px;padding:6px 4px;border-bottom:2px solid {BORDER};'
        f'font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:0.8px;color:{TEXT_MUTED};">'
        f'<div>Time</div><div>Event</div><div>Summary</div><div>Version</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for i, event in enumerate(filtered[:max_rows]):
        bg         = "#FAFBF9" if i % 2 == 0 else "#FFFFFF"
        ts         = str(event.get("ts", ""))[:16].replace("T", " ")
        etype      = event.get("event_type", "")
        icon_name  = EVENT_ICONS.get(etype, "circle")
        summary    = event.get("summary", "")
        ver        = event.get("state_version", "")
        ver_str    = f"v{ver}" if ver else "—"

        st.markdown(
            f'<div style="display:grid;grid-template-columns:90px 130px 1fr 80px;'
            f'gap:4px;padding:6px 4px;background:{bg};'
            f'border-bottom:1px solid {BORDER};font-size:{SIZE_SM};'
            f'font-family:{FONT_BODY};color:{TEXT_PRIMARY};">'
            f'<div style="color:{TEXT_MUTED};font-family:monospace;">{ts}</div>'
            f'<div style="display:flex;align-items:center;gap:5px;">'
            f'{icon(icon_name, size=13, color=BRAND_ACCENT)}'
            f'<span style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};">{etype}</span></div>'
            f'<div>{summary}</div>'
            f'<div style="text-align:center;color:{TEXT_MUTED};">{ver_str}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if len(filtered) > max_rows:
        st.caption(f"Showing {max_rows} of {len(filtered)} events. "
                   "Export the audit log for the full history.")
