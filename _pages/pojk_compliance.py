"""
CarbonLens V7 — POJK 51 / BRSR Compliance Module
- POJK No.51/POJK.03/2017 full 10-topic auto-mapping
- POJK 18/2023 Taksonomi Hijau Indonesia overlay
- Auto-populate from ESG Analytics + Carbon Accounting data
- Gap analysis with action items per topic
- Export: CSV checklist + progress report
"""

import streamlit as st
import pandas as pd
import utils.state as S
from components.ui import page_header, kpi_card, insight_panel, empty_state, divider
from config.settings import COLORS

POJK51_TOPICS = {
    "E1 — Konsumsi Energi": {
        "desc": "Total konsumsi energi, intensitas energi, dan porsi energi terbarukan",
        "gri": "GRI 302", "required": True,
        "inputs": ["total_energy_kwh", "renewable_energy_kwh", "energy_intensity_unit"],
        "auto_keys": ["total_energy_kwh"],
        "guidance": "Wajib untuk perusahaan sektor keuangan & emiten BEI. Sertakan energi dari semua sumber termasuk bahan bakar & listrik.",
        "action": "Laporkan total kWh per sumber energi, intensitas energi (kWh/revenue atau kWh/m²), dan porsi EBT.",
    },
    "E2 — Emisi GRK": {
        "desc": "Emisi Scope 1 & 2, intensitas emisi GRK per unit output",
        "gri": "GRI 305", "required": True,
        "inputs": ["scope1_tco2e", "scope2_tco2e", "emission_intensity"],
        "auto_keys": ["scope1_tco2e", "scope2_tco2e"],
        "guidance": "Referensi: Kepmen ESDM 18/2023 untuk faktor emisi PLN. Scope 3 dianjurkan meski belum wajib.",
        "action": "Gunakan modul Carbon Accounting untuk menghitung Scope 1/2/3 sesuai GHG Protocol.",
    },
    "E3 — Konsumsi Air": {
        "desc": "Total pengambilan air, konsumsi, dan daur ulang air",
        "gri": "GRI 303", "required": True,
        "inputs": ["water_m3", "water_recycled_pct"],
        "auto_keys": ["water_m3"],
        "guidance": "Pisahkan sumber air: air tanah, PDAM, air permukaan. Perhatikan konteks kelangkaan air di lokasi operasi.",
        "action": "Laporkan dalam m³/tahun. Sertakan persentase daur ulang bila tersedia.",
    },
    "E4 — Pengelolaan Limbah": {
        "desc": "Total limbah padat & B3, tingkat daur ulang, metode pembuangan",
        "gri": "GRI 306", "required": True,
        "inputs": ["waste_tonnes", "recycling_rate_pct", "hazardous_waste_tonnes"],
        "auto_keys": ["waste_tonnes"],
        "guidance": "Pisahkan limbah B3 dan non-B3. Referensi PP 22/2021 pengelolaan limbah B3.",
        "action": "Dokumentasikan manifest pengangkutan limbah B3 dan sertifikat pengolah berizin.",
    },
    "S1 — Data Ketenagakerjaan": {
        "desc": "Jumlah karyawan, rasio gender, tingkat turnover, status kepegawaian",
        "gri": "GRI 401", "required": True,
        "inputs": ["employees_total", "female_pct", "turnover_pct", "contract_pct"],
        "auto_keys": [],
        "guidance": "Pisahkan data berdasarkan gender dan level jabatan. Sesuai UU Ketenagakerjaan No.13/2003.",
        "action": "Isi data ketenagakerjaan di ESG Analytics → Social & Governance Data Inputs.",
    },
    "S2 — Pelatihan & Pengembangan": {
        "desc": "Rata-rata jam pelatihan per karyawan, jenis program, investasi SDM",
        "gri": "GRI 404", "required": True,
        "inputs": ["training_hours_avg", "training_budget_idr"],
        "auto_keys": [],
        "guidance": "Sertakan pelatihan ESG/sustainability. Dianjurkan min. 20 jam/karyawan/tahun.",
        "action": "Hitung rata-rata jam pelatihan = total jam pelatihan ÷ jumlah karyawan.",
    },
    "S3 — Keselamatan Kerja": {
        "desc": "Tingkat kecelakaan kerja, fatality rate, hari kerja hilang",
        "gri": "GRI 403", "required": True,
        "inputs": ["injury_rate", "fatalities", "lost_day_rate"],
        "auto_keys": [],
        "guidance": "Referensi: Permenaker No.5/2018 K3. Formula injury rate = (jml kecelakaan × 200.000) ÷ jam kerja total.",
        "action": "Dokumentasikan semua insiden K3 dan laporan ke Disnaker sesuai PP 50/2012.",
    },
    "G1 — Komposisi Dewan": {
        "desc": "Ukuran dewan, rasio independensi, keberagaman gender dewan",
        "gri": "GRI 405 / GRI 2-9", "required": True,
        "inputs": ["board_size", "independent_pct", "female_board_pct"],
        "auto_keys": [],
        "guidance": "OJK mensyaratkan min. 30% komisaris independen (POJK 33/2014). Dianjurkan min. 1 wanita di dewan.",
        "action": "Laporkan komposisi dewan per akhir tahun buku.",
    },
    "G2 — Anti-Korupsi & Etika": {
        "desc": "Pelatihan anti-korupsi, mekanisme whistleblower, insiden korupsi",
        "gri": "GRI 205", "required": True,
        "inputs": ["anticorrupt_training_pct", "corruption_incidents", "has_whistleblower"],
        "auto_keys": [],
        "guidance": "Referensi: UU No.31/1999 jo UU No.20/2001 Pemberantasan Korupsi. Wajib bagi BUMN & emiten.",
        "action": "Implementasikan program anti-korupsi dan laporkan mekanisme pelaporan pelanggaran.",
    },
    "G3 — Strategi Keberlanjutan": {
        "desc": "Kebijakan keberlanjutan, target emisi, integrasi ESG dalam strategi bisnis",
        "gri": "GRI 2-22 / GRI 2-23", "required": False,
        "inputs": [],
        "auto_keys": [],
        "guidance": "Dianjurkan namun belum wajib. Semakin relevan untuk akses green finance dan investor ESG.",
        "action": "Tetapkan target reduksi emisi berbasis sains (SBTi) dan sertakan dalam rapat umum pemegang saham.",
    },
}

TAKSONOMI_HIJAU = {
    "TH-E1 — Mitigasi Perubahan Iklim": {
        "desc": "Kegiatan yang berkontribusi pada pengurangan emisi GRK",
        "criteria": ["Memiliki target reduksi emisi terukur", "Menggunakan energi terbarukan ≥ 30%", "Intensitas emisi menurun YoY"],
        "color": "#10B981",
    },
    "TH-E2 — Adaptasi Perubahan Iklim": {
        "desc": "Kegiatan yang meningkatkan ketahanan terhadap risiko iklim",
        "criteria": ["Memiliki asesmen risiko iklim", "Implementasi sistem manajemen risiko iklim", "Rencana adaptasi terdokumentasi"],
        "color": "#06B6D4",
    },
    "TH-E3 — Ekonomi Sirkular": {
        "desc": "Pengelolaan sumber daya berkelanjutan dan minimasi limbah",
        "criteria": ["Tingkat daur ulang > 50%", "Program pengurangan limbah B3", "Laporan material flow terdokumentasi"],
        "color": "#8B5CF6",
    },
    "TH-S1 — Inklusivitas Sosial": {
        "desc": "Kontribusi pada pemberdayaan sosial dan pengurangan kesenjangan",
        "criteria": ["Program CSR terukur dengan dampak sosial", "Pengembangan UMKM lokal", "Pelatihan komunitas sekitar"],
        "color": "#F97316",
    },
}


def _compliance_score(responses: dict) -> dict:
    required = [t for t, v in POJK51_TOPICS.items() if v["required"]]
    answered = [t for t in required if responses.get(t, {}).get("completed")]
    optional = [t for t, v in POJK51_TOPICS.items() if not v["required"]]
    opt_done = [t for t in optional if responses.get(t, {}).get("completed")]
    score = len(answered) / len(required) * 100 if required else 0
    return {
        "score":    round(score),
        "answered": len(answered),
        "required": len(required),
        "optional_done": len(opt_done),
        "total":    len(POJK51_TOPICS),
        "grade":    "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D",
        "status":   "Compliant" if score >= 80 else "Partial" if score >= 50 else "Non-Compliant",
        "missing":  [t for t in required if t not in answered],
    }


def _auto_populate(df) -> dict:
    """Pull values from session state & uploaded df."""
    out = {}
    if df is not None and "Emission" in df.columns:
        from utils.state import get_scope_results
        _sc = get_scope_results()
        out["scope1_tco2e"]    = round(_sc["scope1_kg"] / 1000, 2)
        out["scope2_tco2e"]    = round(_sc["scope2_kg"] / 1000, 2)
        out["total_energy_kwh"]= round(float(df["Energy"].sum()) if "Energy" in df.columns else df["Emission"].sum() * 14.2, 0)
        out["water_m3"]        = round(float(df["Water"].sum()) if "Water" in df.columns else 0, 0)
        out["waste_tonnes"]    = round(float(df["Waste"].sum()) if "Waste" in df.columns else 0, 2)
    out["employees_total"]         = S.get("employees", 0) or 0
    out["female_pct"]              = S.get("women_workforce_pct") or 0
    out["turnover_pct"]            = S.get("employee_turnover_pct") or 0
    out["training_hours_avg"]      = S.get("training_hours_per_employee") or 0
    out["injury_rate"]             = S.get("injury_rate") or 0
    out["board_size"]              = S.get("board_size", 0) or 0
    out["independent_pct"]         = S.get("board_independence_pct") or 0
    out["female_board_pct"]        = S.get("women_board_pct") or 0
    out["anticorrupt_training_pct"]= S.get("anti_corruption_training_pct") or 0
    out["recycling_rate_pct"]      = S.get("recycle_pct", 0) or 0
    out["renewable_energy_kwh"]    = (out.get("total_energy_kwh", 0) or 0) * (S.get("renew_pct", 0) or 0) / 100
    return out


def render():
    S.init()
    page_header(
        title="POJK 51 / Taksonomi Hijau Compliance",
        subtitle="OJK POJK No.51/2017 · Taksonomi Hijau Indonesia · GRI-aligned disclosure tracker",
        badge="Regulatori", badge_type="indigo",
    )

    df = S.get("uploaded_df")
    has_data = df is not None

    if not has_data:
        empty_state("📋", "Belum Ada Data ESG",
                    "Upload dataset ESG di ESG Analytics terlebih dahulu — data emisi, energi, air, dan limbah akan otomatis mengisi checklist POJK 51.",
                    "→ Ke ESG Analytics")
        if st.button("◈  Ke ESG Analytics", type="primary", key="pojk_goto"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    # Init state
    if "pojk_responses" not in st.session_state:
        st.session_state["pojk_responses"] = {}
    if "taksonomi_responses" not in st.session_state:
        st.session_state["taksonomi_responses"] = {}
    responses = st.session_state["pojk_responses"]
    tak_resp  = st.session_state["taksonomi_responses"]

    auto = _auto_populate(df)
    comp = _compliance_score(responses)

    # ── KPI Row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    status_type = "green" if comp["score"] >= 80 else "yellow" if comp["score"] >= 50 else "red"
    with k1: kpi_card("Compliance Score", f"{comp['score']}%", icon="📊", icon_bg="#E0F2FE",
                       badge=comp["status"], badge_type=status_type)
    with k2: kpi_card("POJK 51 Grade", comp["grade"], icon="🏷️", icon_bg="#EEF2FF",
                       badge=f"{comp['answered']}/{comp['required']} topik wajib", badge_type="slate")
    with k3: kpi_card("Topik Optional", f"{comp['optional_done']}/1", icon="⚪", icon_bg="#F9FAFB",
                       badge="bonus disclosure", badge_type="slate")
    with k4:
        tak_done = sum(1 for k, v in tak_resp.items() if v.get("eligible"))
        kpi_card("Taksonomi Hijau", f"{tak_done}/{len(TAKSONOMI_HIJAU)}", icon="🌿", icon_bg="#ECFDF5",
                  badge="aktivitas eligible", badge_type="green" if tak_done > 0 else "slate")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 POJK 51 Checklist",
        "🌿 Taksonomi Hijau Indonesia",
        "📊 Gap Analysis",
        "⬇️ Export",
    ])

    # ── Tab 1: POJK 51 ────────────────────────────────────────────────────────
    with tab1:
        st.markdown("""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
             padding:12px 16px;font-size:12px;color:#1E40AF;margin-bottom:16px;">
            <strong>POJK No.51/POJK.03/2017</strong> — OJK mewajibkan lembaga jasa keuangan
            dan emiten BEI untuk menyampaikan laporan keberlanjutan tahunan. Data emisi, energi,
            air, dan limbah dari ESG Analytics <strong>otomatis terisi</strong> di bawah ini.
            Tandai setiap topik sebagai "telah diungkapkan" untuk tracking kesiapan compliance.
        </div>
        """, unsafe_allow_html=True)

        for topic, meta in POJK51_TOPICS.items():
            req_badge = "🔴 Wajib" if meta["required"] else "⚪ Dianjurkan"
            is_done   = responses.get(topic, {}).get("completed", False)
            status_icon = "✅" if is_done else "○"
            border_color = "#10B981" if is_done else "#E2E8F0"

            with st.expander(f"{status_icon}  {topic}  ·  {req_badge}  ·  {meta['gri']}", expanded=False):
                st.markdown(f"""
                <div style="font-size:12px;color:#475569;margin-bottom:8px;">{meta['desc']}</div>
                <div style="background:#F8FAFC;border-left:3px solid #6366F1;padding:8px 12px;
                     border-radius:0 6px 6px 0;font-size:11px;color:#475569;margin-bottom:12px;">
                    <strong>Panduan:</strong> {meta['guidance']}
                </div>
                <div style="background:#FFF7ED;border-left:3px solid #F97316;padding:8px 12px;
                     border-radius:0 6px 6px 0;font-size:11px;color:#92400E;margin-bottom:12px;">
                    <strong>Action:</strong> {meta['action']}
                </div>
                """, unsafe_allow_html=True)

                if meta["inputs"]:
                    col_l, col_r = st.columns(2, gap="medium")
                    values = {}
                    for i, inp in enumerate(meta["inputs"]):
                        auto_val = auto.get(inp, 0.0)
                        label    = inp.replace("_", " ").title()
                        is_auto  = inp in meta.get("auto_keys", []) and auto_val > 0
                        label_suffix = " ✦ auto" if is_auto else ""
                        with (col_l if i % 2 == 0 else col_r):
                            values[inp] = st.number_input(
                                f"{label}{label_suffix}", value=float(auto_val),
                                key=f"pojk_{topic}_{inp}", min_value=0.0,
                                help="Nilai otomatis dari data ESG Analytics" if is_auto else None,
                            )
                else:
                    values = {}
                    st.caption("Topik ini bersifat kualitatif — centang bila kebijakan/dokumen sudah tersedia.")

                col_check, col_note = st.columns([1, 2])
                with col_check:
                    done = st.checkbox("✅ Tandai sudah diungkapkan", value=is_done, key=f"pojk_done_{topic}")
                with col_note:
                    note = st.text_input("Referensi pengungkapan / catatan",
                                         value=responses.get(topic, {}).get("note", ""),
                                         key=f"pojk_note_{topic}",
                                         placeholder="mis: Laporan Keberlanjutan 2024, hal. 45")
                responses[topic] = {"completed": done, "note": note, "values": values}

        st.session_state["pojk_responses"] = responses

    # ── Tab 2: Taksonomi Hijau ────────────────────────────────────────────────
    with tab2:
        st.markdown("""
        <div style="background:#ECFDF5;border:1px solid #6EE7B7;border-radius:10px;
             padding:12px 16px;font-size:12px;color:#064E3B;margin-bottom:16px;">
            <strong>Taksonomi Hijau Indonesia (OJK, 2022)</strong> — Kerangka klasifikasi
            kegiatan ekonomi yang dianggap ramah lingkungan. Eligibilitas taksonomi hijau
            membuka akses ke <strong>green bond, sustainability-linked loan</strong>, dan
            insentif fiskal dari pemerintah. Centang kriteria yang telah dipenuhi organisasi Anda.
        </div>
        """, unsafe_allow_html=True)

        for th_key, th_meta in TAKSONOMI_HIJAU.items():
            is_eligible = tak_resp.get(th_key, {}).get("eligible", False)
            icon = "🟢" if is_eligible else "○"
            with st.expander(f"{icon}  {th_key}", expanded=False):
                st.markdown(f"""
                <div style="font-size:12px;color:#475569;margin-bottom:12px;">{th_meta['desc']}</div>
                <div style="font-size:11px;font-weight:700;color:#374151;margin-bottom:8px;">Kriteria Eligibilitas:</div>
                """, unsafe_allow_html=True)

                criteria_results = {}
                for c in th_meta["criteria"]:
                    checked = st.checkbox(c, value=tak_resp.get(th_key, {}).get(c, False),
                                          key=f"tak_{th_key}_{c}")
                    criteria_results[c] = checked

                all_met = all(criteria_results.values())
                tak_resp.setdefault(th_key, {}).update(criteria_results)
                tak_resp[th_key]["eligible"] = all_met

                if all_met:
                    st.success(f"✅ Aktivitas ini **eligible** untuk Taksonomi Hijau — dapat dilaporkan sebagai green activity.")
                else:
                    met = sum(criteria_results.values())
                    st.info(f"⚪ {met}/{len(th_meta['criteria'])} kriteria terpenuhi. Penuhi semua kriteria untuk mendapat status eligible.")

        st.session_state["taksonomi_responses"] = tak_resp

    # ── Tab 3: Gap Analysis ──────────────────────────────────────────────────
    with tab3:
        st.markdown("""
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
             color:#94A3B8;margin-bottom:16px;">Gap Analysis — Topik Belum Diungkapkan</div>
        """, unsafe_allow_html=True)

        if comp["missing"]:
            st.markdown("""
            <div style="background:#FFF1F2;border:1px solid #FECDD3;border-radius:10px;
                 padding:12px 16px;font-size:12px;color:#9F1239;margin-bottom:16px;">
                ⚠️ Topik wajib berikut belum ditandai sebagai diungkapkan. Lengkapi sebelum batas
                pelaporan POJK 51 (biasanya 30 April untuk laporan tahun fiskal sebelumnya).
            </div>
            """, unsafe_allow_html=True)
            for missing_topic in comp["missing"]:
                meta = POJK51_TOPICS[missing_topic]
                st.markdown(f"""
                <div style="display:flex;align-items:flex-start;gap:12px;padding:10px 14px;
                     background:white;border:1px solid #FCA5A5;border-radius:8px;margin-bottom:8px;
                     border-left:4px solid #EF4444;">
                    <div style="font-size:18px;margin-top:2px;">○</div>
                    <div>
                        <div style="font-size:13px;font-weight:700;color:#1F2937;">{missing_topic}</div>
                        <div style="font-size:11px;color:#6B7280;margin-top:2px;">{meta['gri']} · {meta['desc']}</div>
                        <div style="font-size:11px;color:#DC2626;margin-top:4px;font-weight:600;">
                            Action: {meta['action']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Semua topik wajib POJK 51 sudah diungkapkan! Siap untuk pelaporan regulatori.")

        # Progress bar visual
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:20px;
             border-top:3px solid #6366F1;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
                 color:#94A3B8;margin-bottom:16px;">Progress Pengungkapan POJK 51</div>
        """, unsafe_allow_html=True)

        for topic, meta in POJK51_TOPICS.items():
            is_done = responses.get(topic, {}).get("completed", False)
            color   = "#10B981" if is_done else ("#FCA5A5" if meta["required"] else "#E2E8F0")
            icon    = "✅" if is_done else ("○" if meta["required"] else "–")
            req_dot = " ●" if meta["required"] else ""
            note    = responses.get(topic, {}).get("note", "")
            note_html = f'<span style="color:#9CA3AF;font-size:10px;"> · {note}</span>' if note else ""
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;'
                f'border-bottom:1px solid #F8FAFC;">'
                f'<span style="font-size:13px;">{icon}</span>'
                f'<div style="flex:1;font-size:12px;color:#374151;">{topic}{req_dot}{note_html}</div>'
                f'<span style="font-size:10px;color:#94A3B8;white-space:nowrap;">{meta["gri"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # Insights panel
        insights = []
        if comp["score"] < 80:
            insights.append({"icon": "⚠️", "type": "alert",
                "text": f"Compliance score <strong>{comp['score']}%</strong> — belum memenuhi threshold 80% untuk status <em>Compliant</em>. "
                        f"Lengkapi <strong>{comp['required'] - comp['answered']} topik wajib</strong> yang tersisa."})
        if comp["score"] >= 80:
            insights.append({"icon": "✅", "type": "info",
                "text": f"Compliance score <strong>{comp['score']}%</strong> — memenuhi threshold POJK 51. "
                        f"Pertimbangkan untuk menambahkan topik optional (G3) untuk meningkatkan grade ke A."})
        tak_eligible = sum(1 for v in tak_resp.values() if v.get("eligible"))
        if tak_eligible > 0:
            insights.append({"icon": "🌿", "type": "info",
                "text": f"<strong>{tak_eligible} aktivitas eligible</strong> untuk Taksonomi Hijau Indonesia — "
                        f"dapat dimanfaatkan untuk akses green bond dan sustainability-linked financing dengan bunga lebih rendah."})
        if insights:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            insight_panel(insights)

    # ── Tab 4: Export ─────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### ⬇️ Export Compliance Report")

        rows = []
        for topic, meta in POJK51_TOPICS.items():
            resp = responses.get(topic, {})
            rows.append({
                "Topik":       topic,
                "GRI":         meta["gri"],
                "Wajib/Optional": "Wajib" if meta["required"] else "Optional",
                "Status":      "Diungkapkan" if resp.get("completed") else "Belum Diungkapkan",
                "Referensi":   resp.get("note", ""),
                "Panduan":     meta["action"],
            })
        checklist_df = pd.DataFrame(rows)

        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.download_button(
                "⬇️  Export Checklist POJK 51 (CSV)",
                data=checklist_df.to_csv(index=False).encode(),
                file_name="carbonlens_pojk51_checklist.csv",
                mime="text/csv", use_container_width=True,
            )
        with col_b:
            summary = {
                "Compliance Score (%)": comp["score"],
                "Grade": comp["grade"],
                "Status": comp["status"],
                "Topik Wajib Diungkapkan": comp["answered"],
                "Total Topik Wajib": comp["required"],
                "Aktivitas Taksonomi Hijau Eligible": sum(1 for v in tak_resp.values() if v.get("eligible")),
            }
            summary_df = pd.DataFrame([summary])
            st.download_button(
                "⬇️  Export Summary Report (CSV)",
                data=summary_df.to_csv(index=False).encode(),
                file_name="carbonlens_pojk51_summary.csv",
                mime="text/csv", use_container_width=True,
            )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:16px 20px;
             font-size:12px;color:#475569;">
            <strong>Catatan regulasi:</strong> POJK No.51/POJK.03/2017 berlaku untuk lembaga jasa keuangan
            dan emiten BEI. Batas pelaporan umumnya 30 April untuk laporan tahun fiskal sebelumnya.
            Taksonomi Hijau Indonesia diterbitkan OJK tahun 2022 dan terus diperbarui.
            Konsultasikan dengan auditor ESG untuk verifikasi pihak ketiga.
        </div>
        """, unsafe_allow_html=True)
