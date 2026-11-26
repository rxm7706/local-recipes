---
title: '117.16: The scripts-lib lane runs under xdist and builds its flag reports once'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-16-the-scripts-lib-lane-runs-under-xdist-and-builds-its-flag-reports-once
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'tests/scripts/test_flag_inventory.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `scripts-lib-test` runs 1,074 tests on one process: 108 s alone, 286 to 362 s inside a full preflight, and 90 to 157 s of the Detectors `scripts-suite` job, the second bound of a PR's CI (median 234 s). Three tests of `test_flag_inventory.py` each build the same eight live reports (45 s summed).

**Approach:** Pass `-n auto --dist loadgroup` in the task, give an `xdist_group` to the tests that cannot share a worker's process with others, and build the live reports in one module-scoped fixture. CI runs the same task line, so the job gains what the lane gains.

Ledger key: `117-16-the-scripts-lib-lane-runs-under-xdist-and-builds-its-flag-reports-once`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (every pytest lane goes under xdist where its tests allow; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same tree shape, same machine).

**Never:**
- Never drop a file from `tests/scripts/scripts-lib-test.txt`.
- Never delete, skip or re-mark a test to gain time.

## Acceptance Criteria

**Given** the lane on one process
**When** it runs under xdist with its reports built once
**Then** it passes with the same passed and skipped counts
**And** it takes under 40 s alone on 16 threads

- **AC1 — The lane passes with the count it had.** Expected: exit 0, `1074 passed, 3 skipped`.

  ```bash
  pixi run --frozen -e pyforge-guild scripts-lib-test
  ```

</intent-contract>

## Evidence (2026-11-26)

Standalone: 106.67 s for `1074 passed, 3 skipped`, 108 CPU-seconds (one core). `test_the_live_reports_agree_with_the_gate_on_the_warned_specs_of_every_station` 17.9 s, `test_the_live_tree_builds_eight_reports_and_exits_0` 13.8 s, `test_no_table_cell_of_a_live_or_checked_in_report_has_an_odd_number_of_backticks` 13.5 s. CI `scripts-suite`: 234 s median, 318 s at most, over eight PR heads.
