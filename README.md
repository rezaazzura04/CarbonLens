# CarbonLens

**ESG and carbon accounting intelligence for Indonesian organisations.**

CarbonLens turns a monthly emissions spreadsheet into an ESG score, a
GHG Protocol-aligned carbon inventory, a data-quality confidence rating,
sector benchmarking, decarbonization scenario planning, and an exportable
report — with every number traceable back to its source and every estimate
clearly labelled as an estimate.

Built as an undergraduate thesis artefact (Teknik Lingkungan, Universitas
Brawijaya; target publication: *Journal of Cleaner Production*) and as a
portfolio demonstration of applied ESG/carbon-accounting domain knowledge
combined with software engineering practice.

**Status: portfolio / pre-commercial build.** Not production-ready, not a
certified assurance tool — see Limitations below.

---

## Live Demo

**⚠️ Not yet deployed at the time of this commit.**

*Add the Streamlit Community Cloud (or equivalent) URL here once deployed —
this is the single highest-impact addition to this README. Until then, see
[Local setup](#local-setup) below to run it yourself in under a minute.*

## Screenshots

*Add 3–5 real screenshots here once the app is deployed and rendering live —
recommended: Executive Summary, Carbon Accounting, ESG Analytics, Data
Quality / Provenance, and one more strong page. Use actual rendered UI, not
mockups and not screenshots from an older version.*

---

## What problem does it solve?

Small and mid-sized Indonesian organisations that need to start tracking
Scope 1/2/3 emissions and ESG indicators typically have three options:
expensive consulting engagements, generic international tools that don't
use Indonesian emission factors, or a spreadsheet with no data-quality
checking, no audit trail, and no way to tell a real number from a guess.
CarbonLens is a working demonstration of a fourth option: a self-serve
platform that uses the correct national emission factors (Kepmen ESDM No.
18/2023 for the electricity grid), scores data quality and ESG confidence
explicitly rather than silently, and never presents a modelled estimate
with the same visual confidence as a disclosed fact.

## Who is it for

ESG analysts, carbon accounting practitioners, and sustainability
consultants evaluating whether a lightweight, transparent tool could
replace part of a manual spreadsheet-based workflow — and reviewers
(recruiters, thesis committee, technical collaborators) assessing the
underlying engineering and domain work.

## Key capabilities

| Destination | What you do there |
|---|---|
| Executive Summary | Get the current ESG grade, total emissions, and data-quality confidence at a glance |
| Carbon Accounting | See the Scope 1/2/3 inventory, trend and forecast, sector benchmark, and (experimental) spatial/land-use context |
| ESG Analytics | Review the E/S/G score breakdown and update Social/Governance disclosure indicators |
| Data Quality | See exactly which fields are flagged, why, and what to fix |
| Governance & Audit | Browse the full audit trail and the methodology library (every formula and weight, with its source) |
| Reporting & Compliance | Check GRI disclosure coverage and export CSV, JSON, Excel, or PDF |
| Decarbonization | Model emission-reduction scenarios against levers (efficiency, electrification, renewable procurement) |

Opening the app puts you straight into **Demo Mode** with a clearly-labelled
synthetic organisation — every page above is immediately explorable with no
setup. Click "Set Up My Organisation" in the sidebar to switch to your own
data.

## Demo vs. real data

| Mode | What it is |
|---|---|
| **Demo** | A clearly-labelled synthetic organisation with a 12-month synthetic dataset — the default on first launch |
| **Real** | Your own organisation profile + uploaded CSV, after "Set Up My Organisation" |

Demo data is never presented as real data, and the two are structurally
isolated — switching to a real organisation clears the demo state rather
than blending it in.

---

## Technical architecture

```
app.py
  └─► state_service                (primary orchestration entry point)
        ├─► carbon_service         ──► calculations/ghg.py
        ├─► esg_service            ──► calculations/esg_scoring.py
        ├─► data_quality_service   ──► calculations/data_quality.py
        ├─► report_service         ──► reportlab (PDF), openpyxl (Excel)
        ├─► gis_service            ──► calculations/gis_math.py, Earth Engine
        ├─► audit_service          ──► audit/writer.py · audit/reader.py
        └─► auth_service           ──► identity/RBAC only, no login system
              └─► repository/      (session_repo · disk_repo · audit_repo)
                    └─► models/    (21 TypedDicts across 9 domain files)
```

**Invariants:**
- `repository/session_repo.py` is the only file that touches
  `st.session_state` — every page, including the onboarding wizard, goes
  through `state_service` wrapper functions instead.
- `calculations/` contains only pure functions — no Streamlit, no I/O, no
  side effects.
- Pages call `state_service` (and, for two specific features,
  `gis_service`/`audit_service` directly); never `calculations` or
  `repository` directly.
- `org_id` is a UUID4 assigned exclusively by the service layer — never
  derived from company name, never constructed in a page.
- The canonical forecast (`state_service.get_forecast_validation()`) is the
  only forecast computation in the platform — no page or export path
  recalculates it independently.
- Input-hash caching (not time-based) backs the ESG/DQ/carbon computation
  and the forecast — same input always returns the same cached result;
  changed input always invalidates.

No multi-user login system exists in this build by design (see "Important
limitations" below) — `services/auth_service.py` retains only the
identity/RBAC boundary (`get_current_user`, `has_permission`,
`init_demo_mode`), with no credential storage, password hashing, or login
UI anywhere in the codebase.

For sprint-by-sprint build history and the detailed findings behind every
remediation round, see `ENGINEERING_HISTORY.md`,
`PHASE5B_REMEDIATION_REPORT.md`, `PHASE6_DELIVERY_REPORT.md`, and
`PHASE5C_GIS_GRADUATION_ASSESSMENT.md`.

### RBAC

| Role | Permissions |
|---|---|
| admin | All — upload, export, report, manage users, view all |
| analyst | Upload, export, view all |
| viewer | View only |

Enforced at the actual mutating action, not at page level — Organisation
Setup, ESG Analytics disclosure updates, and Decarbonization scenario edits
require `can_upload`; Reporting exports require `can_export`/`can_report`.
Executive Summary, Carbon Accounting, Data Quality, and Governance are
read-only and fully accessible to every role. Since this build has no login
screen, the local identity is always `analyst`-level — these gates are
retained as reusable infrastructure for a future authenticated deployment.

### Project structure

```
carbonlens/
├── app.py                  Entry point (session init → routing, no login)
├── pages/                  Seven destinations
├── components/             UI primitives (charts, tables, theme)
├── services/                Business logic orchestration
├── calculations/           Pure functions (zero side effects)
├── models/                 TypedDicts (domain data contracts)
├── repository/             I/O isolation layer
├── state/                  ComputedState lifecycle + input-hash cache
├── audit/                  Append-only audit log
├── config/                 Constants, emission factors, navigation
└── tests/                  606 tests (unit + integration)
```

---

## Testing

```bash
pytest -q                       # full suite — 606 tests
pytest tests/unit -q            # calculations + regression only
pytest tests/integration -q     # integration tests only
```

Continuous integration runs the full suite on every push and pull request —
see `.github/workflows/ci.yml`.

## Methodology & provenance, in brief

- **Carbon accounting**: GHG Protocol-aligned Scope 1/2/3, with a
  province-aware PLN grid emission factor (Kepmen ESDM No. 18/2023) and a
  diesel factor of 2.6967 kg CO₂e/L (IPCC 2006 + AR6 GWP100). Scope 3
  covers 12 of 15 GHG Protocol categories; the 3 excluded categories are
  explicitly screened-and-documented, not silently dropped. Scope 3 factors
  themselves are spend/activity-based proxies (DEFRA 2023, USEEIO v2.0,
  GLEC v3) — each one now carries an explicit "proxy factor, not
  activity-specific" note in the Governance → Emission Factor Library, so
  that limitation is visible in the UI, not just in this README.
- **ESG scoring**: composite score weighted Environmental 40% / Social 30% /
  Governance 30%. These weights, and every other formula/weight in the
  platform, are **CarbonLens's own internal methodology** — the Methodology
  Library (Governance page) states this explicitly and does not attribute
  them to GRI, even where a related GRI disclosure topic is referenced
  alongside a number.
- **Data quality & confidence**: every ESG and DQ score below a 50%
  confidence threshold is marked **Provisional** rather than presented as
  final.
- **Forecasting**: a single validated forecast path (chronological
  holdout, compared against a naive baseline, gated by data-quality status)
  feeds every page and every export — never independently recalculated per
  page.

Full formula-level detail, with citations, is in the in-app Methodology
Library (Governance & Audit → Methodology Library) — that is the
authoritative source, not this README.

### GIS status: Experimental

Carbon Accounting has an opt-in "Spatial / Land-Use Context" tab that
estimates forest cover and above-ground biomass for an approximate site
location. It is permanently badged **EXPERIMENTAL — Modelled Estimate**,
never runs on page load, and falls back to clearly-labelled synthetic data
when Google Earth Engine credentials aren't configured (true in this
development environment). The underlying live-Earth-Engine query path is
fully implemented (Sentinel-2 NDVI + Hansen forest-cover masking) but has
not been exercised against real satellite data — full reasoning in
`PHASE5C_GIS_GRADUATION_ASSESSMENT.md`. It will not be marked "Advanced" or
"Validated" until that's independently demonstrated in a real deployment.

## Important limitations

- **Not production-ready** and not a certified assurance tool. Independent
  verification of emission factors and methodology weights is required
  before any formal regulatory submission (POJK 51, GRI).
- **Scope 3 factors are proxy-based** where exact factor-level provenance
  (a specific document page or dataset row) isn't available — see
  Methodology above and the in-app Emission Factor Library notes.
- **GIS is Experimental** — see above. Don't cite spatial/biomass figures
  from this tab as measured data.
- **Single local user, no login** — this is a deliberate portfolio-scope
  decision, not a partially-built auth system. See Architecture above for
  what would need to change to reintroduce multi-user authentication.
- **Province-centroid GIS buffer**, not a precise facility coordinate —
  intentionally coarse for an exploratory feature.
- **Persistence follows the deployment environment.** `disk_repo` writes
  organisation/state JSON to local disk for cross-session convenience. On a
  host with ephemeral storage (e.g. most free-tier PaaS redeploys), that
  state will not survive a redeploy — this is an accepted limitation for a
  single-user portfolio demo, not a bug, and is not masked by a database
  layer.
- **No AI Consultant / AI-powered features.** Nothing in this codebase is
  LLM- or AI-driven; none of the portfolio-facing copy for this project
  should claim otherwise.

---

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens directly to Home — no login, no credentials.
