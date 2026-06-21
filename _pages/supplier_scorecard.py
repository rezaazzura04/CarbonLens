"""
CarbonLens V7 — Supplier ESG Scorecard (Scope 3 Category 1)
- Editable supplier table → weighted Scope 3 Cat.1
- Weighted ESG risk scoring per supplier (Environment + Social + Governance proxies)
- Concentration risk flagging
- Engagement priority ranking
- Feeds Carbon Accounting Cat.1 override
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, empty_state
from config.settings import COLORS, PLOTLY_THEME as T

# USEEIO v2.0 sector-adjusted emission factors (kg CO2e / USD spend)
SECTOR_EF_USD = {
    "Agriculture & Food":        0.38,
    "Mining & Quarrying":        0.72,
    "Manufacturing — General":   0.42,
    "Manufacturing — Heavy":     0.68,
    "Construction":              0.51,
    "Transport & Logistics":     0.55,
    "Retail & Distribution":     0.28,
    "ICT & Software":            0.18,
    "Energy & Utilities":        0.85,
    "Financial Services":        0.12,
    "Healthcare":                0.35,
    "Professional Services":     0.15,
    "Other / Unspecified":       0.42,
}

RISK_THRESHOLD_PCT = 20.0

# ESG risk proxy scoring weights
ESG_RISK_WEIGHTS = {
    "env":  0.50,   # emission intensity, sector EF
    "soc":  0.30,   # labor practices proxy
    "gov":  0.20,   # disclosure quality
}

# Sector-level ESG risk baseline (0=low, 1=high)
SECTOR_ESG_RISK = {
    "Agriculture & Food":        {"env": 0.65, "soc": 0.60, "gov": 0.45},
    "Mining & Quarrying":        {"env": 0.90, "soc": 0.75, "gov": 0.55},
    "Manufacturing — General":   {"env": 0.55, "soc": 0.50, "gov": 0.45},
    "Manufacturing — Heavy":     {"env": 0.80, "soc": 0.60, "gov": 0.50},
    "Construction":              {"env": 0.60, "soc": 0.65, "gov": 0.40},
    "Transport & Logistics":     {"env": 0.70, "soc": 0.55, "gov": 0.45},
    "Retail & Distribution":     {"env": 0.35, "soc": 0.50, "gov": 0.40},
    "ICT & Software":            {"env": 0.20, "soc": 0.30, "gov": 0.35},
    "Energy & Utilities":        {"env": 0.85, "soc": 0.50, "gov": 0.60},
    "Financial Services":        {"env": 0.15, "soc": 0.40, "gov": 0.50},
    "Healthcare":                {"env": 0.40, "soc": 0.45, "gov": 0.50},
    "Professional Services":     {"env": 0.15, "soc": 0.35, "gov": 0.40},
    "Other / Unspecified":       {"env": 0.50, "soc": 0.50, "gov": 0.50},
}

RISK_LABEL = {(0.0, 0.33): ("Low", "green"), (0.33, 0.60): ("Medium", "yellow"), (0.60, 1.0): ("High", "red")}


def _risk_label(score: float):
    for (lo, hi), (label, badge) in RISK_LABEL.items():
        if lo <= score <= hi:
            return label, badge
    return "High", "red"


def _empty_table():
    return pd.DataFrame([
        {"Supplier": "", "Sector": "Manufacturing — General", "Annual Spend (USD)": 0.0,
         "Disclosed Emissions (tCO2e)": 0.0, "Has Disclosure": False,
         "ISO 14001": False, "CDP Rated": False, "Code of Conduct Signed": False},
    ])


def _compute(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_spend = df["Annual Spend (USD)"].sum()
    for _, row in df.iterrows():
        ef = SECTOR_EF_USD.get(row["Sector"], 0.42)
        if row.get("Has Disclosure") and row["Disclosed Emissions (tCO2e)"] > 0:
            em = row["Disclosed Emissions (tCO2e)"]
            method = "Supplier-disclosed"
        else:
            em = round(row["Annual Spend (USD)"] * ef / 1000, 4)
            method = f"USEEIO ({ef} kg/USD)"

        spend_share = row["Annual Spend (USD)"] / total_spend * 100 if total_spend > 0 else 0

        # ESG risk scoring
        risk_base = SECTOR_ESG_RISK.get(row["Sector"], {"env": 0.5, "soc": 0.5, "gov": 0.5})
        env_risk  = risk_base["env"] * (0.6 if row.get("ISO 14001") else 1.0)
        soc_risk  = risk_base["soc"]
        gov_risk  = risk_base["gov"] * (0.5 if row.get("CDP Rated") else 1.0) * (0.7 if row.get("Code of Conduct Signed") else 1.0)
        # Disclosure quality adjustment
        if row.get("Has Disclosure"):
            gov_risk = gov_risk * 0.6

        composite_risk = (
            env_risk * ESG_RISK_WEIGHTS["env"] +
            soc_risk * ESG_RISK_WEIGHTS["soc"] +
            gov_risk * ESG_RISK_WEIGHTS["gov"]
        )
        risk_lbl, risk_badge = _risk_label(composite_risk)

        rows.append({
            "Supplier":                    row["Supplier"],
            "Sector":                      row["Sector"],
            "Annual Spend (USD)":          round(row["Annual Spend (USD)"], 0),
            "Spend Share (%)":             round(spend_share, 1),
            "Computed Emissions (tCO2e)":  em,
            "Methodology":                 method,
            "Env Risk":                    round(env_risk, 2),
            "Social Risk":                 round(soc_risk, 2),
            "Gov Risk":                    round(gov_risk, 2),
            "ESG Risk Score":              round(composite_risk, 2),
            "Risk Level":                  risk_lbl,
            "ISO 14001":                   bool(row.get("ISO 14001", False)),
            "CDP Rated":                   bool(row.get("CDP Rated", False)),
            "CoC Signed":                  bool(row.get("Code of Conduct Signed", False)),
            "High Concentration":          spend_share > RISK_THRESHOLD_PCT,
            "Has Disclosure":              bool(row.get("Has Disclosure", False)),
            "Engagement Priority":         round(composite_risk * spend_share / 100, 3),
        })
    return pd.DataFrame(rows)


def render():
    S.init()
    page_header(
        title="Supplier ESG Scorecard",
        subtitle="Scope 3 Cat.1 · Weighted ESG Risk Scoring · Engagement Priority Ranking · GHG Protocol aligned",
        badge="Supply Chain", badge_type="orange",
    )

    st.markdown("""
    <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;
         padding:12px 16px;font-size:12px;color:#92400E;margin-bottom:16px;">
        <strong>Supplier ESG Scorecard</strong> — Hitung emisi Scope 3 Kategori 1 (Purchased Goods & Services)
        per supplier. ESG Risk Score dihitung berdasarkan sektor, sertifikasi, dan kualitas pengungkapan.
        Suplier dengan risiko tinggi dan spend besar diprioritaskan untuk engagement program.
    </div>
    """, unsafe_allow_html=True)

    # ── Editable table ────────────────────────────────────────────────────────
    if "supplier_table" not in st.session_state:
        existing = S.get("supplier_table")
        base = pd.DataFrame(existing) if existing else _empty_table()
        # ensure new columns exist
        for col, default in [("ISO 14001", False), ("CDP Rated", False), ("Code of Conduct Signed", False)]:
            if col not in base.columns:
                base[col] = default
        st.session_state["supplier_table"] = base

    st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
        padding:20px;border-top:3px solid #F97316;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
             color:#94A3B8;margin-bottom:14px;">Data Spend & Emisi Supplier</div>
    """, unsafe_allow_html=True)

    edited = st.data_editor(
        st.session_state["supplier_table"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Supplier":     st.column_config.TextColumn("Nama Supplier", width="medium"),
            "Sector":       st.column_config.SelectboxColumn("Sektor", options=list(SECTOR_EF_USD.keys()), width="medium"),
            "Annual Spend (USD)": st.column_config.NumberColumn("Spend Tahunan (USD)", format="$%.0f", min_value=0.0),
            "Disclosed Emissions (tCO2e)": st.column_config.NumberColumn(
                "Emisi Disclosed (tCO2e)", format="%.3f", min_value=0.0,
                help="Isi 0 jika supplier belum mengungkapkan — akan diestimasi dari USEEIO"),
            "Has Disclosure": st.column_config.CheckboxColumn("Ada Disclosure?"),
            "ISO 14001":      st.column_config.CheckboxColumn("ISO 14001 ✓", help="Supplier bersertifikat ISO 14001"),
            "CDP Rated":      st.column_config.CheckboxColumn("CDP Rated ✓", help="Supplier berpartisipasi di CDP"),
            "Code of Conduct Signed": st.column_config.CheckboxColumn("CoC Signed ✓", help="Supplier sudah tanda tangani Code of Conduct"),
        },
        key="supplier_editor",
    )
    st.session_state["supplier_table"] = edited
    S.set("supplier_table", edited.to_dict("records"))
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    valid = edited[edited["Supplier"].astype(str).str.strip() != ""]
    if valid.empty:
        empty_state("🏭", "Belum ada supplier",
                    "Tambahkan supplier di tabel di atas — masukkan spend, sektor, dan data emisi untuk menghitung estimasi Scope 3 Cat.1.")
        return

    computed = _compute(valid)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_em       = computed["Computed Emissions (tCO2e)"].sum()
    total_spend    = computed["Annual Spend (USD)"].sum()
    n_disclosed    = int(computed["Has Disclosure"].sum())
    n_total        = len(computed)
    n_high_risk    = int((computed["Risk Level"] == "High").sum())
    disclosure_pct = round(n_disclosed / n_total * 100) if n_total > 0 else 0
    avg_esg_risk   = round(computed["ESG Risk Score"].mean(), 2)
    _, risk_badge  = _risk_label(avg_esg_risk)

    k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
    with k1: kpi_card("Scope 3 Cat.1 Total", f"{total_em:,.2f} tCO₂e", icon="🏭", icon_bg="#FFF7ED")
    with k2: kpi_card("Total Spend",         f"${total_spend:,.0f}",   icon="💰", icon_bg="#E0F2FE")
    with k3: kpi_card("Supplier Disclosure", f"{disclosure_pct}%",     icon="📋", icon_bg="#ECFEFF",
                       badge=f"{n_disclosed}/{n_total}", badge_type="cyan")
    with k4: kpi_card("Avg ESG Risk",        f"{avg_esg_risk:.2f}",    icon="⚠️", icon_bg="#FFF1F2",
                       badge=_risk_label(avg_esg_risk)[0], badge_type=risk_badge)
    with k5: kpi_card("High-Risk Supplier",  str(n_high_risk),         icon="🔴", icon_bg="#FFF1F2",
                       badge="Prioritaskan engagement", badge_type="red" if n_high_risk > 0 else "green")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📊 Breakdown & Risk", "🎯 Engagement Priority", "⬇️ Export"])

    with tab1:
        # Per-supplier table
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #F97316;margin-bottom:14px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Per-Supplier ESG Risk & Emisi</div>
        """, unsafe_allow_html=True)

        display_df = computed[[
            "Supplier", "Sector", "Annual Spend (USD)", "Spend Share (%)",
            "Computed Emissions (tCO2e)", "ESG Risk Score", "Risk Level",
            "Env Risk", "Social Risk", "Gov Risk", "Methodology",
        ]].sort_values("Engagement Priority" if "Engagement Priority" in computed.columns else "ESG Risk Score", ascending=False)

        st.dataframe(
            display_df, use_container_width=True, hide_index=True,
            height=min(400, 48 + 36 * len(display_df)),
            column_config={
                "Annual Spend (USD)":         st.column_config.NumberColumn(format="$%.0f"),
                "Spend Share (%)":            st.column_config.NumberColumn(format="%.1f%%"),
                "Computed Emissions (tCO2e)": st.column_config.NumberColumn(format="%.3f"),
                "ESG Risk Score":             st.column_config.NumberColumn(format="%.2f"),
                "Env Risk":                   st.column_config.NumberColumn(format="%.2f"),
                "Social Risk":                st.column_config.NumberColumn(format="%.2f"),
                "Gov Risk":                   st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Scatter: spend vs risk
        if len(computed) >= 2:
            st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                padding:20px;border-top:3px solid #F97316;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                     color:#94A3B8;margin-bottom:14px;">Spend vs ESG Risk — Supplier Positioning</div>
            """, unsafe_allow_html=True)

            color_map = {"Low": "#10B981", "Medium": "#F59E0B", "High": "#EF4444"}
            fig = go.Figure()
            for rl in ["High", "Medium", "Low"]:
                sub = computed[computed["Risk Level"] == rl]
                if sub.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=sub["Annual Spend (USD)"].tolist(),
                    y=sub["ESG Risk Score"].tolist(),
                    mode="markers+text",
                    name=f"{rl} Risk",
                    text=sub["Supplier"].tolist(),
                    textposition="top center",
                    textfont=dict(size=9),
                    marker=dict(color=color_map[rl], size=sub["Computed Emissions (tCO2e)"].apply(
                        lambda v: max(10, min(40, v * 3 + 10))).tolist(),
                        line=dict(color="white", width=1)),
                    hovertemplate="<b>%{text}</b><br>Spend: $%{x:,.0f}<br>Risk: %{y:.2f}<extra></extra>",
                ))

            # Quadrants
            mid_spend = computed["Annual Spend (USD)"].median()
            mid_risk  = 0.50
            fig.add_vline(x=mid_spend, line_dash="dot", line_color="#CBD5E1", line_width=1)
            fig.add_hline(y=mid_risk,  line_dash="dot", line_color="#CBD5E1", line_width=1)

            fig.update_layout(
                height=320, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=T["font_family"], color=T["font_color"]),
                xaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="Annual Spend (USD)", tickprefix="$"),
                yaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="ESG Risk Score", range=[0, 1]),
                legend=dict(orientation="h", y=-0.2, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                annotations=[
                    dict(x=mid_spend * 1.8, y=0.9, text="High Priority", showarrow=False,
                         font=dict(size=9, color="#EF4444"), bgcolor="#FFF1F2", borderpad=3),
                    dict(x=mid_spend * 0.3, y=0.1, text="Low Priority", showarrow=False,
                         font=dict(size=9, color="#10B981"), bgcolor="#ECFDF5", borderpad=3),
                ],
            )
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")
            st.caption("Ukuran bubble = volume emisi. Pojok kanan atas = supplier prioritas engagement tertinggi.")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        # Ranked engagement list
        priority = computed.sort_values("Engagement Priority", ascending=False).reset_index(drop=True)
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:4px;">Engagement Priority Ranking</div>
            <div style="font-size:11px;color:#CBD5E1;margin-bottom:16px;">
                Skor = ESG Risk × Spend Share — prioritaskan supplier dengan risiko tinggi dan spend besar
            </div>
        """, unsafe_allow_html=True)

        for i, row in priority.iterrows():
            rl, rb = _risk_label(row["ESG Risk Score"])
            badge_colors = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444"}
            bc = badge_colors.get(rb, "#94A3B8")
            missing_certs = []
            if not row.get("ISO 14001"): missing_certs.append("ISO 14001")
            if not row.get("CDP Rated"):  missing_certs.append("CDP Rating")
            if not row.get("CoC Signed"): missing_certs.append("Code of Conduct")
            cert_html = (f'<div style="font-size:10px;color:#EF4444;margin-top:3px;">Missing: {", ".join(missing_certs)}</div>'
                         if missing_certs else
                         '<div style="font-size:10px;color:#10B981;margin-top:3px;">✓ Semua sertifikasi lengkap</div>')

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;padding:12px 14px;
                 background:white;border:1px solid #E2E8F0;border-radius:10px;margin-bottom:8px;
                 border-left:4px solid {bc};">
                <div style="font-size:22px;font-weight:900;color:#CBD5E1;width:28px;text-align:center;">
                    {i+1}
                </div>
                <div style="flex:1;">
                    <div style="font-size:13px;font-weight:700;color:#1F2937;">{row['Supplier']}</div>
                    <div style="font-size:11px;color:#6B7280;">{row['Sector']} · ${row['Annual Spend (USD)']:,.0f} spend · {row['Spend Share (%)']:.1f}% of total</div>
                    {cert_html}
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px;font-weight:800;color:{bc};">{rl} Risk</div>
                    <div style="font-size:10px;color:#9CA3AF;">{row['Computed Emissions (tCO2e)']:.3f} tCO₂e</div>
                    <div style="font-size:10px;color:#9CA3AF;">Score: {row['ESG Risk Score']:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Insights
        insights = []
        top = priority.iloc[0] if len(priority) > 0 else None
        if top is not None:
            insights.append({"icon": "🏭", "type": "info",
                "text": f"<strong>{top['Supplier']}</strong> adalah prioritas engagement tertinggi — "
                        f"ESG Risk {top['ESG Risk Score']:.2f}, kontribusi {top['Spend Share (%)']:.1f}% total spend "
                        f"dan {top['Computed Emissions (tCO2e)']:.2f} tCO₂e."})
        if n_high_risk > 0:
            insights.append({"icon": "⚠️", "type": "alert",
                "text": f"<strong>{n_high_risk} supplier</strong> berisiko tinggi. Pertimbangkan program Supplier Sustainability "
                        f"Development — wajibkan pengisian CDP dan penandatanganan CoC sebagai prasyarat perpanjangan kontrak."})
        if disclosure_pct < 50:
            insights.append({"icon": "📋", "type": "warn",
                "text": f"Baru <strong>{disclosure_pct}%</strong> supplier yang mengungkapkan emisi. "
                        f"Tingkatkan ke >50% untuk memenuhi standar CDP Supply Chain reporting."})
        if insights:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            insight_panel(insights)

    with tab3:
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.download_button(
                "⬇️  Export Supplier Scorecard (CSV)",
                data=computed.to_csv(index=False).encode(),
                file_name="carbonlens_supplier_scorecard.csv", mime="text/csv",
                use_container_width=True,
            )
        with col_b:
            if st.button("📤  Kirim ke Scope 3 Cat.1 (Carbon Accounting)", type="primary",
                         use_container_width=True, key="send_cat1"):
                S.set("scope3_cat1_override_tco2e", float(total_em))
                S.set("scope3_cat1_source",
                      f"Supplier Scorecard ({n_total} suppliers, {disclosure_pct}% disclosed, avg ESG risk {avg_esg_risk:.2f})")
                st.success(f"✅ {total_em:,.2f} tCO₂e dikirim ke Carbon Accounting sebagai Cat.1 — Purchased Goods & Services")

        st.caption("Pengiriman ini menggantikan estimasi generik spend × 0.42 di Carbon Accounting dengan total supplier-weighted yang terdokumentasi per supplier.")
