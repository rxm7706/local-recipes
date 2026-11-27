---
title: '117.20: The platform-ci-local concurrency tests start the second run when the first holds the lock'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-20-the-platform-ci-local-concurrency-tests-start-the-second-run-when-the-first-holds-the-lock
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_killed_holder.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Three tests of `test_platform_ci_local_concurrency.py` take about 33 s each. A slow run's stubbed `python` sleeps 8 s on every call, and the second run starts on a fixed clock (one or two seconds after the first), so the first run is made slow enough to be sure to overlap. The CI shard of `steward-live-test` that holds them takes 101 s of tests where the shard beside it takes 21 s.

**Approach:** Start the second run when the first has reached the point the test is about: it holds the lock (its `.holder` record exists), or, without a lock, its services are up. Then a slow run's stubbed `python` needs to sleep only long enough to still be running when the second run arrives: a few seconds, set by the test.

Ledger key: `117-20-the-platform-ci-local-concurrency-tests-start-the-second-run-when-the-first-holds-the-lock`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- spec-pyforge-steward CAP-152 (the platform-ci-local tests the oracle map files under it; no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every assertion each test makes: both runs pass under the lock, a waiter past its wait names the holder, overlapping runs without the lock cross-stop or fail.

**Never:**
- Never delete, skip or re-mark a test, lower a coverage floor, or weaken a lint, type or detector gate to gain time.
- Never change `scripts/platform-ci-local.sh` for a test's timing.

## Acceptance Criteria

**Given** the three overlap tests, about 33 s each
**When** the second run starts when the first holds the lock or has its services up, and the slow stub sleeps seconds
**Then** each test asserts what it asserted, and the three take under 40 s together alone

- **AC1 — The concurrency module passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py -q --durations=5
  ```

- **AC2 — The module passes five times in a row beside a loaded machine.** Expected: exit 0 each time.

  ```bash
  for i in 1 2 3 4 5; do pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py -q -n 4 || exit 1; done
  ```

</intent-contract>

## Evidence (2026-11-26)

`pyforge-steward-live-test` alone on 16 threads, `--durations`: `test_two_overlapping_runs_with_lock_both_pass` 33.60 s, `test_lock_wait_timeout_names_holder` 33.06 s, `test_without_lock_overlapping_runs_do_not_both_pass` 32.80 s. PR #2406's `steward-live-test` shards: 101, 21, 23 and 86 s of tests.

## Review round (2026-11-26)

The independent review found two of the three overlap tests unable to fail for the reason their names give, a defect older than this story: the service stub wrote the postgres stand-in's pid to `.active` and compared it with its own, which always differ, so every stop read as a cross-stop, and only under `PLATFORM_CI_LOCAL_NO_LOCK`. `.active` now names the run that started the services (its stub log), a cross-stop is a stop by another run, the stub writes every start and stop to an ordered `.events` file, the lock test asserts from it that two runs' services were never up at once and the no-lock test that they were. The SIGKILL test kills the holder once its services are up, as its name intends. A parametrized test holds the overlap reading on events written by hand. Measured: the three tests take 8.4 to 9.0 s each (33 s before); the module passed five times in a row with four workers beside 12 busy cores.

## Result (2026-11-26)

A full preflight of all 50 lanes, measured with the harness that measured the baseline on the same machine: 312.5 s cold and 319.1 s warm, against 543.2 s and 532.1 s after PR #2405 (42% and 40% less); about 3,900 CPU-seconds against 6,100. `pyforge-herald-live-test` starts 13 to 17 s in on 6 workers and takes 105 to 118 s; the run is bound by the machine. The only red lanes are `detectors-ci` and `test-ci-meta`, reading the measurement's own uncommitted probe lines, as in the baseline.
