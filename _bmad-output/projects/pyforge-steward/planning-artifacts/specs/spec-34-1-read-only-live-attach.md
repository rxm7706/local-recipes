---
title: Read-only live attach
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 784ca512df6a9fba6b7b0fd1843003d53b23b33e
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

**Problem:** Atlas DuckDB cannot yet federate a multi-schema Postgres read-only. Mode A (CAP-19 / canopy:FR-46) has no attach path. Agents and scans still have a hole toward OLTP.

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

- [x] Named attach helper in `pyforge-atlas` (plane connection + `ATTACH … READ_ONLY`).
- [x] Fixture Postgres: two schemas, no `pgvector`.
- [x] Tests: federated read green; write refused; no `SQLQueryDataSet`; no `INSTALL` in the consumer path (string/AST gate acceptable).
- [x] Ledger `34-1-read-only-live-attach` → `review` then `done` via `sprint-ledger-sync` (do not hand-edit the tracked twin as the only write).

## Design notes

- Default OQ `query-plane-face`: **in-process DuckDB**. Do not block on Mosaic.
- Reuse `connect_writer` / `connect_reader` for `atlas.duckdb`. Do not mint a second writable file in this story. Filename generalization is later if 34.3 needs it.
- `LOAD postgres` from the pre-provisioned extension cache only (canopy:AD-22; same
  LOAD-only shape as Atlas `vss` in `rag/store.py`). If postgres extension is
  missing, fail loud — do not `INSTALL`.
- Steward owns the through-line; Atlas owns the engine. Tests live under `pyforge-atlas/tests/`.

## Verification

`pixi run -e pyforge-atlas -- pytest src/shared/packages/pyforge-atlas/tests/test_read_only_live_attach.py src/shared/packages/pyforge-atlas/tests/test_one_duckdb_writer.py -q`. Host import-linter still green.

## Suggested Review Order

**Attach helper**

- Entry: LOAD-only then ATTACH READ_ONLY on an existing plane handle
  [`live_attach.py:56`](../../../../../../src/shared/packages/pyforge-atlas/src/pyforge/atlas/live_attach.py#L56)

- Fail loud when the postgres extension cache is empty
  [`live_attach.py:42`](../../../../../../src/shared/packages/pyforge-atlas/src/pyforge/atlas/live_attach.py#L42)

**Same writer file**

- No second `.duckdb`; live Postgres rides `connect_writer`
  [`duckdb_writer.py:4`](../../../../../../src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py#L4)

**Proofs**

- Two-schema fixture, federated JOIN, write refused
  [`test_read_only_live_attach.py:87`](../../../../../../src/shared/packages/pyforge-atlas/tests/test_read_only_live_attach.py#L87)

- Runtime execute log is SET/SET/LOAD only
  [`test_read_only_live_attach.py`](../../../../../../src/shared/packages/pyforge-atlas/tests/test_read_only_live_attach.py)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `27c4cc64b1` (2026-08-26, "Merge pull request #866 from rxm7706/steward/34-1-read-only-live-attach"). Ledger row `34-1-read-only-live-attach: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/live_attach.py`, `src/shared/packages/pyforge-atlas/tests/test_read_only_live_attach.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
