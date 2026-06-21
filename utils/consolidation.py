"""
CarbonLens V7 — Multi-Entity Consolidation
GHG Protocol consolidation approaches: equity share or financial/operational control.
For holding companies and consultants managing multiple client entities.
"""

from __future__ import annotations
import pandas as pd

CONSOLIDATION_METHODS = {
    "equity_share": {
        "label": "Equity Share",
        "desc": "Each entity's emissions are scaled by the parent's % ownership stake.",
    },
    "financial_control": {
        "label": "Financial Control",
        "desc": "100% of emissions from entities the parent financially controls "
                "(majority ownership / consolidates financials); 0% from others.",
    },
    "operational_control": {
        "label": "Operational Control",
        "desc": "100% of emissions from entities the parent has full authority to "
                "introduce/implement operating policies, regardless of ownership %.",
    },
}


def consolidate(entities: list[dict], method: str = "equity_share") -> dict:
    """
    entities: list of dicts with keys:
        name, ownership_pct (0-100), control (bool),
        scope1_kg, scope2_kg, scope3_kg, total_kg

    Returns consolidated totals + per-entity contribution breakdown.
    """
    rows = []
    cons_s1 = cons_s2 = cons_s3 = 0.0

    for e in entities:
        name   = e.get("name", "Unnamed Entity")
        own    = float(e.get("ownership_pct", 100)) / 100
        ctrl   = bool(e.get("control", True))
        s1, s2, s3 = float(e.get("scope1_kg",0)), float(e.get("scope2_kg",0)), float(e.get("scope3_kg",0))

        if method == "equity_share":
            factor = own
        elif method in ("financial_control", "operational_control"):
            factor = 1.0 if ctrl else 0.0
        else:
            factor = 1.0

        c_s1, c_s2, c_s3 = s1*factor, s2*factor, s3*factor
        cons_s1 += c_s1; cons_s2 += c_s2; cons_s3 += c_s3

        rows.append({
            "Entity": name,
            "Ownership %": round(own*100, 1),
            "Controlled": "Yes" if ctrl else "No",
            "Reported Scope 1 (kg)":     round(s1, 1),
            "Reported Scope 2 (kg)":     round(s2, 1),
            "Reported Scope 3 (kg)":     round(s3, 1),
            "Reported Total (kg)":       round(s1+s2+s3, 1),
            "Consolidation Factor":      round(factor, 2),
            "Consolidated Scope 1 (kg)": round(c_s1, 1),
            "Consolidated Scope 2 (kg)": round(c_s2, 1),
            "Consolidated Scope 3 (kg)": round(c_s3, 1),
            "Consolidated Total (kg)":   round(c_s1+c_s2+c_s3, 1),
        })

    return {
        "method":        method,
        "method_label":  CONSOLIDATION_METHODS.get(method,{}).get("label", method),
        "rows":          rows,
        "total_s1_kg":   cons_s1,
        "total_s2_kg":   cons_s2,
        "total_s3_kg":   cons_s3,
        "total_kg":      cons_s1 + cons_s2 + cons_s3,
        "n_entities":    len(entities),
    }


def entities_from_csv(df: pd.DataFrame) -> list[dict]:
    """
    Parse an uploaded entity CSV with columns:
    Entity, Ownership %, Controlled (Yes/No), Scope1_kg, Scope2_kg, Scope3_kg
    """
    entities = []
    for _, row in df.iterrows():
        entities.append({
            "name":          str(row.get("Entity", "Unnamed Entity")),
            "ownership_pct": float(row.get("Ownership %", 100) or 100),
            "control":       str(row.get("Controlled", "Yes")).strip().lower() in ("yes","true","1"),
            "scope1_kg":     float(row.get("Scope1_kg", 0) or 0),
            "scope2_kg":     float(row.get("Scope2_kg", 0) or 0),
            "scope3_kg":     float(row.get("Scope3_kg", 0) or 0),
        })
    return entities
