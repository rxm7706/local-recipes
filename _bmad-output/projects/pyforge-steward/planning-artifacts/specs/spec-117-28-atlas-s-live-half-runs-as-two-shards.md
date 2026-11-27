---
title: '117.28: Atlas''s live half runs as two shards'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-28-atlas-s-live-half-runs-as-two-shards
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
  - 'tests/durations/pyforge-atlas-live.json'
  - 'tests/durations/README.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `atlas-live-test` is the longest station-test job that still runs unsharded: 97 to 126 s on PR #2412's runs, with a test step of 65 to 84 s. Its task runs three pytest runs (the unit and meta live tests under coverage, the integration live tests, and the inventory quartet), and each spends most of its time starting.

**Approach:** The job runs as two shards, as steward's live half runs four. `PYTEST_ADDOPTS` gives each of the task's three pytest runs its pytest-split group, read from `tests/durations/pyforge-atlas-live.json`. The file is written from empty under xdist with four workers, as the README says. Each shard renames and uploads its own coverage report, `atlas-live-<group>.json`; `atlas-gate` already reads `coverage-atlas-*` artifacts and `atlas-live*.json` reports.

Ledger key: `117-28-atlas-s-live-half-runs-as-two-shards`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every live test runs in exactly one shard, and no shard's pytest run is left with no tests (exit 5).

**Never:**
- Never change what the task runs locally, a test, a floor or the gate's rule.

## Acceptance Criteria

**Given** the two shards run as CI runs them
**When** each runs the task with its group
**Then** both exit 0 and their tests add up to the unsharded run's

- **AC1 — Both shards pass and cover every test.** Expected: exit 0 each, 637 tests between them.

  ```bash
  PYTEST_XDIST_AUTO_NUM_WORKERS=4 PYTEST_ADDOPTS="--splits 2 --group 1 --durations-path=tests/durations/pyforge-atlas-live.json" pixi run --frozen -e pyforge-atlas pyforge-atlas-live-test
  ```

- **AC2 — The durations file is one the workflow names.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_durations_files.py -q
  ```

- **AC3 — On the PR's own CI run, both shards and `atlas-gate` pass.**

</intent-contract>

## Result (2026-11-27)

- `tests/durations/pyforge-atlas-live.json` holds 637 tests (82.5 s of test time), written from empty with `PYTEST_XDIST_AUTO_NUM_WORKERS=4` and `--store-durations`; atlas has no xdist groups, so no id carries a group suffix.
- Run as CI runs them on this machine, shard 1 passed 195, 106 and 50 tests in its three runs, and shard 2 passed 175, 58 and 53: 637 between them, none left empty. Each shard took 66.6 and 71.3 s, against 68.5 s unsharded: here the runs' start-up, not their tests, sets the time, as this Dream's measurement said. The CI shard times are read from the PR's own run.
- AC1: both exit 0. AC2: the durations and workflow tests pass (57).
