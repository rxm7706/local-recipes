---
title: 'Restarts reconcile'
type: feature
created: '2026-08-25'
status: done
baseline_commit: cc235ef3aadb7c0089dd0fc171b6a121d7fcd551
baseline_revision: cc235ef3aadb7c0089dd0fc171b6a121d7fcd551
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A killed Mason boot that re-inserts index rows duplicates them. MinIO/boto3 would be a fourth infra kind (canopy:FR-29, BS-8, canopy:AD-13, parent AD-1).

**Approach:** Mason boot re-index upserts by a stable artifact key against PostgreSQL (and RWX files if present). Interrupted mid-flight + resume → one row per key. Tests fail if reconciliation is removed. No MinIO.

## Boundaries & Constraints

**Always:** Mechanism lives in `pyforge.mason` (`boot.py`). Canonical store is PostgreSQL-shaped unique-key upsert (`INSERT … ON CONFLICT DO NOTHING`). RWX is optional filesystem scan (canopy:AD-13). Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Parent AD-2: no `pyforge.*` under `src/platform/`. Tests fail if reconcile is removed (canopy:AD-15).

**Block If:** Implementation would add MinIO/S3/boto3, put `pyforge.*` under `src/platform/`, or add a pixi package for an object-store client.

**Never:** Start 26.1+. MinIO/S3/boto3. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers. A second index in chrome (`django-mason`) that bypasses mason. Object-store scan.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Interrupted then resume | RWX with 3 files; first boot stops after 1 upsert | Second boot → 3 rows, not 4+; keys unique | `BootInterrupted` on first pass |
| PG-only (no RWX) | Store already has keys; `rwx_root` missing | Reconcile is a no-op upsert; row count unchanged | No error |
| RWX files present | Empty store; two files on RWX | Two rows keyed by relative path | Directories skipped |
| Naive insert (mechanism absent) | Same interrupted+resume against `insert_always` | Duplicate rows | Documents the trap; canopy:AD-15 |
| Reconcile removed | AST of `boot.py` without unique-key `ON CONFLICT` upsert | Test fails | canopy:AD-15 |
| No object store | `boot.py` AST import graph | No `boto3`/`minio`/`s3` | Review-blocking if present |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-mason/src/pyforge/mason/boot.py` -- NEW: `SqliteIndexStore` (PG-shaped unique key), `reconcile_boot`, `scan_rwx`, `insert_always` trap, `BootInterrupted`
- `src/shared/packages/pyforge-mason/tests/unit/test_boot_reconcile.py` -- NEW: live matrix (interrupt+resume, PG-only, RWX, naive trap)
- `src/platform/tests/test_restarts_reconcile.py` -- NEW: estate canopy:AD-15 AST + no MinIO/boto3/S3 (no `pyforge.*` import)
- `src/shared/packages/django-mason/` -- read-only chrome; do not add a second indexer
- `src/shared/packages/pyforge-mason/src/pyforge/mason/models.py` -- read-only leaf; do not park behaviour here
- Never: `src/platform/**` importing `pyforge.*`; Epic 26; pixi.toml; boto3/MinIO

## Tasks & Acceptance

**Execution:**
- `pyforge/mason/boot.py` -- unique-key upsert reconcile + optional RWX scan
- mason unit tests -- interrupt+resume applies once
- `src/platform/tests/test_restarts_reconcile.py` -- canopy:AD-15 + no object-store client

**Acceptance Criteria:**
- Given work interrupted mid-flight, when the process restarts, then the effect applies once.
- And reconcile is against PostgreSQL (and RWX files if any), not MinIO.
- And the test fails if reconciliation is removed.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` platform gate now executes `_UPSERT` SQL (interrupt one row, resume three unique keys) so CI proves once-only without `import pyforge`
  - `[low]` `[patch]` canopy:AD-15 binds `ON CONFLICT` / `PRIMARY KEY` to `_UPSERT` / `_CREATE_INDEX` constants, not a source-wide substring

## Design Notes

`SqliteIndexStore` uses stdlib `sqlite3` with `PRIMARY KEY` and `ON CONFLICT DO NOTHING` — the same SQL PostgreSQL accepts. Tests do not require a live cluster. Artifact key is the POSIX relative path under the RWX root. `insert_always` is the canopy:AD-15 trap: append-only INSERT with no unique key. `interrupt_after` is a test seam that raises `BootInterrupted` after N upserts; production callers omit it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Mason boot re-index upserts RWX files into a PostgreSQL-shaped unique-key table (`ON CONFLICT DO NOTHING`). Interrupted boot plus restart yields one row per artifact. Naive append store duplicates (canopy:AD-15 trap). No MinIO/boto3/S3.

Files changed:
- `pyforge/mason/boot.py` -- `SqliteIndexStore`, `reconcile_boot`, `scan_rwx`, `NaiveAppendStore`
- `pyforge-mason/tests/unit/test_boot_reconcile.py` -- interrupt+resume, PG-only, RWX, naive trap, second full boot
- `src/platform/tests/test_restarts_reconcile.py` -- live SQL once-only + canopy:AD-15 AST + no object-store imports
- this spec

Review findings: 2 patches (medium SQL-in-CI, low AST constants). Deferred 0. Rejected 4 (live PG cluster, concurrent boots, size refresh on same key, django-mason AppConfig.ready). Follow-up review: false (score 4).

Verification: mason unit 5 passed; platform `test_restarts_reconcile` + `test_no_pyforge_import` 4 passed.

Residual: `SqliteIndexStore` is stdlib sqlite with PostgreSQL-compatible upsert SQL, not a live cluster DSN.
