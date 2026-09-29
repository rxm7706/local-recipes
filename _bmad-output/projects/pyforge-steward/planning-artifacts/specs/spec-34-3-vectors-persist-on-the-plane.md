---
title: Vectors persist on the plane
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 9d3ad9105b
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** RAG still defaults to in-memory DuckDB. canopy:FR-48 needs HNSW on the CAP-19 plane writer.

**Approach:** Extract `REAL[]` (or list) rows onto `atlas.duckdb` via `connect_writer`. Cast to `FLOAT[N]`, `LOAD vss` only, nearest-neighbor returns the planted row. Production opener injects that writer.

## Acceptance Criteria

- Given `REAL[]` rows, when the extract runs, then `FLOAT[N]` + `vss` nearest-neighbor returns the planted row.
- Given the writer, when used, then it is the CAP-19 plane (`atlas.duckdb`).
- Given the consumer path, when it boots, then it only `LOAD`s `vss`.
- Given Atlas RAG, when opened for the plane, then it is not a second writable `.duckdb` and not the implicit in-memory default.

## Boundaries & Constraints

**Always:** Same `atlas.duckdb`. `LOAD` only. Ledger `34-3-vectors-persist-on-the-plane`.

**Never:** `INSTALL` on consumer boot. Second `.duckdb`. Mosaic required. Chroma. Start 34.4–34.5 in this spec.

</intent-contract>

## Tasks

- [x] `extract_real_arrays_onto_plane` + `open_plane_rag_store` on `connect_writer`.
- [x] Tests: planted NN; no INSTALL; filename is `atlas.duckdb` only.
- [x] Ledger → `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/test_query_plane_vectors.py -q`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `38d1f8a33a` (2026-08-26, "Merge pull request #869 from rxm7706/steward/34-3-vectors-on-the-plane"). Ledger row `34-3-vectors-persist-on-the-plane: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-3-vectors-persist-on-the-plane.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_vectors.py`, `src/shared/packages/pyforge-atlas/tests/test_query_plane_vectors.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
