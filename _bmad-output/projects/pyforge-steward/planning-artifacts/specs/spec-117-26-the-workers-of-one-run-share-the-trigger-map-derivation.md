---
title: '117.26: The workers of one run share the trigger-map derivation'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-26-the-workers-of-one-run-share-the-trigger-map-derivation
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_station_tests_trigger_map.py` is one xdist group (Story 117.14), so its 60 tests run in one worker and `real_derivation()`, cached per process, is computed once. That derivation takes 27.1 s over 20 jobs that do not depend on each other (the slowest, marshal's package half, 5.75 s), and the module takes 37.6 s. On CI the shard that holds the group takes 51 to 80 s of tests, the longest of steward's live half.

**Approach:** When the run has xdist workers (`PYTEST_XDIST_TESTRUNUID`), each job's reads are derived once.
- The first worker to claim a job takes the job's lock, derives it, and writes it as JSON to a directory the run's workers share.
- A worker that reaches a job another worker holds waits on the lock and reads the file.
- Each worker takes the jobs in an order offset by its index, so the workers derive different jobs at once.

With the derivation shared, the module needs no xdist group. A run without xdist, or a platform without `fcntl`, derives in-process as before.

Ledger key: `117-26-the-workers-of-one-run-share-the-trigger-map-derivation`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- A shared derivation is exactly the in-process one: the JSON round trip keeps every key, path and handoff.
- The directory is the run's own, so two runs never read each other's derivation.

**Never:**
- Never change what the module asserts, or skip a test.

## Acceptance Criteria

**Given** the module run under xdist with several workers
**When** the workers derive the jobs
**Then** each job is derived once in the run, every worker reads the same reads, and the module passes

- **AC1 — Steward's live half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — A shared derivation equals the in-process one.** Expected: the round-trip test passes.

  ```bash
  pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -n 4
  ```

</intent-contract>

## Result (2026-11-26)

- `derive_all` derives in-process when there are no xdist workers (or no `fcntl`); otherwise each job goes through `derive_shared`, under a lock per job in `$TMPDIR/station-tests-trigger-map-<PYTEST_XDIST_TESTRUNUID>/`.
- The first pass takes each job's lock without blocking: a free job is derived and written (renamed into place), a written one is read, and a held one is skipped. The second pass waits for the skipped jobs. A first version that only staggered each worker's start, and waited on every held lock, took about 12 s per worker; this one takes about 9.7 s (27.1 s of work, the slowest job 5.75 s).
- The module's `xdist_group` mark is gone. It now takes 19.5 s on 4 workers against 37.5 s on one. The longest chain is one worker's share of the derivation followed by `test_every_read_and_declared_glob_fires_its_job` (8.7 s, 999 subprocess calls).
- Four new tests: a shared derivation equals the in-process one, and a second worker reads the file rather than deriving again; a job another worker holds is skipped, then read; each of four workers starts on a different job and takes every job; outside xdist nothing is shared.
- AC1: `pyforge-steward-live-test` exits 0 (1,908 passed). AC2: the module passes under `-n 4` (64 passed).
