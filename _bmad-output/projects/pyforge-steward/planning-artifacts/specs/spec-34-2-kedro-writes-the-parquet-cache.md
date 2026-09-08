---
title: Kedro writes the Parquet cache
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 9d3ad9105b
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Mode B (canopy:FR-47) has no named Kedro extract. Dashboards and autonomous SQL still have a hole toward OLTP for heavy tables.

**Approach:** In Atlas (the one Kedro home, canopy:AD-21), register named pipeline `query_plane_cache`. Catalog writes compressed Parquet under `data/primary/`. A scan of that file does not use an OLTP writer role. Refresh is Kedro, not Airflow, not `01_raw`.

## Acceptance Criteria

- Given the named pipeline, when `kedro run` (or SequentialRunner of that pipeline) completes, then the Parquet cache exists.
- Given a scan of that cache, when it runs, then it does not open an OLTP writer role.
- Given the refresh path, when reviewed, then it is not Airflow and not an `01_raw` folder tree.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only. Ledger key `34-2-kedro-writes-the-parquet-cache`. Catalog owns IO. Host never imports `pyforge.*`.

**Block If:** Airflow, `01_raw`, a second writable `.duckdb`, Mosaic as required, starting 34.3–34.5 in this spec, pandas SQL federation.

**Never:** `INSTALL` on boot. Vizro-ai. Eight Kedro projects. A ninth station.

</intent-contract>

## Tasks

- [x] Named `query_plane_cache` pipeline + catalog entries (`query_plane_estate_source`, `query_plane_estate`).
- [x] Scan helper that reads Parquet only (no OLTP writer DSN).
- [x] Tests: cache exists after run; scan unused writer DSN; no Airflow / `01_raw`.
- [x] Catalog prefix/count fixtures updated. Ledger → `done` via `sprint-ledger-sync`.

## Design notes

- Kedro is optional for extracts elsewhere; Atlas is the one home.
- Compression via Parquet `save_args` (zstd). Layout `data/<layer>/<name>/`.
- Reuse SequentialRunner in tests if a full `kedro run` CLI needs a pre-seeded source file.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/test_query_plane_parquet_cache.py src/shared/packages/pyforge-atlas/tests/catalog -q`
