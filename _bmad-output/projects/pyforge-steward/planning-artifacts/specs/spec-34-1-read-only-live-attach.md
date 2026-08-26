---
title: Read-only live attach
type: feature
created: '2026-08-26'
status: ready
updated: '2026-08-26'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Atlas DuckDB cannot yet federate a multi-schema Postgres read-only. Mode A (CAP-19 / FR-46) has no attach path. Agents and scans still have a hole toward OLTP.

**Approach:** In `pyforge-atlas`, open the plane writer (FR-27 / `duckdb_writer`) and `ATTACH` a fixture Postgres **READ_ONLY**. Prove a federated SELECT across two schemas; prove a write is refused; prove the path is not pandas `SQLQueryDataSet`; prove consumer boot does not `INSTALL` extensions (AD-13: `LOAD` only).

## Acceptance Criteria

- Given a fixture Postgres with two schemas and no `pgvector`, when the plane attaches, then a federated read succeeds and a write through that attach is refused.
- Given the attach path, when reviewed, then it is not pandas `SQLQueryDataSet`.
- Given consumer boot of the attach path, when it runs, then it does not `INSTALL` extensions (postgres / vss).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Ledger key `34-1-read-only-live-attach`. Host never imports `pyforge.*`.

**Block If:** Implementation would add Mosaic `duckdb-server` as required, start 34.2–34.5, add `pgvector` to the fixture, pull OLTP through pandas, or put `django-lasuite` / Vault / a second `.duckdb` writer on the path.

**Never:** `INSTALL` on boot. Write to OLTP via the attach. A ninth station. Airflow. `01_raw`.

</intent-contract>

## Tasks

- [ ] Named attach helper in `pyforge-atlas` (plane connection + `ATTACH … READ_ONLY`).
- [ ] Fixture Postgres: two schemas, no `pgvector`.
- [ ] Tests: federated read green; write refused; no `SQLQueryDataSet`; no `INSTALL` in the consumer path (string/AST gate acceptable).
- [ ] Ledger `34-1-read-only-live-attach` → `review` then `done` via `sprint-ledger-sync` (do not hand-edit the tracked twin as the only write).

## Design notes

- Default OQ `query-plane-face`: **in-process DuckDB**. Do not block on Mosaic.
- Reuse `connect_writer` / `connect_reader` for `atlas.duckdb`. Do not mint a second writable file in this story. Filename generalization is later if 34.3 needs it.
- `LOAD postgres` from the pre-provisioned extension cache only (same shape as `vss` AD-13). If postgres extension is missing, fail loud — do not `INSTALL`.
- Steward owns the through-line; Atlas owns the engine. Tests live under `pyforge-atlas/tests/`.

## Verification

`pixi run -e local-recipes` (or the atlas env already used for `test_one_duckdb_writer`) on the new tests. Host import-linter still green.
