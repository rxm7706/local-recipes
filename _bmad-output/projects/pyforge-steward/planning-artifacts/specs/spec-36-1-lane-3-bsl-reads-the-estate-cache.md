---
title: Lane 3 BSL reads the estate cache
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 79fbe9fa65
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Vizro/BSL still has no declared model over the CAP-19 estate Parquet (canopy:FR-47). Lane 3 cannot prove it reads the plane cache.

**Approach:** Add a BSL model + dashboard loader over `query_plane_estate`. Query returns planted rows. No OLTP DSN. No vizro-ai.

## Acceptance Criteria

- Given the 34.2 Parquet cache, when the BSL model queries it, then planted rows return.
- Given the loader, when reviewed, then it does not open an OLTP writer role.

## Boundaries & Constraints

**Always:** Ledger `36-1-lane-3-bsl-reads-the-estate-cache`. Atlas BSL seam. Host never imports `pyforge.*`.

**Never:** vizro-ai. Django raw SQL. A new Vizro page inventory (DW-D2). Mosaic required.

</intent-contract>

## Tasks

- [x] `build_estate_cache_model` + `load_estate_cache`.
- [x] Test over planted Parquet; no postgres DSN on the loader.
- [x] Ledger via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/test_estate_cache_bsl.py src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py -q`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `d9ac225a4f` (2026-08-26, "Merge pull request #872 from rxm7706/steward/36-1-lane-3-bsl-estate-cache"). Ledger row `36-1-lane-3-bsl-reads-the-estate-cache: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-36-1-lane-3-bsl-reads-the-estate-cache.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/__init__.py`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py`, `src/shared/packages/pyforge-atlas/tests/test_estate_cache_bsl.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
