---
title: Estate cache Vizro page
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: d9ac225a4f
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** 36.1 landed the BSL loader; Lane 3 still has no Vizro page for the estate cache.

**Approach:** Add a grounded `estate-cache` page to the Atlas Vizro inventory, wired to `load_estate_cache`. Dry-run only — no server. Not vizro-ai. Not imported into Django.

## Acceptance Criteria

- Given `build_dashboard`, when it runs, then an `estate-cache` page exists with a stable id and title.
- Given planted estate Parquet, when the page loader runs, then it matches an independent BSL query.
- Given the host, when reviewed, then `src/platform/` does not import Vizro.

## Boundaries & Constraints

**Always:** Ledger `36-2-estate-cache-vizro-page`. Reuse `_data_page`. Host never imports `pyforge.*` or `vizro`.

**Never:** vizro-ai. 28-page inventory. Mosaic required. Django Vizro mount.

</intent-contract>

## Tasks

- [x] `PAGE_INVENTORY` + `build_dashboard` wire `estate-cache`.
- [x] Dry-run test: page present; loader equals independent BSL query.
- [x] Ledger via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py src/shared/packages/pyforge-atlas/tests/test_estate_cache_bsl.py -q`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9446d14bc2` (2026-08-26, "Merge pull request #873 from rxm7706/steward/36-2-estate-cache-vizro-page"). Ledger row `36-2-estate-cache-vizro-page: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-36-2-estate-cache-vizro-page.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py`, `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
