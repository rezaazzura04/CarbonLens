"""
CarbonLens — Navigation sidebar.

Information architecture (final IA polish pass):
  CARBONLENS (brand)
  OVERVIEW      -> Executive Summary
  ANALYSIS      -> Carbon Accounting, ESG Analytics, Data Quality
  ACTION        -> Decarbonization, Reporting & Compliance
  GOVERNANCE    -> Methodology & Data, GIS · Spatial Context
  ORGANISATION  -> compact context (existing data only), moved to the bottom
  ENVIRONMENT   -> small muted footer metadata

Demo Mode no longer renders as a large card above navigation — its status
now appears as a compact badge in the main page header (see
components/ui.py::page_header), so the sidebar is stable and calm whether
the user is in Demo Mode or viewing a configured organisation.

"GIS · Spatial Context" is a real, clickable sidebar row under GOVERNANCE
(matching the required IA), but intentionally routes to the existing
"carbon_accounting" destination rather than a new page — GIS remains an
opt-in Experimental tab embedded inside Carbon Accounting (Phase 5-C
architecture decision, unchanged). This satisfies the IA requirement
without adding a new route, a new page, or graduating GIS's prominence;
the row never shows the "active" highlight itself, since Carbon Accounting
is the true destination.

Reads/writes navigation and slot state exclusively through
services.state_service — components never import repository.session_repo
directly.
"""
from __future__ import annotations
import html
import streamlit as st
from components.compat import width_stretch_kwargs
from components.theme.colors import (
    BRAND_ACCENT, BRAND_LIME,
    SIDEBAR_BG, SIDEBAR_ACTIVE_BG, SIDEBAR_TEXT, SIDEBAR_TEXT_MUTED, SIDEBAR_BORDER,
)
from components.theme.typography import SIZE_XS, SIZE_SM, SIZE_BASE, SIZE_LG, WEIGHT_BOLD, WEIGHT_BLACK, FONT_BRAND, FONT_BODY, TRACKING_WIDE
from components.theme.icons import icon, icon_data_uri
from config.navigation import ROUTES, ROUTE_MAP

# Sidebar section groupings — ids must exist in config.navigation.ROUTES.
_NAV_GROUPS = [
    ("OVERVIEW",  ["executive_summary"]),
    ("ANALYSIS",  ["carbon_accounting", "esg_analytics", "data_quality"]),
    ("ACTION",    ["decarbonization", "reporting_compliance"]),
    ("GOVERNANCE", ["governance"]),   # "GIS · Spatial Context" appended manually — see _render_nav
]


def render_sidebar() -> None:
    """Render the complete navigation sidebar."""
    from services.state_service import (
        get_active_page, set_active_page,
        get_active_slot, set_active_slot,
    )
    from state.session import get_company_summary, get_active_org
    from components.theme.colors import page_accent

    with st.sidebar:
        _render_logo()
        st.markdown(
            f'<div style="height:1px;background:{SIDEBAR_BORDER};margin:4px 0 10px;"></div>',
            unsafe_allow_html=True,
        )
        _render_nav(get_active_page, set_active_page, page_accent)
        st.markdown(
            f'<div style="height:1px;background:{SIDEBAR_BORDER};margin:14px 0 10px;"></div>',
            unsafe_allow_html=True,
        )
        _render_organisation_section(
            get_active_slot, set_active_slot, get_company_summary, get_active_org,
        )
        _render_demo_mode_card()
        _render_environment_footer()


def _render_logo() -> None:
    """
    Render the CarbonLens brand lockup as a single integrated image (icon +
    wordmark + tagline baked into one picture), not a composited icon-image
    + separately-styled HTML text — the logo and tagline are one visual
    unit, per the approved brand asset. A dedicated dark-background variant
    (assets/logo_lockup_dark.png) is used here: the source lockup has a
    near-black ring and dark "Carbon" text meant for a light/white page,
    which would be nearly invisible against the sidebar's dark-green fill,
    so the ring/"Carbon" were recoloured to white and the leaf/"Lens" to
    a light lime for contrast — the same two-colour brand identity, just
    the light-on-dark variant instead of dark-on-light.
    """
    import pathlib, base64
    logo_path = pathlib.Path(__file__).parent.parent / "assets" / "logo_lockup_dark.png"
    try:
        b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        st.markdown(
            f'<div style="padding:16px 4px 14px;">'
            f'<img src="data:image/png;base64,{b64}" style="width:100%;max-width:210px;display:block;">'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        # Fallback so the sidebar never breaks if the asset is missing —
        # same content, composited, only reached if the file read fails.
        st.markdown(
            f'<div style="padding:14px 0 12px;">'
            f'<div style="font-family:{FONT_BRAND};font-size:{SIZE_LG};font-weight:{WEIGHT_BLACK};'
            f'color:{SIDEBAR_TEXT};">CarbonLens</div>'
            f'<div style="font-size:8px;color:{SIDEBAR_TEXT_MUTED};text-transform:uppercase;">'
            f'See Clearly. Act Wisely.</div></div>',
            unsafe_allow_html=True,
        )


def _section_label(text: str) -> None:
    st.markdown(
        f'<div style="font-family:{FONT_BODY};font-size:9px;font-weight:{WEIGHT_BOLD};'
        f'text-transform:uppercase;letter-spacing:{TRACKING_WIDE};'
        f'color:{SIDEBAR_TEXT_MUTED};margin:12px 0 4px 4px;">{text}</div>',
        unsafe_allow_html=True,
    )


def _nav_row(rid: str, label: str, icon_name: str, accent: str, light: str,
             is_active: bool, key: str, target_id: str | None = None) -> None:
    """
    Render one flat/compact navigation row.
    `target_id` overrides the destination navigated to on click (used only
    by the GIS shortcut row, which is labelled differently from where it
    actually routes — see module docstring).

    Inactive rows use a real st.button (so they're genuinely clickable),
    with its Lucide icon fused INSIDE the button itself via a CSS
    background-image on the button element — st.button cannot render
    arbitrary HTML/SVG in its own label, so a background-image is the only
    way to make the icon feel attached to the button rather than sitting
    beside it in a separate column.

    Dark-sidebar note: the active/inactive colour scheme below no longer
    uses the `accent`/`light` per-page colours (which gave Carbon
    Accounting a green highlight, Data Quality an amber one, etc.) — on a
    single dark-green filled sidebar, five different pastel accent colours
    floating on top would look inconsistent rather than branded. Every nav
    row now uses one uniform light-on-dark treatment; `accent`/`light` are
    still accepted (call sites elsewhere are unchanged) but unused here.
    Per-page accent colours remain fully in effect elsewhere in the app
    (page headers, KPI cards) — this change is scoped to the sidebar only.
    """
    from services.state_service import set_active_page

    if is_active:
        st.markdown(
            f'<div style="background:{SIDEBAR_ACTIVE_BG};'
            f'border-radius:8px;padding:9px 12px 9px 14px;margin:1px 0;display:flex;'
            f'align-items:center;gap:10px;font-size:{SIZE_BASE};'
            f'font-weight:{WEIGHT_BOLD};color:{SIDEBAR_TEXT};">'
            f'{icon(icon_name, size=16, color=SIDEBAR_TEXT)}<span>{label}</span></div>',
            unsafe_allow_html=True,
        )
        return

    icon_uri  = icon_data_uri(icon_name, color=SIDEBAR_TEXT_MUTED, size=16)
    marker_id = f"cl-nav-{key}"
    st.markdown(
        f'<div id="{marker_id}" style="display:none;"></div>'
        f'<style>'
        # "+ * button" (not "+ div[data-testid=\"stButton\"] button"): the
        # marker's wrapper and the button's wrapper are guaranteed to be
        # true DOM siblings (st.markdown() and st.button() are unnested,
        # consecutive top-level calls, so Streamlit always places their
        # root wrappers side by side) — but exactly which data-testid the
        # immediate sibling itself carries has varied across Streamlit
        # versions/builds. "+ *" only assumes strict adjacency (which is
        # structurally guaranteed) and then finds the button *anywhere*
        # inside that one sibling, regardless of intermediate wrapper
        # tags. Deliberately "+" (immediate sibling only), never "~" (any
        # later sibling) — "~" would also match every other nav row's
        # button rendered further down the same list.
        f'div[data-testid="stMarkdown"]:has(#{marker_id}) + * button {{'
        f'  background-color: transparent;'
        f'  background-image: url("{icon_uri}");'
        f'  background-repeat: no-repeat;'
        f'  background-position: 14px center;'
        f'  border: none !important;'
        f'  box-shadow: none !important;'
        f'  padding-left: 40px !important;'
        f'  text-align: left !important;'
        f'  justify-content: flex-start !important;'
        f'  font-weight: 500 !important;'
        f'  color: {SIDEBAR_TEXT_MUTED} !important;'
        f'}}'
        f'div[data-testid="stMarkdown"]:has(#{marker_id}) + * button:hover {{'
        f'  background-color: {SIDEBAR_ACTIVE_BG} !important;'
        f'  border-color: {SIDEBAR_ACTIVE_BG} !important;'
        f'  color: {SIDEBAR_TEXT} !important;'
        f'}}'
        f'</style>',
        unsafe_allow_html=True,
    )
    if st.button(label, key=key, **width_stretch_kwargs()):
        set_active_page(target_id or rid)
        st.rerun()


def _render_nav(get_page_fn, set_page_fn, accent_fn) -> None:
    """Render the grouped, flat navigation list (OVERVIEW/ANALYSIS/ACTION/GOVERNANCE)."""
    active_page = get_page_fn()

    for group_label, route_ids in _NAV_GROUPS:
        _section_label(group_label)
        for rid in route_ids:
            route = ROUTE_MAP.get(rid)
            if not route:
                continue
            accent, light = accent_fn(rid)
            _nav_row(
                rid, route["label"], route["icon"], accent, light,
                is_active=(rid == active_page), key=f"nav_{rid}",
            )
        if group_label == "GOVERNANCE":
            # GIS · Spatial Context — real row, routes to the existing
            # Carbon Accounting destination (see module docstring). Never
            # shows the active highlight itself: Carbon Accounting's own
            # row already carries "active" state when the user is there.
            _nav_row(
                "gis_shortcut", "GIS \u00b7 Spatial Context", "gis",
                accent_fn("carbon_accounting")[0], accent_fn("carbon_accounting")[1],
                is_active=False, key="nav_gis_shortcut", target_id="carbon_accounting",
            )


def _render_organisation_section(get_slot_fn, set_slot_fn, get_summary_fn, get_org_fn) -> None:
    """
    Compact organisation context — moved below primary navigation per the
    final IA polish. Shows only fields that already exist in the current
    organisation record; never invents new fields. The slot switcher
    (multi-organisation support, unchanged functionality) lives here too,
    since switching organisation is contextual, not primary navigation.

    Rebrand polish: dropped the checkmark/circle (\u2713/\u25cb) "setup status"
    prefix that used to precede each name in the switcher — organisation
    setup status is not a checklist the sidebar needs to broadcast; the
    name alone is enough, matching the simplified reference design.
    """
    _section_label("ORGANISATION")

    companies   = get_summary_fn()
    active_slot = get_slot_fn()
    org         = get_org_fn()

    if org:
        company = org.get("company_name", "") or (companies[active_slot]["name"] if companies else "")
        initials = "".join(w[0] for w in company.split()[:2]).upper() or "?"
        company_safe  = html.escape(company)
        initials_safe = html.escape(initials)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:2px 4px 6px;">'
            f'<div style="width:26px;height:26px;border-radius:50%;background:{SIDEBAR_ACTIVE_BG};'
            f'color:{SIDEBAR_TEXT};font-family:{FONT_BODY};font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">{initials_safe}</div>'
            f'<div style="font-family:{FONT_BODY};font-size:{SIZE_BASE};font-weight:{WEIGHT_BOLD};'
            f'color:{SIDEBAR_TEXT};line-height:1.2;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{company_safe}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    options = list(range(len(companies)))
    def _fmt(i: int) -> str:
        return companies[i]["name"]

    selected = st.selectbox(
        "org", options=options, format_func=_fmt, index=active_slot,
        key="sidebar_org_select", label_visibility="collapsed",
    )
    if selected != active_slot:
        set_slot_fn(selected)
        st.rerun()

    if org:
        sector   = org.get("sector", "")
        province = org.get("province", "")
        period   = org.get("reporting_period", "")
        rows = [r for r in [sector, province, period] if r]
        if rows:
            st.markdown(
                f'<div style="font-size:{SIZE_XS};color:{SIDEBAR_TEXT_MUTED};padding:2px 4px 0;'
                f'line-height:1.6;">{" \u00b7 ".join(rows)}</div>',
                unsafe_allow_html=True,
            )

    try:
        from services.auth_service import is_demo_mode
        if is_demo_mode():
            st.markdown(
                f'<div style="margin-top:4px;">',
                unsafe_allow_html=True,
            )
            if st.button("Set up real organisation", key="sidebar_setup_real_org",
                         **width_stretch_kwargs()):
                from services.demo_service import exit_demo_mode
                from services.state_service import set_active_page
                exit_demo_mode(slot=0)
                set_active_page("executive_summary")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        pass


def _render_demo_mode_card() -> None:
    """
    Demo Mode entry point, restored to the sidebar per the reference
    design. Real action, not decorative: clicking it calls the existing
    services.demo_service.enable_demo_mode() (already used by app.py's own
    startup flow) and reruns — app.py's top-level check
    (`if is_demo_mode_active(): init_demo_organisation()`) then populates
    the demo organisation on the very next render, exactly the same path
    already exercised on first launch. When already in Demo Mode, the card
    becomes a plain status row instead of a repeatable no-op button.
    """
    try:
        from services.demo_service import is_demo_mode_active, enable_demo_mode
    except Exception:
        return

    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)

    if is_demo_mode_active():
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.06);border:1px solid {SIDEBAR_BORDER};'
            f'border-radius:10px;padding:10px 12px;display:flex;align-items:center;gap:8px;">'
            f'{icon("check_circle", size=15, color=BRAND_LIME)}'
            f'<div style="font-size:{SIZE_XS};font-weight:{WEIGHT_BOLD};color:{SIDEBAR_TEXT};">'
            f'Demo Mode \u2014 Active</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    marker_id = "cl-demo-mode-card"
    icon_uri  = icon_data_uri("esg", color=BRAND_LIME, size=16)
    st.markdown(
        f'<div id="{marker_id}" style="display:none;"></div>'
        f'<style>'
        f'div[data-testid="stMarkdown"]:has(#{marker_id}) + * button {{'
        f'  background-color: rgba(255,255,255,0.06) !important;'
        f'  background-image: url("{icon_uri}") !important;'
        f'  background-repeat: no-repeat !important;'
        f'  background-position: 12px 12px !important;'
        f'  border: 1px solid {SIDEBAR_BORDER} !important;'
        f'  border-radius: 10px !important;'
        f'  text-align: left !important;'
        f'  justify-content: flex-start !important;'
        f'  padding: 10px 12px 10px 38px !important;'
        f'  color: {SIDEBAR_TEXT} !important;'
        f'  font-weight: 500 !important;'
        f'}}'
        f'div[data-testid="stMarkdown"]:has(#{marker_id}) + * button:hover {{'
        f'  background-color: rgba(255,255,255,0.12) !important;'
        f'  border-color: {BRAND_LIME} !important;'
        f'}}'
        f'</style>',
        unsafe_allow_html=True,
    )
    if st.button("Demo Mode \u2014 Explore with sample data \u2192",
                 key="sidebar_demo_mode_card", **width_stretch_kwargs()):
        enable_demo_mode()
        st.rerun()


def _render_environment_footer() -> None:
    """Small, muted environment/build metadata — never competes with navigation."""
    st.markdown(
        f'<div style="height:1px;background:{SIDEBAR_BORDER};margin:14px 0 8px;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:9px;font-weight:{WEIGHT_BOLD};text-transform:uppercase;'
        f'letter-spacing:{TRACKING_WIDE};color:{SIDEBAR_TEXT_MUTED};margin:0 0 4px 4px;">'
        f'ENVIRONMENT</div>'
        f'<div style="font-size:{SIZE_XS};color:{SIDEBAR_TEXT_MUTED};padding:0 4px;line-height:1.7;">'
        f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
        f'background:{BRAND_LIME};margin-right:6px;"></span>'
        f'Portfolio \u00b7 thesis build<br>'
        f'<span style="padding-left:12px;">Design system v1.0 \u00b7 FY24 locked</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
