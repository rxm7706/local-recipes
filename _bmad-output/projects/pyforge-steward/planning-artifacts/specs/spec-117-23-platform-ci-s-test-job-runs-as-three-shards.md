---
title: '117.23: Platform CI''s test job runs as three shards'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-23-platform-ci-s-test-job-runs-as-three-shards
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - '.github/workflows/platform-ci.yml'
  - 'tests/durations/platform.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** After PR #2407, a PR that runs every workflow took 196 s of CI, and Platform CI's `test` job was the longest job: 196 s, 141 s of it the platform suite under `pytest -n 4` on one runner (89 s on PR #2405; the suite varies). The station suites are sharded with `pytest-split` (Stories 117.10, 117.21); this job is not, because `pytest-split` is not in the `platform-ci-test` environment.

**Approach:** Add `pytest-split` to the `platform-ci-test` feature and lock it with the pinned pixi. Run the job as three shards, each with its own PostgreSQL and Redis services as now, each running its `pytest-split` group of the suite on top of xdist, with the durations measured from the suite into `tests/durations/platform.json`. The local twin (`platform-ci-local -- --test`) runs the suite unsharded, as the station twins do.

Ledger key: `117-23-platform-ci-s-test-job-runs-as-three-shards`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- spec-pyforge-steward CAP-166 (the CI surfaces registry: a matrix adds no job id; no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Lock only with the pixi version the workspace pins, and prove the lock in a clean clone.
- Keep every step of the job, its services and its timeout; a shard runs the steps the job ran.

**Never:**
- Never delete, skip or re-mark a test, lower a coverage floor, or weaken a lint, type or detector gate to gain time.
- Never move a platform test out of the suite or change what the local twin runs.

## Acceptance Criteria

**Given** Platform CI's `test` job, one runner, 141 s of suite on PR #2407
**When** it runs as three `pytest-split` shards over measured durations
**Then** each shard runs a third of the suite, every test still runs in exactly one shard, and the job's longest shard ends before 120 s

- **AC1 — The lock is current in a clean clone with the pinned pixi.** Expected: exit 0.

  ```bash
  pixi exec --spec pixi=0.80.0 pixi install -e platform-ci-test --locked
  ```

- **AC2 — The workflow meta-tests and the platform policy tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

</intent-contract>

## Evidence (2026-11-26)

PR #2407's `test` job: Initialize containers 26 s, checkout 6 s, Install test dependencies 18 s, Full test suite 141 s (196 s). PR #2405's: 25, 4, 16 and 89 s (140 s). The 53 jobs of #2407 peaked at 40 running at once, and the two jobs created last waited 33 and 38 s for a runner.
