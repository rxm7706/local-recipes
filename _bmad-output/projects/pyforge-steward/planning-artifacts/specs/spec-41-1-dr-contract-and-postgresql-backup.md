---
title: "DR contract and PostgreSQL backup"
type: "feature"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "CRITICAL"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/deploy/charts/platform/templates/postgres-statefulset.yaml"
  - "src/platform/deploy/charts/platform/values.yaml"
  - "src/platform/deploy/README.md"
warnings: []
deferred:
  - "Standby replica / CloudNativePG (sizing)."
  - "Object-store destination plugin beyond the RWX default (steward deploy-profile)."
---

<intent-contract>

## Intent

**Problem:** The chart ships one PostgreSQL replica on an 8 GiB PVC with no backup, no WAL
archive, no point-in-time recovery, no restore drill and no stated RPO/RTO. The
Dream's sizing table promises "1 primary + 1 standby, 100–500 GB" and BS-8's
"idempotent startup reconciliation with PostgreSQL as the canonical anchor"
presupposes a restore that nothing produces. A lost PVC loses Guildhall content,
supervisor history, Langflow flows, Scribe's graph and every `RunState`. Red-team
**B-2**, **S-8**, directive **R-3**.

**Approach:** Write the one-page DR contract first (per store: RPO, RTO, mechanism, owner,
drill cadence, reconciliation order) as a tracked doc under `deploy/`, then ship
the smallest mechanism that meets it: a Helm CronJob on the platform image
running `pg_basebackup` plus continuous WAL archiving (`archive_command`) to a
profile-selected destination (RWX PVC by default; object store via the steward
deploy-profile plugin), a `restore.md` runbook, and a `pyforge steward` duty
that performs a restore into a scratch database and asserts row counts (the
drill). Standby/operator (CloudNativePG / Crunchy) stays a sizing option named
in the contract, not built here.

## Acceptance Criteria

- Given `deploy/DR.md`, when read, then every store (PostgreSQL, redis-broker, redis-cache, media RWX, DB-GPT SQLite PVC, DuckDB cache) has RPO, RTO, mechanism, owner and drill cadence, and the BS-8 reconciliation order is written down.
- Given `helm template`, when rendered with defaults, then a `CronJob` on the platform image runs a base backup on a schedule value and the postgres container has `archive_mode=on` with an `archive_command` targeting the backup volume; disabling it is a values choice that renders a loud NOTES.txt warning, never a silent default.
- Given the OCP overlay, when rendered, then the backup CronJob carries the same `restricted-v2` contexts as every platform-image pod.
- Given `pyforge steward restore --drill`, when run against a backup, then it restores into a scratch database, asserts `run_state` / Wagtail page counts match the backup manifest, and exits non-zero on mismatch; the duty freezes evidence like every steward duty (crash exit 70).
- Given the Dream sizing table, when updated, then the PostgreSQL row states the shipped shape (1 replica + backup) and names the operator/standby option as sizing, not proof.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `41-1-dr-contract-and-postgresql-backup`. Host never imports `pyforge.*`. Backups run on the platform image (no second image). Secrets by reference only (canopy:AD-12). Steward duty exit domain unchanged.

**Block If:** Implementation would add a PostgreSQL operator, a second Postgres image, or MinIO as a required kind; or would claim PITR without a WAL archive.

**Never:** A backup that lands on the same PVC as the data with no second copy. `pg_dump` alone called "PITR".

</intent-contract>

## Tasks

- [x] `deploy/DR.md` (contract) + `deploy/restore.md` (runbook)
- [x] CronJob template + values (`postgres.backup.*`), archive settings on the StatefulSet
- [x] steward `restore --drill` duty + test
- [x] chart invariant tests for CronJob presence and contexts
- [x] Dream sizing row
- [x] Ledger `41-1-dr-contract-and-postgresql-backup` → `done`.

## Dev Notes

**2026-09-02 — landed in two parts.** The implementation merged as
`9a201b96fd` ("Merge 41-1 into main"), but its ledger row was never advanced
off `backlog`. `marshal factory drain --station pyforge-steward` therefore kept
selecting 41.1 every tick; each dispatch's supervisor correctly read
`story_merged_on_main: true` and closed the run ~1.2 s after launch without
touching the ledger, so the next tick re-dispatched. Nine concurrent
`bmad-build-auto` sessions accumulated in one worktree before the loop was
stopped. The row below is what breaks it.

That first merge also shipped three defects, all fixed here:

1. **`volumes:` on `StatefulSet.spec` instead of the pod spec.** `helm template`
   with default values (`postgres.backup.enabled: true`) rendered
   `StatefulSet.spec.volumes` — not a `StatefulSetSpec` field — leaving
   `spec.template.spec.volumes` empty while the postgres container still mounted
   `backup`. The API server rejects that pod outright, so **the DR story stopped
   PostgreSQL from starting at all.** The invariant test asserted the
   `volumeMount` but never a backing volume, so it passed either way.
2. **`archive_command` with no `mkdir -p`.** Archiving starts at boot; the
   CronJob does not create `wal/` until its first scheduled run, so every
   segment failed and `pg_wal` grew unbounded on the data PVC for up to a full
   schedule interval.
3. **The chart's first CronJob broke three test helpers.** A CronJob nests its
   pod template at `spec.jobTemplate.spec.template`; three helpers reached for
   `spec.template` and raised `KeyError: 'template'`, and a fourth hard-coded
   `len(pvcs) == 3` against the new backup PVC. Four tests in
   `test_chart_invariants.py` were red on `main`. AC 3 (OCP overlay
   `restricted-v2` on the backup CronJob) was crashing rather than checking.

Verification after the fix: `test_chart_invariants.py` 62/62 pass (was 59/62 on
`main`); `pyforge-steward-test` 998 pass. Six collection errors elsewhere in
`src/platform/tests` (`test_atlas_mcp_host`, `test_front_door_publish`,
`test_mcp_host_sidecar`, `test_start_get_survives_disconnect`,
`test_structlog_otel_correlation`, `policy/test_test_databases_still_migrate`)
are pre-existing on clean `main`, need a live Django DB fixture, and are
unrelated to this story.

## Verification

`pixi run -e platform-dev -- python -m pytest -o addopts= src/platform/tests/test_chart_invariants.py -k backup`; `pixi run -e pyforge-steward pyforge-steward-test -k restore`.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.1). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `c8988f5799` (2026-09-02, "steward: fix Story 41.1 backup chart defects and close its ledger row"). Ledger row `41-1-dr-contract-and-postgresql-backup: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-1-dr-contract-and-postgresql-backup.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/deploy/charts/platform/templates/postgres-statefulset.yaml`, `src/platform/tests/test_chart_invariants.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
