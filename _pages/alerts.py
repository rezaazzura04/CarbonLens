"""
CarbonLens V7 — Smart Alert & Notification Center
Scheduled monitoring, anomaly detection, threshold alerts.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import utils.state as S
from components.ui import page_header, kpi_card, empty_state, divider

ALERT_TYPES = {
    "emission_spike":   {"label": "Emission Spike",        "icon": "🔴", "color": "#F43F5E"},
    "benchmark_breach": {"label": "Benchmark Breach",      "icon": "🟠", "color": "#F97316"},
    "data_gap":         {"label": "Data Gap Detected",     "icon": "🟡", "color": "#F59E0B"},
    "target_at_risk":   {"label": "Target At Risk",        "icon": "🔵", "color": "#0EA5E9"},
    "yoy_regression":   {"label": "YoY Regression",        "icon": "📉", "color": "#8B5CF6"},
    "data_quality":     {"label": "Data Quality Issue",    "icon": "⚠️", "color": "#64748B"},
}


def _detect_alerts(df: pd.DataFrame, sector: str, prev_df: pd.DataFrame = None) -> list:
    """Run all alert checks against uploaded data. Returns list of alert dicts."""
    alerts = []
    if df is None or "Emission" not in df.columns:
        return alerts

    em   = df["Emission"]
    mean = em.mean()
    std  = em.std() if len(em) > 2 else 0
    from utils.calculations import get_benchmark
    bench = get_benchmark(sector)

    # 1. Emission spike — any month >30% above average
    for idx, row in df.iterrows():
        if row["Emission"] > mean * 1.30:
            month = row.get("Month", f"Row {idx}")
            pct   = (row["Emission"] - mean) / mean * 100
            alerts.append({
                "type":     "emission_spike",
                "severity": "high" if pct > 50 else "medium",
                "title":    f"Emission spike in {month}",
                "detail":   f"{row['Emission']:,.0f} tCO₂e — {pct:+.0f}% above monthly average ({mean:,.0f}).",
                "action":   "Investigate operational activity during this period.",
                "ts":       datetime.now().isoformat(),
            })

    # 2. Benchmark breach — average intensity vs sector
    area   = float(S.get("area_m2", 5000))
    intens = mean / area * 100 if area > 0 else 0
    if intens > bench * 1.1:
        gap = (intens - bench) / bench * 100
        alerts.append({
            "type":     "benchmark_breach",
            "severity": "high" if gap > 30 else "medium",
            "title":    f"Above {sector} benchmark by {gap:.0f}%",
            "detail":   f"Current intensity {intens:.1f} kg CO₂e/m² vs benchmark {bench} kg CO₂e/m².",
            "action":   "Review Carbon Accounting for reduction opportunities.",
            "ts":       datetime.now().isoformat(),
        })

    # 3. Data gaps — missing months in sequence
    if "Month" in df.columns:
        expected = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        present  = set(df["Month"].tolist())
        missing  = [m for m in expected if m not in present]
        if missing:
            alerts.append({
                "type":     "data_gap",
                "severity": "low",
                "title":    f"Missing data for {len(missing)} month(s)",
                "detail":   f"No records found for: {', '.join(missing[:6])}{'...' if len(missing)>6 else ''}.",
                "action":   "Upload complete dataset or verify data collection for missing periods.",
                "ts":       datetime.now().isoformat(),
            })

    # 4. YoY regression
    if prev_df is not None and "Emission" in prev_df.columns:
        curr_total = float(em.sum())
        prev_total = float(prev_df["Emission"].sum())
        if curr_total > prev_total * 1.05:
            reg = (curr_total - prev_total) / prev_total * 100
            alerts.append({
                "type":     "yoy_regression",
                "severity": "high" if reg > 15 else "medium",
                "title":    f"Emissions increased {reg:.0f}% year-over-year",
                "detail":   f"Current: {curr_total:,.0f} tCO₂e vs previous year: {prev_total:,.0f} tCO₂e.",
                "action":   "Review decarbonization plan and accelerate interventions.",
                "ts":       datetime.now().isoformat(),
            })

    # 5. Data quality — negative values or extreme outliers
    neg = (em < 0).sum()
    if neg > 0:
        alerts.append({
            "type":     "data_quality",
            "severity": "high",
            "title":    f"{neg} negative emission value(s) detected",
            "detail":   "Negative emissions are physically impossible. Check data entry.",
            "action":   "Correct data at source and re-upload.",
            "ts":       datetime.now().isoformat(),
        })

    z_scores = np.abs((em - mean) / std) if std > 0 else pd.Series([0]*len(em))
    extreme  = (z_scores > 3).sum()
    if extreme > 0:
        alerts.append({
            "type":     "data_quality",
            "severity": "medium",
            "title":    f"{extreme} extreme outlier(s) detected (>3σ)",
            "detail":   "Values more than 3 standard deviations from mean may indicate data errors.",
            "action":   "Verify outlier months against source records.",
            "ts":       datetime.now().isoformat(),
        })

    # 6. Social indicator alerts (GRI 400-series) — when columns present in df
    now = datetime.now().isoformat()

    if "Injury_Rate" in df.columns:
        inj = float(df["Injury_Rate"].mean())
        if inj > 5.0:
            alerts.append({"type":"data_quality","severity":"high",
                "title":f"High injury rate — {inj:.1f} per 200k hrs (GRI 403-9)",
                "detail":f"Current injury rate {inj:.1f} significantly exceeds the 3.0 industry reference threshold.",
                "action":"Review safety programs and investigate root causes. Consider ISO 45001 implementation.",
                "ts": now})
        elif inj > 3.0:
            alerts.append({"type":"benchmark_breach","severity":"medium",
                "title":f"Injury rate above benchmark — {inj:.1f} per 200k hrs",
                "detail":f"Injury rate {inj:.1f} is above the 3.0 reference level. Industry leaders target <1.0.",
                "action":"Review workplace safety protocols and training effectiveness.",
                "ts": now})

    if "Employee_Turnover_pct" in df.columns:
        turn = float(df["Employee_Turnover_pct"].mean())
        if turn > 25.0:
            alerts.append({"type":"benchmark_breach","severity":"high",
                "title":f"Critical employee turnover — {turn:.1f}% (GRI 401-1)",
                "detail":f"Turnover rate {turn:.1f}% is above 25% — indicates significant workforce instability.",
                "action":"Investigate retention issues: compensation, management, working conditions. Benchmark against sector.",
                "ts": now})
        elif turn > 15.0:
            alerts.append({"type":"benchmark_breach","severity":"medium",
                "title":f"Elevated employee turnover — {turn:.1f}%",
                "detail":f"Turnover {turn:.1f}% above typical 10–15% range for Indonesian manufacturing sector.",
                "action":"Consider employee engagement survey and retention programs.",
                "ts": now})

    if "Training_Hours_Per_Employee" in df.columns:
        hrs = float(df["Training_Hours_Per_Employee"].mean())
        if hrs < 8.0:
            alerts.append({"type":"benchmark_breach","severity":"medium",
                "title":f"Low training investment — {hrs:.0f} hrs/employee (GRI 404-1)",
                "detail":f"Only {hrs:.0f} hours training per employee. GRI 404 best practice is ≥20 hrs/year.",
                "action":"Expand training programs. Low training correlates with higher turnover and safety incidents.",
                "ts": now})

    if "Women_Workforce_pct" in df.columns:
        wwf = float(df["Women_Workforce_pct"].mean())
        if wwf < 20.0:
            alerts.append({"type":"benchmark_breach","severity":"low",
                "title":f"Low gender diversity in workforce — {wwf:.1f}% women (GRI 405-1)",
                "detail":f"Women represent {wwf:.1f}% of workforce. MSCI ESG best practice targets ≥30%.",
                "action":"Review recruitment practices and diversity inclusion programs.",
                "ts": now})

    # 7. Governance alerts (GRI 2 / SASB)
    if "Board_Independence_pct" in df.columns:
        bi = float(df["Board_Independence_pct"].mean())
        if bi < 30.0:
            alerts.append({"type":"benchmark_breach","severity":"high",
                "title":f"Board independence below minimum — {bi:.1f}% (GRI 2-9/2-10)",
                "detail":f"Board independence {bi:.1f}% is below the 33% minimum recommended by OJK governance guidelines.",
                "action":"Review board composition. POJK 33/2014 recommends minimum 1/3 independent commissioners.",
                "ts": now})

    if "Anti_Corruption_Training_pct" in df.columns:
        act = float(df["Anti_Corruption_Training_pct"].mean())
        if act < 50.0:
            alerts.append({"type":"benchmark_breach","severity":"medium",
                "title":f"Low anti-corruption training coverage — {act:.1f}% (GRI 205-2)",
                "detail":f"Only {act:.1f}% of employees have received anti-corruption training. GRI 205-2 recommends 100%.",
                "action":"Expand anti-corruption training to all employees, especially customer-facing roles.",
                "ts": now})

    return alerts


def render():
    page_header(
        title="Alert Center",
        subtitle="Smart anomaly detection · Threshold monitoring · Emission spike alerts",
        badge="Live Monitoring", badge_type="sky",
    )

    df      = S.get("uploaded_df")
    prev_df = S.get("prev_year_df")
    sector  = S.get("sector", "Manufacturing")

    if df is None:
        empty_state("🔔", "No Data to Monitor",
                    "Upload your ESG dataset in ESG Analytics to enable smart alert monitoring.",
                    "→ Go to ESG Analytics")
        if st.button("◈  Go to ESG Analytics", type="primary", key="alerts_goto"):
            st.session_state.active_page = "esg_analytics"
            st.rerun()
        return

    # ── Alert config ───────────────────────────────────────────────────────────
    with st.expander("⚙️ Alert Thresholds", expanded=False):
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            spike_pct = st.slider("Emission spike threshold (%)", 10, 100, 30,
                                   key="alert_spike", help="Alert when month exceeds avg by this %")
        with c2:
            bench_pct = st.slider("Benchmark breach threshold (%)", 5, 50, 10,
                                   key="alert_bench", help="Alert when intensity exceeds benchmark by this %")
        with c3:
            enable_email = st.toggle("Email notifications", value=False, key="alert_email",
                                      help="Coming soon — connect SMTP in config")

    # ── Run detection ──────────────────────────────────────────────────────────
    alerts = _detect_alerts(df, sector, prev_df)

    # ── Summary KPIs ───────────────────────────────────────────────────────────
    high_alerts   = [a for a in alerts if a["severity"] == "high"]
    medium_alerts = [a for a in alerts if a["severity"] == "medium"]
    low_alerts    = [a for a in alerts if a["severity"] == "low"]

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1: kpi_card("Total Alerts",   str(len(alerts)),        icon="🔔", icon_bg="#E0F2FE")
    with k2: kpi_card("High Priority",  str(len(high_alerts)),   icon="🔴", icon_bg="#FFE4E6",
                       badge="Immediate action" if high_alerts else "None", badge_type="red" if high_alerts else "green")
    with k3: kpi_card("Medium",         str(len(medium_alerts)), icon="🟠", icon_bg="#FFF7ED")
    with k4: kpi_card("Low / Info",     str(len(low_alerts)),    icon="🟡", icon_bg="#FEF9C3")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if not alerts:
        st.markdown("""
        <div style="text-align:center;padding:40px 24px;background:#F0FDF4;border-radius:14px;
             border:1.5px solid #BBF7D0;">
            <div style="font-size:32px;margin-bottom:10px;">✅</div>
            <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:6px;">
                No alerts detected</div>
            <div style="font-size:13px;color:#64748B;">
                Your data is within normal parameters. Keep monitoring regularly.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Alert list ─────────────────────────────────────────────────────────────
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts_sorted  = sorted(alerts, key=lambda x: severity_order.get(x["severity"], 3))

    sev_colors = {"high": "#F43F5E", "medium": "#F97316", "low": "#F59E0B"}
    sev_bg     = {"high": "#FFF1F2", "medium": "#FFF7ED", "low": "#FFFBEB"}

    for alert in alerts_sorted:
        a_info = ALERT_TYPES.get(alert["type"], {"icon":"⚠️","color":"#64748B"})
        color  = sev_colors.get(alert["severity"], "#64748B")
        bg     = sev_bg.get(alert["severity"], "#F8FAFC")

        st.markdown(f"""
        <div style="background:{bg};border:1px solid {color}40;border-left:4px solid {color};
             border-radius:10px;padding:14px 16px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:16px;">{a_info['icon']}</span>
                    <span style="font-size:13px;font-weight:700;color:#0F172A;">{alert['title']}</span>
                </div>
                <span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;
                      background:{color}20;color:{color};">{alert['severity'].upper()}</span>
            </div>
            <div style="font-size:12px;color:#475569;margin-bottom:6px;">{alert['detail']}</div>
            <div style="font-size:11px;color:#0EA5E9;font-weight:600;">→ {alert['action']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Export alerts ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    col_dl, _ = st.columns([1, 3])
    with col_dl:
        alerts_df = pd.DataFrame([{
            "Severity": a["severity"].upper(),
            "Type":     ALERT_TYPES.get(a["type"],{}).get("label", a["type"]),
            "Title":    a["title"],
            "Detail":   a["detail"],
            "Action":   a["action"],
            "Detected": a["ts"][:10],
        } for a in alerts_sorted])
        st.download_button(
            "⬇️  Export Alerts CSV",
            data=alerts_df.to_csv(index=False).encode(),
            file_name="carbonlens_alerts.csv",
            mime="text/csv",
            use_container_width=True,
        )
