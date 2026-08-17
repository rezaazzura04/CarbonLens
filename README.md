# CarbonLens V8
## ESG and Carbon Accounting Intelligence Platform

**Status:** Sprint 11 — Final Integration Hardening · Pre-Release Candidate  
**Institution:** Teknik Lingkungan, Universitas Brawijaya  
**Purpose:** Undergraduate thesis artefact + Q1 journal publication (target: Journal of Cleaner Production)

---


## Demo Mode (Login-Free Entry)

CarbonLens V8 runs in **Demo Mode** by default — no login required.

A demo identity with **analyst-level permissions** is auto-initialised on app start:

| Property | Value |
|---|---|
| Username | `demo_user` |
| Display Name | `Demo Mode` |
| Role | `analyst` |
| Permissions | view, upload, calculate, export |
| Restrictions | No user management |

**Demo Mode is clearly labelled** and never masquerades as a real corporate user.
All RBAC logic remains active. Audit events are attributed to `demo_user`.

To enable multi-user authentication in production, set `CARBONLENS_AUTH_REQUIRED=true`
and reinstate the login gate in `app.py`.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Default credentials: `analyst` / `analyst123` · `viewer` / `viewer123`

---

## Platform Architecture

```
app.py
  └─► state_service                (primary orchestration entry point)
        ├─► carbon_service         ──► calculations/ghg.py
        ├─► esg_service            ──► calculations/esg_scoring.py
        ├─► data_quality_service   ──► calculations/data_quality.py
        ├─► report_service         ──► components/report_sections.py
        ├─► audit_service          ──► audit/writer.py · audit/reader.py
        └─► auth_service           ──► repository/disk_repo.py
              └─► repository/      (session_repo · disk_repo · audit_repo)
                    └─► models/    (TypedDicts · ComputedState)
```

**Architecture invariants (non-negotiable):**
- `repository/session_repo.py` is the ONLY file that calls `st.session_state`
- `audit/writer.py` is the ONLY audit write point
- `services/state_service.py` is the ONLY ComputedState entry point for pages
- `calculations/` contains ONLY pure functions — no Streamlit, no I/O
- Pages call state_service; never calculations or repository directly

---

## Seven Production Destinations

| # | Destination | Status | Sprint |
|---|---|---|---|
| 1 | Executive Summary | ✅ Production | Sprint 6 |
| 2 | Carbon Accounting | ✅ Production | Sprint 7 |
| 3 | ESG Analytics | ✅ Production | Sprint 8 |
| 4 | Data Quality | ✅ Production | Sprint 9 |
| 5 | Governance & Audit | ✅ Production | Sprint 10 |
| 6 | Reporting & Compliance | ✅ Production | Sprint 11 |
| 7 | Decarbonization | ✅ Production | Phase 5-A |

---

## Sprint Status

| Sprint | Deliverable | Status |
|---|---|---|
| Sprint 2 | Engineering Foundation (models, repo, state, audit, config) | ✅ FROZEN |
| Sprint 3 | Calculation Engine (8 pure modules, 127 unit tests) | ✅ FROZEN |
| Sprint 4 | Business Services (9 services, full DI chain) | ✅ FROZEN |
| Sprint 5 | UI Component System (theme, charts, tables, components) | ✅ FROZEN |
| Sprint 6 | Executive Summary page (reference implementation 1) | ✅ FROZEN |
| Sprint 7 | Carbon Accounting page (reference implementation 2) | ✅ FROZEN |
| Sprint 8 | ESG Analytics page (reference implementation 3) | ✅ FROZEN |
| Sprint 9 | Data Quality Workspace | ✅ FROZEN |
| Sprint 10 | Governance & Audit Workspace | ✅ FROZEN |
| Sprint 11 | Final Integration Hardening | ✅ APPROVED & FROZEN |
| Phase 5-A | Decarbonization Planner (Target Tracker + Scenario Simulator) | ✅ APPROVED & FROZEN |
| Phase 5-B | Forecast Hardening + Demo Mode + P0 Usability + Org Setup | ✅ APPROVED & FROZEN |
| Sprint 12 | Decarbonization page | Scheduled |

---

## Running Tests

```bash
# Full suite
pytest -q

# Unit tests only (calculations + regression)
pytest tests/unit -q

# Integration tests only
pytest tests/integration -q

# Specific sprint
pytest tests/integration/test_sprint11_hardening.py -v
```

**Current test count:** 511 tests · 0 failures · 0 syntax errors

---

## Key Technical Facts

| Parameter | Value | Source |
|---|---|---|
| Diesel EF | 2.6967 kg CO₂e/L | IPCC 2006 + AR6 GWP100 (Phase 0 H3) |
| PLN national grid | 0.7160 kg CO₂e/kWh | Kepmen ESDM No.18/2023 |
| ESG weights | E=40%, S=30%, G=30% | Phase 0 C2 |
| Provisional floor | 50% S/G disclosure | Phase 0 C3 |
| Scope 3 coverage | 12 of 15 categories | GHG Protocol (Phase 0 H2) |
| DQ confidence blend | 40% + 35% + 25% | Phase 2 |
| Methodology library | 29 entries | Phase 3 |
| Audit event types | 16 approved types (13 Phase 3 + 3 Phase 5-A) | Phase 3 / Phase 5-A |
| Demo Mode | Login-free analyst entry | Phase 5-B |
| GRI indicators tracked | 16 | Phase 3 |

---

## Remaining Roadmap

```
Sprint 12  ○  Decarbonization page (Scenario & Target Planner)
Phase 5    ○  Advanced Features (GIS Intelligence, Forecast hardening)
Phase 6    ○  Performance Architecture (input-hash caching, session persistence)
Final QA   ○  External user testing Round 2 (15–20 participants)
Release    ○  Release Candidate — not yet production-ready
```

**This platform is NOT yet production-ready.** It is a validated research artefact for an undergraduate thesis. Independent verification of emission factors and methodology weights is required before formal regulatory submission (POJK 51, GRI).

---

## RBAC

| Role | Permissions |
|---|---|
| admin | All — upload, export, report, manage users, view all |
| analyst | Upload, export, view all |
| viewer | View only |

---

## Project Structure

```
carbonlens_v8/
├── app.py                  Entry point (auth → routing)
├── pages/                  Seven V8 destinations
├── components/             UI primitives (charts, tables, theme)
├── services/               Business logic orchestration
├── calculations/           Pure functions (zero side effects)
├── models/                 TypedDicts (16 domain models)
├── repository/             I/O isolation layer
├── state/                  ComputedState lifecycle + cache
├── audit/                  Append-only audit log
├── config/                 Constants, emission factors, navigation
└── tests/                  368 tests (unit + integration)
```

## Demo Mode — Two-Mode Architecture

CarbonLens V8 implements an explicit two-mode entry model:

| Mode | Trigger | Org | Data |
|---|---|---|---|
| **Demo Mode** | `CARBONLENS_AUTH_REQUIRED=false` (default) | CarbonLens Demo Organisation | 12-month synthetic dataset |
| **Real Mode** | `CARBONLENS_AUTH_REQUIRED=true` | User-configured | User-uploaded CSV |

### Demo Mode flow
```
App launch
  → init_demo_mode()          (analyst identity, no login)
  → init_demo_organisation()  (demo org + dataset in slot 0, idempotent)
  → Executive Summary         (populated — no org-blocked dead-end)
  → all 7 destinations        (accessible)
  → "Set Up My Organisation"  (exits demo, clears slot 0, opens real org flow)
```

Demo Mode is clearly labelled in the sidebar. Demo data is never presented as
real organisational data. The `is_demo=True` flag prevents contamination of
real organisation slots.
