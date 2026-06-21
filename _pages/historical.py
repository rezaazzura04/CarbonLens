"""
CarbonLens V7 — Multi-Year Historical Tracker
- Upload 3-5 yearly CSVs or manual entry
- CAGR, YoY delta, SBTi trajectory overlay
- ESG score trend per tahun (E+S+G)
- Dekarbonisasi gap analysis vs target
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, empty_state, divider
from config.settings import PLOTLY_THEME as T, COLORS

METRICS = ["emission", "energy", "water", "waste", "employees"]
METRIC_LABELS = {
    "emission":  "Total Emissions (tCO₂e)",
    "energy":    "Energy Consumption (MWh)",
    "water":     "Water Consumption (m³)",
    "waste":     "Waste Generated (tonnes)",
    "employees": "Employee Count",
}
METRIC_COLORS = {
    "emission": "#F97316", "energy": "#0EA5E9", "water": "#06B6D4",
    "waste": "#8B5CF6", "employees": "#64748B",
}


def _sbti_trajectory(baseline: float, start_year: int, n_years: int = 10,
                     reduction_pct: float = 4.2) -> list:
    """SBTi 1.5°C — ~4.2% absolute reduction per year from baseline."""
    return [round(baseline * ((1 - reduction_pct / 100) ** i), 1) for i in range(n_years + 1)]


def _paris_trajectory(baseline: float, n_years: int = 10) -> list:
    """Paris 2°C — ~2.5% reduction/year."""
    return [round(baseline * ((1 - 0.025) ** i), 1) for i in range(n_years + 1)]


def render():
    S.init()
    page_header(
        title="Multi-Year Historical Tracker",
        subtitle="Upload 3-5 yearly datasets · CAGR · SBTi trajectory · Dekarbonisasi gap analysis",
        badge="Historical", badge_type="indigo",
    )

    hist = S.get_historical_data()

    # ── Upload / manual entry ──────────────────────────────────────────────────
    with st.container():
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;margin-bottom:14px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Tambah / Update Data Tahun</div>
        """, unsafe_allow_html=True)

        tab_upload, tab_manual = st.tabs(["📂 Upload CSV", "✏️ Manual Entry"])

        with tab_upload:
            st.caption("Upload CSV tahunan (format sama dengan ESG Analytics: Month, Emission, Energy, Water, Waste). Total akan dijumlah otomatis.")
            col_yr, col_file = st.columns([1, 3], gap="medium")
            with col_yr:
                upload_year = st.number_input("Tahun", min_value=2015, max_value=2035, value=2024, step=1, key="hist_upload_year")
            with col_file:
                up_file = st.file_uploader("CSV file", type=["csv"], key="hist_upload_file", label_visibility="collapsed")

            if up_file is not None:
                try:
                    df_y = pd.read_csv(up_file)
                    if "Emission" not in df_y.columns:
                        st.error("CSV harus mengandung kolom 'Emission'.")
                    else:
                        data = {
                            "emission": float(df_y["Emission"].sum()),
                            "energy":   float(df_y["Energy"].sum())  if "Energy" in df_y.columns else 0.0,
                            "water":    float(df_y["Water"].sum())   if "Water"  in df_y.columns else 0.0,
                            "waste":    float(df_y["Waste"].sum())   if "Waste"  in df_y.columns else 0.0,
                            "employees": int(S.get("employees", 0)),
                        }
                        st.info(f"Preview — Total emisi {int(upload_year)}: **{data['emission']:,.0f} tCO₂e**")
                        if st.button(f"➕  Tambahkan {int(upload_year)}", type="primary", key="hist_add_upload"):
                            S.save_historical_year(int(upload_year), data)
                            st.success(f"✅ {int(upload_year)} ditambahkan.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Gagal membaca CSV: {e}")

        with tab_manual:
            st.caption("Masukkan total agregat per tahun secara manual — berguna untuk data sebelum digitalisasi.")
            mc1, mc2, mc3 = st.columns(3, gap="medium")
            with mc1:
                man_year     = st.number_input("Tahun", min_value=2010, max_value=2035, value=2023, step=1, key="hist_man_year")
                man_emission = st.number_input("Total Emisi (tCO₂e)", min_value=0.0, step=10.0, key="hist_man_em")
            with mc2:
                man_energy = st.number_input("Energi (MWh)", min_value=0.0, step=10.0, key="hist_man_energy")
                man_water  = st.number_input("Air (m³)", min_value=0.0, step=10.0, key="hist_man_water")
            with mc3:
                man_waste = st.number_input("Limbah (tonnes)", min_value=0.0, step=1.0, key="hist_man_waste")
                man_emp   = st.number_input("Karyawan", min_value=0, step=1, key="hist_man_emp")

            if st.button("➕  Tambahkan tahun", type="primary", key="hist_add_manual"):
                S.save_historical_year(int(man_year), {
                    "emission": man_emission, "energy": man_energy,
                    "water": man_water, "waste": man_waste, "employees": int(man_emp),
                })
                st.success(f"✅ {int(man_year)} ditambahkan.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    hist = S.get_historical_data()

    # Auto-include current year tip
    current_df = S.get("uploaded_df")
    if current_df is not None and "Emission" in current_df.columns:
        from datetime import date
        cur_year = str(date.today().year)
        if cur_year not in hist:
            st.info(f"💡 Dataset ESG Analytics saat ini belum tercatat sebagai tahun {cur_year}. Tambahkan via Manual Entry di atas.")

    if not hist or len(hist) < 2:
        empty_state("📅", "Butuh Minimal 2 Tahun Data",
                    f"Saat ini ada {len(hist)} tahun tercatat. Tambahkan minimal 2 tahun (idealnya 3-5) untuk melihat tren, CAGR, dan analisis dekarbonisasi.")
        if hist:
            single_df = pd.DataFrame([
                {"Tahun": y, **{METRIC_LABELS[m]: v.get(m, 0) for m in METRICS}}
                for y, v in sorted(hist.items())
            ])
            st.dataframe(single_df, use_container_width=True, hide_index=True)
        return

    # ── Build dataframe ───────────────────────────────────────────────────────
    years    = sorted(hist.keys(), key=lambda y: int(y))
    hist_df  = pd.DataFrame([
        {"Year": int(y), **{m: hist[y].get(m, 0) for m in METRICS}}
        for y in years
    ]).sort_values("Year").reset_index(drop=True)

    em_cagr    = S.compute_cagr(hist_df["emission"].tolist())
    first_em   = hist_df["emission"].iloc[0]
    last_em    = hist_df["emission"].iloc[-1]
    first_year = int(hist_df["Year"].iloc[0])
    last_year  = int(hist_df["Year"].iloc[-1])
    total_chg  = (last_em - first_em) / first_em * 100 if first_em > 0 else 0

    # SBTi gap
    sbti_traj   = _sbti_trajectory(first_em, first_year, n_years=len(years)-1)
    paris_traj  = _paris_trajectory(first_em, n_years=len(years)-1)
    sbti_target = sbti_traj[-1]
    sbti_gap    = last_em - sbti_target

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1: kpi_card("Tahun Direkam", f"{len(hist_df)}", icon="📅", icon_bg="#EEF2FF")
    with k2: kpi_card("Emission CAGR",
                       f"{em_cagr*100:+.1f}%/yr" if em_cagr is not None else "—",
                       icon="📈", icon_bg="#FFF7ED",
                       badge="Menurun ✓" if (em_cagr or 0) < 0 else "Meningkat ⚠",
                       badge_type="green" if (em_cagr or 0) < 0 else "red")
    with k3: kpi_card("Perubahan Total",
                       f"{total_chg:+.1f}%",
                       icon="Δ", icon_bg="#FFE4E6" if total_chg > 0 else "#ECFDF5",
                       badge=f"{first_year} → {last_year}", badge_type="slate")
    with k4: kpi_card("Gap vs SBTi 1.5°C",
                       f"{sbti_gap:+,.0f} tCO₂e",
                       icon="🎯", icon_bg="#FFF7ED" if sbti_gap > 0 else "#ECFDF5",
                       badge="Di atas target" if sbti_gap > 0 else "On-track ✓",
                       badge_type="red" if sbti_gap > 0 else "green")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_trend, tab_sbti, tab_yoy, tab_intensity = st.tabs([
        "📈 Tren Multi-Tahun",
        "🎯 Trajektori SBTi",
        "📊 YoY Comparison",
        "⚡ Intensitas & Efisiensi",
    ])

    # ── Tab Trend ─────────────────────────────────────────────────────────────
    with tab_trend:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;margin-bottom:14px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:2px;">Tren Multi-Tahun</div>
            <div style="font-size:11px;color:#CBD5E1;margin-bottom:14px;">Semua metrik dinormalisasi ke tahun pertama = 100</div>
        """, unsafe_allow_html=True)

        sel_metrics = st.multiselect("Tampilkan metrik:", METRICS,
                                      default=["emission", "energy"],
                                      format_func=lambda m: METRIC_LABELS[m],
                                      key="hist_metrics_sel")
        if not sel_metrics:
            sel_metrics = ["emission"]

        fig = go.Figure()
        for m in sel_metrics:
            series = hist_df[m].tolist()
            normalized = [v / series[0] * 100 if series[0] > 0 else 0 for v in series]
            fig.add_trace(go.Scatter(
                x=hist_df["Year"].tolist(), y=normalized, mode="lines+markers",
                name=METRIC_LABELS[m],
                line=dict(color=METRIC_COLORS[m], width=2.5),
                marker=dict(size=8),
                hovertemplate=f"<b>{METRIC_LABELS[m]}</b><br>%{{x}}: %{{y:.1f}} (index)<extra></extra>",
            ))
        fig.add_hline(y=100, line_dash="dot", line_color="#CBD5E1",
                      annotation_text="Baseline", annotation_font_size=10)
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=T["font_family"], color=T["font_color"]),
            xaxis=dict(showgrid=False, dtick=1, tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Index (Tahun 1 = 100)", tickfont=dict(size=11)),
            legend=dict(orientation="h", y=-0.2, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        )
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Chart error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab SBTi ─────────────────────────────────────────────────────────────
    with tab_sbti:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #10B981;margin-bottom:14px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:2px;">Trajektori SBTi vs Aktual</div>
            <div style="font-size:11px;color:#CBD5E1;margin-bottom:14px;">
                SBTi 1.5°C: −4.2%/tahun · Paris 2°C: −2.5%/tahun · Dari baseline tahun pertama
            </div>
        """, unsafe_allow_html=True)

        # Extend to 2030
        n_ext = max(2030 - last_year, 0)
        ext_years = list(range(first_year, last_year + n_ext + 1))
        sbti_full  = _sbti_trajectory(first_em, first_year, n_years=len(ext_years)-1)
        paris_full = _paris_trajectory(first_em, n_years=len(ext_years)-1)

        fig2 = go.Figure()
        # Actual
        fig2.add_trace(go.Scatter(
            x=hist_df["Year"].tolist(), y=hist_df["emission"].tolist(),
            mode="lines+markers", name="Emisi Aktual",
            line=dict(color="#F97316", width=3),
            marker=dict(size=9, color="#F97316"),
            hovertemplate="<b>Aktual %{x}</b>: %{y:,.0f} tCO₂e<extra></extra>",
        ))
        # SBTi 1.5
        fig2.add_trace(go.Scatter(
            x=ext_years, y=sbti_full,
            mode="lines", name="SBTi 1.5°C (−4.2%/yr)",
            line=dict(color="#10B981", width=2, dash="dash"),
            hovertemplate="<b>SBTi 1.5°C %{x}</b>: %{y:,.0f} tCO₂e<extra></extra>",
        ))
        # Paris 2
        fig2.add_trace(go.Scatter(
            x=ext_years, y=paris_full,
            mode="lines", name="Paris 2°C (−2.5%/yr)",
            line=dict(color="#06B6D4", width=2, dash="dot"),
            hovertemplate="<b>Paris 2°C %{x}</b>: %{y:,.0f} tCO₂e<extra></extra>",
        ))
        # Net zero 2050 target line
        fig2.add_hline(y=0, line_dash="dot", line_color="#E2E8F0", annotation_text="Net Zero", annotation_font_size=9)

        fig2.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=T["font_family"], color=T["font_color"]),
            xaxis=dict(showgrid=False, dtick=1, tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="tCO₂e", tickfont=dict(size=11)),
            legend=dict(orientation="h", y=-0.2, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        )
        try:
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.warning(f"Chart error: {e}")

        # Gap summary
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style="background:#ECFDF5;border:1px solid #6EE7B7;border-radius:8px;padding:12px 16px;">
                <div style="font-size:11px;font-weight:700;color:#065F46;">Target SBTi 1.5°C ({last_year})</div>
                <div style="font-size:22px;font-weight:800;color:#10B981;">{sbti_target:,.0f} tCO₂e</div>
                <div style="font-size:11px;color:#6B7280;">Aktual: {last_em:,.0f} · Gap: {sbti_gap:+,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            sbti_2030 = sbti_full[min(2030 - first_year, len(sbti_full)-1)]
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:12px 16px;">
                <div style="font-size:11px;font-weight:700;color:#1E40AF;">Target SBTi 1.5°C (2030)</div>
                <div style="font-size:22px;font-weight:800;color:#3B82F6;">{sbti_2030:,.0f} tCO₂e</div>
                <div style="font-size:11px;color:#6B7280;">Reduksi wajib: {first_em - sbti_2030:,.0f} tCO₂e dari baseline</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab YoY ──────────────────────────────────────────────────────────────
    with tab_yoy:
        yoy_rows = []
        for i, row in hist_df.iterrows():
            r = {"Tahun": int(row["Year"])}
            for m in METRICS:
                r[METRIC_LABELS[m]] = round(row[m], 1)
            if i > 0:
                prev = hist_df.iloc[i-1]
                for m in ["emission", "energy", "water", "waste"]:
                    chg = (row[m] - prev[m]) / prev[m] * 100 if prev[m] > 0 else 0
                    r[f"{m.title()} YoY %"] = round(chg, 1)
            yoy_rows.append(r)

        yoy_df = pd.DataFrame(yoy_rows)
        st.dataframe(
            yoy_df, use_container_width=True, hide_index=True,
            column_config={
                "emission YoY %": st.column_config.NumberColumn(format="%+.1f%%"),
                "energy YoY %":   st.column_config.NumberColumn(format="%+.1f%%"),
                "water YoY %":    st.column_config.NumberColumn(format="%+.1f%%"),
                "waste YoY %":    st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )

        # Bar chart YoY emission change
        if len(hist_df) >= 2:
            yoy_vals = []
            yoy_yrs  = []
            for i in range(1, len(hist_df)):
                prev = hist_df["emission"].iloc[i-1]
                curr = hist_df["emission"].iloc[i]
                chg  = (curr - prev) / prev * 100 if prev > 0 else 0
                yoy_vals.append(round(chg, 1))
                yoy_yrs.append(int(hist_df["Year"].iloc[i]))

            fig3 = go.Figure(go.Bar(
                x=yoy_yrs, y=yoy_vals,
                marker=dict(color=["#10B981" if v < 0 else "#EF4444" for v in yoy_vals], cornerradius=6),
                text=[f"{v:+.1f}%" for v in yoy_vals],
                textposition="outside",
                hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
            ))
            fig3.add_hline(y=0, line_color="#CBD5E1", line_width=1)
            fig3.add_hline(y=-4.2, line_dash="dash", line_color="#10B981",
                           annotation_text="SBTi 1.5°C", annotation_font_size=9)
            fig3.update_layout(
                height=260, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=T["font_family"], color=T["font_color"]),
                title=dict(text="YoY Perubahan Emisi (%)", font=dict(size=12, color="#64748B")),
                xaxis=dict(showgrid=False, dtick=1),
                yaxis=dict(showgrid=True, gridcolor="#E2E8F0", ticksuffix="%"),
                showlegend=False,
            )
            try:
                st.plotly_chart(fig3, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")

        col_dl, col_del = st.columns([2, 1], gap="medium")
        with col_dl:
            st.download_button(
                "⬇️  Export Historical Data (CSV)",
                data=yoy_df.to_csv(index=False).encode(),
                file_name="carbonlens_historical_trend.csv", mime="text/csv",
                use_container_width=True,
            )
        with col_del:
            del_year = st.selectbox("Hapus tahun:", years, key="hist_del_select", label_visibility="collapsed")
            if st.button(f"🗑️  Hapus {del_year}", use_container_width=True, key="hist_del_btn"):
                S.delete_historical_year(int(del_year))
                st.rerun()

    # ── Tab Intensitas ────────────────────────────────────────────────────────
    with tab_intensity:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;margin-bottom:14px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:2px;">Intensitas Emisi per Karyawan</div>
            <div style="font-size:11px;color:#CBD5E1;margin-bottom:14px;">tCO₂e / karyawan — ukuran efisiensi dekarbonisasi relatif</div>
        """, unsafe_allow_html=True)

        if hist_df["employees"].sum() > 0:
            hist_df["intensity_per_emp"] = hist_df.apply(
                lambda r: round(r["emission"] / r["employees"], 2) if r["employees"] > 0 else 0, axis=1
            )
            hist_df["intensity_per_energy"] = hist_df.apply(
                lambda r: round(r["emission"] / r["energy"] * 1000, 2) if r["energy"] > 0 else 0, axis=1
            )

            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=hist_df["Year"].tolist(), y=hist_df["intensity_per_emp"].tolist(),
                name="tCO₂e / karyawan",
                marker=dict(color="#6366F1", cornerradius=6),
                hovertemplate="<b>%{x}</b>: %{y:.2f} tCO₂e/karyawan<extra></extra>",
            ))
            fig4.update_layout(
                height=280, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=T["font_family"], color=T["font_color"]),
                xaxis=dict(showgrid=False, dtick=1),
                yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="tCO₂e / karyawan"),
                showlegend=False,
            )
            try:
                st.plotly_chart(fig4, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")
        else:
            st.info("Tambahkan data jumlah karyawan per tahun di Manual Entry untuk melihat intensitas emisi per karyawan.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Insights ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    insights = []
    if em_cagr is not None:
        if em_cagr < -0.042:
            insights.append({"icon": "✅", "type": "info",
                "text": f"CAGR emisi <strong>{em_cagr*100:.1f}%/tahun</strong> — lebih cepat dari trajektori SBTi 1.5°C (−4.2%/tahun). Pertahankan momentum ini."})
        elif em_cagr < -0.025:
            insights.append({"icon": "🟡", "type": "warn",
                "text": f"CAGR emisi <strong>{em_cagr*100:.1f}%/tahun</strong> — sesuai Paris 2°C tapi belum memenuhi SBTi 1.5°C. Percepat transisi energi terbarukan."})
        elif em_cagr < 0:
            insights.append({"icon": "⚠️", "type": "warn",
                "text": f"CAGR emisi <strong>{em_cagr*100:.1f}%/tahun</strong> — menurun tapi lebih lambat dari Paris 2°C (−2.5%/tahun). Perlu akselerasi signifikan."})
        else:
            insights.append({"icon": "🔴", "type": "alert",
                "text": f"Emisi <strong>meningkat</strong> dengan CAGR {em_cagr*100:+.1f}%/tahun. Tanpa intervensi, emisi 2030 akan mencapai "
                        f"<strong>{last_em * (1+em_cagr)**max(2030-last_year,1):,.0f} tCO₂e</strong>."})
    if sbti_gap > 0:
        annual_needed = sbti_gap / max(2030 - last_year, 1)
        insights.append({"icon": "🎯", "type": "warn",
            "text": f"Gap vs SBTi 1.5°C: <strong>{sbti_gap:+,.0f} tCO₂e</strong>. "
                    f"Untuk on-track ke 2030, perlu reduksi tambahan ~<strong>{annual_needed:,.0f} tCO₂e/tahun</strong>."})
    if len(years) < 3:
        insights.append({"icon": "📅", "type": "warn",
            "text": "Baru 2 tahun data — tambahkan minimal tahun ke-3 untuk estimasi CAGR dan SBTi trajectory yang lebih akurat."})

    if insights:
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Trajectory Insights</div>
        """, unsafe_allow_html=True)
        insight_panel(insights)
        st.markdown("</div>", unsafe_allow_html=True)
