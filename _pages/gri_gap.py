"""
CarbonLens V7 — GRI Gap Analysis
GRI 200 (Governance) + GRI 300 (Environmental) + GRI 400 (Social)
Full 3-series coverage with per-series breakdown, action roadmap, and export.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import utils.state as S
from utils.frameworks import run_gap_analysis, GRI_TOPIC_COLORS, GRI_SERIES_COLORS
from components.ui import page_header, kpi_card, insight_panel, empty_state
from config.settings import PLOTLY_THEME as T


def render():
    S.init()
    page_header(
        title="GRI Standards Gap Analysis",
        subtitle="GRI 200 Governance · GRI 300 Environmental · GRI 400 Social · GRI Standards 2021",
        badge="GRI Full Coverage", badge_type="green",
    )

    df = S.get("uploaded_df")
    if df is None:
        empty_state("📊", "No ESG Data Connected",
                    "Upload dataset di ESG Analytics terlebih dahulu — gap analysis akan cross-reference data Anda dengan seluruh GRI 200/300/400.",
                    "→ Ke ESG Analytics")
        if st.button("◈  Ke ESG Analytics", type="primary", key="gri_goto"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    results  = run_gap_analysis(S, df)
    covered  = [r for r in results if r["covered"]]
    missing  = [r for r in results if not r["covered"]]
    cov_pct  = round(len(covered) / len(results) * 100) if results else 0

    # Per-series stats
    series_stats = {}
    for s in ["GRI 200", "GRI 300", "GRI 400"]:
        sub   = [r for r in results if r["series"] == s]
        done  = [r for r in sub if r["covered"]]
        series_stats[s] = {
            "total": len(sub), "done": len(done),
            "pct": round(len(done)/len(sub)*100) if sub else 0,
            "color": GRI_SERIES_COLORS[s],
        }

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
    with k1: kpi_card("Total Coverage", f"{cov_pct}%", icon="📊", icon_bg="#ECFDF5",
                       badge="Strong" if cov_pct>=70 else "Developing" if cov_pct>=40 else "Early stage",
                       badge_type="green" if cov_pct>=70 else "yellow" if cov_pct>=40 else "red")
    with k2: kpi_card("GRI 200 Gov.", f"{series_stats['GRI 200']['pct']}%", icon="⚖️", icon_bg="#EEF2FF",
                       badge=f"{series_stats['GRI 200']['done']}/{series_stats['GRI 200']['total']}", badge_type="indigo")
    with k3: kpi_card("GRI 300 Env.", f"{series_stats['GRI 300']['pct']}%", icon="🌿", icon_bg="#ECFDF5",
                       badge=f"{series_stats['GRI 300']['done']}/{series_stats['GRI 300']['total']}", badge_type="green")
    with k4: kpi_card("GRI 400 Soc.", f"{series_stats['GRI 400']['pct']}%", icon="👥", icon_bg="#FDF2F8",
                       badge=f"{series_stats['GRI 400']['done']}/{series_stats['GRI 400']['total']}", badge_type="pink")
    with k5: kpi_card("Gaps to Close", str(len(missing)), icon="⚠️", icon_bg="#FFF1F2",
                       badge=f"of {len(results)} disclosures", badge_type="red" if len(missing)>8 else "yellow")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_ov, tab_200, tab_300, tab_400, tab_export = st.tabs([
        "📊 Overview",
        "⚖️ GRI 200 — Governance",
        "🌿 GRI 300 — Environmental",
        "👥 GRI 400 — Social",
        "⬇️ Export",
    ])

    def _series_tab(series_key: str, color: str):
        sub_results = [r for r in results if r["series"] == series_key]
        sub_covered = [r for r in sub_results if r["covered"]]
        sub_missing = [r for r in sub_results if not r["covered"]]
        sub_pct     = round(len(sub_covered)/len(sub_results)*100) if sub_results else 0

        # Progress bar
        st.markdown(f"""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px 20px;
             margin-bottom:14px;border-left:4px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:12px;font-weight:700;color:#1F2937;">{series_key} Coverage</div>
                <div style="font-size:18px;font-weight:800;color:{color};">{sub_pct}%</div>
            </div>
            <div style="height:8px;background:#F3F4F6;border-radius:4px;overflow:hidden;">
                <div style="width:{sub_pct}%;height:100%;background:{color};border-radius:4px;"></div>
            </div>
            <div style="font-size:11px;color:#94A3B8;margin-top:6px;">
                {len(sub_covered)} covered · {len(sub_missing)} gaps remaining
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Checklist
        for r in sub_results:
            is_done = r["covered"]
            icon    = "✅" if is_done else "○"
            bg      = "#F0FDF4" if is_done else "white"
            border  = "#6EE7B7" if is_done else "#E2E8F0"
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:12px;padding:10px 14px;
                 background:{bg};border:1px solid {border};border-radius:8px;margin-bottom:6px;">
                <span style="font-size:16px;margin-top:1px;">{icon}</span>
                <div style="flex:1;">
                    <div style="font-size:12px;font-weight:700;color:#1F2937;">{r['code']} — {r['title']}</div>
                    <div style="font-size:11px;color:#6B7280;margin-top:2px;">{r['desc']}</div>
                    <div style="font-size:10px;color:#94A3B8;margin-top:3px;">
                        {'✦ Data source: ' if is_done else '→ Fill via: '}{r['module']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if sub_missing:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            gaps_by_topic = {}
            for r in sub_missing:
                gaps_by_topic.setdefault(r["topic"], []).append(r)
            insight_list = []
            for topic, gaps in gaps_by_topic.items():
                insight_list.append({
                    "icon": "⚠️", "type": "warn",
                    "text": f"<strong>{topic}</strong> — {len(gaps)} disclosure(s) belum terpenuhi: "
                            + ", ".join(f"{g['code']}" for g in gaps)
                            + f". Lengkapi via: {gaps[0]['module']}."
                })
            insight_panel(insight_list)

    # ── Overview tab ─────────────────────────────────────────────────────────
    with tab_ov:
        col_chart, col_gaps = st.columns([1, 1.3], gap="medium")

        with col_chart:
            st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                padding:20px;border-top:3px solid #10B981;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                     color:#94A3B8;margin-bottom:14px;">Coverage by GRI Topic</div>
            """, unsafe_allow_html=True)

            topic_summary = {}
            for r in results:
                t = r["topic"]
                topic_summary.setdefault(t, {"total": 0, "covered": 0, "series": r["series"]})
                topic_summary[t]["total"]  += 1
                if r["covered"]:
                    topic_summary[t]["covered"] += 1

            topics_list = list(topic_summary.keys())
            pcts   = [topic_summary[t]["covered"] / topic_summary[t]["total"] * 100 for t in topics_list]
            colors = [GRI_TOPIC_COLORS.get(t, "#64748B") for t in topics_list]

            fig = go.Figure(go.Bar(
                x=pcts, y=topics_list, orientation="h",
                marker=dict(color=colors, cornerradius=5),
                text=[f"{p:.0f}%" for p in pcts], textposition="outside",
                textfont=dict(size=10, family=T["font_family"]),
                hovertemplate="<b>%{y}</b>: %{x:.0f}%<extra></extra>",
            ))
            fig.update_layout(
                height=max(320, len(topics_list) * 28),
                margin=dict(l=10, r=40, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=T["font_family"], color=T["font_color"]),
                xaxis=dict(range=[0, 120], showgrid=True, gridcolor="#E2E8F0", title="% Covered"),
                yaxis=dict(showgrid=False, tickfont=dict(size=10)),
            )
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart error: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_gaps:
            st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
                padding:20px;border-top:3px solid #F43F5E;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                     color:#94A3B8;margin-bottom:14px;">Priority Gaps to Close</div>
            """, unsafe_allow_html=True)

            if not missing:
                st.markdown("""
                <div style="text-align:center;padding:30px 10px;">
                    <div style="font-size:28px;margin-bottom:8px;">🎉</div>
                    <div style="font-size:13px;font-weight:700;">Full coverage achieved!</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:4px;">Semua GRI 200/300/400 terpenuhi.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Show top 8 gaps, prioritize mandatory-feeling ones
                for r in missing[:8]:
                    color = GRI_SERIES_COLORS.get(r["series"], "#64748B")
                    st.markdown(
                        f'<div style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #F8FAFC;">'
                        f'<div style="width:4px;background:{color};border-radius:2px;flex-shrink:0;"></div>'
                        f'<div>'
                        f'<div style="font-size:12px;font-weight:700;color:#0F172A;">{r["code"]} — {r["title"]}</div>'
                        f'<div style="font-size:10px;color:#94A3B8;">{r["series"]} · {r["module"]}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
                if len(missing) > 8:
                    st.caption(f"+ {len(missing)-8} lainnya — lihat tab per-series di atas")
            st.markdown("</div>", unsafe_allow_html=True)

        # Series comparison bar
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown("""<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;
            padding:20px;border-top:3px solid #6366F1;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:14px;">Coverage per GRI Series</div>
        """, unsafe_allow_html=True)
        for s, st_data in series_stats.items():
            pct = st_data["pct"]
            col = st_data["color"]
            st.markdown(f"""
            <div style="margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#1F2937;">{s}</div>
                    <div style="font-size:12px;font-weight:700;color:{col};">{pct}% · {st_data['done']}/{st_data['total']}</div>
                </div>
                <div style="height:8px;background:#F3F4F6;border-radius:4px;overflow:hidden;">
                    <div style="width:{pct}%;height:100%;background:{col};border-radius:4px;transition:width 0.3s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Insights
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        insights = []
        weakest = min(series_stats, key=lambda s: series_stats[s]["pct"])
        insights.append({"icon": "🎯", "type": "warn" if series_stats[weakest]["pct"] < 70 else "info",
            "text": f"Series paling lemah: <strong>{weakest}</strong> dengan coverage "
                    f"<strong>{series_stats[weakest]['pct']}%</strong>. "
                    f"Prioritaskan pengisian data untuk {weakest.split()[1]} indicators."})
        if any(r["code"] in ("GRI 305-5", "GRI 302-4") and not r["covered"] for r in results):
            insights.append({"icon": "📅", "type": "warn",
                "text": "GRI 305-5 dan 302-4 membutuhkan minimal 2 tahun data historis. "
                        "Tambahkan data tahun sebelumnya di <strong>Historical Tracker</strong>."})
        if any(r["code"] == "GRI 308-1" and not r["covered"] for r in results):
            insights.append({"icon": "🏭", "type": "info",
                "text": "GRI 308-1 (supplier environmental screening) bisa dipenuhi dengan menambahkan "
                        "minimal 1 supplier di <strong>Supplier ESG Scorecard</strong>."})
        insight_panel(insights)

    with tab_200:
        _series_tab("GRI 200", GRI_SERIES_COLORS["GRI 200"])

    with tab_300:
        _series_tab("GRI 300", GRI_SERIES_COLORS["GRI 300"])

    with tab_400:
        _series_tab("GRI 400", GRI_SERIES_COLORS["GRI 400"])

    # ── Export tab ────────────────────────────────────────────────────────────
    with tab_export:
        st.markdown("#### ⬇️ Export GRI Gap Analysis")

        table_df = pd.DataFrame([{
            "GRI Series":  r["series"],
            "Code":        r["code"],
            "Topic":       r["topic"],
            "Disclosure":  r["title"],
            "Description": r["desc"],
            "Status":      "✅ Covered" if r["covered"] else "⬜ Gap",
            "Data Source / Action": r["module"],
        } for r in results])

        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.download_button(
                "⬇️  Export Full GRI Checklist (CSV)",
                data=table_df.to_csv(index=False).encode(),
                file_name="carbonlens_gri_gap_analysis.csv", mime="text/csv",
                use_container_width=True,
            )
        with col_b:
            gaps_only = table_df[table_df["Status"] == "⬜ Gap"]
            st.download_button(
                "⬇️  Export Gaps Only (CSV)",
                data=gaps_only.to_csv(index=False).encode(),
                file_name="carbonlens_gri_gaps_only.csv", mime="text/csv",
                use_container_width=True,
            )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.dataframe(table_df, use_container_width=True, hide_index=True, height=400)
