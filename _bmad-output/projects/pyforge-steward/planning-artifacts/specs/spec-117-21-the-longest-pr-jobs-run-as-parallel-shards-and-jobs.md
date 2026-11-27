---
title: '117.21: The longest PR jobs run as parallel shards and jobs'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-21-the-longest-pr-jobs-run-as-parallel-shards-and-jobs
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - '.github/workflows/detectors.yml'
  - 'docs/governance/ci-surfaces.yaml'
  - 'tests/durations/pyforge-herald.json'
  - 'tests/durations/pyforge-steward-live.json'
  - 'tests/durations/pyforge-marshal-live.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A PR that runs every workflow took 242 s (#2405), bound by `herald-live-test`'s two shards (181 and 204 s, of which 12 to 15 s install `uv` with `setup-uv` although `uv` is in herald's pixi environment) and the gate after them. A warm PR took 168 s (#2406), bound by `scripts-suite`, which runs four suites one after another. `marshal-live-test` is one job of 85 to 103 s of tests, and `steward-live-test`'s four shards are uneven (101, 86, 23 and 21 s).

**Approach:** Run `herald-live-test` as three `pytest-split` shards and drop its `setup-uv` step. Split `scripts-suite` into two jobs that run side by side: the stdlib-only suites in `pyforge-ci`, and the library suites in `pyforge-guild` and `pyforge-doctor`. Run `marshal-live-test` as two shards whose coverage reports the marshal gate merges. Measure the shard durations of herald, steward's and marshal's live halves again after the stories that move them (herald 59.1, steward 117.20).

Ledger key: `117-21-the-longest-pr-jobs-run-as-parallel-shards-and-jobs`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- spec-pyforge-steward CAP-166 (the CI surfaces registry: a job added is a registered surface; no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every step, task and environment a job runs; a split moves steps between jobs and drops none.
- Register every new job in `docs/governance/ci-surfaces.yaml` and render the gates.

**Never:**
- Never delete, skip or re-mark a test, lower a coverage floor, or weaken a lint, type or detector gate to gain time.
- Never narrow a trigger path or a `changes` output (ruling D4, Story 98.1).

## Acceptance Criteria

**Given** the PR jobs of #2405 and #2406
**When** herald's live half runs as three shards without `setup-uv`, `scripts-suite` as two jobs, and marshal's live half as two shards
**Then** a PR that runs every workflow finishes in under 150 s, and no job of a warm PR runs longer than 120 s

- **AC1 — The workflow meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — The CI surfaces registry renders unchanged.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check
  ```

</intent-contract>

## Evidence (2026-11-26)

PR #2405 job steps: `herald-live-test (2)` checkout 12, setup-pixi 14, setup-uv 15, docs-site install 8, tests 148 s; `scripts-suite` (#2406, warm) checkout 24, setup-pixi 27, `pyforge-doctor-scripts-test` 45, aggregate 5, `scripts-lib-test` 54, `pyforge-deps-test` 10 s; `marshal-live-test` tests 85 to 103 s.
