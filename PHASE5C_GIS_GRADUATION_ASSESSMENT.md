# CarbonLens V8 — Phase 5-C GIS Graduation Assessment

Per the V8 Final Product Blueprint §10, a Spatial / Land-Use Context feature
graduates from **Experimental** to **Advanced** only once all three
conditions are independently satisfied. This assessment evaluates each one
honestly against what was actually built and verified in this session —
not against what the feature is capable of in principle.

---

## Condition (a) — Biomass citation independently verified against a real calibration dataset

**Status: Addressed at build time, not "verified."**

The previous codebase's NDVI→AGB formula was attributed directly to
Saatchi et al. (2011, PNAS) as if it reproduced their model — it didn't;
Saatchi's actual pantropical biomass map was fit from an ensemble of
ICESat lidar, MODIS, QSCAT/SRTM texture, and ancillary data, not a
single-variable NDVI regression.

Since this feature was built fresh for Phase 5-C rather than retrofitted,
the citation was written honestly from the start
(`config.constants.NDVI_AGB_PROXY_CITATION`): the same functional form is
used (no independently-derived, better-calibrated alternative was available
without real biomass ground-truth data), but it is now labeled a
"simplified proxy... NOT a reproduction of [Saatchi's] ensemble... regression,"
with an explicit NDVI-saturation caveat.

**What this does NOT mean:** the formula itself has not been calibrated or
validated against any real biomass measurement (field plots, lidar,
allometric data). It remains an illustrative order-of-magnitude proxy. The
honest label prevents the false-authority problem the original audit
flagged; it does not make the underlying number scientifically validated.
Graduating this condition for real would require sourcing an actual
calibration dataset and fitting/validating coefficients against it —
outside this session's scope.

---

## Condition (b) — Forest-pixel masking validated against ground truth

**Status: Structurally correct, not "validated."**

`calculations/gis_math.py::estimate_forest_carbon_stock()` is the only
function in this codebase capable of producing a biomass or carbon-stock
figure, and it structurally cannot blend land-cover classes — it requires
a per-class NDVI breakdown and a per-class area breakdown, and only ever
applies the forest-class NDVI to the biomass proxy. A regression test
(`test_estimate_forest_carbon_stock_never_blends_land_cover`) confirms that
changing non-forest NDVI values has zero effect on the output.

This fixes the specific mistake the original codebase made (blending
agriculture/water/built-up NDVI into a single whole-AOI figure). It does
**not** mean the masking has been checked against real ground-truth land
cover for any actual site — the live Earth Engine path (see condition (c))
uses Hansen Global Forest Change's ≥30% canopy-cover threshold as the
forest mask, which is a standard, defensible, citable choice, but "uses a
standard method" and "validated against ground truth for our specific use
case" are different claims. No such validation was performed or attempted.

---

## Condition (c) — At least one live, demonstrable Earth Engine call

**Status: Not satisfied. Cannot be satisfied from this build environment.**

This is the condition that actually gates graduation, and it's worth being
precise about why:

- `earthengine-api` is now a genuine, active, installed dependency —
  `import ee` succeeds (verified: `test_earthengine_api_is_genuinely_installed`).
  This closes the previous gap where the dependency wasn't even listed.
- `services/gis_service.py::_try_live_earth_engine()` is fully implemented:
  it builds a real `ee.Geometry.Point` + buffer, queries Sentinel-2
  surface reflectance for NDVI, masks to forest using the Hansen
  `treecover2000 ≥ 30%` band, and reduces both to a region mean — this is
  a structurally correct, real Earth Engine query, not a stub.
- `ee.Initialize()` requires actual Earth Engine credentials — either a
  service account key or an interactive `earthengine authenticate` session
  tied to a registered Earth Engine account. **This development environment
  has no such credentials and no network path to Earth Engine's API
  domain**, so `ee.Initialize()` correctly and predictably raises a clean
  `EEException`, which the service catches and falls back to synthetic
  data (verified: `test_live_earth_engine_attempt_never_raises_on_missing_credentials`).

**What would actually satisfy this condition:** deploying this app
somewhere with real Earth Engine credentials configured, opening the
Spatial Context tab, clicking "Load Spatial Analysis," and confirming the
result's `data_source` field reads `"earth_engine_live"` instead of
`"synthetic_fallback"`. That is an infrastructure/credentials step that
belongs to Reza, not something achievable inside this development session
— this environment's network allowlist doesn't even reach Earth Engine's
API, so no amount of further code changes here would change this outcome.

---

## Overall verdict

**PHASE 5-C — REMAINS EXPERIMENTAL.**

Two of three graduation conditions were addressed as well as they can be
without real calibration data or a live-credentialed deployment (a: honest
citation, not full validation; b: structurally-correct masking, not
ground-truth-validated). The third condition (c) is a hard requirement this
build environment cannot meet, full stop — it needs Reza's own Earth Engine
account and a real deployment.

This is the intended, honest outcome for this phase. The feature is
correctly built, correctly labeled, gracefully degrades, and does not
overclaim — which is what "Experimental" is supposed to mean. It should
**not** be marked "Advanced," "Production," or "Validated" in the README,
the thesis writeup, or anywhere else until condition (c) is independently
confirmed against a real deployment, and ideally until (a)/(b) get genuine
external validation too.

## What would move this forward

1. Set up an Earth Engine service account for the real deployment; run one
   query; confirm `data_source: "earth_engine_live"` in the result.
2. If pursuing the thesis/journal angle: source a real calibration dataset
   (field AGB plots, published allometric equations for Indonesian tropical
   forest types) and refit the proxy coefficients against it — replacing
   `NDVI_AGB_PROXY_A`/`NDVI_AGB_PROXY_B` with genuinely derived values, and
   updating the citation to describe the actual derivation.
3. Consider whether province-centroid buffering is precise enough for the
   intended use case, or whether real facility coordinates (collected at
   onboarding) would be a more defensible AOI — this was a deliberate
   scope-limiting choice for this session, not a technical ceiling.
