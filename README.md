<div align="center">

# 🌊 CarbonLens V7
### ESG Intelligence Platform for Sustainability Reporting & Decarbonization Planning

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Anthropic](https://img.shields.io/badge/Claude_API-Sonnet_4.6-8B5CF6?style=flat)](https://anthropic.com)
[![GHG Protocol](https://img.shields.io/badge/GHG_Protocol-Scope_1%2F2%2F3-10B981?style=flat)](https://ghgprotocol.org)
[![GRI](https://img.shields.io/badge/GRI-200%2F300%2F400-0EA5E9?style=flat)](https://globalreporting.org)
[![License](https://img.shields.io/badge/License-MIT-64748B?style=flat)](LICENSE)

**[🚀 Live Demo](https://carbonlens-v7.streamlit.app)** · **[📧 Contact](mailto:rezaazzura04@gmail.com)**

</div>

---

## What is CarbonLens?

CarbonLens is a **full-stack ESG analytics platform** built to demonstrate the intersection of climate science, data engineering, and AI — domains at the core of modern sustainability roles.

It covers the full decarbonization workflow: upload raw emissions data → compute GHG inventory → benchmark against sector peers → simulate abatement pathways → generate GRI-compliant reports → estimate carbon credit requirements for residual gaps.

> **Why I built this:** Most enterprise ESG tools cost thousands of dollars per year and require consultants to operate. CarbonLens puts professional-grade sustainability analytics — the kind typically locked behind a Big4 engagement — into a single open-source app.

---

## Features

### 🌿 Environmental Analytics
- **GHG Inventory** — Scope 1, 2, and 3 calculations using IPCC AR6 emission factors and PLN regional grid factors (Kepmen ESDM 18/2023, 7 subsystems)
- **Sector Benchmarking** — Peer comparison against KLHK PROPER and IESR-calibrated reference data for Manufacturing, Plantation, Mining, and Property sectors
- **Multi-Year Historical Tracking** — SBTi 1.5°C and Paris 2°C trajectory overlay with CAGR analysis

### 👥 Social & Governance
- **Full E+S+G Scoring** — Weighted composite score (E 40% / S 30% / G 30%) with grade bands aligned to major rating agency methodology
- **GRI 200/300/400 Gap Analysis** — Auto-map organization data against 28 GRI disclosures across Economic, Environmental, and Social series
- **POJK 51/2017 + Taksonomi Hijau Indonesia** — OJK regulatory compliance checklist for Indonesia-listed companies

### 🤖 AI & Predictive
- **Decarbonization Planner** — MACC-based reverse optimizer: input a target year and reduction % → system generates the lowest-cost lever combination (renewable energy, efficiency, fleet electrification, waste, water) with cost estimates and glide path chart
- **ML Forecasting** — Scikit-learn regression for 12-month emission forecasting with confidence intervals and SBTi target overlay
- **AI Consultant** — Context-aware ESG advisory powered by Claude Sonnet 4.6 *(requires personal Anthropic API key — free $5 credit at [console.anthropic.com](https://console.anthropic.com), input directly in the app. All other 20 pages work fully without any key.)*

### 🗺️ Geospatial & Supply Chain
- **GIS Intelligence** — Interactive Folium maps with emission hotspot overlay; GEE (Google Earth Engine) satellite integration for land-use change monitoring
- **Supplier ESG Scorecard** — USEEIO v2.0 spend-based Scope 3 factors with weighted risk scoring and engagement priority ranking

### 📊 Reporting & Export
- **PDF ESG Report** — GRI-referenced full sustainability report, auto-generated (ReportLab)
- **Excel Export** — Multi-sheet workbook: ESG Overview + Monthly Data + Scope Breakdown + S&G Indicators + Historical Trend
- **Carbon Credit Center** — Offset volume estimator with registry links (IDX Carbon, Gold Standard, Verra VCS) and Indonesia carbon market context (Perpres 110/2025, SRN-PPI → SRUK transition)
- **JSON Export** — API-ready structured output from all major modules

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Streamlit 1.45 | Multi-page, session-state-isolated architecture |
| Charts | Plotly 5.24 | Interactive visualizations |
| AI | Claude Sonnet 4.6 (Anthropic) | Context-aware ESG narrative |
| ML | Scikit-learn | Emission forecasting, anomaly detection |
| GIS | Folium + Streamlit-Folium | Interactive geospatial mapping |
| PDF | ReportLab | Programmatic PDF generation |
| Excel | OpenPyXL | Multi-sheet workbook export |
| Auth | hashlib SHA-256 | Password hashing, role-based access |
| Data | Pandas + NumPy | Data wrangling and statistical analysis |

---

## Architecture

```
carbonlens/
├── app.py                      # Entry point + page router
├── config/
│   └── settings.py             # Design tokens, emission factors, nav groups, typography scale
├── components/
│   ├── ui.py                   # 15+ reusable UI components (KPI cards, gauges, step headers)
│   ├── sidebar.py              # 4-group collapsible navigation (Core / Analysis / Compliance / Reports)
│   └── styles.py               # Global CSS + 6-class typography scale
├── _pages/                     # 20 application pages
│   ├── dashboard.py            # Executive overview
│   ├── esg_analytics.py        # 3-step data hub (Upload → S+G → Analytics)
│   ├── carbon_accounting.py    # GHG Scope 1/2/3 calculator
│   ├── ai_consultant.py        # Claude API-powered ESG advisor
│   ├── ai_prediction.py        # ML forecasting engine
│   ├── scenario_sim.py         # Decarbonization planner + MACC optimizer
│   ├── benchmarking.py         # Sector peer comparison + KLHK PROPER benchmarks
│   ├── gis_intelligence.py     # Geospatial emission mapping + GEE integration
│   ├── historical.py           # Multi-year trend + SBTi trajectory
│   ├── pojk_compliance.py      # OJK POJK 51 + Taksonomi Hijau Indonesia
│   ├── gri_gap.py              # GRI 200/300/400 gap analysis
│   ├── supplier_scorecard.py   # Supply chain ESG risk scoring (USEEIO v2.0)
│   ├── carbon_credit.py        # Offset portfolio optimizer
│   ├── target_tracker.py       # Net-zero target management
│   ├── esg_reporting.py        # GRI-referenced PDF report generator
│   ├── data_export.py          # Multi-format export center
│   ├── consolidation.py        # Multi-entity GHG consolidation
│   ├── alerts.py               # Emission anomaly alerts
│   └── user_management.py      # Multi-tenant RBAC (Admin / Analyst / Viewer)
└── utils/
    ├── calculations.py         # GHG Protocol engine, ESG scoring, NumpyEncoder
    ├── state.py                # Multi-company (5-slot) session state management
    ├── frameworks.py           # GRI 200/300/400 disclosure definitions
    ├── charts.py               # Chart factory (emission_bar, trend, scatter, gauge)
    ├── auth.py                 # Authentication + audit logging
    └── gee_client.py           # Google Earth Engine client (graceful fallback if unavailable)
```

---

## Standards & Methodology

| Standard | Coverage | Where |
|---|---|---|
| GHG Protocol | Scope 1, 2, 3 (15 categories) | `utils/calculations.py` |
| GRI Standards 2021 | GRI 200 + 300 + 400 (28 disclosures) | `utils/frameworks.py` |
| POJK 51/2017 | 10 mandatory topics | `_pages/pojk_compliance.py` |
| Taksonomi Hijau Indonesia | 4 eligibility categories | `_pages/pojk_compliance.py` |
| SBTi 1.5°C / Well-below 2°C | −4.2%/yr and −2.5%/yr trajectories | `_pages/historical.py`, `_pages/ai_prediction.py` |
| KLHK PROPER 2023–2024 | 4 Indonesia sectors (4,495 companies) | `_pages/benchmarking.py` |
| USEEIO v2.0 | Scope 3 spend-based emission factors | `_pages/supplier_scorecard.py` |
| IPCC AR6 | GWP100 emission factors | `utils/calculations.py` |
| Kepmen ESDM 18/2023 | PLN grid EF (7 regional subsystems) | `config/settings.py` |
| Perpres 110/2025 | Indonesia voluntary carbon market (SRN-PPI → SRUK) | `_pages/carbon_credit.py` |

---

## Quick Start

```bash
# Clone
git clone https://github.com/rezaazzura04/carbonlens-v7.git
cd carbonlens-v7

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
```

App opens at `http://localhost:8501`. No API key needed to use any of the 20 pages — AI Consultant falls back to rule-based mode automatically.

**To enable AI Consultant:** paste your Anthropic API key directly in the app (AI Consultant page → Settings). New accounts get $5 free credit at [console.anthropic.com](https://console.anthropic.com).

### Sample Data

Download template CSVs from the app (ESG Analytics → Step 1 → Templates), or use these to get started immediately:

| File | Upload to | Description |
|---|---|---|
| `environmental_2024.csv` | ESG Analytics → Step 1 | Monthly Scope 1+2, energy, water, waste — PT Semen Nusantara |
| `social_governance_annual.csv` | ESG Analytics → Step 2 | 3-year S+G indicators (GRI 401/403/404/405) |
| `environmental_2023_previous.csv` | ESG Analytics → Step 1 → Previous Year | Enables YoY comparison charts |

```csv
Month,Emission,Energy,Water,Waste
Jan,261.1,115042,4183,26.8
Feb,258.3,112887,4091,29.4
...
```

---

## ESG Score Methodology

```
ESG Score = (E_score × 0.40) + (S_score × 0.30) + (G_score × 0.30)
```

**Environmental (40%)** — Carbon intensity vs sector benchmark, renewable energy share, water efficiency, waste diversion rate, data completeness

**Social (30%)** — Employee turnover, training hours per employee, gender diversity, lost-time injury frequency rate (GRI 401/403/404/405)

**Governance (30%)** — Board independence, women at board level, anti-corruption training coverage, ethics disclosures (GRI 2-9/2-22/205)

| Grade | Score | Label |
|---|---|---|
| A | 90–100 | Excellent |
| A− | 75–90 | Very Good |
| B+ | 60–75 | Good |
| B− | 40–60 | Moderate |
| C | 20–40 | Poor |
| D | 0–20 | Critical |

---

## Roadmap

- [ ] CSRD / ESRS alignment (EU Corporate Sustainability Reporting Directive)
- [ ] Google Earth Engine live satellite integration (land-use change, NDVI, blue carbon verification)
- [ ] Multi-language toggle (Bahasa Indonesia / English)
- [ ] FastAPI backend for programmatic data ingestion (enterprise API endpoint)

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

<div align="center">

**Built by Muhammad Reza Azzura** · Environmental Engineering · Universitas Brawijaya · 2026

*Open to ESG Analyst, Carbon Accounting, and Sustainability Data roles*

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-carbonlens--v7.streamlit.app-0EA5E9?style=flat)](https://carbonlens-v7.streamlit.app)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/rezaazzura)
[![Email](https://img.shields.io/badge/Email-rezaazzura04@gmail.com-EA4335?style=flat&logo=gmail)](mailto:rezaazzura04@gmail.com)

</div>
