"""
CarbonLens V7 — Reporting Framework Definitions
GRI 200 (Governance), 300 (Environmental), 400 (Social) disclosures
mapped to platform data sources. Globally applicable, distinct from
pojk_compliance.py (Indonesia OJK-specific).
"""

from __future__ import annotations

GRI_DISCLOSURES = [
    # ── GRI 200 — Economic / Governance ──────────────────────────────────────
    {
        "code": "GRI 2-9",  "topic": "Governance",
        "title": "Governance structure and composition",
        "desc": "Size, composition, independence, and diversity of governing body.",
        "check": lambda S, df: (S.get("board_independence_pct") or 0) > 0,
        "module": "ESG Analytics — Board independence %",
        "series": "GRI 200",
    },
    {
        "code": "GRI 2-10", "topic": "Governance",
        "title": "Nomination and selection of highest governance body",
        "desc": "Process for nominating and selecting board/committee members.",
        "check": lambda S, df: (S.get("board_independence_pct") or 0) > 0,
        "module": "ESG Analytics — Board data",
        "series": "GRI 200",
    },
    {
        "code": "GRI 2-22", "topic": "Governance",
        "title": "Statement on sustainable development strategy",
        "desc": "Statement from highest governance body on sustainable development.",
        "check": lambda S, df: bool(S.get("has_code_of_conduct")),
        "module": "ESG Analytics — Code of Conduct",
        "series": "GRI 200",
    },
    {
        "code": "GRI 205-2", "topic": "Governance",
        "title": "Communication & training on anti-corruption",
        "desc": "% governance body + employees trained on anti-corruption policies.",
        "check": lambda S, df: (S.get("anti_corruption_training_pct") or 0) > 0,
        "module": "ESG Analytics — Anti-corruption training %",
        "series": "GRI 200",
    },
    {
        "code": "GRI 205-3", "topic": "Governance",
        "title": "Confirmed incidents of corruption",
        "desc": "Number of confirmed incidents of corruption and actions taken.",
        "check": lambda S, df: bool(S.get("has_whistleblower_policy")),
        "module": "ESG Analytics — Whistleblower policy",
        "series": "GRI 200",
    },
    # ── GRI 300 — Environmental ───────────────────────────────────────────────
    {
        "code": "GRI 301-1", "topic": "Materials",
        "title": "Materials used by weight or volume",
        "desc": "Total materials used in production/operations.",
        "check": lambda S, df: bool(S.get("materials_table")) and
                 any(str(r.get("Material","")).strip() for r in (S.get("materials_table") or [])),
        "module": "Carbon Accounting — Materials Used",
        "series": "GRI 300",
    },
    {
        "code": "GRI 301-2", "topic": "Materials",
        "title": "Recycled input materials used",
        "desc": "Percentage of recycled materials in total material inputs.",
        "check": lambda S, df: (S.get("recycle_pct", 0) or 0) > 0,
        "module": "Profile — Recycling Rate / Carbon Accounting",
        "series": "GRI 300",
    },
    {
        "code": "GRI 302-1", "topic": "Energy",
        "title": "Energy consumption within the organization",
        "desc": "Total fuel + electricity consumption (direct + indirect).",
        "check": lambda S, df: df is not None and "Energy" in df.columns and df["Energy"].sum() > 0,
        "module": "ESG Analytics — Energy column",
        "series": "GRI 300",
    },
    {
        "code": "GRI 302-3", "topic": "Energy",
        "title": "Energy intensity",
        "desc": "Energy consumption per unit activity (per m², per employee).",
        "check": lambda S, df: df is not None and "Energy" in df.columns and (S.get("area_m2", 0) or 0) > 0,
        "module": "Carbon Accounting — intensity normalization",
        "series": "GRI 300",
    },
    {
        "code": "GRI 302-4", "topic": "Energy",
        "title": "Reduction of energy consumption",
        "desc": "Year-on-year reduction in energy consumption.",
        "check": lambda S, df: len(S.get_historical_data()) >= 2,
        "module": "Historical Tracker — 2+ years required",
        "series": "GRI 300",
    },
    {
        "code": "GRI 303-3", "topic": "Water",
        "title": "Water withdrawal",
        "desc": "Total water withdrawal by source.",
        "check": lambda S, df: df is not None and "Water" in df.columns and df["Water"].sum() > 0,
        "module": "ESG Analytics — Water column",
        "series": "GRI 300",
    },
    {
        "code": "GRI 303-5", "topic": "Water",
        "title": "Water consumption",
        "desc": "Total water consumption (including water-stressed areas).",
        "check": lambda S, df: df is not None and "Water" in df.columns and df["Water"].sum() > 0,
        "module": "ESG Analytics — Water column",
        "series": "GRI 300",
    },
    {
        "code": "GRI 305-1", "topic": "Emissions",
        "title": "Direct (Scope 1) GHG emissions",
        "desc": "Gross direct GHG emissions in metric tons CO2-equivalent.",
        "check": lambda S, df: (S.get("ca_scope1_kg", 0) or 0) > 0,
        "module": "Carbon Accounting — Scope 1",
        "series": "GRI 300",
    },
    {
        "code": "GRI 305-2", "topic": "Emissions",
        "title": "Energy indirect (Scope 2) GHG emissions",
        "desc": "Gross location/market-based Scope 2 emissions.",
        "check": lambda S, df: (S.get("ca_scope2_kg", 0) or 0) > 0,
        "module": "Carbon Accounting — Scope 2",
        "series": "GRI 300",
    },
    {
        "code": "GRI 305-3", "topic": "Emissions",
        "title": "Other indirect (Scope 3) GHG emissions",
        "desc": "Gross Scope 3 emissions by category.",
        "check": lambda S, df: (S.get("ca_scope3_kg", 0) or 0) > 0,
        "module": "Carbon Accounting — Scope 3 (12 categories)",
        "series": "GRI 300",
    },
    {
        "code": "GRI 305-4", "topic": "Emissions",
        "title": "GHG emissions intensity",
        "desc": "GHG emissions intensity ratio (per unit activity).",
        "check": lambda S, df: (S.get("ca_intens_m2", 0) or 0) > 0 or (S.get("ca_intens_emp", 0) or 0) > 0,
        "module": "Carbon Accounting — intensity normalization",
        "series": "GRI 300",
    },
    {
        "code": "GRI 305-5", "topic": "Emissions",
        "title": "Reduction of GHG emissions",
        "desc": "GHG emissions reduced as a result of reduction initiatives.",
        "check": lambda S, df: len(S.get_historical_data()) >= 2,
        "module": "Historical Tracker — 2+ years required",
        "series": "GRI 300",
    },
    {
        "code": "GRI 306-3", "topic": "Waste",
        "title": "Waste generated",
        "desc": "Total weight of waste generated, by composition.",
        "check": lambda S, df: df is not None and "Waste" in df.columns and df["Waste"].sum() > 0,
        "module": "ESG Analytics — Waste column",
        "series": "GRI 300",
    },
    {
        "code": "GRI 306-4", "topic": "Waste",
        "title": "Waste diverted from disposal",
        "desc": "Total weight of waste diverted (recycling, reuse, composting).",
        "check": lambda S, df: (S.get("recycle_pct", 0) or 0) > 0,
        "module": "Profile — Recycling Rate",
        "series": "GRI 300",
    },
    {
        "code": "GRI 308-1", "topic": "Supplier Environmental Assessment",
        "title": "New suppliers screened using environmental criteria",
        "desc": "% new suppliers screened against environmental criteria.",
        "check": lambda S, df: bool(S.get("supplier_table")),
        "module": "Supplier ESG Scorecard",
        "series": "GRI 300",
    },
    # ── GRI 400 — Social ─────────────────────────────────────────────────────
    {
        "code": "GRI 401-1", "topic": "Employment",
        "title": "New employee hires and employee turnover",
        "desc": "Total new hires and turnover rate by age, gender, region.",
        "check": lambda S, df: (S.get("employee_turnover_pct") or 0) > 0,
        "module": "ESG Analytics — Employee Turnover %",
        "series": "GRI 400",
    },
    {
        "code": "GRI 401-2", "topic": "Employment",
        "title": "Benefits provided to full-time employees",
        "desc": "Benefits (health, parental leave, retirement) provided to full-time vs part-time.",
        "check": lambda S, df: (S.get("employees", 0) or 0) > 0,
        "module": "Profile — Employee count (proxy)",
        "series": "GRI 400",
    },
    {
        "code": "GRI 403-9", "topic": "Occupational Health & Safety",
        "title": "Work-related injuries",
        "desc": "Injury rate, occupational diseases, lost days, fatalities.",
        "check": lambda S, df: (S.get("injury_rate") or 0) >= 0 and S.get("injury_rate") is not None,
        "module": "ESG Analytics — Injury Rate",
        "series": "GRI 400",
    },
    {
        "code": "GRI 404-1", "topic": "Training & Education",
        "title": "Average hours of training per year per employee",
        "desc": "Average training hours per employee by gender and category.",
        "check": lambda S, df: (S.get("training_hours_per_employee") or 0) > 0,
        "module": "ESG Analytics — Training Hours",
        "series": "GRI 400",
    },
    {
        "code": "GRI 404-2", "topic": "Training & Education",
        "title": "Programs for upgrading employee skills",
        "desc": "Type and scope of programs for skill enhancement and transition assistance.",
        "check": lambda S, df: (S.get("training_hours_per_employee") or 0) > 0,
        "module": "ESG Analytics — Training Hours (proxy)",
        "series": "GRI 400",
    },
    {
        "code": "GRI 405-1", "topic": "Diversity & Equal Opportunity",
        "title": "Diversity of governance bodies and employees",
        "desc": "% employees and governance body by gender, age group, minority.",
        "check": lambda S, df: (S.get("women_workforce_pct") or 0) > 0 or (S.get("women_board_pct") or 0) > 0,
        "module": "ESG Analytics — Women Workforce % / Board %",
        "series": "GRI 400",
    },
    {
        "code": "GRI 405-2", "topic": "Diversity & Equal Opportunity",
        "title": "Ratio of basic salary of women to men",
        "desc": "Ratio of basic salary and remuneration of women to men.",
        "check": lambda S, df: (S.get("women_workforce_pct") or 0) > 0,
        "module": "ESG Analytics — Gender data (proxy)",
        "series": "GRI 400",
    },
    {
        "code": "GRI 406-1", "topic": "Non-Discrimination",
        "title": "Incidents of discrimination and corrective actions",
        "desc": "Number of incidents of discrimination and corrective actions taken.",
        "check": lambda S, df: bool(S.get("has_code_of_conduct")),
        "module": "ESG Analytics — Code of Conduct (proxy)",
        "series": "GRI 400",
    },
    {
        "code": "GRI 414-1", "topic": "Supplier Social Assessment",
        "title": "New suppliers screened using social criteria",
        "desc": "% new suppliers screened using social criteria.",
        "check": lambda S, df: bool(S.get("supplier_table")),
        "module": "Supplier ESG Scorecard",
        "series": "GRI 400",
    },
]

GRI_TOPIC_COLORS = {
    # 200
    "Governance":                   "#6366F1",
    # 300
    "Materials":                    "#8B5CF6",
    "Energy":                       "#0EA5E9",
    "Water":                        "#06B6D4",
    "Emissions":                    "#F97316",
    "Waste":                        "#10B981",
    "Supplier Environmental Assessment": "#64748B",
    # 400
    "Employment":                   "#EC4899",
    "Occupational Health & Safety": "#EF4444",
    "Training & Education":         "#F59E0B",
    "Diversity & Equal Opportunity":"#8B5CF6",
    "Non-Discrimination":           "#3B82F6",
    "Supplier Social Assessment":   "#64748B",
}

GRI_SERIES_COLORS = {
    "GRI 200": "#6366F1",
    "GRI 300": "#10B981",
    "GRI 400": "#EC4899",
}


def run_gap_analysis(S, df) -> list[dict]:
    """Evaluate every GRI disclosure against current platform state."""
    results = []
    for d in GRI_DISCLOSURES:
        try:
            covered = bool(d["check"](S, df))
        except Exception:
            covered = False
        results.append({
            "code":    d["code"],
            "topic":   d["topic"],
            "title":   d["title"],
            "desc":    d["desc"],
            "covered": covered,
            "module":  d["module"],
            "series":  d.get("series", "GRI 300"),
        })
    return results
