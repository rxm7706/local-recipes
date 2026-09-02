---
title: "Query-plane process boundary"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "28404c71f1b3bda015ba1a51957236589bf09303"
review_loop_iteration: 0
followup_review_recommended: false
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/shared/packages/pyforge-atlas/src/pyforge/atlas/"
  - "docs/dreams/pyforge-unifying-strategy.md"
warnings: []
deferred:
  - "Mosaic `duckdb-server` as an optional query face (query-plane-face OQ)."
  - summary: >-
      Reconcile `resilience-invariants.md` BS-5 row to Story 41.2 single-writer-on-RWO / Parquet model (still describes read-only shared mounts).
    evidence: |-
      Companion invariant doc not in Story 41.2 AC scope; Dream/stack updated but tier-2 resilience doc drift remains.
    severity: medium
  - summary: >-
      Extend estate DuckDB policy gate to cover file-backed `ibis.duckdb.connect` and aliased `duckdb` imports.
    evidence: |-
      AST gate matches bare `duckdb.connect` only; production dashboard/semantic layers use no-arg in-memory ibis today but file-backed regression would pass.
    severity: medium
  - summary: >-
      Add positive Helm fixture when writer plane PVC lands (`pyforge.io/query-plane`, RWO).
    evidence: |-
      Chart RWO invariant is vacuous on live render until a plane PVC template exists; spec residual already notes this.
    severity: low
  - summary: >-
      Run duckdb-boundary chart live-render proofs in platform-ci-test (helm currently platform-dev only).
    evidence: |-
      @requires_helm proofs skip in platform-ci-test; guard fixtures only catch synthetic violations, not template regressions.
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The plane is a `.duckdb` **file** with one `filelock`-guarded writer. In Mode C the
writer is a Celery pod and the readers are web and Vizro pods, which implies the
file on RWX storage; DuckDB does not support concurrent access over network
filesystems, `filelock` on NFS is advisory, and the SPEC records BS-5 as
"genuinely unbuilt — production code calls bare `duckdb.connect()`". Red-team
**S-3**, directive **R-11**.

**Approach:** Rule: the `.duckdb` file is never shared across pods. The writer owns it on RWO
storage; everything it publishes for other processes is Parquet (plus the
`vss` index rebuilt by the reader on `ATTACH`); readers open Parquet and the
read-only Postgres attach. Enforce with a policy test that every non-writer
`duckdb.connect(` in the estate passes `read_only=True` or targets `:memory:`,
and a chart test that no PVC labelled for the plane is `ReadWriteMany`.

## Acceptance Criteria

- Given the estate source, when the policy test runs, then every `duckdb.connect(` outside the single declared writer module passes `read_only=True` or `:memory:`; the writer module is named once in `pyforge.atlas` and the test fails if a second appears.
- Given Mode C, when the Vizro/BSL page loads, then it reads Parquet + Postgres attach only; no `.duckdb` path is mounted into web or Vizro pods (chart invariant).
- Given a writer PVC, when rendered, then it is `ReadWriteOnce`; a `ReadWriteMany` claim for the plane fails the invariant.
- Given the Dream § The query plane and `stack.md`, when updated, then "single writer" is restated as "single process on RWO; Parquet is the shared artifact".

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `41-2-query-plane-process-boundary`. Host never imports `pyforge.*`. Kedro stays the only writer of derived layers (FR-27). BSL stays the dashboard contract.

**Block If:** Implementation would put the `.duckdb` file on RWX "with locking", add a DuckDB server as a required kind, or make Mosaic `duckdb-server` mandatory.

**Never:** A reader opening the writer's file without `read_only=True`. Two writable plane files.

</intent-contract>

## Tasks

- [x] Policy test in `pyforge-testing-kit` or atlas tests
- [x] Chart invariant for plane volumes
- [x] Atlas writer module declaration + `read_only=True` sweep
- [x] Dream / stack.md wording
- [x] Ledger `41-2-query-plane-process-boundary` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas kedro-test -k duckdb_boundary`; chart invariants in `platform-dev`.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.

## Code Map

- `pyforge/atlas/duckdb_writer.py` — `DUCKDB_WRITER_MODULE` constant; sole `read_only=False` connect site
- `src/shared/packages/pyforge-atlas/tests/test_duckdb_boundary.py` — estate-wide AST policy gate
- `pyforge/scribe/graph_store_plane.py` — writes via `connect_writer`; reads via `read_only=True`
- `src/platform/tests/test_chart_invariants.py` — reader pod mount + plane PVC RWO invariants
- `docs/dreams/pyforge-unifying-strategy.md` + `stack.md` — single writer on RWO wording

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-02 — Review pass 2 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 3: (high 0, medium 2, low 1)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` PlaneGraphStorePlugin ignored `write` flag — honor `context["write"]` when constructing PlaneGraphStore; add unit test for read-only plugin path.

### 2026-09-02 — Review pass 3 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` Chart reader invariant incorrectly included Celery `worker` (the writer) alongside `web`; AC2 names web/Vizro readers only — restrict `_QUERY_PLANE_READER_COMPONENTS` to `web` (Vizro/BSL runs in web pod).

### 2026-09-02 — Review pass 4 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 22
- addressed_findings:
  - `[medium]` `[patch]` Read-only plane open did not assert `connect_writer` is bypassed — monkeypatch test `test_read_only_open_never_calls_connect_writer`.
  - `[low]` `[patch]` Plugin `write` flag used `bool()` coercion — require strict `is True` so `"false"` cannot open writer path; add `test_plugin_write_string_false_is_not_writer`.

### 2026-09-02 — Review pass 5 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 18
- addressed_findings:
  - none

### 2026-09-02 — Review pass 6 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 21
- addressed_findings:
  - none

### 2026-09-02 — Review pass 7 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 23
- addressed_findings:
  - none

### 2026-09-02 — Review pass 8 (bmad-build-auto dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 24
- addressed_findings:
  - none

## Auto Run Result

Status: done

Summary: Story 41.2 re-dispatched via bmad-build-auto on branch `dispatch/pyforge-steward/41.2` at HEAD `6d82a55866`. Implementation complete since baseline `28404c71f1b3bda015ba1a51957236589bf09303`; review pass 8 (follow-up on `done` spec) confirmed AC coverage with no new patches. Query-plane process boundary: estate AST policy gate, chart invariants (web reader mount ban + plane PVC RWO), `DUCKDB_WRITER_MODULE`, Scribe plane store read/write split, Dream/stack wording.

Files changed (since baseline):
- `pyforge/atlas/duckdb_writer.py` — `DUCKDB_WRITER_MODULE`
- `pyforge/atlas/tests/test_duckdb_boundary.py` — policy + guard tests
- `pyforge/scribe/graph_store_plane.py` — writer/reader connect split; plugin honors `write` with `is True`
- `pyforge/scribe/tests/unit/test_graph_store_plane.py` — read-only reopen, connect_writer bypass, plugin write=False/string
- `src/platform/tests/test_chart_invariants.py` — web-only reader mount ban + plane PVC RWO invariants
- `docs/dreams/pyforge-unifying-strategy.md` — query plane + BS-5 rows
- `spec-pyforge-unifying-strategy/stack.md` — duckdb row
- `sprint-status-ledger.yaml` — `41-2-query-plane-process-boundary: done`

Review findings (pass 8): 0 patches, 0 new deferrals, 24 rejected (duplicates of frontmatter `deferred` or prior passes: ibis/alias AST, helm platform-ci skip, scribe importorskip skips, subPath/ephemeral mount edges, vacuous PVC until template, runtime Parquet/ATTACH vs chart-proxy AC2, resilience-invariants drift, connect_reader seam preference, write=True default, sidecar reader scope, estate scan roots, AST static-limit edge cases). Intent-alignment: diff implements enforcement-first Reading C; runtime Mode C delivery explicitly out of scope. Follow-up review: false (0 patched findings; score 0).

Verification (this dispatch): `pixi run -e pyforge-atlas kedro-test -k duckdb_boundary` → 3 passed; `pixi run -e pyforge-scribe pyforge-scribe-test -k graph_store_plane` → 2 passed, 4 skipped; `pixi run -e platform-dev pytest -c /dev/null --rootdir=src/platform src/platform/tests/test_chart_invariants.py -k duckdb_boundary` → 4 passed.

Residual: No plane PVC in chart yet (Parquet is cross-pod artifact). When writer PVC lands on Celery worker, require `pyforge.io/query-plane: "true"` + RWO. See frontmatter `deferred` list for follow-on work.
