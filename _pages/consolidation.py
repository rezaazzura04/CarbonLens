"""
CarbonLens V7 — Multi-Entity Consolidation
Upload subsidiary/BU emission data, consolidate at group level using
GHG Protocol equity share or control approaches. For holding companies
and consultants managing multiple client entities.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils.state as S
from utils.consolidation import consolidate, entities_from_csv, CONSOLIDATION_METHODS
from components.ui import page_header, kpi_card, insight_panel, empty_state, divider
from config.settings import PLOTLY_THEME as T


def _sample_entities() -> pd.DataFrame:
    return pd.DataFrame([
        {"Entity": "Parent Co — HQ",        "Ownership %": 100, "Controlled": "Yes", "Scope1_kg": 120000, "Scope2_kg": 340000, "Scope3_kg": 980000},
        {"Entity": "Subsidiary A (Mfg)",    "Ownership %": 80,  "Controlled": "Yes", "Scope1_kg": 85000,  "Scope2_kg": 210000, "Scope3_kg": 540000},
        {"Entity": "Subsidiary B (Logistics)","Ownership %": 51, "Controlled": "Yes", "Scope1_kg": 210000, "Scope2_kg": 40000,  "Scope3_kg": 320000},
        {"Entity": "Joint Venture C",       "Ownership %": 35,  "Controlled": "No",  "Scope1_kg": 65000,  "Scope2_kg": 95000,  "Scope3_kg": 180000},
    ])


def render():
    page_header(
        title="Multi-Entity Consolidation",
        subtitle="GHG Protocol equity share / control approaches · For holding companies & multi-client consultants",
        badge="Group Reporting", badge_type="purple",
    )

    st.markdown("""
    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
         padding:12px 16px;font-size:12px;color:#1E40AF;margin-bottom:16px;">
        <strong>GHG Protocol Corporate Standard</strong> requires organizations to choose one of three
        consolidation approaches before aggregating emissions across subsidiaries, joint ventures, or
        business units: <strong>Equity Share</strong> (scale by ownership %), <strong>Financial Control</strong>,
        or <strong>Operational Control</strong>. The chosen approach must be applied consistently and disclosed.
    </div>
    """, unsafe_allow_html=True)

    # ── Entity data input ──────────────────────────────────────────────────────
    if "consolidation_entities" not in st.session_state:
        existing = S.get("consolidation_entities")
        st.session_state["consolidation_entities"] = (
            pd.DataFrame(existing) if existing else _sample_entities()
        )

    st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
        padding:20px;border-top:3px solid #8B5CF6;margin-bottom:14px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
             color:#94A3B8;margin-bottom:14px;">Entity / Subsidiary Data</div>
    """, unsafe_allow_html=True)

    tab_edit, tab_upload = st.tabs(["✏️ Edit Table", "📂 Upload CSV"])

    with tab_upload:
        st.caption("CSV columns: Entity, Ownership %, Controlled (Yes/No), Scope1_kg, Scope2_kg, Scope3_kg")
        up = st.file_uploader("Upload entity CSV", type=["csv"], key="cons_upload", label_visibility="collapsed")
        if up is not None:
            try:
                up_df = pd.read_csv(up)
                required = {"Entity","Ownership %","Controlled","Scope1_kg","Scope2_kg","Scope3_kg"}
                if not required.issubset(set(up_df.columns)):
                    st.error(f"CSV missing required columns: {required - set(up_df.columns)}")
                else:
                    st.session_state["consolidation_entities"] = up_df
                    st.success(f"✅ Loaded {len(up_df)} entities from CSV.")
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")

    with tab_edit:
        edited = st.data_editor(
            st.session_state["consolidation_entities"],
            num_rows="dynamic", use_container_width=True,
            column_config={
                "Entity": st.column_config.TextColumn("Entity Name", width="medium"),
                "Ownership %": st.column_config.NumberColumn("Ownership %", min_value=0.0, max_value=100.0, format="%.1f%%"),
                "Controlled": st.column_config.SelectboxColumn("Controlled?", options=["Yes","No"]),
                "Scope1_kg": st.column_config.NumberColumn("Scope 1 (kg)", format="%.0f"),
                "Scope2_kg": st.column_config.NumberColumn("Scope 2 (kg)", format="%.0f"),
                "Scope3_kg": st.column_config.NumberColumn("Scope 3 (kg)", format="%.0f"),
            },
            key="cons_editor",
        )
        st.session_state["consolidation_entities"] = edited
        S.set("consolidation_entities", edited.to_dict("records"))

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    entities_df = st.session_state["consolidation_entities"]
    entities_df = entities_df[entities_df["Entity"].astype(str).str.strip() != ""]
    if entities_df.empty:
        empty_state("🏢", "No entities added", "Add at least one entity above to run consolidation.")
        return

    entities = entities_from_csv(entities_df)

    # ── Method selector ─────────────────────────────────────────────────────────
    col_method, col_info = st.columns([1, 2], gap="medium")
    with col_method:
        method = st.selectbox(
            "Consolidation approach",
            options=list(CONSOLIDATION_METHODS.keys()),
            format_func=lambda k: CONSOLIDATION_METHODS[k]["label"],
            key="cons_method",
        )
    with col_info:
        st.markdown(
            f'<div style="font-size:12px;color:#64748B;padding-top:24px;">'
            f'{CONSOLIDATION_METHODS[method]["desc"]}</div>',
            unsafe_allow_html=True
        )

    result = consolidate(entities, method=method)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1: kpi_card("Entities",            str(result["n_entities"]),                icon="🏢", icon_bg="#F5F3FF")
    with k2: kpi_card("Consolidated Total",  f"{result['total_kg']/1000:,.1f} tCO₂e",  icon="🌍", icon_bg="#E0F2FE")
    with k3: kpi_card("Method",              result["method_label"],                    icon="📐", icon_bg="#F1F5F9", badge="GHG Protocol", badge_type="slate")
    with k4:
        sum_reported = sum(r["Reported Total (kg)"] for r in result["rows"])
        diff_pct = (result["total_kg"] - sum_reported) / sum_reported * 100 if sum_reported > 0 else 0
        kpi_card("vs Sum of Reported", f"{diff_pct:+.1f}%", icon="Δ", icon_bg="#FFF7ED",
                  badge="Adjusted by ownership/control", badge_type="orange")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Entity breakdown vs consolidated ──────────────────────────────────────
    col_chart, col_donut = st.columns([1.5, 1], gap="medium")

    with col_chart:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #8B5CF6;height:100%;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Entity Breakdown — Reported vs Consolidated</div>
        """, unsafe_allow_html=True)

        names    = [r["Entity"] for r in result["rows"]]
        reported = [r["Reported Total (kg)"]/1000 for r in result["rows"]]
        consol   = [r["Consolidated Total (kg)"]/1000 for r in result["rows"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Reported (100%)", x=names, y=reported,
                              marker=dict(color="#CBD5E1", cornerradius=4)))
        fig.add_trace(go.Bar(name=f"Consolidated ({result['method_label']})", x=names, y=consol,
                              marker=dict(color="#8B5CF6", cornerradius=4)))
        fig.update_layout(
            height=300, barmode="group", margin=dict(l=10,r=10,t=10,b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=T["font_family"], color=T["font_color"]),
            yaxis=dict(title="tCO₂e", showgrid=True, gridcolor="#E2E8F0"),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.25, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_donut:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #8B5CF6;height:100%;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Consolidated Scope Mix</div>
        """, unsafe_allow_html=True)

        fig2 = go.Figure(go.Pie(
            labels=["Scope 1","Scope 2","Scope 3"],
            values=[result["total_s1_kg"], result["total_s2_kg"], result["total_s3_kg"]],
            hole=0.55,
            marker=dict(colors=["#F43F5E","#F59E0B","#0EA5E9"]),
            textinfo="label+percent",
        ))
        fig2.update_layout(
            height=300, margin=dict(l=10,r=10,t=10,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family=T["font_family"], color=T["font_color"]),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Full table ────────────────────────────────────────────────────────────
    st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
        padding:20px;border-top:3px solid #8B5CF6;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
             color:#94A3B8;margin-bottom:14px;">Full Consolidation Table</div>
    """, unsafe_allow_html=True)

    cons_table = pd.DataFrame(result["rows"])
    st.dataframe(cons_table, use_container_width=True, hide_index=True, height=min(380, 48+36*len(cons_table)))

    st.download_button(
        "⬇️  Export Consolidation CSV",
        data=cons_table.to_csv(index=False).encode(),
        file_name=f"carbonlens_consolidation_{method}.csv", mime="text/csv",
        use_container_width=False,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Insights ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    insights = []
    excluded = [r for r in result["rows"] if r["Consolidation Factor"] == 0]
    if excluded:
        insights.append({"icon":"ℹ️","type":"info",
            "text": f"<strong>{len(excluded)} entit(y/ies)</strong> excluded entirely under "
                    f"{result['method_label']} (not controlled): {', '.join(e['Entity'] for e in excluded)}. "
                    f"Switch to Equity Share to include a proportional share instead."})

    partial = [r for r in result["rows"] if 0 < r["Consolidation Factor"] < 1]
    if partial and method == "equity_share":
        insights.append({"icon":"📐","type":"info",
            "text": f"<strong>{len(partial)} entit(y/ies)</strong> are partially consolidated "
                    f"based on ownership percentage. Total consolidated emissions "
                    f"({result['total_kg']/1000:,.1f} tCO₂e) are "
                    f"{'lower' if diff_pct<0 else 'higher'} than the simple sum of all entities "
                    f"({sum_reported/1000:,.1f} tCO₂e) by {abs(diff_pct):.1f}%."})

    insights.append({"icon":"📋","type":"warn",
        "text": f"Document the chosen consolidation approach (<strong>{result['method_label']}</strong>) "
                f"in your sustainability report — GHG Protocol requires consistent application year-over-year "
                f"and disclosure of the chosen boundary."})

    st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
        padding:20px;border-top:3px solid #8B5CF6;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
             color:#94A3B8;margin-bottom:14px;">Consolidation Notes</div>
    """, unsafe_allow_html=True)
    insight_panel(insights)
    st.markdown("</div>", unsafe_allow_html=True)
