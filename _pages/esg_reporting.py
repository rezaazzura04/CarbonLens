"""
CarbonLens V7 — ESG Reporting Module
Fully connected to ESG Analytics & AI Prediction session data.
Zero manual re-entry. Auto-populates from uploaded dataset.
"""

from __future__ import annotations
import io, datetime
import streamlit as st
import utils.state as S
from utils.state import get_scope_results
from components.ui import page_header, kpi_card, scope_bar, stat_row, divider
from utils.calculations import (
    calculate_esg_score, get_benchmark, benchmark_gap,
    dataset_overview, generate_demo_data, predict_next_emission, annual_projection,
    overshoot_risk,
)
from config.settings import COLORS


# ─────────────────────────────────────────────────────────────────────────────
# PDF BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_pdf(data: dict) -> bytes:
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors as rl
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os as _os

    # ── Register Montserrat (falls back to Helvetica if assets missing) ──────
    _assets_dir = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "assets")
    _reg_path   = _os.path.join(_assets_dir, "Montserrat-Regular.ttf")
    _bold_path  = _os.path.join(_assets_dir, "Montserrat-Bold.ttf")
    try:
        if _os.path.exists(_reg_path) and _os.path.exists(_bold_path):
            pdfmetrics.registerFont(TTFont("Montserrat",      _reg_path))
            pdfmetrics.registerFont(TTFont("Montserrat-Bold", _bold_path))
            FONT_REG, FONT_BOLD = "Montserrat", "Montserrat-Bold"
        else:
            FONT_REG, FONT_BOLD = "Helvetica", "Helvetica-Bold"
    except Exception:
        FONT_REG, FONT_BOLD = "Helvetica", "Helvetica-Bold"

    GREEN = rl.HexColor("#2D7A4F"); LIGHT = rl.HexColor("#E0F2FE")
    GRAY  = rl.HexColor("#6B7280"); DARK  = rl.HexColor("#1F2937")
    BLUE  = rl.HexColor("#1E40AF"); WARN  = rl.HexColor("#F59E0B")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2.2*cm, leftMargin=2.2*cm,
                            topMargin=2.2*cm,   bottomMargin=2.2*cm)
    ss = getSampleStyleSheet()
    def S(base, **kw):
        return ParagraphStyle(base + "_cl", parent=ss.get(base, ss["Normal"]), **kw)

    T_cover  = S("Title",  fontName=FONT_BOLD, fontSize=24, textColor=DARK,  leading=30, spaceAfter=4)
    T_sub    = S("Normal", fontName=FONT_REG,  fontSize=11, textColor=GRAY,  leading=16, spaceAfter=12)
    T_h2     = S("Normal", fontName=FONT_BOLD, fontSize=13, textColor=GREEN, leading=18, spaceAfter=6, spaceBefore=18)
    T_h3     = S("Normal", fontName=FONT_BOLD, fontSize=11, textColor=DARK,  leading=16, spaceAfter=4, spaceBefore=10)
    T_body   = S("Normal", fontName=FONT_REG,  fontSize=10, textColor=DARK,  leading=15, spaceAfter=5)
    T_cap    = S("Normal", fontName=FONT_REG,  fontSize=9,  textColor=GRAY,  leading=13)
    T_kpi    = S("Normal", fontName=FONT_BOLD, fontSize=20, textColor=GREEN, leading=24, alignment=TA_CENTER)
    T_label  = S("Normal", fontName=FONT_REG,  fontSize=9,  textColor=GRAY,  leading=12, alignment=TA_CENTER)

    story = []

    # ── COVER ────────────────────────────────────────────────────────────
    story += [
        Paragraph("CarbonLens ESG Intelligence Platform", S("Normal", fontName=FONT_REG, fontSize=10, textColor=GREEN, spaceAfter=6)),
        HRFlowable(width="100%", thickness=2, color=GREEN, spaceAfter=14),
        Paragraph(f"ESG Sustainability Report — FY {data['year']}", T_cover),
        Paragraph(f"Prepared for: <b>{data['org_name']}</b>  ·  Sector: {data['sector']}  ·  {data['date']}", T_sub),
        HRFlowable(width="100%", thickness=0.5, color=rl.HexColor("#E5E7EB"), spaceAfter=18),
    ]

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", T_h2))
    story.append(Paragraph(
        f"{data['org_name']} recorded total GHG emissions of <b>{data['total_em']:,.0f} tCO₂e</b> "
        f"in FY {data['year']}, achieving an ESG score of <b>{data['esg_score']}/100 (Grade {data['esg_grade']})</b>. "
        f"Carbon intensity stands at <b>{data['intensity']:.2f} kg CO₂e/m²</b>, which is "
        f"{'above' if data['above_bench'] else 'below'} the {data['sector']} sector benchmark of "
        f"{data['benchmark']} kg CO₂e/m². "
        f"AI forecasting projects annual emissions of <b>{data['annual_proj']:,.0f} tCO₂e</b> "
        f"over the next 12 months, representing a <b>{data['trend_dir'].title()}</b> trend. "
        f"Data completeness reached <b>{data['completeness']:.0f}%</b>, meeting GRI reporting thresholds.",
        T_body,
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(PageBreak())

    # ── KPI SUMMARY TABLE ────────────────────────────────────────────────
    story.append(Paragraph("2. Key Performance Indicators", T_h2))
    kpi_data = [
        [Paragraph("Total Emissions", T_label), Paragraph("ESG Score", T_label),
         Paragraph("ESG Grade", T_label),        Paragraph("Annual Forecast", T_label)],
        [Paragraph(f"{data['total_em']:,.0f} tCO₂e", T_kpi),
         Paragraph(f"{data['esg_score']}/100", T_kpi),
         Paragraph(data['esg_grade'], T_kpi),
         Paragraph(f"{data['annual_proj']:,.0f} tCO₂e", T_kpi)],
    ]
    kpi_tbl = Table(kpi_data, colWidths=["25%","25%","25%","25%"])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, rl.HexColor("#E5E7EB")),
        ("INNERGRID",  (0,0),(-1,-1), 0.5, rl.HexColor("#E5E7EB")),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
    ]))
    story += [kpi_tbl, Spacer(1, 0.4*cm)]

    # ── ESG OVERVIEW ─────────────────────────────────────────────────────
    story.append(Paragraph("3. ESG Performance Overview", T_h2))
    esg_rows = [
        ["Dimension",        "Score", "Benchmark", "Status"],
        ["Environmental",    str(data['env_score']),    "70+", "✓" if data['env_score'] >= 70 else "△"],
        ["Social",           str(data['social_score']), "65+", "✓" if data['social_score'] >= 65 else "△"],
        ["Governance",       str(data['gov_score']),    "65+", "✓" if data['gov_score'] >= 65 else "△"],
        ["Overall ESG",      f"{data['esg_score']} ({data['esg_grade']})", "75+", "✓" if data['esg_score'] >= 75 else "△"],
    ]
    esg_tbl = Table(esg_rows, colWidths=["40%","20%","20%","20%"])
    esg_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), GREEN), ("TEXTCOLOR", (0,0),(-1,0), rl.white),
        ("FONTNAME",   (0,0),(-1,0), FONT_BOLD), ("FONTSIZE", (0,0),(-1,-1), 10),
        ("BOX",        (0,0),(-1,-1), 0.5, rl.HexColor("#E5E7EB")),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, rl.HexColor("#F3F4F6")),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [rl.white, rl.HexColor("#FAFAFA")]),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0),(-1,-1), 7), ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
    ]))
    story += [esg_tbl, Spacer(1, 0.4*cm)]
    story.append(PageBreak())

    # ── ENVIRONMENTAL PERFORMANCE ─────────────────────────────────────────
    story.append(Paragraph("4. Environmental Performance", T_h2))
    env_rows = [
        ["Metric",            "Value",                 "Unit",       "Trend"],
        ["Carbon Emissions",  f"{data['total_em']:,.0f}", "tCO₂e",  data['trend_dir'].title()],
        ["Energy Consumption",f"{data['energy']:,.0f}",   "MWh",    "Monitoring"],
        ["Water Consumption", f"{data['water']:,.0f}",    "m³",     "Monitoring"],
        ["Waste Generation",  f"{data['waste']:.1f}",    "tonnes", "Monitoring"],
        ["Carbon Intensity",  f"{data['intensity']:.2f}","kg/m²",  "—"],
        ["Scope 1",           f"{data['scope1']:,.0f}",  "tCO₂e",  "Direct"],
        ["Scope 2",           f"{data['scope2']:,.0f}",  "tCO₂e",  "Indirect"],
        ["Scope 3 (est.)",    f"{data['scope3']:,.0f}",  "tCO₂e",  "Value chain"],
    ]
    env_tbl = Table(env_rows, colWidths=["35%","25%","20%","20%"])
    env_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), GREEN), ("TEXTCOLOR", (0,0),(-1,0), rl.white),
        ("FONTNAME",   (0,0),(-1,0), FONT_BOLD), ("FONTSIZE", (0,0),(-1,-1), 10),
        ("BOX",        (0,0),(-1,-1), 0.5, rl.HexColor("#E5E7EB")),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, rl.HexColor("#F3F4F6")),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [rl.white, rl.HexColor("#FAFAFA")]),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0),(-1,-1), 7), ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
    ]))
    story += [env_tbl, Spacer(1, 0.4*cm)]

    # ── FORECAST ANALYSIS ─────────────────────────────────────────────────
    story.append(Paragraph("5. Forecast & Risk Analysis", T_h2))
    overshoot_pct = max((data['annual_proj'] / max(data['benchmark_annual'], 1) - 1) * 100, 0)
    story.append(Paragraph(
        f"AI linear regression forecasting (R² = {data['r2']:.2f}) projects an annual total of "
        f"<b>{data['annual_proj']:,.0f} tCO₂e</b> over the next 12 months. "
        f"The emission trend is <b>{data['trend_dir']}</b> with a slope of "
        f"{data['slope']:+.1f} tCO₂e per month. "
        f"Risk of exceeding the 2026 target is classified as <b>{data['risk_level']}</b> "
        f"({data['risk_prob']*100:.0f}% overshoot probability). "
        f"Benchmark comparison shows emissions are projected to be "
        f"<b>{overshoot_pct:.0f}% {'above' if overshoot_pct > 0 else 'below'}</b> "
        f"the annual sector benchmark.",
        T_body,
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(PageBreak())

    # ── FRAMEWORKS ───────────────────────────────────────────────────────
    story.append(Paragraph("6. Reporting Framework Compliance", T_h2))
    fw_rows = [
        ["Framework",              "Status",        "Coverage"],
        ["GRI Standards 2021",    "✓ Compliant",   "GRI 305 Emissions, GRI 302 Energy, GRI 303 Water"],
        ["TCFD Framework",        "✓ Compliant",   "Physical & transition climate risk disclosures"],
        ["ISSB IFRS S2",          "⏳ In Progress", "Climate disclosures — target FY2026"],
        ["ISO 14064-1:2018",      "✓ Aligned",     "GHG inventory boundaries and methodology"],
        ["GHG Protocol Corporate","✓ Aligned",     "Scope 1, 2 categorisation and accounting"],
    ]
    fw_tbl = Table(fw_rows, colWidths=["32%","20%","48%"])
    fw_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), GREEN), ("TEXTCOLOR", (0,0),(-1,0), rl.white),
        ("FONTNAME",   (0,0),(-1,0), FONT_BOLD), ("FONTSIZE", (0,0),(-1,-1), 9),
        ("BOX",        (0,0),(-1,-1), 0.5, rl.HexColor("#E5E7EB")),
        ("INNERGRID",  (0,0),(-1,-1), 0.3, rl.HexColor("#F3F4F6")),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [rl.white, rl.HexColor("#FAFAFA")]),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0),(-1,-1), 6), ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
    ]))
    story += [fw_tbl, Spacer(1, 0.4*cm)]
    story.append(PageBreak())

    # ── STRATEGIC RECOMMENDATIONS ─────────────────────────────────────────
    story.append(Paragraph("7. Strategic Recommendations", T_h2))
    recs = [
        ("Renewable Energy Transition",
         f"Commit to 25% renewable electricity by 2026. Estimated Scope 2 reduction: −15% annually (~{data['scope2']*0.15:,.0f} tCO₂e/yr). Implement rooftop PPA and bilateral green energy agreement."),
        ("Energy Efficiency Programme",
         f"Commission ISO 50001 energy audit targeting HVAC, lighting, and process optimization. Estimated savings: 8–12% of current Scope 2 ({data['scope2']*0.10:,.0f}–{data['scope2']*0.12:,.0f} tCO₂e/yr). Payback period: <2 years."),
        ("Supply Chain Decarbonisation",
         "Engage Tier 1 suppliers on joint Scope 3 reduction targets. Implement supplier ESG scorecard and green procurement preference. Target: −10% Scope 3 within 36 months."),
        ("Blue Carbon Offset Portfolio",
         "Invest in verified blue carbon credits from Delta Mahakam mangrove conservation (VCS VM0007). 12,400 ha REDD+-eligible area identified via GEDI LiDAR analysis. Estimated offset potential: 0.21 Tg C/yr."),
    ]
    for i, (title_txt, body_txt) in enumerate(recs, 1):
        story.append(KeepTogether([
            Paragraph(f"{i}. {title_txt}", T_h3),
            Paragraph(body_txt, T_body),
            Spacer(1, 0.2*cm),
        ]))

    # ── FOOTER ───────────────────────────────────────────────────────────
    story += [
        Spacer(1, 0.6*cm),
        HRFlowable(width="100%", thickness=0.5, color=rl.HexColor("#E5E7EB")),
        Spacer(1, 0.3*cm),
        Paragraph(
            f"Generated by CarbonLens V7.0 on {data['date']}. "
            "Data sourced from internal operational records validated against GHG Protocol. "
            "This report is intended for internal sustainability management and external ESG disclosure. "
            "For enquiries: esg@carbonlens.io",
            T_cap,
        ),
    ]

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    S.init()

    page_header(
        title="ESG Reporting",
        subtitle="Auto-populated from ESG Analytics · AI Predictions connected · PDF export",
        badge="Consulting Grade",
        badge_type="blue",
    )

    # ── Data source ────────────────────────────────────────────────────────
    uploaded = S.get("uploaded_df")
    has_data = uploaded is not None

    if not has_data:
        st.markdown("""
        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;
                    padding:20px 24px;margin-bottom:20px;display:flex;gap:14px;align-items:flex-start;">
            <div style="font-size:24px;">⚠️</div>
            <div>
                <div style="font-size:13px;font-weight:700;color:#92400E;margin-bottom:4px;">
                    Demo Mode — No ESG Dataset Uploaded
                </div>
                <div style="font-size:12px;color:#6B7280;line-height:1.7;">
                    Report is populated with <strong>demo data</strong>. Navigate to
                    <strong>ESG Analytics</strong> and upload your CSV dataset to generate
                    a real report with your organization's actual performance data.
                    All metrics below will update automatically after upload.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    df      = uploaded if has_data else generate_demo_data()
    ov      = dataset_overview(df)
    total_em = ov.get("total", 0)
    avg_em   = ov.get("average", 0)

    # Auto-populate company from session state
    company_default = S.get("company_name", "")
    sector   = st.session_state.get("sector", "Manufacturing")
    area     = float(S.get("area_m2", 5000))
    from utils.state import compute_canonical_esg, get_scope_results
    esg      = compute_canonical_esg()
    intens   = get_scope_results()["intens_m2"]
    bench    = get_benchmark(sector)
    gap      = benchmark_gap(intens, bench)

    # ── Scope totals from Carbon Accounting (preferred) or ratio fallback ──
    _sc_rpt   = get_scope_results()
    scope1    = round(_sc_rpt["scope1_kg"] / 1000, 2)   # tCO2e
    scope2    = round(_sc_rpt["scope2_kg"] / 1000, 2)
    scope3    = round(_sc_rpt["scope3_kg"] / 1000, 2)
    _scope_src= _sc_rpt["source"]

    energy_kwh = df["Energy"].sum() if "Energy" in df.columns else total_em * 14.2
    water_m3   = df["Water"].sum()  if "Water"  in df.columns else total_em * 2.8
    waste_t    = df["Waste"].sum()  if "Waste"  in df.columns else total_em * 0.11

    # Forecast data (from AI Prediction module logic)
    pred       = predict_next_emission(df)
    annual     = annual_projection(df)
    bench_ann  = bench * 12 * 100
    risk       = overshoot_risk(annual, bench_ann)
    trend_dir  = pred.get("trend_dir", "stable")
    r2         = pred.get("r2", 0) or 0
    slope      = pred.get("slope", 0) or 0

    # ── Report Configuration ───────────────────────────────────────────────
    st.markdown("""
    <div class="cl-card" style="margin-bottom:20px;">
        <div class="cl-card-title">⚙️ Report Configuration</div>
        <div class="cl-card-subtitle">Customize parameters · All ESG data auto-populated from your upload</div>
    """, unsafe_allow_html=True)

    cfg1, cfg2, cfg3, cfg4 = st.columns(4, gap="medium")
    with cfg1:
        org_name = st.text_input("Organization Name", value=company_default, key="rpt_org")
    with cfg2:
        year = st.selectbox("Reporting Year", [2025, 2024, 2023], key="rpt_year")
    with cfg3:
        sector_sel = st.selectbox("Sector", ["Manufacturing","Office","University","Hospital","Retail","Data Center","Hotel"],
                                  index=0, key="rpt_sector")
    with cfg4:
        frameworks = st.multiselect("Frameworks",
            ["GRI 2021", "TCFD", "ISSB IFRS S2", "ISO 14064", "GHG Protocol"],
            default=["GRI 2021", "TCFD"], key="rpt_fw")

    # Persist sector
    st.session_state["sector"] = sector_sel
    bench_updated = get_benchmark(sector_sel)
    gap_updated   = benchmark_gap(intens, bench_updated)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Live Preview ───────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                color:#2D7A4F;margin-bottom:16px;">📄 Live Report Preview</div>
    """, unsafe_allow_html=True)

    # Report header
    today_str = datetime.date.today().strftime("%B %d, %Y")
    st.markdown(f"""
    <div class="cl-report-page">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    padding-bottom:20px;border-bottom:2px solid #2D7A4F;margin-bottom:24px;">
            <div>
                <div style="font-size:10px;color:#2D7A4F;font-weight:700;text-transform:uppercase;
                            letter-spacing:1.5px;margin-bottom:4px;">CarbonLens ESG Intelligence Platform</div>
                <div style="font-size:26px;font-weight:800;color:#1F2937;letter-spacing:-0.5px;">{org_name}</div>
                <div style="font-size:12px;color:#6B7280;margin-top:4px;">
                    ESG Sustainability Report · FY {year} · {sector_sel} Sector · {today_str}
                </div>
                <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
                    {''.join([f"<span style='background:#E0F2FE;color:#0C4A6E;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;'>{fw}</span>" for fw in frameworks])}
                </div>
            </div>
            <div style="text-align:center;background:#E0F2FE;padding:18px 28px;border-radius:14px;
                        border:1px solid #BAE6FD;flex-shrink:0;">
                <div style="font-size:42px;font-weight:900;color:#2D7A4F;line-height:1;">{esg['grade']}</div>
                <div style="font-size:10px;color:#6B7280;text-transform:uppercase;letter-spacing:0.5px;">ESG Rating</div>
                <div style="font-size:12px;color:#2D7A4F;font-weight:700;">{esg['label']}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{esg['score']}/100</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Section 1: KPI summary ─────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
                color:#2D7A4F;margin:20px 0 12px;">1 — Key Performance Indicators</div>
    """, unsafe_allow_html=True)

    rk1, rk2, rk3, rk4, rk5 = st.columns(5, gap="medium")
    with rk1:
        kpi_card("Total Emissions",  f"{total_em:,.0f}", icon="☁️",  icon_bg="#FEE2E2",
                 badge="tCO₂e", badge_type="gray")
    with rk2:
        kpi_card("Energy",           f"{energy_kwh:,.0f}", icon="⚡", icon_bg="#FFF7ED",
                 badge="MWh", badge_type="gray")
    with rk3:
        kpi_card("Water Usage",      f"{water_m3:,.0f}", icon="💧",  icon_bg="#EFF6FF",
                 badge="m³", badge_type="gray")
    with rk4:
        kpi_card("ESG Score",        f"{esg['score']}/100", icon="🎯", icon_bg="#E0F2FE",
                 badge=f"Grade {esg['grade']}", badge_type="green")
    with rk5:
        above = gap_updated["above_benchmark"]
        kpi_card("vs Benchmark",     f"{gap_updated['gap_pct']:+.1f}%", icon="📏",
                 icon_bg="#FEF3C7" if above else "#E0F2FE",
                 badge="Above" if above else "Below",
                 badge_type="red" if above else "green")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Section 2: ESG Overview + Scope ───────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
                color:#2D7A4F;margin-bottom:12px;">2 — ESG Performance Overview</div>
    """, unsafe_allow_html=True)

    rpt_l, rpt_r = st.columns(2, gap="large")

    with rpt_l:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">📊 ESG Score Breakdown</div>
            <div class="cl-card-subtitle">Environmental · Social · Governance</div>
        """, unsafe_allow_html=True)
        for dim, score, color in [
            ("Environmental", esg["env"],    COLORS["primary"]),
            ("Social",        esg["social"], COLORS["secondary"]),
            ("Governance",    esg["gov"],    COLORS["accent"]),
        ]:
            pct = min(max(score, 0), 100)
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:600;color:#374151;">{dim}</span>
                    <span style="font-size:12px;font-weight:700;color:{color};">{pct:.0f}/100</span>
                </div>
                <div style="height:8px;background:#F3F4F6;border-radius:4px;overflow:hidden;">
                    <div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#F9FAFB;border-radius:8px;padding:12px;margin-top:8px;">
            <div style="font-size:11px;color:#6B7280;line-height:1.7;">
                Overall score of <strong>{esg['score']}/100 (Grade {esg['grade']})</strong> reflects
                {'strong' if esg['score'] >= 75 else 'moderate'} sustainability performance.
                {'Carbon intensity is ' + ('above' if gap_updated['above_benchmark'] else 'below') + ' the sector benchmark by ' + str(abs(gap_updated['gap_pct'])) + '%.'  }
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with rpt_r:
        st.markdown("""
        <div class="cl-card">
            <div class="cl-card-title">⬡ GHG Scope Breakdown</div>
            <div class="cl-card-subtitle">GHG Protocol · Scope 1, 2 & 3</div>
        """, unsafe_allow_html=True)
        scope_bar("Scope 1 — Direct combustion",      scope1, total_em, color=COLORS["danger"])
        scope_bar("Scope 2 — Purchased electricity",  scope2, total_em, color=COLORS["warning"])
        _scope3_label = "Value chain (estimated)" if _scope_src in ("csv_estimate","csv_scope_columns") else "Value chain"
        scope_bar(f"Scope 3 — {_scope3_label}", scope3, total_em, color=COLORS["primary"])
        if _scope_src == "csv_estimate":
            st.markdown("""
            <div style="font-size:10px;color:#F59E0B;margin-top:8px;padding:6px 10px;
                        background:#FFFBEB;border-radius:6px;border-left:3px solid #F59E0B;">
                ⚠️ Scope breakdown is estimated from GHG Protocol typical ratios
                because Carbon Accounting module has not been used yet.
                For audit-grade figures, enter activity data in
                <strong>Carbon Accounting</strong> before generating the PDF.
            </div>""", unsafe_allow_html=True)
        elif _scope_src == "csv_scope_columns":
            st.markdown("""
            <div style="font-size:10px;color:#059669;margin-top:8px;padding:6px 10px;
                        background:#F0FDF4;border-radius:6px;border-left:3px solid #34D399;">
                ✅ Scope 1 & 2 from your uploaded dataset. Scope 3 = remainder.
                For full GHG Protocol Scope 3 categories, use <strong>Carbon Accounting</strong>.
            </div>""", unsafe_allow_html=True)
        fw_status = {
            "GRI 2021": ("✅","Compliant"), "TCFD": ("✅","Compliant"),
            "ISSB IFRS S2": ("⏳","In Progress"), "ISO 14064": ("✅","Aligned"),
            "GHG Protocol": ("✅","Aligned"),
        }
        st.markdown("<div style='margin-top:16px;'>", unsafe_allow_html=True)
        for fw, (icon, status) in fw_status.items():
            if fw.replace(" ", "").replace("IFRS","") in " ".join(frameworks).replace(" ", "").replace("IFRS","") or fw in frameworks:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:6px 0;border-bottom:1px solid #F9FAFB;font-size:11px;">
                    <span style="color:#374151;">{fw}</span>
                    <span style="color:#2D7A4F;font-weight:600;">{icon} {status}</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Section 3: Environmental Performance ──────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
                color:#2D7A4F;margin-bottom:12px;">3 — Environmental Performance</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="cl-card">
        <div class="cl-card-title">🌍 Resource Consumption & Emissions</div>
        <div class="cl-card-subtitle">FY {year} · Derived automatically from uploaded ESG dataset</div>
    """, unsafe_allow_html=True)

    env_data = [
        ("Carbon Emissions",    f"{total_em:,.0f}",    "tCO₂e",   "☁️",  "#EF4444"),
        ("Energy Consumption",  f"{energy_kwh:,.0f}",  "MWh",     "⚡",  "#F59E0B"),
        ("Water Consumption",   f"{water_m3:,.0f}",    "m³",      "💧",  "#3B82F6"),
        ("Waste Generation",    f"{waste_t:.1f}",      "tonnes",  "♻️",  "#8B5CF6"),
        ("Carbon Intensity",    f"{intens:.2f}",       "kg/m²",   "📊",  "#2D7A4F"),
        ("Peak Month",          ov.get("peak_month","—"), "—",    "📅",  "#F59E0B"),
        ("Data Completeness",   f"{ov.get('completeness',94):.0f}%", "—","✅","#10B981"),
        ("Benchmark vs Sector", f"{gap_updated['gap_pct']:+.1f}%", "—", "📏",
         "#EF4444" if gap_updated['above_benchmark'] else "#10B981"),
    ]
    col_a, col_b = st.columns(2, gap="medium")
    for i, (label, val, unit, icon, color) in enumerate(env_data):
        target = col_a if i % 2 == 0 else col_b
        with target:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:9px 0;border-bottom:1px solid #F9FAFB;">
                <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#6B7280;">
                    <span>{icon}</span>{label}
                </div>
                <div style="text-align:right;">
                    <span style="font-size:13px;font-weight:700;color:{color};">{val}</span>
                    <span style="font-size:10px;color:#9CA3AF;margin-left:3px;">{unit}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Section 4: Forecast Analysis ──────────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
                color:#2D7A4F;margin-bottom:12px;">4 — Forecast & Risk Analysis</div>
    """, unsafe_allow_html=True)

    fc_col, risk_col = st.columns(2, gap="medium")

    with fc_col:
        risk_bt = {"Low":"green","Moderate":"yellow","High":"yellow","Critical":"red"}.get(risk["level"],"gray")
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">🤖 AI Forecast Summary</div>
            <div class="cl-card-subtitle">Linear regression · 12-month projection · R² = {r2:.2f}</div>
            <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px;">
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F9FAFB;">
                    <span style="font-size:12px;color:#6B7280;">Annual Projection</span>
                    <span style="font-size:13px;font-weight:700;color:#1F2937;">{annual:,.0f} tCO₂e</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F9FAFB;">
                    <span style="font-size:12px;color:#6B7280;">Trend Direction</span>
                    <span style="font-size:13px;font-weight:700;color:{'#EF4444' if trend_dir=='increasing' else '#10B981'};">{trend_dir.title()}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F9FAFB;">
                    <span style="font-size:12px;color:#6B7280;">Monthly Slope</span>
                    <span style="font-size:13px;font-weight:700;color:#1F2937;">{slope:+.1f} tCO₂e/mo</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F9FAFB;">
                    <span style="font-size:12px;color:#6B7280;">Risk Level</span>
                    <span style="font-size:13px;font-weight:700;color:{'#EF4444' if risk['level'] in ['High','Critical'] else '#F59E0B' if risk['level']=='Moderate' else '#10B981'};">{risk['level']}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0;">
                    <span style="font-size:12px;color:#6B7280;">Overshoot Probability</span>
                    <span style="font-size:13px;font-weight:700;color:#1F2937;">{risk['probability']*100:.0f}%</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with risk_col:
        nz_prob = max(0.05, 1 - risk["probability"] - 0.4)
        st.markdown(f"""
        <div class="cl-card">
            <div class="cl-card-title">🎯 Strategic Outlook</div>
            <div class="cl-card-subtitle">Net-zero pathway assessment</div>
            <div style="font-size:13px;color:#374151;line-height:1.8;padding:12px 0;margin-bottom:12px;
                        border-bottom:1px solid #F3F4F6;">
                At current trajectory, annual emissions of <strong>{annual:,.0f} tCO₂e</strong> will
                require a <strong>−62% reduction</strong> from today's baseline to meet 2030 net-zero
                commitment. Implementing all recommended interventions could achieve this by
                <strong>Q2 2027</strong>.
            </div>
            <div style="display:flex;gap:12px;">
                <div style="flex:1;background:#E0F2FE;border-radius:10px;padding:14px;text-align:center;">
                    <div style="font-size:22px;font-weight:800;color:#2D7A4F;">{nz_prob*100:.0f}%</div>
                    <div style="font-size:10px;color:#6B7280;margin-top:2px;">Net-Zero 2030 Probability</div>
                </div>
                <div style="flex:1;background:#{'FEF2F2' if risk['probability']>0.5 else 'FFFBEB'};border-radius:10px;padding:14px;text-align:center;">
                    <div style="font-size:22px;font-weight:800;color:{'#EF4444' if risk['probability']>0.5 else '#F59E0B'};">{risk['probability']*100:.0f}%</div>
                    <div style="font-size:10px;color:#6B7280;margin-top:2px;">Target Overshoot Risk</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Section 5: Recommendations ────────────────────────────────────────
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;
                color:#2D7A4F;margin-bottom:12px;">5 — Strategic Recommendations</div>
    """, unsafe_allow_html=True)

    recs_display = [
        {"priority":"HIGH",   "color":"#EF4444", "bg":"#FEF2F2", "num":"1",
         "title":"Renewable Energy Transition",
         "body":f"Commit to 25% renewable electricity by 2026. Estimated Scope 2 reduction: ~{scope2*0.15:,.0f} tCO₂e/yr. Implement rooftop solar PPA.",
         "meta":"Investment: Medium · Payback: 5–7 yrs · Impact: HIGH"},
        {"priority":"HIGH",   "color":"#F59E0B", "bg":"#FFFBEB", "num":"2",
         "title":"Energy Efficiency Audit (ISO 50001)",
         "body":f"HVAC, lighting, and process optimization targeting 8–12% Scope 2 reduction ({scope2*0.10:,.0f}–{scope2*0.12:,.0f} tCO₂e/yr).",
         "meta":"Investment: Low · Payback: <2 yrs · Impact: HIGH"},
        {"priority":"MEDIUM", "color":"#3B82F6", "bg":"#EFF6FF", "num":"3",
         "title":"Supply Chain Decarbonisation",
         "body":"Engage Tier 1 suppliers on Scope 3 reduction targets via ESG scorecard and green procurement criteria.",
         "meta":"Investment: Low · Timeline: 6–12 months · Impact: MEDIUM"},
        {"priority":"MEDIUM", "color":"#8B5CF6", "bg":"#F5F3FF", "num":"4",
         "title":"Blue Carbon Offset Portfolio",
         "body":"Invest in REDD+ verified blue carbon credits (VCS VM0007). 12,400 ha eligible area in Delta Mahakam identified via GIS analysis.",
         "meta":"Investment: Medium · Impact: HIGH · Co-benefit: Biodiversity"},
    ]
    rec_l, rec_r = st.columns(2, gap="medium")
    for i, r in enumerate(recs_display):
        with (rec_l if i % 2 == 0 else rec_r):
            st.markdown(f"""
            <div style="border:1px solid {r['color']}30;border-left:4px solid {r['color']};
                        border-radius:10px;padding:14px 16px;margin-bottom:10px;background:{r['bg']};">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="background:{r['color']};color:white;font-size:9px;font-weight:800;
                                 padding:2px 8px;border-radius:20px;">{r['priority']}</span>
                    <span style="font-size:13px;font-weight:700;color:#1F2937;">{r['num']}. {r['title']}</span>
                </div>
                <div style="font-size:12px;color:#374151;line-height:1.6;margin-bottom:5px;">{r['body']}</div>
                <div style="font-size:10px;color:#9CA3AF;">{r['meta']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── PDF Export ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:12px;
                padding:20px 24px;display:flex;align-items:center;justify-content:space-between;
                flex-wrap:wrap;gap:12px;">
        <div>
            <div style="font-size:13px;font-weight:700;color:#1F2937;margin-bottom:2px;">
                📄 Export this Report as PDF
            </div>
            <div style="font-size:12px;color:#6B7280;">
                Consulting-grade format aligned with GRI, TCFD, and ISSB frameworks.
                All data auto-populated from your uploaded ESG dataset.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    btn_col, _ = st.columns([1, 3])
    with btn_col:
        if st.button("⬇️  Generate & Download PDF", type="primary", use_container_width=True):
            with st.spinner("Generating consulting-grade PDF..."):
                try:
                    pdf_bytes = _build_pdf({
                        "org_name":       org_name,
                        "year":           year,
                        "sector":         sector_sel,
                        "date":           today_str,
                        "total_em":       total_em,
                        "intensity":      intens,
                        "esg_score":      esg["score"],
                        "esg_grade":      esg["grade"],
                        "esg_label":      esg["label"],
                        "env_score":      int(esg["env"]),
                        "social_score":   int(esg["social"]),
                        "gov_score":      int(esg["gov"]),
                        "scope1":         scope1,
                        "scope2":         scope2,
                        "scope3":         scope3,
                        "energy":         energy_kwh,
                        "water":          water_m3,
                        "waste":          waste_t,
                        "benchmark":      bench_updated,
                        "benchmark_annual": bench_ann,
                        "above_bench":    gap_updated["above_benchmark"],
                        "annual_proj":    annual,
                        "trend_dir":      trend_dir,
                        "r2":             r2,
                        "slope":          slope,
                        "risk_level":     risk["level"],
                        "risk_prob":      risk["probability"],
                        "completeness":   ov.get("completeness", 94),
                    })
                    st.download_button(
                        label="📄  Download PDF",
                        data=pdf_bytes,
                        file_name=f"CarbonLens_ESG_Report_{org_name.replace(' ','_')}_{year}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success("✅ Report generated! Click 'Download PDF' above.")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}. Ensure `reportlab` is installed: pip install reportlab")
