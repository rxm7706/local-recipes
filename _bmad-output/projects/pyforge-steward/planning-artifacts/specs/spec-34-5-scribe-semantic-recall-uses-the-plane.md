---
title: Scribe semantic recall uses the plane
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 9d3ad9105b
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Semantic recall ranks on PostgreSQL/pgvector (28.2). canopy:FR-50 moves ranking onto the CAP-19 plane behind the store port.

**Approach:** A `PlaneGraphStore` driver writes embeddings to `atlas.duckdb` and ranks with DuckDB SQL. `recall.answer(..., mode="semantic")` still calls `query_similar` only. Callers do not `isinstance` the driver. Lexical recall is unchanged.

## Acceptance Criteria

- Given the durable plane driver, when semantic recall runs, then a no-overlap query still hits.
- Given callers, when reviewed, then they do not `isinstance` the driver.
- Given lexical recall, when run, then it is unchanged.
- Given a private Chroma or in-memory DuckDB path, when constructed, then it fails.

## Boundaries & Constraints

**Always:** Ledger `34-5-scribe-semantic-recall-uses-the-plane`. Port only — no `GraphStore` class rename. Host never imports `pyforge.*`.

**Never:** Chroma. Implicit `:memory:` DuckDB as the index home. Second `.duckdb`.

</intent-contract>

## Tasks

- [x] `graph_store_plane.py` + CAP-18 plugin (owner `atlas`).
- [x] Tests: no-overlap hit; no isinstance; lexical unchanged; chroma / memory refused.
- [x] Ledger → `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/test_scribe_plane_recall.py -q`
`pixi run -e pyforge-scribe -- pytest src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py -q`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `79fbe9fa65` (2026-08-26, "Merge pull request #871 from rxm7706/steward/34-5-scribe-semantic-on-the-plane"). Ledger row `34-5-scribe-semantic-recall-uses-the-plane: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-5-scribe-semantic-recall-uses-the-plane.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-atlas/tests/test_scribe_plane_recall.py`, `src/shared/packages/pyforge-scribe/pyproject.toml`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plane.py`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py`, `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
