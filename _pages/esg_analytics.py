"""
CarbonLens V7 — ESG Analytics
Core intelligence engine · Data upload hub · ESG scoring · Executive insights
"""

import streamlit as st
import pandas as pd
import utils.state as S
import numpy as np
from components.ui import page_header, kpi_card, insight_panel, divider
from utils.charts import emission_bar, correlation_scatter, emission_trend
from utils.calculations import dataset_overview, detect_outliers, generate_demo_data, calculate_esg_score, get_benchmark
from config.settings import COLORS, INDUSTRY_BENCHMARKS


def _esg_score_from_df(df, sector="Manufacturing", force=True):
    """Compute canonical ESG (single source of truth across the platform)."""
    from utils.state import compute_canonical_esg
    # Store completeness from the active dataset so canonical compute uses it
    ov = dataset_overview(df)
    S.set("completeness", ov.get("completeness", 94))

    # If the uploaded CSV provides E-pillar time-series columns, use the most
    # recent row's values to refine the canonical ESG inputs (overrides
    # onboarding defaults with actual reported data).
    if force and len(df) > 0:
        latest = df.iloc[-1]
        if "Renewable_pct" in df.columns and pd.notna(latest.get("Renewable_pct")):
            S.set("renew_pct", float(latest["Renewable_pct"]))
        if "Water_Withdrawal" in df.columns and "Water_Recycled" in df.columns:
            w_with = float(latest.get("Water_Withdrawal", 0) or 0)
            w_rec  = float(latest.get("Water_Recycled", 0) or 0)
            if w_with > 0:
                S.set("water_recycled_pct", round(w_rec / w_with * 100, 1))
        if "Waste_Generated" in df.columns and "Waste_Recycled" in df.columns:
            wa_gen = float(latest.get("Waste_Generated", 0) or 0)
            wa_rec = float(latest.get("Waste_Recycled", 0) or 0)
            if wa_gen > 0:
                S.set("recycle_pct", round(wa_rec / wa_gen * 100, 1))

    return compute_canonical_esg(force=force)


# ─────────────────────────────────────────────────────────────────────────────
# CSV VALIDATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_COLS   = ["Emission"]
OPTIONAL_COLS   = ["Month", "Year", "Energy", "Water", "Waste", "Company", "Facility",
                   "Scope1_tCO2e", "Scope2_tCO2e", "Renewable_pct",
                   "Water_Withdrawal", "Water_Recycled",
                   "Waste_Generated", "Waste_Recycled",
                   # GRI Social indicators (optional, organization-level — repeat per row or fill once)
                   "Employee_Turnover_pct", "Training_Hours_Per_Employee",
                   "Women_Workforce_pct", "Women_Management_pct", "Injury_Rate",
                   # GRI Governance indicators (optional)
                   "Board_Independence_pct", "Women_Board_pct",
                   "Anti_Corruption_Training_pct"]
NUMERIC_COLS    = ["Emission", "Energy", "Water", "Waste",
                   "Scope1_tCO2e", "Scope2_tCO2e", "Renewable_pct",
                   "Water_Withdrawal", "Water_Recycled",
                   "Waste_Generated", "Waste_Recycled",
                   "Employee_Turnover_pct", "Training_Hours_Per_Employee",
                   "Women_Workforce_pct", "Women_Management_pct", "Injury_Rate",
                   "Board_Independence_pct", "Women_Board_pct",
                   "Anti_Corruption_Training_pct", "Year"]
MIN_ROWS        = 3
MAX_ROWS        = 1200
SPIKE_THRESHOLD = 3.0     # Z-score above this → spike alert
NEGATIVE_CHECK  = True


# ── Unit detection thresholds ────────────────────────────────────────────────
# If median Emission value is in these ranges, it's likely a different unit.
# tCO₂e typical monthly range for orgs: 10–50,000
# kg CO₂e: values 1000× higher  →  divide by 1000
# MT CO₂e: values 1000× lower   →  multiply by 1000

def _detect_emission_unit(series: pd.Series) -> tuple[str, float]:
    """
    Detect likely unit of Emission column.
    Returns (unit_label, conversion_factor_to_tco2e).
    """
    median = series.dropna().median()
    if median <= 0:
        return "tCO₂e", 1.0
    if median > 500_000:
        # Almost certainly kg CO₂e — convert to tCO₂e by dividing 1000
        return "kg CO₂e", 0.001
    if median > 50_000:
        # Likely kg CO₂e for a large facility
        return "kg CO₂e (suspected)", 0.001
    if median < 0.05:
        # Almost certainly MT CO₂e (megatonnes) — multiply by 1_000_000
        return "MT CO₂e", 1_000_000.0
    if median < 1.0:
        # Likely MT CO₂e (heavy industry reporting in megatonnes)
        return "MT CO₂e (suspected)", 1_000_000.0
    # Normal range: tCO₂e
    return "tCO₂e", 1.0


# ── Month normalizer ──────────────────────────────────────────────────────────

_MONTH_MAP = {
    # English short & long
    "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "aug": "Aug",
    "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
    "january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
    "june": "Jun", "july": "Jul", "august": "Aug", "september": "Sep",
    "october": "Oct", "november": "Nov", "december": "Dec",
    # Indonesian
    "januari": "Jan", "februari": "Feb", "maret": "Mar", "april": "Apr",
    "mei": "May", "juni": "Jun", "juli": "Jul", "agustus": "Aug",
    "september": "Sep", "oktober": "Oct", "november": "Nov", "desember": "Dec",
    # Numeric month
    "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr",
    "5": "May", "6": "Jun", "7": "Jul", "8": "Aug",
    "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}

_MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]

def _normalize_month_col(series: pd.Series) -> tuple[pd.Series, int, list]:
    """
    Normalize Month column to standard 3-letter English format.
    Handles: ISO dates (2024-01), numeric (1–12), Indonesian (Januari), English variants.
    Returns (normalized_series, n_changed, unrecognized_values).
    """
    import re
    result    = []
    n_changed = 0
    unknown   = []

    for val in series:
        s = str(val).strip()

        # ISO date: 2024-01, 2024-1, 01/2024, Jan-2024, Jan 2024
        iso = re.match(r'^\d{4}[-/](\d{1,2})$', s)
        if iso:
            m = _MONTH_MAP.get(iso.group(1).lstrip("0") or "0", None)
            if m:
                result.append(m)
                if m != s: n_changed += 1
                continue

        # Month-year: Jan-2024, Jan 2024, January 2024, Januari 2024
        my = re.match(r'^([A-Za-z]+)[\s\-_/]?\d{2,4}$', s)
        if my:
            key = my.group(1).lower()
            m   = _MONTH_MAP.get(key)
            if m:
                result.append(m)
                if m != s: n_changed += 1
                continue

        # Quarter: Q1, Q2, Q3, Q4 → map to midpoint month
        qtr = re.match(r'^Q([1-4])[\s\-]?\d{0,4}$', s, re.IGNORECASE)
        if qtr:
            q_to_m = {"1": "Feb", "2": "May", "3": "Aug", "4": "Nov"}
            result.append(q_to_m[qtr.group(1)])
            n_changed += 1
            continue

        # Direct lookup (handles "Jan", "February", "Januari", "1", "01")
        key = s.lower().lstrip("0") or "0"
        m   = _MONTH_MAP.get(s.lower()) or _MONTH_MAP.get(key)
        if m:
            result.append(m)
            if m != s: n_changed += 1
        else:
            result.append(s)   # keep original
            unknown.append(s)

    return pd.Series(result, index=series.index), n_changed, unknown


def _validate_df(df: pd.DataFrame, filename: str) -> tuple[bool, list, list, dict]:
    """
    Validate uploaded CSV. Returns (is_valid, errors, warnings, transforms).
    errors     — block upload
    warnings   — shown but don't block
    transforms — dict of mutations applied (unit conversion, month normalization)
    """
    errors     = []
    warnings   = []
    transforms = {}

    # 1. Required columns
    missing_req = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_req:
        errors.append(f"Missing required column(s): **{', '.join(missing_req)}**. "
                       f"Your file has: {df.columns.tolist()}")

    if errors:
        return False, errors, warnings, transforms

    # 2. Row count
    if len(df) < MIN_ROWS:
        errors.append(f"Too few rows: {len(df)}. Minimum required: {MIN_ROWS}.")
    if len(df) > MAX_ROWS:
        warnings.append(f"Large dataset: {len(df)} rows. Only the first {MAX_ROWS} rows will be used.")
        df = df.head(MAX_ROWS)

    # 3. Numeric column validation
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        # Coerce to numeric
        coerced = pd.to_numeric(df[col], errors="coerce")
        n_bad   = coerced.isna().sum() - df[col].isna().sum()
        if n_bad > 0:
            warnings.append(f"Column **{col}**: {n_bad} non-numeric value(s) found and set to NaN.")
        df[col] = coerced

        # Negative values
        n_neg = (coerced < 0).sum()
        if NEGATIVE_CHECK and n_neg > 0:
            warnings.append(f"Column **{col}**: {n_neg} negative value(s) detected. "
                             f"Negative emissions should be verified (possible data entry error).")

    # 3b. Unit detection — auto-convert if not tCO₂e
    if "Emission" in df.columns:
        unit_label, conv_factor = _detect_emission_unit(df["Emission"].dropna())
        if conv_factor != 1.0:
            df["Emission"] = (df["Emission"] * conv_factor).round(4)
            transforms["unit_conversion"] = {
                "detected": unit_label,
                "factor":   conv_factor,
                "column":   "Emission",
            }
            warnings.append(
                f"**Unit auto-conversion applied**: Emission column appears to be in "
                f"**{unit_label}** (median value suggested non-tCO₂e scale). "
                f"Values multiplied by {conv_factor:g} and converted to **tCO₂e**. "
                f"Please verify this is correct — go to the raw data tab to inspect."
            )
        # Apply same factor to Energy, Water, Waste if they exist and same scale issue
        for col in ["Energy", "Water", "Waste"]:
            if col in df.columns and conv_factor != 1.0 and col in NUMERIC_COLS:
                # Only convert if the magnitude is proportionally off too
                pass  # Energy/Water/Waste have different expected magnitudes — don't auto-convert

    # 3c. Month normalization
    if "Month" in df.columns:
        norm_series, n_changed, unknown = _normalize_month_col(df["Month"])
        if n_changed > 0:
            df["Month"] = norm_series
            transforms["month_normalization"] = {
                "n_changed": n_changed,
                "examples":  list(unknown[:3]),
            }
            warnings.append(
                f"**Month format normalized**: {n_changed} month value(s) converted to "
                f"standard 3-letter format (e.g. 'Januari' → 'Jan', '2024-01' → 'Jan'). "
                f"Sorting and chart axes are now correct."
            )
        if unknown:
            warnings.append(
                f"**{len(unknown)} unrecognized month value(s)**: "
                f"{', '.join(repr(u) for u in unknown[:5])}. "
                "These will appear as-is. Expected formats: Jan–Dec, January, Januari, 2024-01, 1–12."
            )

        # Sort dataframe by canonical month order so charts always render Jan→Dec
        known_months = {m: i for i, m in enumerate(_MONTH_ORDER)}
        df["_month_order"] = df["Month"].map(lambda x: known_months.get(x, 99))
        df = df.sort_values("_month_order").drop(columns=["_month_order"]).reset_index(drop=True)
        transforms["month_sorted"] = True

    # 4. Missing data
    completeness = df.notna().mean().mean() * 100
    if completeness < 80:
        warnings.append(f"Data completeness is only **{completeness:.0f}%**. "
                         "GRI requires ≥90% for third-party verification.")

    # 5. Emission spike detection (Z-score)
    if "Emission" in df.columns:
        em = df["Emission"].dropna()
        if len(em) >= 4:
            mean, std = em.mean(), em.std()
            if std > 0:
                z_scores = (em - mean) / std
                spikes   = df.loc[z_scores.abs() > SPIKE_THRESHOLD, "Month"].tolist()                            if "Month" in df.columns else []
                n_spikes = (z_scores.abs() > SPIKE_THRESHOLD).sum()
                if n_spikes > 0:
                    months_str = ", ".join(str(m) for m in spikes[:5])
                    warnings.append(
                        f"**{n_spikes} emission spike(s)** detected "
                        f"({SPIKE_THRESHOLD}σ above mean): **{months_str}**. "
                        "Review for data errors or legitimate peak events."
                    )

        # Flat data warning (all values identical)
        if em.nunique() == 1:
            warnings.append("All emission values are identical — this may indicate "
                             "placeholder data rather than actual measurements.")

    # 6. Benchmark breach check (Emission vs sector benchmark)
    bench = get_benchmark(S.get("sector", "Manufacturing"))
    area  = float(S.get("area_m2", 5000))
    if "Emission" in df.columns and bench > 0 and area > 0:
        total_em  = df["Emission"].sum()
        intensity = total_em * 1000 / area
        gap_pct   = (intensity / bench - 1) * 100
        if gap_pct > 20:
            warnings.append(
                f"**Benchmark breach**: Carbon intensity is **{gap_pct:.0f}% above** "
                f"the {S.get('sector','Manufacturing')} benchmark ({bench} kg/m²). "
                "Immediate decarbonization action recommended."
            )

    return len(errors) == 0, errors, warnings, transforms


def _load_and_validate(uploaded_file):
    """Load CSV with validation, display results, store to session_state only if valid."""
    try:
        df_raw = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"❌ Failed to read file: {e}")
        return

    is_valid, errors, warnings, transforms = _validate_df(df_raw, uploaded_file.name)

    # Apply transforms mutated inside _validate_df back to df_raw
    # (unit conversion and month normalization modify df in-place within _validate_df,
    # but we passed df_raw in — re-read from file and re-apply so we have the clean copy)
    # Actually _validate_df modifies columns directly on the passed df, so df_raw IS mutated.
    # transforms dict records what changed for display purposes only.

    # Show errors (blocking)
    if errors:
        for err in errors:
            st.error(f"❌ {err}")
        st.markdown("""
        <div style="background:#FFF8F8;border:1px solid #FEE2E2;border-radius:10px;
                    padding:14px 18px;font-size:12px;color:#991B1B;margin-top:8px;">
            <strong>Expected CSV format:</strong><br>
            <code>Month,Emission,Energy,Water,Waste</code><br>
            <code>Jan,245.5,3480,820,28.1</code><br>
            <code>Feb,231.0,3210,795,25.4</code><br><br>
            👆 Open <strong>"Download CSV Template & Data Guide"</strong> above for ready-to-use templates.
        </div>
        """, unsafe_allow_html=True)
        return

    # Show smart alerts / warnings (non-blocking)
    if warnings:
        st.markdown("""
        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;
                    padding:14px 18px;margin-bottom:12px;">
            <div style="font-size:12px;font-weight:700;color:#92400E;margin-bottom:8px;">
                ⚠️ Smart Upload Alerts ({n})
            </div>
        """.replace("{n}", str(len(warnings))), unsafe_allow_html=True)
        for w in warnings:
            st.markdown(f"""
            <div style="font-size:12px;color:#78350F;margin-bottom:6px;
                        padding:6px 10px;background:#FEF3C7;border-radius:6px;
                        border-left:3px solid #F59E0B;">
                {w}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Store validated data (single source of truth — per-slot only)
    S.set("uploaded_df", df_raw)

    # Extract company name
    if "Company" in df_raw.columns:
        company = str(df_raw["Company"].iloc[0])
    else:
        name    = uploaded_file.name.replace(".csv", "").replace("_", " ").title()
        company = name if len(name) < 40 else "Uploaded Organization"
    S.set("company_name", company)

    # Success summary
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Rows loaded",     len(df_raw))
    with col_b:
        st.metric("Columns",         len(df_raw.columns))
    with col_c:
        completeness = round(df_raw.notna().mean().mean() * 100, 1)
        st.metric("Data quality",    f"{completeness}%")
    with col_d:
        alert_count = len(warnings)
        st.metric("Alerts",          alert_count, delta="Review" if alert_count else "Clean",
                  delta_color="inverse" if alert_count else "off")

    # Show transform badges
    if transforms:
        badges = []
        if "unit_conversion" in transforms:
            uc = transforms["unit_conversion"]
            badges.append(f'<span style="background:#FEF3C7;color:#92400E;font-size:10px;'
                          f'font-weight:700;padding:2px 9px;border-radius:20px;margin-right:6px;">'
                          f'⚡ Unit converted: {uc["detected"]} → tCO₂e (×{uc["factor"]:g})</span>')
        if "month_normalization" in transforms:
            mn = transforms["month_normalization"]
            badges.append(f'<span style="background:#DCFCE7;color:#14532D;font-size:10px;'
                          f'font-weight:700;padding:2px 9px;border-radius:20px;margin-right:6px;">'
                          f'📅 Month normalized: {mn["n_changed"]} value(s) standardized</span>')
        if "month_sorted" in transforms:
            badges.append(f'<span style="background:#DCFCE7;color:#14532D;font-size:10px;'
                          f'font-weight:700;padding:2px 9px;border-radius:20px;">'
                          f'↕️ Sorted Jan→Dec</span>')
        if badges:
            st.markdown(
                f'<div style="margin-top:8px;">{"".join(badges)}</div>',
                unsafe_allow_html=True
            )
    if not warnings:
        st.success(f"✅ Dataset validated · {len(df_raw)} rows · "
                   f"{len(df_raw.columns)} columns · No issues detected")

    # Immediately recompute ESG score with new data so all pages reflect upload
    with st.spinner("🔄 Calculating ESG score from new data..."):
        from utils.state import compute_canonical_esg
        compute_canonical_esg(force=True)
    st.success("✅ ESG score updated — scroll down to see full analytics")



def render():
    S.init()

    page_header(
        title="ESG Analytics",
        subtitle="Upload emissions data · Enrich with S+G indicators · View full E+S+G analytics",
        badge="Data Hub", badge_type="indigo",
    )

    from components.ui import step_header, card_start, card_end

    has_data = S.get("uploaded_df") is not None

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 1 — UPLOAD
    # ══════════════════════════════════════════════════════════════════════════
    step_header(1, 3, "Upload Environmental Dataset",
                "Upload CSV dengan kolom Emission (wajib) · Energy, Water, Waste (opsional)",
                accent="#6366F1")

    with st.container():
        col_upload, col_tpl = st.columns([3, 1], gap="medium")

        with col_upload:
            if has_data:
                df_existing = S.get("uploaded_df")
                st.success(f"✅ Dataset connected — {len(df_existing)} rows · Klik upload baru untuk replace")
            uploaded_file = st.file_uploader(
                "Upload CSV file", type=["csv"],
                label_visibility="collapsed", key="esg_uploader"
            )
            if uploaded_file:
                # Visible processing feedback — distinct file triggers fresh analysis
                file_signature = f"{uploaded_file.name}_{uploaded_file.size}"
                if st.session_state.get("_last_processed_file") != file_signature:
                    with st.status("Memproses dataset baru...", expanded=True) as status:
                        st.write("📄 Membaca file CSV...")
                        _load_and_validate(uploaded_file)
                        st.write("✅ Validasi struktur data selesai")
                        st.write("🔄 Menghitung ulang ESG Score (E+S+G)...")
                        status.update(label="✅ Dataset baru berhasil dianalisis!",
                                      state="complete", expanded=False)
                    st.session_state["_last_processed_file"] = file_signature
                    st.toast("Data baru berhasil dimuat — semua skor telah diperbarui", icon="✅")

            # S+G annual upload
            with st.expander("👥 Upload ESG (Social + Governance) Annual CSV — optional", expanded=False):
                import io as _io
                sg_uploaded = st.file_uploader(
                    "Annual S+G CSV", type=["csv"], key="sg_uploader", label_visibility="collapsed"
                )
                if sg_uploaded:
                    try:
                        sg_df = pd.read_csv(sg_uploaded)
                        latest = sg_df.sort_values("Year").iloc[-1] if "Year" in sg_df.columns else sg_df.iloc[-1]
                        field_map = {
                            "Employee_Turnover_pct":        "employee_turnover_pct",
                            "Training_Hours_per_Employee":  "training_hours_per_employee",
                            "Women_Workforce_pct":          "women_workforce_pct",
                            "Women_Management_pct":         "women_management_pct",
                            "Injury_Rate_per_200k_hrs":     "injury_rate",
                            "Board_Independence_pct":       "board_independence_pct",
                            "Women_Board_pct":              "women_board_pct",
                            "Anti_Corruption_Training_pct": "anti_corruption_training_pct",
                            "Has_Code_of_Conduct":          "has_code_of_conduct",
                            "Has_Whistleblower_Policy":     "has_whistleblower_policy",
                        }
                        filled = []
                        for col, key in field_map.items():
                            if col in sg_df.columns and pd.notna(latest.get(col)):
                                val = latest[col]
                                S.set(key, bool(val) if "Has_" in col else float(val) if col != "Year" else int(val))
                                filled.append(col)
                        from utils.state import compute_canonical_esg
                        compute_canonical_esg(force=True)
                        st.success(f"✅ S+G data imported: {', '.join(filled)}")
                    except Exception as e:
                        st.error(f"S+G upload error: {e}")

            # Previous year
            with st.expander("📅 Upload Previous Year Data — optional (enables YoY comparison)", expanded=False):
                prev_file = st.file_uploader("Previous year CSV", type=["csv"], key="prev_year_uploader", label_visibility="collapsed")
                if prev_file:
                    try:
                        prev_df = pd.read_csv(prev_file)
                        if "Emission" in prev_df.columns:
                            S.set("prev_year_df", prev_df)
                            st.success(f"✅ Previous year loaded — {len(prev_df)} rows, {prev_df['Emission'].sum():,.0f} tCO₂e total")
                        else:
                            st.error("Previous year CSV must contain 'Emission' column.")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with col_tpl:
            st.markdown("""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                 padding:14px 16px;">
                <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                     letter-spacing:0.8px;margin-bottom:10px;">Templates</div>
            """, unsafe_allow_html=True)

            import io as _io
            import pandas as _tpd
            tpl_min = _tpd.DataFrame({
                "Month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                "Emission": [245.5,231.0,258.2,242.1,267.8,251.3,269.4,263.7,248.9,241.0,256.4,271.8],
            })
            tpl_full = _tpd.DataFrame({
                "Month":    tpl_min["Month"].tolist(),
                "Emission": tpl_min["Emission"].tolist(),
                "Energy":   [3481,3278,3664,3437,3801,3566,3822,3741,3532,3421,3638,3857],
                "Water":    [820,795,841,810,868,836,874,856,821,808,848,881],
                "Waste":    [28.1,25.4,29.6,27.3,31.0,28.8,31.5,30.2,27.9,26.8,29.4,32.1],
            })
            tpl_sg = _tpd.DataFrame({
                "Year": [2023,2024,2025],
                "Employee_Turnover_pct": [16.0,14.5,13.0],
                "Training_Hours_per_Employee": [6,8,10],
                "Women_Workforce_pct": [28,30,32],
                "Injury_Rate_per_200k_hrs": [3.5,3.0,2.4],
                "Board_Independence_pct": [25,30,33],
                "Women_Board_pct": [10,15,17],
                "Anti_Corruption_Training_pct": [0,40,75],
                "Has_Code_of_Conduct": [False,True,True],
                "Has_Whistleblower_Policy": [False,True,True],
            })
            st.download_button("⬇️ Minimal CSV",  tpl_min.to_csv(index=False).encode(),
                               "cl_template_minimal.csv",  "text/csv", use_container_width=True, key="dl_min")
            st.download_button("⬇️ Full CSV",     tpl_full.to_csv(index=False).encode(),
                               "cl_template_full.csv",     "text/csv", use_container_width=True, key="dl_full")
            st.download_button("⬇️ S+G Template", tpl_sg.to_csv(index=False).encode(),
                               "cl_template_sg.csv",       "text/csv", use_container_width=True, key="dl_sg")
            st.markdown("</div>", unsafe_allow_html=True)

    if not has_data:
        from components.ui import empty_state
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        empty_state("◈", "Upload Dataset untuk Mulai",
                    "Upload CSV di Step 1 — setidaknya kolom Month dan Emission (tCO₂e). "
                    "Setelah upload, Step 2 dan Step 3 otomatis terbuka.")
        return

    df  = S.get("uploaded_df")
    ov  = dataset_overview(df)
    esg = _esg_score_from_df(df, sector=S.get("sector","Manufacturing"))

    # ── Dataset Health KPIs ────────────────────────────────────────────────
    h1, h2, h3, h4 = st.columns(4, gap="medium")
    cv = (df["Emission"].std() / df["Emission"].mean() * 100) if df["Emission"].mean() else 0
    with h1: kpi_card("Total Emission", f"{ov.get('total',0):,.0f} tCO₂e", icon="📊", icon_bg="#FFF7ED")
    with h2: kpi_card("Monthly Avg",    f"{ov.get('average',0):,.0f} tCO₂e", icon="📅", icon_bg="#E0F2FE")
    with h3: kpi_card("Data Completeness", f"{ov.get('completeness',94):.0f}%", icon="✓", icon_bg="#ECFDF5",
                       badge="GRI-ready" if ov.get("completeness",94)>=90 else "Incomplete",
                       badge_type="green" if ov.get("completeness",94)>=90 else "yellow")
    with h4: kpi_card("Variance (CV)",  f"{cv:.1f}%", icon="~", icon_bg="#F5F3FF",
                       badge="Stable" if cv<15 else "High variance",
                       badge_type="green" if cv<15 else "yellow")

    # ── Smart alerts ──────────────────────────────────────────────────────
    outliers = detect_outliers(df)
    if not outliers.empty:
        avg = df["Emission"].mean()
        alerts = []
        for _, row in outliers.iterrows():
            month = row.get("Month","—")
            em    = row["Emission"]
            delta = (em - avg) / max(avg, 1) * 100
            alerts.append({
                "icon": "⚠️", "type": "warn",
                "text": f"<strong>{month}</strong> — {em:,.0f} tCO₂e ({delta:+.0f}% vs avg). "
                        "Verifikasi data atau identifikasi penyebab lonjakan emisi."
            })
        from components.ui import insight_panel as _ip
        _ip(alerts[:3])

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 2 — S+G INPUTS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    step_header(2, 3, "Social & Governance Indicators",
                "Isi data S+G untuk ESG score yang akurat — atau skip jika hanya butuh Environmental analytics",
                accent="#6366F1")

    with st.expander("📋 Social & Governance Data Inputs (GRI/SASB)", expanded=False):
        st.caption("Geser semua slider lalu klik **Save** sekali di bawah — perubahan tidak ter-apply per-geser, jadi halaman tidak reload tiap interaksi.")
        with st.form("sg_inputs_form", clear_on_submit=False):
            sg_col1, sg_col2, sg_col3 = st.columns(3, gap="medium")

            with sg_col1:
                st.markdown('<div style="font-size:12px;font-weight:700;color:#10B981;margin-bottom:8px;">🌿 Environmental (tambahan)</div>', unsafe_allow_html=True)
                water_recycled = st.slider("Water Recycled (%)", 0, 100,
                    value=int(S.get("water_recycled_pct", 0) or 0), key="esg_water_recycled")
                renew = st.slider("Renewable Energy (%)", 0, 100,
                    value=int(S.get("renew_pct", 0) or 0), key="esg_renew")

            with sg_col2:
                st.markdown('<div style="font-size:12px;font-weight:700;color:#EC4899;margin-bottom:8px;">👥 Social — GRI 401/403/404/405</div>', unsafe_allow_html=True)
                employees = st.number_input("Total Employees", min_value=0, step=1,
                    value=int(S.get("employees", 0) or 0), key="esg_employees")
                turnover = st.number_input("Turnover Rate (%/yr)", min_value=0.0, max_value=100.0,
                    value=float(S.get("employee_turnover_pct") or 15.0), step=1.0, key="esg_turnover")
                training = st.number_input("Training Hours/Employee/Year", min_value=0.0, max_value=200.0,
                    value=float(S.get("training_hours_per_employee") or 8.0), step=1.0, key="esg_training")
                women_wf = st.slider("Women in Workforce (%)", 0, 100,
                    value=int(S.get("women_workforce_pct") or 30), key="esg_women_wf")
                injury = st.number_input("Injury Rate (per 200k hrs)", min_value=0.0, max_value=20.0,
                    value=float(S.get("injury_rate") or 3.0), step=0.1, key="esg_injury")

            with sg_col3:
                st.markdown('<div style="font-size:12px;font-weight:700;color:#6366F1;margin-bottom:8px;">⚖️ Governance — GRI 2-9/2-22/205</div>', unsafe_allow_html=True)
                board_size = st.number_input("Board Size", min_value=0, step=1,
                    value=int(S.get("board_size", 0) or 0), key="esg_board_size")
                board_indep = st.slider("Board Independence (%)", 0, 100,
                    value=int(S.get("board_independence_pct") or 30), key="esg_board_indep")
                women_board = st.slider("Women on Board (%)", 0, 100,
                    value=int(S.get("women_board_pct") or 15), key="esg_women_board")
                anti_corr = st.slider("Anti-Corruption Training (%)", 0, 100,
                    value=int(S.get("anti_corruption_training_pct") or 0), key="esg_anti_corr")
                has_coc = st.checkbox("Code of Conduct — GRI 2-23",
                    value=bool(S.get("has_code_of_conduct") or False), key="esg_coc")
                has_wb = st.checkbox("Whistleblower Policy — GRI 2-26",
                    value=bool(S.get("has_whistleblower_policy") or False), key="esg_wb")

            submitted_sg = st.form_submit_button("💾 Save & Recalculate ESG Score", type="primary",
                                                  use_container_width=True)

        if submitted_sg:
            S.set("water_recycled_pct", float(water_recycled))
            S.set("renew_pct", float(renew))
            S.set("employees", int(employees))
            S.set("employee_turnover_pct", float(turnover))
            S.set("training_hours_per_employee", float(training))
            S.set("women_workforce_pct", float(women_wf))
            S.set("injury_rate", float(injury))
            S.set("board_size", int(board_size))
            S.set("board_independence_pct", float(board_indep))
            S.set("women_board_pct", float(women_board))
            S.set("anti_corruption_training_pct", float(anti_corr))
            S.set("has_code_of_conduct", bool(has_coc))
            S.set("has_whistleblower_policy", bool(has_wb))
            from utils.state import compute_canonical_esg
            compute_canonical_esg(force=True)
            esg = _esg_score_from_df(df, sector=S.get("sector","Manufacturing"))
            st.success(f"✅ ESG score diperbarui: {esg['score']}/100 · Grade {esg['grade']}")
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 3 — ANALYTICS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    step_header(3, 3, "ESG Analytics & Insights",
                "Charts, ESG composition, benchmark comparison, dan decarbonization recommendations",
                accent="#6366F1")

    # ── ESG Score Row ──────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4, gap="medium")
    grade_color = "green" if esg["score"] >= 70 else "yellow" if esg["score"] >= 50 else "red"
    with sc1: kpi_card("ESG Score",       f"{esg['score']}/100", icon="★", icon_bg="#EEF2FF",
                        badge=f"Grade {esg['grade']}", badge_type=grade_color)
    with sc2: kpi_card("Environmental",   f"{esg['env']:.1f}",   icon="🌿", icon_bg="#ECFDF5",
                        badge="E-Pillar", badge_type="green")
    with sc3: kpi_card("Social",          f"{esg['social']:.1f}",icon="👥", icon_bg="#FDF2F8",
                        badge="S-Pillar", badge_type="pink")
    with sc4: kpi_card("Governance",      f"{esg['gov']:.1f}",   icon="⚖️", icon_bg="#EEF2FF",
                        badge="G-Pillar", badge_type="indigo")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── 3 primary charts — each answers one question ───────────────────────
    tabs = st.tabs(["📊 Distribution", "📈 Trend", "🎯 ESG Composition", "🔗 Correlation", "⚠️ Outliers"])

    with tabs[0]:
        card_start("Monthly Emission Distribution", "Mana bulan dengan emisi tertinggi?")
        fig = emission_bar(df, height=300)
        try: st.plotly_chart(fig, use_container_width=True)
        except: pass
        card_end()

    with tabs[1]:
        card_start("Emission Trend", "Apakah emisi menurun dari waktu ke waktu?")
        fig = emission_trend(df, height=300)
        try: st.plotly_chart(fig, use_container_width=True)
        except: pass
        card_end()

    with tabs[2]:
        card_start("ESG Composition E+S+G", "Seberapa seimbang skor E, S, dan G?")
        from components.ui import esg_gauge, metric_bar
        g_col, c_col = st.columns([1, 1.4], gap="medium")
        with g_col:
            esg_gauge(esg["score"], title=f"{esg['label']} · Grade {esg['grade']}", height=220)
        with c_col:
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            metric_bar("Environmental", esg["env"],  100, "#10B981")
            metric_bar("Social",        esg["social"],100, "#EC4899")
            metric_bar("Governance",    esg["gov"],   100, "#6366F1")

            bench = get_benchmark(S.get("sector","Manufacturing"))
            em_total = ov.get("total", 0)
            area   = float(S.get("area_m2", 5000) or 5000)
            intens = em_total * 1000 / max(area, 1) if area > 0 else 0
            gap    = (intens - bench) / max(bench, 1) * 100
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:10px 14px;">
                <div style="font-size:10px;font-weight:700;color:#94A3B8;margin-bottom:6px;
                     text-transform:uppercase;letter-spacing:0.5px;">vs Sector Benchmark</div>
                <div style="font-size:22px;font-weight:700;color:{'#EF4444' if gap>0 else '#10B981'};">
                    {gap:+.1f}%</div>
                <div style="font-size:12px;color:#64748B;">
                    {intens:.2f} vs {bench} kg/m² ({S.get('sector','Manufacturing')})</div>
            </div>
            """, unsafe_allow_html=True)
        card_end()

    with tabs[3]:
        card_start("Correlation Analysis", "Apakah energi & air berkorelasi dengan emisi?")
        corr_cols = [c for c in ["Energy", "Water", "Waste"] if c in df.columns]
        if corr_cols:
            corr_sel = st.selectbox("Bandingkan Emission vs", corr_cols,
                                    key="corr_x_col", label_visibility="visible")
            fig = correlation_scatter(df, x_col=corr_sel, y_col="Emission",
                                      x_label=corr_sel, y_label="Emission (tCO₂e)",
                                      height=280)
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
        else:
            st.info("Tambahkan kolom 'Energy', 'Water', atau 'Waste' di CSV untuk melihat analisis korelasi.")
        card_end()

    with tabs[4]:
        card_start("Outlier Detection", "Bulan mana yang perlu investigasi?")
        outlier_df = detect_outliers(df)
        if not outlier_df.empty:
            st.dataframe(outlier_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Tidak ada outlier signifikan terdeteksi (Z-score < 3.0 pada semua bulan).")
        card_end()

    # ── ESG Performance Analysis + Recommendations ─────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    total   = ov.get("total", 0)
    average = ov.get("average", 0)
    peak    = ov.get("peak", 0)
    pm      = ov.get("peak_month", "—")
    lm      = ov.get("low_month",  "—")

    card_start("ESG Performance Analysis", "Benchmark · Strengths · Gaps · Recommendations")

    pa, pb = st.columns(2, gap="large")
    with pa:
        st.markdown(f"""
        <div style="font-size:12px;color:#374151;line-height:1.8;padding:14px 16px;
                    background:#F9FAFB;border-radius:10px;margin-bottom:12px;">
            Total emisi: <strong>{total:,.0f} tCO₂e</strong> ·
            rata-rata bulanan <strong>{average:,.0f} tCO₂e</strong>.
            Puncak di <strong>{pm}</strong> ({peak:,.0f} tCO₂e), terendah di <strong>{lm}</strong>.
            Data completeness <strong>{ov.get('completeness',94):.0f}%</strong>
            {'— GRI-ready ✓' if ov.get('completeness',94)>=90 else '— di bawah threshold 90% GRI'}.
        </div>
        <div style="background:#EFF6FF;border-radius:10px;padding:14px 16px;">
            <div style="font-size:12px;font-weight:700;color:#1E40AF;margin-bottom:6px;">
                🎯 Grade {esg['grade']} · Score {esg['score']}/100
            </div>
            <div style="font-size:12px;color:#374151;line-height:1.7;">
                E: <strong>{esg['env']:.0f}</strong> ·
                S: <strong>{esg['social']:.0f}</strong> ·
                G: <strong>{esg['gov']:.0f}</strong>
                — {'Skor E mengungguli S+G. Tingkatkan Social/Governance disclosure untuk score lebih tinggi.' if esg['env'] > esg['social'] and esg['env'] > esg['gov'] else 'Score E+S+G relatif seimbang.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with pb:
        from components.ui import insight_panel as _ip
        _ip([
            {"text": f"<strong>Strength:</strong> Data completeness {ov.get('completeness',94):.0f}% — siap audit GRI.", "type":"info","icon":"✅"},
            {"text": f"<strong>Strength:</strong> Emisi terendah di {lm} — jadikan referensi operasional.", "type":"info","icon":"✅"},
            {"text": f"<strong>Gap:</strong> Puncak {pm} {((peak-average)/max(average,1)*100):.0f}% di atas rata-rata — perlu load shifting.", "type":"warn","icon":"⚠️"},
            {"text": "Transisi Scope 2 ke energi terbarukan dapat kurangi total emisi 18–22% dalam 24 bulan.", "type":"info","icon":"🌱"},
        ])

    card_end()

    # ── Decarbonization Recommendations ───────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    card_start("Decarbonization Roadmap", "Priority actions · Ranked by impact")

    recs = [
        {"priority":"HIGH",   "color":"#EF4444","bg":"#FEF2F2",
         "title":"Renewable Energy Transition",
         "body":"Procurement solar PPA atau green tariff — eliminasi Scope 2. Target: 30% renewable 2026, 80% 2028.",
         "meta":"Impact: −18% total · Timeframe: 12–18 bulan"},
        {"priority":"HIGH",   "color":"#F59E0B","bg":"#FFFBEB",
         "title":"Energy Efficiency Audit",
         "body":"Audit ISO 50001 untuk HVAC, lighting, dan proses — payback < 2 tahun.",
         "meta":"Impact: −8–12% Scope 2 · Timeframe: 3–6 bulan"},
        {"priority":"MEDIUM", "color":"#3B82F6","bg":"#EFF6FF",
         "title":"Scope 3 Supplier Engagement",
         "body":"Onboard 10 supplier terbesar ke ESG Scorecard — kurangi Scope 3 Cat.1.",
         "meta":"Impact: −5–10% Scope 3 · Timeframe: 6–12 bulan"},
        {"priority":"MEDIUM", "color":"#8B5CF6","bg":"#F5F3FF",
         "title":"Circular Economy Waste Program",
         "body":"Waste segregation, composting, material recovery — reduksi limbah ke TPA.",
         "meta":"Impact: −15% waste · Timeframe: 3–6 bulan"},
    ]
    for r in recs:
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:12px;padding:10px 14px;'
            f'background:{r["bg"]};border-left:4px solid {r["color"]};border-radius:0 8px 8px 0;margin-bottom:6px;">'
            f'<div style="font-size:9px;font-weight:700;color:{r["color"]};min-width:46px;'
            f'padding-top:2px;text-transform:uppercase;">{r["priority"]}</div>'
            f'<div><div style="font-size:12px;font-weight:700;color:#0F172A;">{r["title"]}</div>'
            f'<div style="font-size:12px;color:#374151;margin-top:2px;line-height:1.5;">{r["body"]}</div>'
            f'<div style="font-size:10px;color:#94A3B8;margin-top:4px;">{r["meta"]}</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
    card_end()

    # ── YoY (if prev year loaded) ──────────────────────────────────────────
    prev_records = S.get("prev_year_df")
    if prev_records is not None:
        import numpy as _np
        prev_df = prev_records if isinstance(prev_records, pd.DataFrame) else pd.DataFrame(prev_records)
        if "Emission" in prev_df.columns:
            prev_total = prev_df["Emission"].sum()
            curr_total = df["Emission"].sum()
            yoy_chg    = (curr_total - prev_total) / max(prev_total, 1) * 100
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            card_start("Year-over-Year Comparison", "Perubahan emisi vs tahun sebelumnya")
            yc = st.columns(4, gap="medium")
            with yc[0]: kpi_card("Current Year",  f"{curr_total:,.0f} tCO₂e", icon="📅", icon_bg="#E0F2FE")
            with yc[1]: kpi_card("Previous Year", f"{prev_total:,.0f} tCO₂e", icon="📅", icon_bg="#F1F5F9")
            with yc[2]: kpi_card("YoY Change",    f"{yoy_chg:+.1f}%", icon="Δ",
                                  icon_bg="#ECFDF5" if yoy_chg < 0 else "#FFF1F2",
                                  badge="Menurun ✓" if yoy_chg < 0 else "Meningkat ⚠",
                                  badge_type="green" if yoy_chg < 0 else "red")
            with yc[3]: kpi_card("Absolute Δ",    f"{abs(curr_total-prev_total):,.0f} tCO₂e",
                                  icon="~", icon_bg="#F5F3FF")
            card_end()

    # ── Raw data ───────────────────────────────────────────────────────────
    with st.expander("🗃️ Raw data table", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True, height=260)
