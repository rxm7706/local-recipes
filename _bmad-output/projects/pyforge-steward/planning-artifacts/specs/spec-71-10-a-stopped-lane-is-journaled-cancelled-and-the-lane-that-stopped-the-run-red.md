---
title: "71.10: A stopped lane is journaled cancelled, and the lane that stopped the run red"
type: 'fix'
created: '2026-10-08'
status: 'done'
baseline_revision: '4c3cbb94c56f42f94c61f14839f1f41c92a0343c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-3-selected-lanes-run-concurrently-and-share-no-mutable-state.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-9-a-reduced-suite-lane-never-fails-on-a-segment-that-selects-no-tests.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** when one lane stops `pr-preflight`, the journal and stderr blame the lane it stopped, and they record
the lane that actually failed as `cancelled`. Story 71.3's AC reads: "Given one fake lane that exits 1 while two
others still run When the preflight runs Then it exits 1, the other two are terminated and journaled `cancelled`,
and no child process is left running". Its I/O matrix has `red lane | one exits 1 | others cancelled, exit 1 |
process groups terminated` and `interrupt | SIGINT | every child group terminated | exit 130, journaled`.

- **Every non-zero exit is red.** In `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`,
  `_run_lane_in_pool` (`:300`) journals any non-zero exit `red` (`:336`-`:342`). A lane whose process
  `_RunCoordinator.terminate_children()` (`:219`) sent SIGTERM (`:226`), or SIGKILL after 5 s (`:233`), comes back
  -15 or -9. It is appended to `red_lanes` (`:338`), calls `terminate_children()` again, and returns `red`.
- **The culprit's result is dropped.** The lane that went red calls `terminate_children()` itself (`:341`), and that
  waits for each process it kills. So the killed lane's future finishes before the culprit's. The pool loop takes
  the first finished future (`:499`-`:506`), sees `stop_on_red`, cancels and drops every other future
  (`:507`-`:511`), and never reads their results. Each lane without a collected result is journaled `cancelled`
  with exit 0 and 0 s (`:545`-`:549`). That includes the lane that actually failed, and any lane that was still
  running.
- **The red-lane lines name the wrong lane.** They (`:556`; `:563` under `--keep-going`) print from the journaled
  statuses and `red_lanes`.
- **SIGINT has the same defect.** `_on_sigint` (`:467`) sets `cancel` and terminates the children. The lanes it kills
  come back -15 through the same red branch. The interrupted record (`:516`-`:541`) keeps them `red`, and journals
  lanes without a collected result `cancelled` with 0 s.
- **Measured** in the journal of a one-file herald branch: `hygiene-herald-shelf-two-headings`, two runs at
  `4bf5b746f8` with 14 lanes and `--jobs 16`, so every lane started.
  - `pyforge-herald-coverage-gate`: `red`, exit -15, after 14.0 s and 13.1 s.
  - `pyforge-herald-test`, whose reduced lane's pytest exited 5 (Story 71.9's defect): `cancelled`, exit 0, 0.0 s.
  - `detectors-ci`, `pyforge-doctor-scripts-test`, `pyforge-doctor-aggregate-scripts-test` and `pyforge-core-test`,
    all running: `cancelled`, 0.0 s.

  The run's stderr named the gate, not the herald suite. Anyone reading `.steward/preflight-runs.jsonl` sees the
  wrong lane red, as will Story 71.7's check, which reads that journal.
- **Untested.** `test_red_lane_cancels_others` (`tests/unit/test_preflight_concurrency.py:156`) uses an injected
  `run_lane_ctx` with no process for `terminate_children()` to kill. It asserts only that `a` is `red` and that `c`
  is `cancelled` or `not-run`; it says nothing about `b`, the lane that was running. No test runs a real lane
  process through `_subprocess_lane` (`:238`), and no test sends SIGINT.

**Approach:**

- **The coordinator records whom it terminated.** `terminate_children()` marks a lane's process as terminated only
  when it signals a process that has not exited (`poll() is None` when signalled). It also records what triggered
  the stop: the first lane whose own failure set `stop_on_red`, or `interrupt` for SIGINT.
- **A terminated lane is `cancelled`.** When a lane's process was marked, `_run_lane_in_pool` returns `cancelled`
  with the exit code and seconds observed and `cancelled_by: <lane or "interrupt">`. It does not add the lane to
  `red_lanes`, set `stop_on_red` or call `terminate_children()`.
- **A lane that fails on its own is `red`.** A lane whose process exited non-zero before any signal reached it is
  journaled `red` with its own exit code, as today, even while another stop is in progress.
- **Every started lane's result is collected.** After a stop or an interrupt, the pool loop still cancels futures
  that have not started. It then waits for the futures already running (the pool's own exit waits for them today)
  and journals each from its own result. Only a lane that never started is journaled `cancelled` with exit 0 and
  0 s, as today, with no `cancelled_by`.
- **The verdict and summary come from own failures.** The exit code (1 when any lane failed on its own; 130 when
  interrupted) and the stderr red-lane lines name only lanes journaled `red`. A stopped run still exits 1, and an
  interrupted run 130, as today.
- **Reduced lanes (after Story 71.9).** When the terminated process is a segment of a reduced lane, that segment is
  journaled `cancelled` in `suite_reduction_segments`, the later segments `not-run`, and the lane `cancelled`.

Ledger key: `71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red`.
Type / Effort / Deps: fix / S / S-71.9.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): the preflight "runs them concurrently", and "a red lane still
  refuses the push". Story 71.3 built the run-and-cancel contract quoted above, citing CAP-159 (FR-32), and this
  fix makes the code match that AC. It mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.9, and through it 71.8. 71.8 moves each lane's scratch and 71.9 makes `_subprocess_lane` run
  segments; both edit the runner this story edits, so it lands after them. At `ad6f0428ff`, `preflight.py` is
  unchanged since `875f418334`, and 71.5 (`done`) did not touch it.

## Acceptance Criteria

- **(1) The culprit is red, the stopped lane `cancelled`.**
  - Given two lanes run through `_subprocess_lane` as real processes, with a test seam replacing each lane's
    `pixi run` argv by `sys.executable -c`: lane `fail` exits 1 after about 0.5 s, and lane `sleep` sleeps 30 s.
  - When `run_preflight` runs them with `--jobs 2`, without `--keep-going`.
  - Then:
    - The run exits 1 well under 30 s.
    - `fail` is journaled `red` with exit 1 and seconds above 0.
    - `sleep` is journaled `cancelled`, with a negative exit code as observed, seconds above 0, and
      `cancelled_by: "fail"`.
    - The coordinator's `red_lanes` is `["fail"]`.
    - Stderr names `fail` and does not name `sleep` as red.
    - `sleep`'s process group no longer exists (`os.killpg(pgid, 0)` raises `ProcessLookupError`).
- **(2) An interrupt cancels running lanes.**
  - Given two real sleeping lanes, and a timer that sends SIGINT to the test process once both have started.
  - When `run_preflight` runs.
  - Then it exits 130 and the record's verdict is `interrupted`. Both lanes are journaled `cancelled` with their
    observed exit codes, seconds above 0 and `cancelled_by: "interrupt"`. `red_lanes` is empty, and neither process
    group remains.
- **(3) A lane that fails on its own stays red.**
  - Given a lane process that has already exited 2 when `terminate_children()` polls it.
  - When the run ends.
  - Then that process is not marked terminated, the lane is journaled `red` with exit 2, and it is in `red_lanes`
    beside the lane that stopped the run.
- **(4) A lane that never started stays as today.** Given `--jobs 1` and three lanes, the first of which fails. Then
  the two that never started are journaled `cancelled`, exit 0, 0 s, with no `cancelled_by`.
- **(5) A reduced lane stopped mid-segment.** Given a Story 71.9 reduced lane whose first segment is running when
  another lane stops the run. Then the lane is `cancelled`, the running segment is `cancelled` in
  `suite_reduction_segments`, and the later segments are `not-run`.
- **(6) Existing tests pass.** The 71.1-71.9 preflight tests pass unchanged, including `test_red_lane_cancels_others`
  (`:156`) and `test_keep_going_runs_every_lane_and_names_reds`.
- **(7) Mutations fail the new tests.**
  - Dropping the terminated mark fails (1): `sleep` is journaled `red` and appears in `red_lanes`.
  - Going back to discarding running futures' results fails (1): `fail` is journaled `cancelled`, the symptom
    measured on 2026-10-08.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- A lane's verdict stays its own exit code. A stopped run exits 1 and an interrupted run 130.
- Test lane processes are stdlib `sys.executable -c` scripts with short timeouts, and every test reaps what it
  starts.

**Never:**
- Never change which lanes run (Story 71.2), what a lane runs (71.4-71.6, 71.9), or stop-on-red without
  `--keep-going`.
- Never journal a terminated lane `red`, and never journal a lane that failed on its own `cancelled`.
- Never count a cancelled lane toward the verdict, and never drop an observed exit code or seconds.
- Never change the journal path or remove a field. `cancelled_by` is additive.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` is in the surfaces of `spec-pyforge-steward` and `spec-pyforge-core`, and
`test_preflight_concurrency.py` in `spec-pyforge-steward`'s. Append the reconcile to each Spec
`spec-surface-check` names, then one scoped stamp each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Lane | How its process ended | Journaled | In `red_lanes` |
|---|---|---|---|
| the culprit | exited non-zero on its own | `red`, own exit code and seconds | yes |
| running when the run stopped | SIGTERM or SIGKILL from the coordinator | `cancelled`, observed exit code and seconds, `cancelled_by` | no |
| exited non-zero just before the stop's signal | on its own | `red`, own exit code | yes |
| running at SIGINT | terminated | `cancelled`, `cancelled_by: "interrupt"` | no |
| never started | — | `cancelled`, exit 0, 0 s (as today) | no |
| any lane under `--keep-going` | on its own | `red` or `ok` (as today) | if red |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-08 (cancelled lane) entry.
- Epic: Epic 71 (CAP-159, FR-32; `in-progress`).
- Ledger key: `71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red` (the
  `<epic>-10-<slug>` form, as `14-10-…` and `44-10-…`).
- Ledger status at mint: `backlog`.
- Deps: S-71.9 (and through it 71.8).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched.
- Surface: `preflight.py` and its unit tests. Epic 71 declares no `[epic_surfaces]` entry in steward's
  `marshal-policy.toml`, so marshal's derived default (`src/shared/packages/pyforge-steward/**` among it) applies.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- On a branch where one selected lane fails, run `pixi run -e pyforge-guild pr-preflight` without `--keep-going`.
  Expected:
  - the newest line of `.steward/preflight-runs.jsonl` journals that lane `red` with its own exit code and seconds;
  - each lane that was running is `cancelled` with its observed exit code and `cancelled_by` naming that lane;
  - stderr names only that lane.
- Press Ctrl-C during a run. Expected: exit 130; the record's running lanes are `cancelled` with
  `cancelled_by: "interrupt"`, and no lane process remains.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- **2026-10-09 (landing repair).** AC (6) amended for `test_red_lane_cancels_others`: it now runs `jobs=2`
  instead of `jobs=3`; its body and assertions are otherwise the 71.3 text. Under this story's drain, a lane the
  injected runner had already started is journaled from its own result, so with three workers `c` could start
  before `a` stopped the run and finish `ok` (measured 2 failures in 40 runs). With two workers `c` is still
  queued at the stop and is `cancelled`. The fix turn's edit of that test (an added assertion on `b`, which
  always finishes `ok`) failed the coverage-gate run and is reverted.
- **2026-10-09 (landing repair).** `_run_lane_in_pool` checks the terminated mark before `code == 0`, so a lane the
  coordinator signalled is `cancelled` even when it exits 0 (the Approach and the I/O matrix row "running when
  the run stopped"); it was journaled `ok`.
- **2026-10-09 (landing repair).** AC (7) verified by mutation against a scratch copy of `preflight.py`: dropping the
  terminated mark fails `test_real_subprocess_red_lane_cancels_running_peer` (`sleep` journaled `red`), and
  dropping running futures' results fails it too (`fail` journaled `cancelled`, run exits 0).

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 2, maybe-false 1
- findings:
  - `[low]` `[reject]` `subprocess_argv_for_lane` adds a public test seam on `run_preflight` — acceptable for real-process unit tests; no production caller required.
  - `[false]` `[reject]` Pool drain after stop drops culprit results — verified `results_by_task` collects completed futures before drain; fail lane stays `red`.
  - `[false]` `[reject]` SIGINT path still journals terminated lanes as `red` — interrupt handler sets `stop_trigger` and drain collects `cancelled` with `cancelled_by: interrupt`.
  - `[maybe-false]` `[defer]` AC (7) mutation-failure tests not added — would require deliberate regression harness; core AC (1)–(6) covered by new tests.

## Auto Run Result

Status: done

**Summary:** Preflight coordinator now marks process groups it signals as terminated, journals those lanes `cancelled` with `cancelled_by`, keeps own-failure lanes `red`, and drains in-flight pool futures instead of discarding their results.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` — termination tracking, journal field, pool drain, reduced-segment cancel.
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py` — real subprocess, SIGINT, jobs=1, reduced-lane AC tests.
- Spec memlogs for `spec-pyforge-steward` and co-governor `spec-pyforge-core`.

**Review:** 1 low rejected; 2 false; 1 deferred (AC7 mutation tests). Patched thread-safe `terminated_lane_tasks` updates under `proc_lock`.

**followup_review_recommended:** false

**Verification:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2245 passed, 5 skipped. `python scripts/spec_surface_reconcile.py` — OK after memlog reconcile.

**Residual risk:** Two lanes failing concurrently on their own both remain `red` (by design); only coordinator-signalled exits become `cancelled`.
