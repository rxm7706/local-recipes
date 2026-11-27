---
title: '117.25: The live halves'' shard durations hold the ids CI looks up'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-25-the-live-halves-shard-durations-hold-the-ids-ci-looks-up
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'tests/durations/pyforge-herald.json'
  - 'tests/durations/pyforge-steward-live.json'
  - 'tests/durations/pyforge-marshal-live.json'
  - 'tests/durations/pyforge-doctor-live.json'
  - 'tests/durations/README.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - .github/workflows/pyforge-station-tests.yml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The live halves' CI shards are uneven. Over four CI runs each shard's test step took: herald's 76 to 89, 50 to 64 and 37 to 60 s; steward's 45 to 56, 29 to 39, 31 to 34 and 51 to 80 s; marshal's 31 to 48 and 58 to 62 s; doctor's 35 to 58 and 17 to 22 s. Herald's longest live shard ends the station path. The cause is the same in all four lanes.

- Under `--dist loadgroup`, xdist's worker appends `@<group>` to each grouped test's id (`xdist/remote.py`), and pytest-split, whose `pytest_collection_modifyitems` runs last, splits on those ids.
- Steward's 60 trigger-map tests are keyed without the suffix, so on CI they count at the file's 0.39 s average. The file still credits them 532 s, from before Story 117.14 grouped them; alone they take 37.6 s.
- Herald's file holds 481 suffixed keys, some under group names herald Story 59.1 replaced.
- Doctor's and marshal's values are stale: doctor's contract module went from 69 to 16.5 s in doctor Story 67.1.
- `--store-durations` merges into the existing file, so a stale key stays.

**Approach:** Measure each file again from empty, under xdist with four workers as on the runner, one lane at a time with nothing else running: herald's two halves into `pyforge-herald.json` (both halves' shards read it), and the live halves of steward, marshal and doctor into their own files. The stored ids are then the ids the CI shards look up. The workflow, the shard counts and the algorithm do not change.

Ledger key: `117-25-the-live-halves-shard-durations-hold-the-ids-ci-looks-up`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Store each file from empty, so no key outlives its test.
- Store under the lane's own task, with four xdist workers and `--dist loadgroup`, as CI runs it.

**Never:**
- Never delete, skip or re-mark a test, change a shard count, or weaken a gate.

## Acceptance Criteria

**Given** each lane's durations file measured again
**When** each shard of a lane collects under xdist, as on CI
**Then** every collected test finds its own duration, and every test runs in exactly one shard

- **AC1 — Each shard's tests, collected under xdist, are all keyed in the file.** Expected: no test falls back to the average.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC2 — The durations-file test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test
  ```

</intent-contract>

## Result (2026-11-26)

- The four files are written from empty, each under its lane's own task with four xdist workers (`PYTEST_XDIST_AUTO_NUM_WORKERS=4`, `--dist loadgroup`), one lane at a time with nothing else running. Herald's two halves are stored after `docs-site-install`, with `HERALD_DOCS_SITE_REQUIRED=1`. A first store without the install skipped 49 built-site tests, against 3 on CI, and was discarded.
- A simulator collects each lane once, gives grouped ids xdist's `@<group>` suffix, and runs pytest-split's own `duration_based_chunks`. With the old files it reproduces CI's split exactly (steward 944/147/650/164 tests, herald 440/126/256). With the new files no test of any shard falls back to the average (AC1).
- `tests/durations/README.md` says how to write a file the way the shards read it, and what a file cannot fix.
- Measured on this machine, every shard run as CI runs it, old file against new: steward's live half 49.0/25.4/21.9/31.2 s became 30.9/26.2/37.1/32.6 s. Herald's 37.3/35.2/30.0 s became 36.6/38.9/35.8 s. Marshal's 36.3/56.8 s became 37.0/52.7 s, and doctor's 37.1/16.5 s became 37.0/18.9 s. Both columns run Story 117.26's and herald 60.1's test code.
- Marshal's and doctor's live halves stay uneven for a reason no file can fix. A shard costs its start-up, collection and coverage (about 25 s for marshal here) plus its longest test: marshal's tea-architecture smoke test takes 27 s, doctor's capability-effect test 22.7 s. `least_duration` put marshal's two long tests in different shards and gave 55.1 and 49.4 s, so the default algorithm stays.
- AC2: `pyforge-doctor-scripts-test` exits 0 (1,400 passed).
- On CI, the PR's two runs gave each shard's test step as follows. Herald: 61/55/55 and 68/76/68 s, against 76–89, 50–64 and 37–60 s over the four runs before. Steward: 38/42/77/60 and 56/27/42/57 s, against 45–56, 29–39, 31–34 and 51–80 s. Marshal: 41/86 and 41/57 s, against 31–48 and 58–62 s. Doctor: 46/22 and 33/19 s, against 35–58 and 17–22 s.
- The second CI run printed every test's time on the runner (`--durations=0 --durations-min=0` on steward's, marshal's and doctor's live shards, removed again in the next commit). Every test id in those logs matched the files. A split simulated from the CI times leaves each lane's longest shard where it is, so the files stay as written on this machine:
  - Steward's trigger-map module costs about 121 worker-seconds on CI, more than a quarter of the lane's 372. It therefore always spans two shards, and each of them runs the shared derivation (about 20 s).
  - Marshal's tea-architecture smoke test takes 37.9 s on CI, and doctor's capability-effect test 17.5 s. Each sets its shard's length.
  - Some tests differ far more between this machine and the runner (`test_ci_status.py::test_ac6_consumers_read_master_fixture` takes 1.0 s here and 21.7 s on CI), but none of them moves a lane's longest shard.
