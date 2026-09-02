---
title: "Query-plane process boundary"
type: "fix"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
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

- [ ] Policy test in `pyforge-testing-kit` or atlas tests
- [ ] Chart invariant for plane volumes
- [ ] Atlas writer module declaration + `read_only=True` sweep
- [ ] Dream / stack.md wording
- [ ] Ledger `41-2-query-plane-process-boundary` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-atlas pyforge-atlas-test -k duckdb_boundary`; chart invariants in `platform-dev`.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
