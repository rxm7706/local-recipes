---
title: 'One DuckDB writer'
type: feature
created: '2026-08-25'
status: done
baseline_commit: 9d6df2e39f5
baseline_revision: 9d6df2e39f5
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Concurrent writers can corrupt `atlas.duckdb`. Production atlas still defaults to in-memory `duckdb.connect()` / `ibis.duckdb.connect()`; file handles never pass `read_only=True` (FR-27, BS-5, canopy:AD-15).

**Approach:** One atlas-local opener for the existing `atlas.duckdb` filename. A second writer is refused (filelock, already in atlas). Readers connect with `read_only=True`. Tests fail if that boundary is removed.

## Boundaries & Constraints

**Always:** Mechanism lives in `pyforge.atlas` (atlas is the consumer). Only file basename `atlas.duckdb` — do not invent a second DuckDB file. Readers use `read_only=True`. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. `duckdb` and `filelock` are already atlas run-deps.

**Block If:** Implementation would add a new pixi package, put `pyforge.*` under `src/platform/`, open a DuckDB file that is not `atlas.duckdb`, or require MinIO/S3.

**Never:** Start 25.3, 25.4. MinIO/S3. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers. A second analytical DuckDB file. Wiring Vizro/FastAPI hosts in this story beyond the opener.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Second writer | Live `atlas.duckdb`; writer held | `connect_writer` refuses the second | `SecondWriterRefused`; no second RW handle |
| Reader | Same file after a writer created it | `connect_reader` opens `read_only=True` | Readers do not take the writer lock |
| Wrong filename | Path whose name is not `atlas.duckdb` | Refused | `ValueError` — no second store file |
| Mechanism absent | AST of opener without lock / `read_only` | Test fails (canopy:AD-15) | Documents the unguarded `duckdb.connect` trap |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/rag/store.py` -- today's `duckdb.connect()` default is **in-memory**; injectable `connection` is the file-backed seam (pass `connect_writer` / `connect_reader`)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py` -- `ibis.duckdb.connect()` in-memory query-time Parquet seam; not `atlas.duckdb`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py` -- existing `filelock` is Kedro *Parquet* admission, a different surface
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py` -- NEW: `connect_writer` / `connect_reader` / `SecondWriterRefused`
- `src/shared/packages/pyforge-atlas/tests/test_one_duckdb_writer.py` -- NEW: live file ACs
- `src/platform/tests/test_one_duckdb_writer.py` -- NEW: estate canopy:AD-15 AST gate (no `pyforge.*` import)
- Never: `src/platform/**` shipping `pyforge.*`; Epic 25.3 HTMX / 25.4 reconcile; pixi.toml

## Tasks & Acceptance

**Execution:**
- `pyforge/atlas/duckdb_writer.py` -- exclusive writer + `read_only=True` readers on `atlas.duckdb`
- atlas + platform tests -- live refuse + canopy:AD-15 absence

**Acceptance Criteria:**
- Given a live `atlas.duckdb`, when a second writer appears, then it is refused or serialized.
- And readers use `read_only=True`.
- And the test fails if the boundary is removed.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` DuckDB connection `close` is read-only; writer handle is `LockedDuckDB` so the lock releases on `close()`.

## Design Notes

Atlas does not open a persistent `atlas.duckdb` today — RAG/BSL defaults are in-memory. This story adds the file opener rather than converting those defaults (that would persist RAG onto disk and break F3 tests). Callers that need the file inject `connect_writer` / `connect_reader`. Same-process DuckDB often shares one RW instance, so refuse uses `filelock.FileLock(..., thread_local=False)` with `timeout=0` (already an atlas dep). DuckDB's own cross-process writer lock remains underneath.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Atlas-local opener for `atlas.duckdb`: exclusive `filelock` writer (`SecondWriterRefused` on a second writer) and `read_only=True` readers. In-memory RAG/BSL defaults unchanged. Estate AST test lives under `src/platform/tests/` without importing `pyforge.*`.

Files changed:
- `pyforge/atlas/duckdb_writer.py` -- `connect_writer` / `connect_reader` / `LockedDuckDB`
- `pyforge/atlas/rag/store.py` -- comment pointing file-backed opens at the opener
- `pyforge-atlas/tests/test_one_duckdb_writer.py` -- live ACs
- `src/platform/tests/test_one_duckdb_writer.py` -- canopy:AD-15 AST
- this spec

Review findings: 1 low patch (lock release wrapper). Deferred 0. Rejected 0. Follow-up review: false (score 1).

Verification: `pixi run -e pyforge-atlas pytest …/test_one_duckdb_writer.py -q` → 4 passed. `pixi run -e platform-ci-test pytest src/platform/tests/test_one_duckdb_writer.py tests/meta/test_no_pyforge_import.py -q` → 2 passed.

Residual: RAG/BSL still default in-memory; callers must inject this opener for the persistent file. Writer lock leaks if `close()` is never called.
