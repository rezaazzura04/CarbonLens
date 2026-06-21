"""
CarbonLens V7 — Carbon Credit Center (Tier 5)
Estimate offset volume from residual gap, browse project types,
link to registries (Gold Standard, Verra VCS, IDX Carbon).
Feeds from Scenario Simulator residual gap or manual input.
"""

from __future__ import annotations
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, empty_state, card_start, card_end
from config.settings import PLOTLY_THEME as T, COLORS
from utils.calculations import NumpyEncoder

# ── Carbon credit project types ───────────────────────────────────────────────
PROJECT_TYPES = {
    "REDD+ / Avoided Deforestation": {
        "icon": "🌳", "registry": "Verra VCS",
        "price_low": 4,  "price_high": 18,
        "permanence": "30–100 yr", "co_benefits": "Biodiversity, Community livelihood",
        "sdg": ["SDG 13","SDG 15","SDG 1"],
        "indonesia_context": "Kalimantan & Sumatra peat/forest conservation. Eligible untuk CORSIA & voluntary markets.",
        "registry_url": "https://registry.verra.org/",
        "suitable_for": ["Manufaktur","Perkebunan","Mining"],
        "risk": "Medium",
    },
    "Renewable Energy (Solar / Wind)": {
        "icon": "☀️", "registry": "Gold Standard",
        "price_low": 6,  "price_high": 22,
        "permanence": "20–25 yr", "co_benefits": "Clean energy access, Jobs",
        "sdg": ["SDG 7","SDG 13","SDG 8"],
        "indonesia_context": "Solar mini-grid di NTT & Sulawesi. Grid-connected rooftop solar di Jawa. Gold Standard premium.",
        "registry_url": "https://marketplace.goldstandard.org/",
        "suitable_for": ["Properti","Manufacturing","Office"],
        "risk": "Low",
    },
    "Methane Capture (Landfill / POME)": {
        "icon": "♻️", "registry": "Verra VCS / Gold Standard",
        "price_low": 8,  "price_high": 28,
        "permanence": "10–20 yr", "co_benefits": "Waste reduction, Community health",
        "sdg": ["SDG 13","SDG 11","SDG 3"],
        "indonesia_context": "Biogas dari POME (palm oil mill effluent) — relevan untuk sektor perkebunan & food processing.",
        "registry_url": "https://registry.verra.org/",
        "suitable_for": ["Perkebunan","Manufaktur"],
        "risk": "Low",
    },
    "Blue Carbon (Mangrove / Seagrass)": {
        "icon": "🌊", "registry": "Verra VCS",
        "price_low": 15, "price_high": 50,
        "permanence": "50–100 yr", "co_benefits": "Coastal protection, Fisheries, Biodiversity",
        "sdg": ["SDG 14","SDG 13","SDG 15"],
        "indonesia_context": "Indonesia memiliki 20–25% mangrove dunia. High-quality, premium-priced. Cocok untuk coastal industry.",
        "registry_url": "https://registry.verra.org/",
        "suitable_for": ["Manufaktur","Perkebunan","Mining"],
        "risk": "Medium",
    },
    "Improved Cook Stoves": {
        "icon": "🍳", "registry": "Gold Standard",
        "price_low": 5,  "price_high": 15,
        "permanence": "5–10 yr", "co_benefits": "Health, Women empowerment, Deforestation reduction",
        "sdg": ["SDG 3","SDG 5","SDG 13"],
        "indonesia_context": "Program tungku bersih di pedesaan — dampak sosial tinggi, harga karbon menengah.",
        "registry_url": "https://marketplace.goldstandard.org/",
        "suitable_for": ["Manufacturing","Retail","Office"],
        "risk": "Low",
    },
    "IDX Carbon Indonesia": {
        "icon": "🇮🇩", "registry": "IDX Carbon (OJK regulated)",
        "price_low": 2,  "price_high": 12,
        "permanence": "Varies", "co_benefits": "National market development",
        "sdg": ["SDG 13","SDG 17"],
        "indonesia_context": "Bursa Karbon Indonesia (IDX Carbon) diluncurkan Sept 2023 — regulated by OJK. Unit: SPE-GRK & PTBAE-PU.",
        "registry_url": "https://www.idxcarbon.co.id/",
        "suitable_for": ["Semua sektor"],
        "risk": "Low",
    },
    "Soil Carbon / Regenerative Agriculture": {
        "icon": "🌾", "registry": "Verra VCS / Regen Network",
        "price_low": 10, "price_high": 35,
        "permanence": "20–50 yr", "co_benefits": "Food security, Soil health, Water quality",
        "sdg": ["SDG 2","SDG 13","SDG 15"],
        "indonesia_context": "Pertanian regeneratif di Jawa & Sumatra — masih emerging di Indonesia tapi berkembang cepat.",
        "registry_url": "https://registry.verra.org/",
        "suitable_for": ["Perkebunan","Agriculture"],
        "risk": "High",
    },
}

RISK_COLORS = {"Low": "#10B981", "Medium": "#F59E0B", "High": "#EF4444"}

# ── Portfolio optimizer ───────────────────────────────────────────────────────
def _optimize_portfolio(volume_tco2e: float, budget_usd: float | None = None) -> list[dict]:
    """Simple rule-based portfolio: diversify across 3 project types by risk."""
    if volume_tco2e <= 0:
        return []

    # Weight: 50% Low-risk, 30% Medium-risk, 20% High-risk
    allocations = [
        ("IDX Carbon Indonesia",            0.30),
        ("Renewable Energy (Solar / Wind)", 0.25),
        ("REDD+ / Avoided Deforestation",   0.20),
        ("Blue Carbon (Mangrove / Seagrass)",0.15),
        ("Methane Capture (Landfill / POME)",0.10),
    ]
    rows = []
    for ptype, share in allocations:
        meta  = PROJECT_TYPES[ptype]
        vol   = round(volume_tco2e * share, 2)
        price = (meta["price_low"] + meta["price_high"]) / 2
        cost  = round(vol * price, 0)
        rows.append({
            "Project Type":   ptype,
            "Registry":       meta["registry"],
            "Volume (tCO₂e)": vol,
            "Price ($/tCO₂e)":f"${meta['price_low']}–${meta['price_high']}",
            "Est. Cost (USD)": f"${cost:,.0f}",
            "Risk":           meta["risk"],
            "Share":          share,
            "cost_num":       cost,
        })
    return rows


def _donut(rows: list[dict]) -> go.Figure:
    labels = [r["Project Type"].split("(")[0].strip() for r in rows]
    values = [r["Volume (tCO₂e)"] for r in rows]
    colors = [RISK_COLORS.get(r["Risk"], "#64748B") for r in rows]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors),
        textinfo="percent", textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{value:.1f} tCO₂e<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        height=260, margin=dict(l=10,r=10,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=T["font_family"], color=T["font_color"]),
        showlegend=False,
    )
    return fig


def render():
    S.init()
    page_header(
        title="Carbon Credit Center",
        subtitle="Residual gap offset estimator · Project type browser · IDX Carbon · Gold Standard · Verra VCS",
        badge="Tier 5", badge_type="green",
    )

    # ── Pull residual from scenario sim or let user input ─────────────────────
    residual_from_sim = S.get("sim_residual_gap_tco2e") or 0.0
    has_data = S.get("uploaded_df") is not None

    st.markdown("""
    <div style="background:#ECFDF5;border:1px solid #6EE7B7;border-radius:10px;
         padding:12px 16px;font-size:12px;color:#064E3B;margin-bottom:16px;">
        <strong>Carbon Credits sebagai last resort</strong> — GHG Protocol menetapkan hierarki:
        <strong>Reduce → Avoid → Offset</strong>. Carbon credits hanya untuk residual gap yang tidak bisa
        dieliminasi melalui efisiensi atau renewable energy. Gunakan modul
        <strong>Scenario Simulator</strong> untuk meminimalkan offset volume sebelum membeli kredit karbon.
    </div>
    """, unsafe_allow_html=True)

    # ── Input Section ─────────────────────────────────────────────────────────
    card_start("Offset Volume Calculator", "Residual gap dari Scenario Simulator atau input manual")

    col_inp, col_info = st.columns([1.2, 1], gap="medium")
    with col_inp:
        use_sim = residual_from_sim > 0
        if use_sim:
            st.success(f"✦ Residual gap dari Scenario Simulator: **{residual_from_sim:,.1f} tCO₂e**")

        input_mode = st.radio(
            "Sumber volume offset:",
            ["Dari Scenario Simulator" if use_sim else "Scenario Simulator (belum ada data)", "Input manual"],
            key="cc_input_mode",
            horizontal=True,
        )
        if "manual" in input_mode.lower():
            volume = st.number_input("Residual gap yang perlu di-offset (tCO₂e)", min_value=0.0,
                                      value=float(residual_from_sim) if residual_from_sim else 500.0,
                                      step=50.0, key="cc_volume")
        else:
            volume = float(residual_from_sim) if residual_from_sim else 0.0
            st.info(f"Volume: {volume:,.1f} tCO₂e")

        budget = st.number_input("Budget maksimum (USD, 0 = tidak terbatas)",
                                  min_value=0.0, value=0.0, step=1000.0, key="cc_budget")

    with col_info:
        st.markdown("""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
             padding:14px 16px;font-size:12px;color:#374151;line-height:1.8;">
            <strong>Cara kerja:</strong><br>
            1. Set target reduksi di <strong>Scenario Simulator</strong><br>
            2. Residual gap otomatis dikirim ke sini<br>
            3. Pilih mix project type sesuai strategi<br>
            4. Link langsung ke registry untuk pembelian<br><br>
            <strong>Harga referensi 2024–2025:</strong><br>
            IDX Carbon: $2–12/tCO₂e<br>
            Voluntary market: $4–50/tCO₂e<br>
            Gold Standard premium: $15–40/tCO₂e
        </div>
        """, unsafe_allow_html=True)

    card_end()

    if volume <= 0:
        empty_state("🌱", "Masukkan Volume Offset",
                    "Masukkan residual gap di atas atau jalankan Scenario Simulator — residual gap akan otomatis terisi.")
        return

    # ── Cost estimates ────────────────────────────────────────────────────────
    low_cost  = sum(PROJECT_TYPES[p]["price_low"]  for p in list(PROJECT_TYPES)[:3]) / 3 * volume
    high_cost = sum(PROJECT_TYPES[p]["price_high"] for p in list(PROJECT_TYPES)[:3]) / 3 * volume
    idx_cost  = volume * (PROJECT_TYPES["IDX Carbon Indonesia"]["price_low"] +
                          PROJECT_TYPES["IDX Carbon Indonesia"]["price_high"]) / 2

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1: kpi_card("Volume to Offset",  f"{volume:,.1f} tCO₂e", icon="🎯", icon_bg="#ECFDF5")
    with k2: kpi_card("Est. Cost (Low)",   f"${low_cost:,.0f}",    icon="💰", icon_bg="#E0F2FE",
                       badge="Market minimum", badge_type="green")
    with k3: kpi_card("Est. Cost (High)",  f"${high_cost:,.0f}",   icon="💰", icon_bg="#FFF7ED",
                       badge="Premium market", badge_type="orange")
    with k4: kpi_card("IDX Carbon Est.",   f"${idx_cost:,.0f}",    icon="🇮🇩", icon_bg="#ECFDF5",
                       badge="Regulated · OJK", badge_type="green")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📊 Portfolio Optimizer", "🌍 Project Browser", "📤 Export"])

    with tab1:
        portfolio = _optimize_portfolio(volume, budget if budget > 0 else None)

        col_chart, col_table = st.columns([1, 1.5], gap="medium")
        with col_chart:
            card_start("Portfolio Mix", "Diversifikasi berdasarkan risk & registry")
            try:
                st.plotly_chart(_donut(portfolio), use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")

            total_cost = sum(r["cost_num"] for r in portfolio)
            st.markdown(f"""
            <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;
                 padding:10px 14px;text-align:center;margin-top:8px;">
                <div style="font-size:10px;font-weight:700;color:#94A3B8;margin-bottom:2px;">TOTAL EST. COST</div>
                <div style="font-size:22px;font-weight:700;color:#10B981;">${total_cost:,.0f}</div>
                <div style="font-size:10px;color:#64748B;">${total_cost/max(volume,1):,.1f}/tCO₂e blended avg</div>
            </div>
            """, unsafe_allow_html=True)
            card_end()

        with col_table:
            card_start("Recommended Portfolio", "5-project diversified mix")
            for r in portfolio:
                rc = RISK_COLORS.get(r["Risk"], "#64748B")
                meta = PROJECT_TYPES[r["Project Type"]]
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;padding:10px 0;
                     border-bottom:1px solid #F8FAFC;">
                    <div style="font-size:20px;width:28px;text-align:center;">{meta['icon']}</div>
                    <div style="flex:1;">
                        <div style="font-size:12px;font-weight:700;color:#0F172A;">
                            {r['Project Type'].split('(')[0].strip()}</div>
                        <div style="font-size:10px;color:#94A3B8;">{r['Registry']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:12px;font-weight:700;color:#0F172A;">{r['Volume (tCO₂e)']:,.1f} tCO₂e</div>
                        <div style="font-size:10px;color:#64748B;">{r['Price ($/tCO₂e)']}</div>
                        <div style="display:inline-block;font-size:9px;font-weight:700;padding:1px 6px;
                             border-radius:10px;background:{rc}22;color:{rc};margin-top:2px;">{r['Risk']} risk</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            card_end()

        # Insights
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        insight_panel([
            {"icon": "🇮🇩", "type": "info",
             "text": f"<strong>IDX Carbon</strong> adalah entry point yang direkomendasikan untuk emiten BEI — "
                     f"regulated OJK, harga lebih accessible (${PROJECT_TYPES['IDX Carbon Indonesia']['price_low']}–${PROJECT_TYPES['IDX Carbon Indonesia']['price_high']}/tCO₂e), "
                     f"dan memenuhi syarat POJK 51 disclosure."},
            {"icon": "🌊", "type": "info",
             "text": "<strong>Blue Carbon (Mangrove)</strong> adalah pilihan premium dengan co-benefits tertinggi — "
                     "Indonesia memiliki 20–25% mangrove dunia, cocok untuk klien dengan target biodiversity net gain."},
            {"icon": "⚠️", "type": "warn",
             "text": "Carbon credits <strong>bukan pengganti reduksi emisi nyata</strong> — investor ESG dan rating agency "
                     "(MSCI, Sustainalytics) membedakan antara 'avoided emissions' dari kredit dengan 'actual reduction' dari operasi."},
        ])

    with tab2:
        search = st.text_input("🔍 Filter project type", placeholder="redd, solar, mangrove...",
                                key="cc_search")
        for ptype, meta in PROJECT_TYPES.items():
            if search.lower() and search.lower() not in ptype.lower() and search.lower() not in meta["indonesia_context"].lower():
                continue
            rc = RISK_COLORS.get(meta["risk"], "#64748B")
            with st.expander(f"{meta['icon']}  {ptype}  ·  {meta['registry']}  ·  ${meta['price_low']}–${meta['price_high']}/tCO₂e", expanded=False):
                col_l, col_r = st.columns(2, gap="medium")
                with col_l:
                    cost_l = round(volume * meta["price_low"], 0)
                    cost_h = round(volume * meta["price_high"], 0)
                    st.markdown(f"""
                    <div style="font-size:12px;color:#374151;line-height:1.8;">
                        <strong>Registry:</strong> {meta['registry']}<br>
                        <strong>Price range:</strong> ${meta['price_low']}–${meta['price_high']}/tCO₂e<br>
                        <strong>Est. cost for {volume:,.0f} tCO₂e:</strong> ${cost_l:,.0f}–${cost_h:,.0f}<br>
                        <strong>Permanence:</strong> {meta['permanence']}<br>
                        <strong>Risk:</strong> <span style="color:{rc};font-weight:700;">{meta['risk']}</span><br>
                        <strong>Co-benefits:</strong> {meta['co_benefits']}<br>
                        <strong>SDGs:</strong> {', '.join(meta['sdg'])}
                    </div>
                    """, unsafe_allow_html=True)
                with col_r:
                    st.markdown(f"""
                    <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;
                         padding:12px 14px;font-size:12px;color:#064E3B;margin-bottom:10px;">
                        <strong>🇮🇩 Indonesia context:</strong><br>{meta['indonesia_context']}
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button(f"🔗 Browse {meta['registry']}", meta["registry_url"],
                                   use_container_width=True)

    with tab3:
        portfolio = _optimize_portfolio(volume, budget if budget > 0 else None)
        export_rows = []
        for r in portfolio:
            meta = PROJECT_TYPES[r["Project Type"]]
            export_rows.append({
                "Project Type":        r["Project Type"],
                "Registry":            r["Registry"],
                "Volume (tCO₂e)":      r["Volume (tCO₂e)"],
                "Price Range ($/tCO₂e)":r["Price ($/tCO₂e)"],
                "Est. Cost (USD)":     r["cost_num"],
                "Risk Level":          r["Risk"],
                "Permanence":          meta["permanence"],
                "SDGs":                ", ".join(meta["sdg"]),
                "Registry URL":        meta["registry_url"],
            })
        export_df = pd.DataFrame(export_rows)
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.download_button(
                "⬇️  Export Portfolio (CSV)",
                data=export_df.to_csv(index=False).encode(),
                file_name="carbonlens_carbon_credit_portfolio.csv", mime="text/csv",
                use_container_width=True,
            )
        with col_b:
            import json
            summary = {
                "offset_volume_tco2e": volume,
                "estimated_cost_low":  round(low_cost, 0),
                "estimated_cost_high": round(high_cost, 0),
                "recommended_portfolio": [
                    {"project": r["Project Type"], "volume": r["Volume (tCO₂e)"],
                     "est_cost": r["cost_num"], "registry": r["Registry"]}
                    for r in portfolio
                ],
                "registries": {
                    "idx_carbon": "https://www.idxcarbon.co.id/",
                    "gold_standard": "https://marketplace.goldstandard.org/",
                    "verra_vcs": "https://registry.verra.org/",
                },
            }
            st.download_button(
                "⬇️  Export Summary (JSON)",
                data=json.dumps(summary, indent=2, cls=NumpyEncoder).encode(),
                file_name="carbonlens_carbon_credit_summary.json", mime="application/json",
                use_container_width=True,
            )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.dataframe(export_df, use_container_width=True, hide_index=True)

        st.markdown("""
        <div style="font-size:10px;color:#94A3B8;margin-top:10px;line-height:1.6;">
            <strong>Disclaimer:</strong> Harga karbon adalah estimasi berdasarkan referensi pasar 2024–2025.
            Harga aktual bervariasi berdasarkan vintag, co-benefit, dan kondisi pasar. Verifikasi melalui
            registry resmi sebelum pembelian. CarbonLens tidak terafiliasi dengan registry manapun.
        </div>
        """, unsafe_allow_html=True)
