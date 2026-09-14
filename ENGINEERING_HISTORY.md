# CarbonLens V8 — Engineering History

This document holds the sprint-by-sprint build history and audit/remediation
findings that used to live in the main README. It exists for anyone who
wants to verify the engineering process (thesis committee, technical
reviewer, future maintainer) without cluttering the product-facing README.

For current architecture, methodology, and status, see `README.md`.
For the full findings/fix detail behind each remediation round, see:
`PHASE5B_REMEDIATION_REPORT.md`, `PHASE6_DELIVERY_REPORT.md`,
`PHASE5C_GIS_GRADUATION_ASSESSMENT.md`.

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
| Sprint 11 | Final Integration Hardening | ✅ FROZEN |
| Phase 5-A | Decarbonization Planner | ✅ FROZEN |
| Phase 5-B | Demo/Real Mode + Forecast Hardening | ✅ Superseded by Phase 5-B Remediation |
| Phase 5-B Remediation | Multi-org isolation, org identity, PDF export, RBAC, persistence handling | ✅ Complete |
| Portfolio Restructure | Login system removed entirely, GRI/benchmark credibility fixes | ✅ Complete |
| Phase 5-C | Spatial / Land-Use Context (Experimental) | ✅ Built, Experimental |
| Phase 6 | Performance Architecture (caching, staged loading, lazy charts) | ✅ Complete / Hardened |
| Final Product Review | Recruiter/ESG/carbon/GIS/product/architecture/academic review + cleanup | ✅ Complete |

---

## Phase 5-B Independent Audit — Findings

An independent source-level release audit found the pre-remediation Phase 5-B
build **NOT READY** at a release score of 56/100. Full before/after detail
in `PHASE5B_REMEDIATION_REPORT.md`. Summary:

| Finding | Severity | Status |
|---|---|---|
| F-01 — Onboarding always wrote to slot 0 regardless of active slot | CRITICAL | ✅ FIXED |
| F-02 — org_id generated from company_name, in the page layer | HIGH | ✅ FIXED |
| F-02b — disk state filename used org_id[:8], collision-prone | HIGH | ✅ FIXED |
| Onboarding page bypassed session_repo (36 direct st.session_state accesses) | HIGH | ✅ FIXED |
| F-03 — report_service duplicated the canonical forecast call | MEDIUM | ✅ FIXED |
| F-04 — PDF export UI claimed availability; raised NotImplementedError | MEDIUM | ✅ FIXED |
| F-06 — RBAC enforced on only 2/8 pages | MEDIUM | ✅ FIXED |
| Disk write failures were never checked by callers | MEDIUM | ✅ FIXED |
| PLN EF default mismatch (0.716 vs canonical 0.7160) | LOW | ✅ FIXED |
| sidebar_nav.py imported repository.session_repo directly | LOW | ✅ FIXED |
| Silent `except Exception: pass` blocks | LOW | ✅ REVIEWED |

## Portfolio Restructure — Findings

Cross-referenced against the original V7 audit documents (security review,
credibility risk assessment) to find gaps the Phase 5-B remediation hadn't
covered.

| Finding | Severity | Status |
|---|---|---|
| Password hashing was bare unsalted SHA-256 (V7-identical vulnerability) | HIGH | ✅ FIXED, then the entire login/password system was removed outright |
| Login/password system left in place but disabled | HIGH | ✅ FIXED — `login()`, `logout()`, password hashing, default credentials all deleted, not just disconnected |
| C2 — Methodology Library's GRI codes sat next to invented weights with no disclaimer | MEDIUM | ✅ FIXED — explicit "not derived from GRI" disclaimer added |
| C5 — Benchmark provenance text existed in code but was never displayed | MEDIUM | ✅ FIXED — surfaced in Methodology Library |
| H2 — Scope 3 screened-category rationale | — | ✅ VERIFIED — already present |

## Phase 6 — Performance Architecture

See `PHASE6_DELIVERY_REPORT.md` for full detail. Summary: input-hash caching
completed and hardened (a real duplicate/less-accurate fingerprint
implementation was found and fixed), session isolation fixed (cache was
previously a bare module-level dict — a real cross-session bug on shared
server processes), Excel/PDF export generation deferred + cached, two
genuinely heavy chart sections made lazy-loaded (Carbon Accounting
trend/forecast chart, Executive Summary ESG pillar charts), forecast and GIS
architecture left untouched by design.

## Final Product Review — Cleanup

A multi-perspective review (recruiter, ESG analyst, carbon accounting
practitioner, sustainability consultant, GIS reviewer, product manager,
technical architect, academic reviewer, real user) found and removed
genuinely dead code and unused dependencies:

- `components/charts/trend_chart.py` — unused duplicate of `line_chart.py`'s `emission_trend_chart`
- `components/report_sections.py` — 314 lines, never imported, stale docstring referencing an unrealized "Sprint 6" PDF plan (PDF was ultimately built directly in `report_service.py`)
- `models/report.py` — unused `GeneratedReport` TypedDict, never instantiated anywhere
- `folium`, `streamlit-folium`, `scipy` — declared in `requirements.txt`, never imported anywhere in source
- Five unused tab-definition lists in `config/navigation.py` (`CARBON_TABS`, `ESG_TABS`, `DATA_QUALITY_TABS`, `DECARB_TABS`, `GOVERNANCE_TABS`) — described sub-tab UI that was never built (including labels like "User Management" and "Carbon Credits" that could mislead a reader into thinking those features exist)
- This README was split into a product-facing `README.md` and this history document

Full findings, scoring, and reasoning in the review conversation this
document was extracted from — this file only captures what changed.
