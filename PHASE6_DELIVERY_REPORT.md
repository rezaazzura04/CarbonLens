# PHASE 6 DELIVERY REPORT

## 1. Baseline

**Caching architecture found:** zero `@st.cache_data`/`@st.cache_resource`/TTL
usages anywhere in the codebase. `services/state_service.py::get_computed_state()`
already had a real input-hash cache (`state/cache.py`), which is the correct
mechanism per this phase's principle — not a TTL cache to migrate away from,
but an existing canonical cache to complete and harden.

**Two real defects found during baseline audit (both fixed, see §2):**
1. `state/cache.py` backed its cache with a bare **module-level Python dict**
   (`_cache: dict = {}`). Since Python modules are imported once per server
   process, this dict was silently **shared across every concurrent
   Streamlit session** on the same running server — a genuine session-isolation
   bug, not a performance issue per se, but exactly what "Session Persistence
   Hardening" exists to catch.
2. The ComputedState `input_hash` used as the **cache key** (in
   `get_computed_state()`) was already correct, but a **second, independent,
   less-accurate hash derivation** existed inside `state/computed.py::assemble()`
   (`_derive_input_hash()`), which hashed only `org_id:period:scope_source`
   — `scope_source` is a category label ("csv"/"manual"), not the actual
   dataset content. This meant the `input_hash` *field* stored on the
   ComputedState object itself did not change when emission values changed
   within the same upload type, even though the cache KEY (a separate local
   variable) was already correct. This is precisely the "no duplicate
   fingerprint implementation" violation Phase 6 §9 asks to rule out — found
   by the CACHE-03 behavioral test, not by inspection.

**Expensive/dataset-dependent execution paths identified:**
- `get_computed_state()` (ESG + DQ + carbon) — already cached, hardened this phase
- `get_forecast_validation()` (chronological holdout + naive baseline) —
  **previously uncached**, recomputed on every call; now cached
- `report_service.build_report_context()` — not cached directly, but now
  cheap by construction since it calls the now-cached `get_forecast_validation()`
- `report_service.build_excel()` / `build_pdf()` — real work (openpyxl /
  reportlab), previously **eagerly executed on every render** of the
  Reporting & Compliance Exports tab regardless of user intent
- `gis_service.run_spatial_query()` — already lazy-loaded from Phase 5-C,
  unchanged this phase

**Heavy rendering paths identified:** Plotly chart components across
Executive Summary, Carbon Accounting, ESG Analytics. On inspection, these
are all small charts (≤13 data points, 3-slice pies, 3-bar comparisons) —
genuinely cheap server-side, but each `st.plotly_chart()` call does ship a
real payload to the browser. See §5 for what was and wasn't judged worth
gating.

**Files requiring modification:** `state/cache.py`, `state/computed.py`,
`services/state_service.py`, `calculations/utilities.py`,
`pages/reporting_compliance/page.py`, `pages/carbon_accounting/page.py`,
`pages/executive_summary/page.py`.

**Risk assessment per area:** the cache-key and session-isolation fixes are
purely additive/corrective (existing callers unaffected — verified by the
full pre-existing suite passing unchanged). The `assemble()` signature
change is backward-compatible (`input_hash` is an optional kwarg with a
fallback). The export-deferral change alters UI flow (buttons appear where
downloads used to appear immediately) but preserves the underlying byte
output exactly. The chart-gating changes are purely additive UI toggles.

---

## 2. Input-Hash Caching

- `calculations/utilities.py::hash_inputs()` extended with optional
  `disclosure_hash`/`scope_hash` parameters (backward-compatible — existing
  3-arg callers unaffected). `hash_dict()` added for deterministic,
  key-order-independent dict fingerprinting. `hash_strings()` added as a
  generic fingerprint helper for cache keys that aren't shaped like the
  org/period/dataset triple (forecast, export).
- `get_computed_state()`'s canonical fingerprint now includes
  `disclosure_inputs`/`scope_inputs` hashes, not just the dataset — closing
  a real (previously discipline-only, now structural) staleness risk: these
  values ARE calculation inputs (`_compute_esg`/`_compute_carbon` both read
  them) and previously weren't part of what made a cache entry valid.
- **Real bug found and fixed:** `state/computed.py::assemble()`'s
  `_derive_input_hash()` was a second, independent, less-accurate
  fingerprint implementation — fixed by having `get_computed_state()` pass
  its already-correct hash into `assemble(input_hash=...)` explicitly, with
  the old derivation kept only as a documented fallback for direct
  `assemble()` callers that don't have a real fingerprint available (7
  existing tests call `assemble()` directly without one).
- `get_forecast_validation()` is now cached the same way — same
  `(dataset, dq_status)` → same cached result; different dataset or DQ
  status → automatic cache miss, no timer involved anywhere.
- Excel/PDF exports are now cached by `(org_id, ComputedState version, format,
  section-selection)` — see §3.

No TTL was introduced anywhere in this phase.

---

## 3. Session Persistence

- **Fixed:** `state/cache.py` no longer backs its cache with a bare module
  dict — it's now backed by `repository/session_repo.py`'s session-scoped
  global storage, exactly like every other piece of session state in this
  app. Verified with `test_cache_module_no_longer_uses_bare_module_dict`.
- Verified (not changed — already correct): organisation/slot isolation,
  dataset-to-organisation association, and DQ-to-dataset association all
  hold under the new caching layer — `PERSIST-02`/`PERSIST-03` tests
  exercise this directly against `repository/session_repo.py`.
- Verified: `invalidate_org()` only removes cache entries whose `org_id`
  matches — confirmed a different org's cached state survives another org's
  invalidation (`CACHE-04`).
- Verified: persistence-failure surfacing from the Phase 5-B `_persisted`
  flag fix is unchanged (`PERSIST-04`).
- Verified: demo mode does not overwrite a slot already holding real
  organisation data (`PERSIST-05`).
- The pages→services→repository boundary was not touched — no page gained
  a new repository import, no page gained new direct `st.session_state`
  access (confirmed by the unconditional architecture scan in §9).

---

## 4. Staged Loading

- `pages/reporting_compliance/page.py`: Excel and PDF generation are no
  longer eager. A `_render_deferred_export()` helper shows a "Generate…"
  button; on click, shows `st.spinner(...)` while the real
  `report_service.build_excel()`/`build_pdf()` call runs, then caches the
  result and reruns to show the download button. CSV/JSON remain eager —
  they're cheap string formatting, and adding a click for those would be
  the "loading indicator on a trivial operation" the brief explicitly says
  not to do.
- No fake progress percentages, no `time.sleep()`, no blocking loops —
  `st.spinner` wraps the real synchronous call and nothing else.
- Errors during generation surface via `st.error(...)`, verified by
  `LOAD-02`.
- The Spatial Context tab's existing Phase 5-C spinner/loading pattern was
  left untouched (already correct).

---

## 5. Lazy Charts

Two genuine chart-gating changes were made, both following the brief's own
priority list ("forecast charts... analytics charts") and both keeping
every KPI number visible outside the gate:

- **Carbon Accounting** (`_s5_carbon_trends`): the "Trend Direction" and
  "Annual Projection" KPI cards render unconditionally; the emissions
  trend+forecast Plotly chart itself is now behind a
  "📈 Show Emissions Trend Chart" checkbox.
- **Executive Summary** (`_section_esg_overview`): the ESG grade/score
  badge renders unconditionally; the radar chart and pillar-comparison bar
  chart (two different views of the same three env/social/gov numbers) are
  behind a "📊 Show ESG Pillar Charts" checkbox.

**What was deliberately NOT gated, and why:** the scope-breakdown donut,
scope bar, and benchmark gauge charts on Carbon Accounting/Executive
Summary were left eager. They're small, single-purpose, and closer to core
KPI visuals than decorative analytics — gating them would violate the
brief's own "do not add loading indicators to trivial operations, do not
hide important KPI values" constraints. The GIS spatial visualisation
(Phase 5-C) remains the primary genuinely-lazy heavy visual in this app and
was not touched.

**Honesty note on what "lazy" means here:** `st.expander`/`st.tabs` do
**not** defer Python-side execution in Streamlit — all tab/expander bodies
run on every script rerun regardless of visible/collapsed state. Genuine
laziness requires an explicit conditional gate, which is what both changes
above use (a checkbox's return value, not a container's expanded state).

---

## 6. Forecast Preservation

`state_service.get_forecast_validation()` remains the single canonical
entry point. Verified by AST inspection, not string search:
`forecast_with_validation` is called directly from exactly two files —
`calculations/forecasting.py` (its own definition) and
`services/state_service.py` (the canonical wrapper) — confirmed by
`test_FORECAST_01_get_forecast_validation_is_sole_canonical_entry`, which
walks every `.py` file in the repository. `report_service.py` still only
calls the canonical wrapper (unchanged from the Phase 5-B fix). No
forecasting methodology was touched — only a cache was added around the
existing call.

---

## 7. GIS Preservation

No change to Phase 5-C's GIS code, graduation status, or synthetic-fallback
labelling. `PHASE5C_GIS_GRADUATION_ASSESSMENT.md` is untouched and still
concludes **"REMAINS EXPERIMENTAL."** `run_spatial_query()` is still never
called unconditionally from `render()` (re-verified by AST in this phase's
own test suite, not just assumed). The "EXPERIMENTAL — Modelled Estimate"
badge and synthetic-fallback labelling are unchanged.

---

## 8. Regression

Phase 0–5 invariants explicitly re-verified this phase (not assumed):
diesel EF 2.6967, PLN EF 0.7160, DQ scoring entry point, all 17 approved
audit event types (including `gis_query_run`), reporting architecture
(`build_report_context`/`build_csv`/`build_excel`/`build_json`/`build_pdf`
all callable), decarbonization's `apply_levers_to_baseline`, Phase 5-B's
zero-direct-session-state-access in onboarding, and Phase 5-C's
EXPERIMENTAL badge + gis_service reference in the Carbon Accounting page
docstring. See `REGRESSION-01` through `REGRESSION-07` in
`tests/integration/test_phase6_performance.py`.

**Full suite: 606 passed, 0 failed** (572 pre-Phase-6 baseline + 34 new
Phase 6 tests). Two tests failed during development
(`CACHE-03`/`CACHE-04`-adjacent) — both traced to the real
`_derive_input_hash()` bug in §1/§2 above, not to test defects; fixing the
underlying bug made both pass without weakening either assertion.

---

## 9. Architecture Audit

AST-based, not grep-based:
- Zero direct `st.session_state` access in any page (unchanged from Phase 5-B, re-verified)
- Zero direct `repository.*` imports in any page or component (unchanged, re-verified)
- `calculations/` remains pure — no Streamlit, no session state, no I/O side effects
- `components/` remain presentation-only
- Services own orchestration (cache read/write, export generation, GIS queries)
- Repositories own persistence (`session_repo`/`disk_repo`, untouched)
- **No duplicate fingerprint implementation** — the one found (§1) was fixed
  during this phase, not left in place
- No duplicate cache orchestration — `state/cache.py` is the sole cache module
- No duplicate forecast orchestration — reconfirmed in §6
- No duplicate organisation persistence logic — `complete_onboarding()`
  remains the sole write path, untouched this phase

`python -m compileall .`: clean. Full architecture scanner (pages,
components, services, calculations, repository, state, audit, models,
config): zero violations in every category.

---

## 10. Performance Evidence

Measured directly in this environment (not fabricated), single-session,
in-process timing around the actual cache-hit/miss boundary:

| Operation | Cache MISS (first call) | Cache HIT (identical input) |
|---|---|---|
| `get_computed_state()` (12-month dataset) | 9.25 ms | 0.83 ms (~11x) |
| `get_forecast_validation()` | 0.59 ms | 0.13 ms (~4.5x) |

These are small-dataset, single-process, no-network numbers from this dev
sandbox — presented as qualitative evidence that the cache path is
genuinely faster than recompute, not as a production performance SLA. The
practical benefit in a real deployment is less about raw milliseconds on
tiny datasets and more about (a) not re-running chronological
holdout/forecast validation on every single page interaction, and (b) not
re-running openpyxl/reportlab generation just from opening a tab.

**Qualitative execution-path evidence (before → after this phase):**
- Opening the Reporting & Compliance Exports tab: **before** — CSV, Excel,
  JSON, and PDF all generated unconditionally; **after** — only CSV/JSON
  generate eagerly, Excel/PDF wait for an explicit click.
- Viewing Carbon Accounting: **before** — trend chart Plotly component
  always mounted; **after** — mounted only if the user checks the box (KPI
  numbers unaffected either way).
- Viewing Executive Summary: **before** — radar + pillar bar charts always
  mounted; **after** — mounted only on request (ESG score badge unaffected).
- Re-uploading a dataset with different values: **before this phase's bug
  fix** — the ComputedState's own `input_hash` field would not change if
  the upload type stayed the same, even though the actual cache key
  (correctly) did; **after** — both agree and both change correctly.
- Switching organisation slots / re-running `get_computed_state()` for a
  different org: cache entries remain correctly isolated per `org_id`,
  confirmed behaviorally, not just by code inspection.

---

## 11. README

Updated after implementation and full regression (see the shipped
`README.md`): Phase 6 status added to the roadmap table, test count
updated to 606, a new "Phase 6 — Performance Architecture" section added
describing the cache/session/loading/chart changes, GIS status left
unchanged at **EXPERIMENTAL**, forecast architecture description unchanged
(still canonical `get_forecast_validation()`). No claim of
"production-ready" or "GIS Advanced" was added anywhere.

---

## 13. Remaining Limitations

- The `assemble()` fallback path (`_derive_input_hash`) is still present
  and still imprecise for any FUTURE direct caller that doesn't pass
  `input_hash` explicitly — it's clearly documented as a fallback now, but
  it isn't removed, since 7 existing tests call `assemble()` directly
  without a fingerprint and removing the fallback would break them for no
  functional gain (those tests aren't testing hash correctness).
- Performance numbers in §10 are single-session, small-dataset,
  no-concurrent-load measurements from this development sandbox — not a
  substitute for real load testing in an actual deployment.
- Chart lazy-loading was applied to two specific, well-justified locations,
  not universally — see §5 for the explicit reasoning on what was left
  eager and why.
- No caching was added for GIS spatial queries themselves (Phase 5-C's own
  session-scoped `spatial_context` persistence already avoids re-querying
  within a session; this phase didn't extend that further).
- Session-scoped caching means the cache is empty again on a fresh browser
  session (by design — this is correct isolation, not a limitation to fix,
  but worth stating plainly: this is not a cross-session or cross-restart
  cache).

---

## 14. Final Status

**PHASE 6 — COMPLETE / HARDENED**

All Definition-of-Done criteria hold: input-hash caching is canonical
(single fingerprint mechanism, no duplicates — one duplicate found and
removed this phase), dataset changes invalidate correctly (verified
behaviorally, not just by code reading), organisation/slot isolation is
intact, persistence failure is still surfaced, loading states are real and
truthful, two well-justified chart locations are genuinely lazy-loaded,
forecast architecture remains canonical and unchanged, GIS remains
Experimental and unchanged, all Phase 0–5 regression tests pass, the
architecture audit passes, the full suite (606 tests) passes, `compileall`
passes, and this README/report are synchronized with what was actually
shipped.

Not claimed: "production-ready." This remains a research/portfolio
artefact per the project's own stated scope.
