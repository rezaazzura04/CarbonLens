"""
CarbonLens V7 — Data Export Center
CSV, JSON, Excel multi-sheet, PDF full ESG report (GRI-referenced)
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import json, io, datetime
import utils.state as S
from components.ui import page_header, kpi_card, empty_state
from utils.calculations import (
    dataset_overview, calculate_esg_score, get_benchmark,
    benchmark_gap, annual_projection, predict_next_emission,
    overshoot_risk, generate_demo_data, NumpyEncoder,
)
from config.settings import COLORS


# ── Builders ─────────────────────────────────────────────────────────────────

def _ctx(df):
    company   = S.get("company_name", "My Organization")
    sector    = S.get("sector", "Manufacturing")
    area_m2   = float(S.get("area_m2", 5000) or 5000)
    from utils.state import compute_canonical_esg, get_scope_results
    esg       = compute_canonical_esg()
    sc        = get_scope_results()
    intensity = sc["intens_m2"]
    bench     = get_benchmark(sector)
    gap       = benchmark_gap(intensity, bench)
    ov        = dataset_overview(df)
    return dict(company=company, sector=sector, area_m2=area_m2,
                esg=esg, sc=sc, intensity=intensity, bench=bench, gap=gap, ov=ov)


def _build_summary_json(df, ctx) -> str:
    pred   = predict_next_emission(df)
    annual = annual_projection(df)
    risk   = overshoot_risk(annual, ctx["bench"] * 1200)
    summary = {
        "metadata": {
            "platform":       "CarbonLens V7",
            "generated":      datetime.datetime.now().isoformat(),
            "company":        ctx["company"],
            "sector":         ctx["sector"],
            "reporting_year": datetime.date.today().year,
        },
        "esg_performance": {
            "overall_score":  ctx["esg"]["score"],
            "grade":          ctx["esg"]["grade"],
            "label":          ctx["esg"]["label"],
            "environmental":  ctx["esg"]["env"],
            "social":         ctx["esg"]["social"],
            "governance":     ctx["esg"]["gov"],
        },
        "ghg_scope": {
            "scope1_tco2e":  round(ctx["sc"]["scope1_kg"] / 1000, 2),
            "scope2_tco2e":  round(ctx["sc"]["scope2_kg"] / 1000, 2),
            "scope3_tco2e":  round(ctx["sc"]["scope3_kg"] / 1000, 2),
            "total_tco2e":   round((ctx["sc"]["scope1_kg"] + ctx["sc"]["scope2_kg"] + ctx["sc"]["scope3_kg"]) / 1000, 2),
            "intensity_kg_m2": round(ctx["intensity"], 2),
            "intensity_kg_emp": round(ctx["sc"].get("intens_emp", 0) or 0, 2),
        },
        "social": {
            "employees":              S.get("employees", 0),
            "women_workforce_pct":    S.get("women_workforce_pct", 0),
            "employee_turnover_pct":  S.get("employee_turnover_pct", 0),
            "training_hours_per_emp": S.get("training_hours_per_employee", 0),
            "injury_rate":            S.get("injury_rate", 0),
        },
        "governance": {
            "board_size":               S.get("board_size", 0),
            "board_independence_pct":   S.get("board_independence_pct", 0),
            "women_board_pct":          S.get("women_board_pct", 0),
            "anti_corruption_pct":      S.get("anti_corruption_training_pct", 0),
            "has_whistleblower":        S.get("has_whistleblower_policy", False),
            "has_code_of_conduct":      S.get("has_code_of_conduct", False),
        },
        "emissions_raw": {
            "total_tco2e":       round(ctx["ov"].get("total", 0), 2),
            "monthly_average":   round(ctx["ov"].get("average", 0), 2),
            "peak_month":        ctx["ov"].get("peak_month", "—"),
            "data_completeness": ctx["ov"].get("completeness", 94),
        },
        "benchmark": {
            "sector":          ctx["sector"],
            "benchmark_kg_m2": ctx["bench"],
            "gap_pct":         round(ctx["gap"]["gap_pct"], 1),
            "above_benchmark": ctx["gap"]["above_benchmark"],
        },
        "forecast": {
            "next_month_tco2e":  round(pred.get("forecast", 0) or 0, 2),
            "annual_projection": round(annual, 2),
            "trend":             pred.get("trend_dir", "stable"),
            "risk_level":        risk["level"],
        },
        "resources": {
            "energy_mwh":   round(df["Energy"].sum(), 1) if "Energy" in df.columns else None,
            "water_m3":     round(df["Water"].sum(), 1)  if "Water"  in df.columns else None,
            "waste_tonnes": round(df["Waste"].sum(), 2)  if "Waste"  in df.columns else None,
        },
    }
    return json.dumps(summary, indent=2, ensure_ascii=False, cls=NumpyEncoder)



def _build_enriched_csv(df, ctx) -> str:
    enriched = df.copy()
    avg   = df["Emission"].mean() if "Emission" in df.columns else 1
    bench = ctx["bench"]
    if "Emission" in df.columns:
        enriched["vs_monthly_avg_%"] = ((df["Emission"] - avg) / avg * 100).round(1)
        enriched["benchmark_gap_%"]  = ((df["Emission"] / (bench * 100) - 1) * 100).round(1)
        enriched["cumulative_tco2e"] = df["Emission"].cumsum().round(2)
    enriched["company"]    = ctx["company"]
    enriched["sector"]     = ctx["sector"]
    enriched["esg_score"]  = ctx["esg"]["score"]
    enriched["esg_grade"]  = ctx["esg"]["grade"]
    enriched["env_score"]  = round(ctx["esg"]["env"], 1)
    enriched["soc_score"]  = round(ctx["esg"]["social"], 1)
    enriched["gov_score"]  = round(ctx["esg"]["gov"], 1)
    return enriched.to_csv(index=False)


def _build_monthly_report(df, ctx) -> pd.DataFrame:
    monthly = df[["Month", "Emission"]].copy() if "Emission" in df.columns else df.copy()
    if "Emission" in monthly.columns:
        sc   = ctx["sc"]
        tot  = sc["scope1_kg"] + sc["scope2_kg"] + sc["scope3_kg"]
        r1   = sc["scope1_kg"] / tot if tot > 0 else 0.295
        r2   = sc["scope2_kg"] / tot if tot > 0 else 0.436
        r3   = sc["scope3_kg"] / tot if tot > 0 else 0.269
        monthly["Scope_1_tco2e"]  = (monthly["Emission"] * r1).round(2)
        monthly["Scope_2_tco2e"]  = (monthly["Emission"] * r2).round(2)
        monthly["Scope_3_tco2e"]  = (monthly["Emission"] * r3).round(2)
        monthly["Benchmark_tco2e"]= round(ctx["bench"] * 100, 1)
        monthly["Gap_%"]          = ((monthly["Emission"] / (ctx["bench"] * 100) - 1) * 100).round(1)
        monthly["Trend"]          = monthly["Emission"].diff().apply(
            lambda x: "↑ Increasing" if x and x > 0 else ("↓ Decreasing" if x and x < 0 else "→ Stable"))
    if "Energy" in df.columns: monthly["Energy_MWh"] = df["Energy"].values
    if "Water"  in df.columns: monthly["Water_m3"]   = df["Water"].values
    if "Waste"  in df.columns: monthly["Waste_t"]    = df["Waste"].values
    return monthly


def _build_excel(df, ctx) -> bytes:
    """Multi-sheet Excel: Overview + Monthly Data + ESG Scorecard + Scope Breakdown + S&G Indicators."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Sheet 1 — Overview / Scorecard
        pred   = predict_next_emission(df)
        annual = annual_projection(df)
        risk   = overshoot_risk(annual, ctx["bench"] * 1200)
        sc1 = pd.DataFrame([{
            "Field": k, "Value": v
        } for k, v in {
            "Company":                ctx["company"],
            "Sector":                 ctx["sector"],
            "Reporting Year":         datetime.date.today().year,
            "Report Generated":       datetime.date.today().isoformat(),
            "Platform":               "CarbonLens V7",
            "— ESG Performance —":    "",
            "Overall ESG Score":      ctx["esg"]["score"],
            "ESG Grade":              ctx["esg"]["grade"],
            "ESG Label":              ctx["esg"]["label"],
            "Environmental Score":    round(ctx["esg"]["env"], 1),
            "Social Score":           round(ctx["esg"]["social"], 1),
            "Governance Score":       round(ctx["esg"]["gov"], 1),
            "— GHG Emissions —":      "",
            "Scope 1 (tCO2e)":        round(ctx["sc"]["scope1_kg"] / 1000, 2),
            "Scope 2 (tCO2e)":        round(ctx["sc"]["scope2_kg"] / 1000, 2),
            "Scope 3 (tCO2e)":        round(ctx["sc"]["scope3_kg"] / 1000, 2),
            "Total Emissions (tCO2e)":round(ctx["ov"].get("total", 0), 2),
            "Carbon Intensity (kg/m2)":round(ctx["intensity"], 2),
            "Benchmark (kg/m2)":      ctx["bench"],
            "Benchmark Gap (%)":      round(ctx["gap"]["gap_pct"], 1),
            "Above Benchmark":        ctx["gap"]["above_benchmark"],
            "— Forecast —":           "",
            "Annual Projection (tCO2e)": round(annual, 2),
            "Next Month Forecast":    round(pred.get("forecast", 0) or 0, 2),
            "Trend":                  pred.get("trend_dir", "stable"),
            "Risk Level":             risk["level"],
        }.items()])
        sc1.to_excel(writer, sheet_name="ESG Overview", index=False)

        # Sheet 2 — Monthly Data
        monthly = _build_monthly_report(df, ctx)
        monthly.to_excel(writer, sheet_name="Monthly Data", index=False)

        # Sheet 3 — Scope Breakdown
        sc_data = pd.DataFrame([
            {"Scope": "Scope 1 — Direct",        "kg CO2e": round(ctx["sc"]["scope1_kg"], 0), "tCO2e": round(ctx["sc"]["scope1_kg"]/1000, 2)},
            {"Scope": "Scope 2 — Electricity",   "kg CO2e": round(ctx["sc"]["scope2_kg"], 0), "tCO2e": round(ctx["sc"]["scope2_kg"]/1000, 2)},
            {"Scope": "Scope 3 — Value Chain",   "kg CO2e": round(ctx["sc"]["scope3_kg"], 0), "tCO2e": round(ctx["sc"]["scope3_kg"]/1000, 2)},
            {"Scope": "TOTAL",                   "kg CO2e": round(ctx["sc"]["scope1_kg"]+ctx["sc"]["scope2_kg"]+ctx["sc"]["scope3_kg"], 0),
             "tCO2e": round((ctx["sc"]["scope1_kg"]+ctx["sc"]["scope2_kg"]+ctx["sc"]["scope3_kg"])/1000, 2)},
        ])
        sc_data.to_excel(writer, sheet_name="Scope Breakdown", index=False)

        # Sheet 4 — S&G Indicators
        sg = pd.DataFrame([{
            "Indicator": k, "Value": v, "Unit": u
        } for k, v, u in [
            ("Total Employees",              S.get("employees", 0),                          "persons"),
            ("Women in Workforce",           S.get("women_workforce_pct", 0),                "%"),
            ("Employee Turnover Rate",       S.get("employee_turnover_pct", 0),              "%"),
            ("Training Hours per Employee",  S.get("training_hours_per_employee", 0),        "hours/year"),
            ("Injury Rate",                  S.get("injury_rate", 0),                        "per 200k hrs"),
            ("Board Size",                   S.get("board_size", 0),                         "persons"),
            ("Board Independence",           S.get("board_independence_pct", 0),             "%"),
            ("Women on Board",               S.get("women_board_pct", 0),                    "%"),
            ("Anti-Corruption Training",     S.get("anti_corruption_training_pct", 0),       "%"),
            ("Has Whistleblower Policy",     "Yes" if S.get("has_whistleblower_policy") else "No", "—"),
            ("Has Code of Conduct",          "Yes" if S.get("has_code_of_conduct") else "No",      "—"),
            ("Recycling Rate",               S.get("recycle_pct", 0),                        "%"),
        ]])
        sg.to_excel(writer, sheet_name="S&G Indicators", index=False)

        # Sheet 5 — Historical (if exists)
        hist = S.get_historical_data()
        if hist:
            hist_rows = []
            for yr, vals in sorted(hist.items()):
                hist_rows.append({"Year": yr, **vals})
            pd.DataFrame(hist_rows).to_excel(writer, sheet_name="Historical Trend", index=False)

    return buf.getvalue()


def _build_pdf_full(df, ctx) -> bytes:
    """Full GRI-referenced ESG report PDF."""
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as _c
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    import random, string as _s

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    BLUE   = _c.HexColor("#0EA5E9")
    GREEN  = _c.HexColor("#10B981")
    INDIGO = _c.HexColor("#6366F1")
    PINK   = _c.HexColor("#EC4899")
    GRAY   = _c.HexColor("#6B7280")
    LGRAY  = _c.HexColor("#F3F4F6")
    DARK   = _c.HexColor("#111827")
    WHITE  = _c.white

    def PS(base="Normal", **kw):
        uid = "".join(random.choices(_s.ascii_lowercase, k=6))
        p   = styles.get(base, styles["Normal"])
        return ParagraphStyle(f"cl_{uid}", parent=p, **kw)

    pred   = predict_next_emission(df)
    annual = annual_projection(df)
    risk   = overshoot_risk(annual, ctx["bench"] * 1200)
    esg    = ctx["esg"]
    sc     = ctx["sc"]
    today  = datetime.date.today()

    story = []

    # ── Cover ──
    story += [
        Spacer(1, 1.5*cm),
        Paragraph("ESG SUSTAINABILITY REPORT", PS(fontName="Helvetica-Bold", fontSize=10,
                  textColor=BLUE, spaceAfter=6, alignment=TA_CENTER)),
        Paragraph(ctx["company"], PS(fontName="Helvetica-Bold", fontSize=26,
                  textColor=DARK, spaceAfter=4, alignment=TA_CENTER)),
        Paragraph(ctx["sector"], PS(fontName="Helvetica", fontSize=13,
                  textColor=GRAY, spaceAfter=4, alignment=TA_CENTER)),
        Paragraph(f"Reporting Year {today.year}  ·  Generated {today.strftime('%B %d, %Y')}",
                  PS(fontName="Helvetica", fontSize=10, textColor=GRAY,
                     spaceAfter=2, alignment=TA_CENTER)),
        Paragraph("Prepared with CarbonLens V7  ·  GRI-Referenced Disclosure",
                  PS(fontName="Helvetica", fontSize=9, textColor=GRAY,
                     spaceAfter=20, alignment=TA_CENTER)),
        HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=20),
    ]

    # ── ESG Score Summary Table ──
    grade_color = GREEN if esg["score"] >= 70 else _c.HexColor("#F97316") if esg["score"] >= 50 else _c.HexColor("#EF4444")
    kpi_data = [
        ["ESG Score", "Grade", "Environmental", "Social", "Governance"],
        [f"{esg['score']}/100", esg["grade"],
         f"{esg['env']:.1f}", f"{esg['social']:.1f}", f"{esg['gov']:.1f}"],
    ]
    kpi_t = Table(kpi_data, colWidths=["20%","20%","20%","20%","20%"])
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), _c.HexColor("#E0F2FE")),
        ("BACKGROUND",   (0,1), (-1,1), WHITE),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",     (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 9),
        ("FONTSIZE",     (0,1), (-1,1), 16),
        ("TEXTCOLOR",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",    (0,1), (0,1), grade_color),
        ("TEXTCOLOR",    (1,1), (1,1), grade_color),
        ("TEXTCOLOR",    (2,1), (2,1), GREEN),
        ("TEXTCOLOR",    (3,1), (3,1), PINK),
        ("TEXTCOLOR",    (4,1), (4,1), INDIGO),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("BOX",          (0,0), (-1,-1), 0.5, _c.HexColor("#E5E7EB")),
        ("INNERGRID",    (0,0), (-1,-1), 0.3, _c.HexColor("#F3F4F6")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story += [kpi_t, Spacer(1, 0.5*cm)]

    # ── Section helper ──
    def section(title: str, color=BLUE):
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(title, PS(fontName="Helvetica-Bold", fontSize=13,
                               textColor=color, spaceAfter=6, spaceBefore=8)))
        story.append(HRFlowable(width="100%", thickness=0.7, color=color, spaceAfter=8))

    def metric_row(label: str, value: str, unit: str = ""):
        return [Paragraph(label, PS(fontName="Helvetica", fontSize=9, textColor=GRAY)),
                Paragraph(f"<b>{value}</b>  {unit}", PS(fontName="Helvetica", fontSize=10, textColor=DARK))]

    def simple_table(data, col_w=None):
        t = Table(data, colWidths=col_w or ["50%", "50%"])
        t.setStyle(TableStyle([
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 9),
            ("BACKGROUND",   (0,0), (-1,0), LGRAY),
            ("TEXTCOLOR",    (0,0), (-1,0), DARK),
            ("ALIGN",        (1,0), (1,-1), "RIGHT"),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, _c.HexColor("#F9FAFB")]),
            ("BOX",          (0,0), (-1,-1), 0.3, _c.HexColor("#E5E7EB")),
            ("INNERGRID",    (0,0), (-1,-1), 0.2, _c.HexColor("#E5E7EB")),
        ]))
        return t

    # ── 1. Executive Summary ──
    section("1. Executive Summary")
    story.append(Paragraph(
        f"This ESG Sustainability Report summarises the environmental, social, and governance "
        f"performance of <b>{ctx['company']}</b> ({ctx['sector']} sector) for the reporting period "
        f"ending {today.year}. The organisation achieved an overall ESG score of <b>{esg['score']}/100</b> "
        f"(Grade <b>{esg['grade']}</b> — {esg['label']}), comprising Environmental {esg['env']:.1f}, "
        f"Social {esg['social']:.1f}, and Governance {esg['gov']:.1f}. "
        f"Total reported GHG emissions amount to "
        f"<b>{ctx['ov'].get('total', 0):,.0f} tCO₂e</b> across all scopes, "
        f"with an annual projection of <b>{annual:,.0f} tCO₂e</b>. "
        f"This report is GRI-referenced in accordance with GRI Standards 2021.",
        PS(fontName="Helvetica", fontSize=10, textColor=DARK, leading=16, spaceAfter=8)))

    # ── 2. Environmental ──
    section("2. Environmental Performance (GRI 300-Series)", GREEN)

    total_em = ctx["ov"].get("total", 0)
    scope1   = round(sc["scope1_kg"] / 1000, 2)
    scope2   = round(sc["scope2_kg"] / 1000, 2)
    scope3   = round(sc["scope3_kg"] / 1000, 2)
    total_sc = scope1 + scope2 + scope3

    em_data = [
        ["GHG Emission Category", "tCO₂e", "Share (%)"],
        ["Scope 1 — Direct Emissions",          f"{scope1:,.2f}", f"{scope1/total_sc*100:.1f}%" if total_sc else "—"],
        ["Scope 2 — Indirect (Electricity)",    f"{scope2:,.2f}", f"{scope2/total_sc*100:.1f}%" if total_sc else "—"],
        ["Scope 3 — Value Chain",               f"{scope3:,.2f}", f"{scope3/total_sc*100:.1f}%" if total_sc else "—"],
        ["TOTAL",                               f"{total_sc:,.2f}", "100%"],
    ]
    em_t = Table(em_data, colWidths=["55%", "25%", "20%"])
    em_t.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",     (0,4), (-1,4), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("BACKGROUND",   (0,0), (-1,0), _c.HexColor("#ECFDF5")),
        ("BACKGROUND",   (0,4), (-1,4), _c.HexColor("#ECFDF5")),
        ("TEXTCOLOR",    (0,4), (-1,4), _c.HexColor("#065F46")),
        ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,3), [WHITE, _c.HexColor("#F9FAFB")]),
        ("BOX",          (0,0), (-1,-1), 0.3, _c.HexColor("#6EE7B7")),
        ("INNERGRID",    (0,0), (-1,-1), 0.2, _c.HexColor("#E5E7EB")),
    ]))
    story += [em_t, Spacer(1, 0.3*cm)]

    env_metrics = [
        ["Metric", "Value"],
        ["Total Emissions (ESG Analytics data)",     f"{total_em:,.0f} tCO₂e"],
        ["Carbon Intensity (kg CO₂e/m²)",            f"{ctx['intensity']:.2f}"],
        ["Sector Benchmark (kg CO₂e/m²)",            f"{ctx['bench']}"],
        ["vs Benchmark",                             f"{ctx['gap']['gap_pct']:+.1f}%"],
        ["Energy Consumption",                       f"{df['Energy'].sum():,.0f} MWh" if 'Energy' in df.columns else "—"],
        ["Water Consumption",                        f"{df['Water'].sum():,.0f} m³"   if 'Water'  in df.columns else "—"],
        ["Waste Generated",                          f"{df['Waste'].sum():,.2f} t"    if 'Waste'  in df.columns else "—"],
        ["Recycling Rate",                           f"{S.get('recycle_pct', 0) or 0:.0f}%"],
    ]
    story += [simple_table(env_metrics, ["55%", "45%"]), Spacer(1, 0.3*cm)]

    # ── 3. Social ──
    section("3. Social Performance (GRI 400-Series)", PINK)
    soc_data = [
        ["Social Indicator", "Value"],
        ["Total Employees",                 str(S.get("employees", 0) or 0)],
        ["Women in Workforce",              f"{S.get('women_workforce_pct', 0) or 0:.1f}%"],
        ["Employee Turnover Rate",          f"{S.get('employee_turnover_pct', 0) or 0:.1f}%"],
        ["Training Hours / Employee / Year",f"{S.get('training_hours_per_employee', 0) or 0:.1f} hrs"],
        ["Injury Rate (per 200k hrs worked)", f"{S.get('injury_rate', 0) or 0:.2f}"],
        ["GRI Reference",                   "GRI 401, 403, 404, 405"],
    ]
    story += [simple_table(soc_data, ["60%", "40%"]), Spacer(1, 0.3*cm)]

    # ── 4. Governance ──
    section("4. Governance Performance (GRI 200-Series)", INDIGO)
    gov_data = [
        ["Governance Indicator", "Value"],
        ["Board Size",                       str(S.get("board_size", 0) or 0)],
        ["Board Independence",               f"{S.get('board_independence_pct', 0) or 0:.1f}%"],
        ["Women on Board",                   f"{S.get('women_board_pct', 0) or 0:.1f}%"],
        ["Anti-Corruption Training Coverage",f"{S.get('anti_corruption_training_pct', 0) or 0:.1f}%"],
        ["Whistleblower Policy",             "Yes" if S.get("has_whistleblower_policy") else "No"],
        ["Code of Conduct",                  "Yes" if S.get("has_code_of_conduct") else "No"],
        ["GRI Reference",                    "GRI 2-9, 2-22, 205"],
    ]
    story += [simple_table(gov_data, ["60%", "40%"]), Spacer(1, 0.3*cm)]

    # ── 5. Forecast & Risk ──
    section("5. Emission Forecast & Risk Assessment")
    fcast_data = [
        ["Forecast Metric", "Value"],
        ["Next Period Forecast",        f"{pred.get('forecast', 0) or 0:,.0f} tCO₂e"],
        ["Annual Projection",           f"{annual:,.0f} tCO₂e"],
        ["Trend Direction",             pred.get("trend_dir", "stable").title()],
        ["Overshoot Risk Level",        risk["level"]],
        ["Model Confidence",            f"{pred.get('confidence', 0) or 0:.0f}%"],
    ]
    story += [simple_table(fcast_data, ["60%", "40%"]), Spacer(1, 0.3*cm)]

    # ── 6. GRI Index ──
    story.append(PageBreak())
    section("6. GRI Content Index (GRI-Referenced)")
    story.append(Paragraph(
        "This report has been prepared with reference to the GRI Standards 2021. "
        "The following disclosures are addressed:",
        PS(fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=8)))

    gri_index = [["GRI Disclosure", "Topic", "Coverage", "Data Source"]]
    from utils.frameworks import run_gap_analysis
    gri_results = run_gap_analysis(S, df)
    for r in gri_results:
        gri_index.append([
            r["code"],
            r["title"][:45] + ("…" if len(r["title"]) > 45 else ""),
            "✓" if r["covered"] else "○",
            r["module"][:38] + ("…" if len(r["module"]) > 38 else ""),
        ])
    gri_t = Table(gri_index, colWidths=["18%", "34%", "8%", "40%"])
    gri_t.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 7.5),
        ("BACKGROUND",   (0,0), (-1,0), LGRAY),
        ("TEXTCOLOR",    (2,1), (2,-1), GREEN),
        ("ALIGN",        (2,0), (2,-1), "CENTER"),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, _c.HexColor("#F9FAFB")]),
        ("BOX",          (0,0), (-1,-1), 0.3, _c.HexColor("#E5E7EB")),
        ("INNERGRID",    (0,0), (-1,-1), 0.2, _c.HexColor("#E5E7EB")),
    ]))
    story += [gri_t, Spacer(1, 0.3*cm)]

    # ── Footer ──
    story += [
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=0.5, color=LGRAY, spaceAfter=6),
        Paragraph(
            f"CarbonLens V7  ·  Generated {today.isoformat()}  ·  "
            f"GRI-Referenced Disclosure  ·  GHG Protocol aligned  ·  "
            f"Kepmen ESDM 18/2023 emission factors",
            PS(fontName="Helvetica", fontSize=7, textColor=GRAY, alignment=TA_CENTER)),
    ]

    doc.build(story)
    return buf.getvalue()


# ── Page render ───────────────────────────────────────────────────────────────

def render():
    S.init()
    page_header(
        title="Data Export Center",
        subtitle="CSV · Excel Multi-Sheet · JSON · PDF Full ESG Report (GRI-Referenced)",
        badge="Export Ready", badge_type="green",
    )

    has_data = S.get("uploaded_df") is not None
    df       = S.get("uploaded_df") if has_data else generate_demo_data()
    ctx      = _ctx(df)

    if not has_data:
        st.info("📌 Menampilkan demo data. Upload dataset di ESG Analytics untuk export data nyata.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Row 1: CSV + JSON ─────────────────────────────────────────────────────
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown("""<div class="cl-card">
            <div style="font-size:32px;margin-bottom:10px;">📊</div>
            <div class="cl-card-title">ESG Dataset (CSV)</div>
            <div class="cl-card-subtitle">Raw data + computed columns — benchmark gap, cumulative, scope ratios, ESG scores E/S/G</div>
        """, unsafe_allow_html=True)
        kpi_card("Records", str(len(df)), icon="📋", icon_bg="#E0F2FE")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️  Download Enriched CSV", data=_build_enriched_csv(df, ctx),
            file_name=f"CarbonLens_{ctx['company'].replace(' ','_')}_ESG_Data.csv",
            mime="text/csv", use_container_width=True, type="primary",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""<div class="cl-card">
            <div style="font-size:32px;margin-bottom:10px;">🔗</div>
            <div class="cl-card-title">ESG Intelligence Summary (JSON)</div>
            <div class="cl-card-subtitle">Structured analysis — ESG E/S/G scores, Scope 1/2/3, S&G indicators, forecast, benchmark · API-ready</div>
        """, unsafe_allow_html=True)
        kpi_card("Fields", "35+", icon="⚙️", icon_bg="#DBEAFE")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️  Download JSON Summary", data=_build_summary_json(df, ctx),
            file_name=f"CarbonLens_{ctx['company'].replace(' ','_')}_Summary.json",
            mime="application/json", use_container_width=True, type="primary",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 2: Monthly + Excel ────────────────────────────────────────────────
    col3, col4 = st.columns(2, gap="medium")

    with col3:
        st.markdown("""<div class="cl-card">
            <div style="font-size:32px;margin-bottom:10px;">📅</div>
            <div class="cl-card-title">Monthly Emission Report (CSV)</div>
            <div class="cl-card-subtitle">Month-by-month Scope 1/2/3 breakdown, benchmark comparison per period, energy/water/waste</div>
        """, unsafe_allow_html=True)
        kpi_card("Months", str(len(df)), icon="📆", icon_bg="#FFF7ED")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        monthly = _build_monthly_report(df, ctx)
        st.download_button(
            "⬇️  Download Monthly Report", data=monthly.to_csv(index=False),
            file_name=f"CarbonLens_{ctx['company'].replace(' ','_')}_Monthly.csv",
            mime="text/csv", use_container_width=True, type="primary",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown("""<div class="cl-card">
            <div style="font-size:32px;margin-bottom:10px;">📗</div>
            <div class="cl-card-title">Excel Multi-Sheet Workbook</div>
            <div class="cl-card-subtitle">5 sheet: ESG Overview · Monthly Data · Scope Breakdown · S&G Indicators · Historical Trend</div>
        """, unsafe_allow_html=True)
        hist_count = len(S.get_historical_data())
        kpi_card("Sheets", f"{'5' if hist_count else '4'}", icon="📋", icon_bg="#ECFDF5",
                 badge=f"+ Historical ({hist_count} yrs)" if hist_count else "No historical yet",
                 badge_type="green" if hist_count else "slate")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        try:
            excel_bytes = _build_excel(df, ctx)
            st.download_button(
                "⬇️  Download Excel Workbook", data=excel_bytes,
                file_name=f"CarbonLens_{ctx['company'].replace(' ','_')}_Workbook.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, type="primary",
            )
        except ImportError:
            st.error("openpyxl not installed. Run: pip install openpyxl")
        except Exception as ex:
            st.error(f"Excel error: {ex}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── PDF Full Report ───────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
         padding:20px;border-top:3px solid #E11D48;">
        <div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:16px;">
            <div style="font-size:32px;">📄</div>
            <div>
                <div style="font-size:14px;font-weight:700;color:#1F2937;">PDF Full ESG Report — GRI-Referenced</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:3px;">
                    Cover · Executive Summary · Environmental (GRI 300) · Social (GRI 400) ·
                    Governance (GRI 200) · Forecast & Risk · GRI Content Index
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c_a, c_b, c_c = st.columns(3, gap="medium")
    with c_a: kpi_card("Sections", "6", icon="📑", icon_bg="#FFF1F2")
    with c_b: kpi_card("GRI Index", f"{len(run_gap_analysis_safe(df))} disclosures", icon="📋", icon_bg="#FFF1F2")
    with c_c: kpi_card("Format", "A4 PDF", icon="🖨️", icon_bg="#FFF1F2")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    col_pdf, _ = st.columns([1, 2])
    with col_pdf:
        if st.button("⬇️  Generate Full PDF Report", type="primary",
                     use_container_width=True, key="de_pdf_full"):
            with st.spinner("Building PDF report..."):
                try:
                    pdf_bytes = _build_pdf_full(df, ctx)
                    st.download_button(
                        "📄  Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"CarbonLens_{ctx['company'].replace(' ','_')}_ESG_Report_{datetime.date.today().year}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success("✅ PDF siap — klik tombol di atas untuk download.")
                except ImportError:
                    st.error("reportlab not installed. Run: pip install reportlab")
                except Exception as ex:
                    st.error(f"PDF error: {ex}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── JSON Preview ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.expander("👁️ Preview JSON Summary", expanded=False):
        st.code(_build_summary_json(df, ctx), language="json")


def run_gap_analysis_safe(df):
    try:
        from utils.frameworks import run_gap_analysis
        return run_gap_analysis(S, df)
    except Exception:
        return []
