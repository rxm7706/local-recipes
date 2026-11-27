---
title: '117.23: Platform CI''s test job runs as three shards'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 117-23-platform-ci-s-test-job-runs-as-three-shards
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - '.github/workflows/platform-ci.yml'
  - 'tests/durations/platform.json'
  - 'tests/scripts/test_durations_files.py'
  - 'src/platform/conftest.py'
  - 'src/platform/tests/test_golden_path_promotion_verdict.py'
  - 'src/platform/tests/test_deploy_gates_on_promotion_verdict.py'
  - 'src/platform/tests/test_golden_path_promotion_closure.py'
  - 'src/platform/tests/test_pixi_environment_first_use.py'
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

## Result (2026-11-26)

- `pytest-split >=0.11.0` is in the `platform-ci-test` feature only. `pixi.lock` gains that one package (0.11.0) in that environment, written with pixi 0.80.0. AC1: `pixi exec --spec pixi=0.80.0 pixi install -e platform-ci-test --locked` exits 0 in a clean clone. `environment.yaml` does not move: the `build` environment it exports does not carry the package. The estate reconcile regenerated the environment matrix of `docs/dreams/pyforge-unifying-strategy.md` (384 packages for `platform-ci-test`) and restamped two generated pages.
- Platform CI's `test` job is a matrix of three groups. `PYTEST_ADDOPTS` gives every pytest run of the job its group: `--splits 3 --group K --durations-path=../../tests/durations/platform.json`. Every step, service and timeout of the job stays.
- Trap: the path must follow `=`. Written as a separate value, an option value that names an existing path moves pytest's rootdir to the repository root. The suite then loses `src/platform`'s pytest settings (`--ds`, `--import-mode=importlib`, the `--ignore` of the dlt test): 15 errors with `AppRegistryNotReady`, or an import error.
- `tests/durations/platform.json` is measured from the full suite through the local twin: 1,590 tests, 348 s of test time, keys relative to `src/platform`. The three groups hold 607, 383 and 600 tests, about 116 s of test time each, and no test is in two groups.
- `tests/scripts/test_durations_files.py` reads the durations path from Platform CI's workflow too, in both spellings, so the file is held to exist and is not reported as orphaned.
- AC2: `pyforge-steward-live-test` exits 0 (1,904 passed). `pyforge-doctor-scripts-test` exits 0 (1,400 passed) and `scripts-lib-test` exits 0 (1,074 passed). The local twin still runs the suite unsharded (`platform-ci-local -- --test`: 1,570 passed, 23 skipped).
- First CI run (PR #2409, run 45929563925): the three shards took 93, 99 and 119 s, each under the 120 s bound, with 37 to 51 s of suite. Shard 2 failed one test, `test_honest_non_clean_promotion_record_is_refused_by_deploy`: its `warden scan` exited 1 with no output.
- Cause, a race the old single job hid: the runner installs only `platform-ci-test`, so the first `pixi run -e pyforge-warden` installs that environment, and that install builds and reinstalls its path packages (`pyforge-core`, `pyforge-testing-kit`, `pyforge-warden`). In the single job one test happened to run it alone first (22 s). In shard 2, two workers started it in the same millisecond, and one process uninstalled `pyforge-warden` while the other ran it. A local check showed the mechanism: of three concurrent first runs, two uninstalled `pyforge-warden`; on an installed environment, none did.
- Fix: a session fixture in `src/platform/conftest.py`, `pyforge_warden_env`, runs `pixi install -e pyforge-warden` once, under an exclusive lock in the parent of the base temporary directory (shared by the xdist workers). The three modules that run the environment use it. `tests/test_pixi_environment_first_use.py` reds a module that runs a pixi environment without its install fixture. From a fresh `pyforge-warden` environment, the three modules passed 3 runs of 3 under `-n 4`. `platform-ci-local -- --test` passes (1,573 passed, 23 skipped).
