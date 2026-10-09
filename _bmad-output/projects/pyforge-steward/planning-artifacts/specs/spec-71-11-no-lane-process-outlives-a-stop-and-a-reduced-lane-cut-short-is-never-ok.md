---
title: "71.11: No lane process outlives a stop, and a reduced lane cut short is never ok"
type: 'fix'
created: '2026-10-09'
status: 'ready-for-dev'
baseline_revision: 'd377581be4c3e4633743c39a8c84fc32ab90e33d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-3-selected-lanes-run-concurrently-and-share-no-mutable-state.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-9-a-reduced-suite-lane-never-fails-on-a-segment-that-selects-no-tests.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two races in the preflight runner, found by the Story 71.10 landing repair. A lane process that starts
just after a stop is never signalled and runs to completion. A reduced lane that SIGINT cuts short between segments
is journaled `ok`. Story 71.3's AC requires that "the other two are terminated and journaled `cancelled`, and no
child process is left running", and that after SIGINT "no lane's process group is still alive". Story 71.9 requires
that a reduced lane's verdict be the station task's own, minus the tests the gate ran. Read on `d377581be4`, with
71.8-71.10 landed, in `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`:

- **Race 1: a late start escapes the stop.**
  - `_run_lane_in_pool` (`:457`) checks the stop flags for the last time at `:474`. It then builds the lane's scratch
    and environment (`:477`-`:485`) and reaches `subprocess.Popen` in `_run_pixi_argv` (`:294`). Only after `Popen`
    does `register_proc` (`:247`, called at `:302`) add the process to `active_procs`, under `proc_lock`
    (`:248`-`:250`).
  - `terminate_children()` (`:257`) takes its snapshot of `active_procs` under `proc_lock` (`:258`-`:259`) and signals
    only those processes.
  - The stop flag is set before `terminate_children()` runs: `stop_on_red.set()` at `:514` is followed by `:515`, and
    `cancel.set()` in `_on_sigint` (`:658`) is followed by `:661`. A lane that passed `:474` but registers after that
    snapshot therefore starts a process that nothing signals.
  - That lane is not in `terminated_lane_tasks`, so it is journaled from its own result: `ok` or `red`. The pool
    drain waits for it (`:699`-`:709`), so a stopped or interrupted run lasts as long as that whole lane.
  - The same holds for the collection check of a lane whose every segment selected nothing (`:386`).
- **Race 1b: a segment starts after a stop on red.** Story 71.9's segment loop (`_subprocess_reduced_suite_lane`,
  `:309`) checks only `coord.cancel` before each segment (`:321`), never `stop_on_red`. After another lane goes red,
  the next segment of a running reduced lane starts, after the `terminate_children()` that would have stopped it has
  already run.
- **Race 2: SIGINT between segments journals the lane `ok`.**
  - When the loop finds `cancel` set, it records the remaining segments `not-run` and breaks (`:321`-`:331`). The
    for-loop's `else` (`:375`-`:389`) is skipped, so `lane_exit` keeps its initial 0 (`:317`).
  - No process of the lane was running when SIGINT arrived, so `terminate_children()` never marked the lane, and
    `_run_lane_in_pool` journals it `ok` (`:496`, `:508`-`:509`).
  - The interrupted record keeps that `ok` (`:714`-`:721`). The same `ok` follows a cancel seen before the first
    segment.
- **Untested.** The tests 71.10 added (`tests/unit/test_preflight_concurrency.py:397`-`:684`) stop or interrupt
  lanes whose processes are already running. None holds a lane between its stop check and `Popen`, and none stops or
  interrupts a reduced lane between segments.

**Approach:**

- **Registration closes the window.** `register_proc` checks `cancel`, and `stop_on_red` unless `--keep-going`,
  under `proc_lock`. If either is set, it adds the lane to `terminated_lane_tasks` and terminates the new process's
  group (SIGTERM, then SIGKILL after 5 s, as `terminate_children()` does) before returning. A registration that comes
  after the stop flag can no longer escape:
  - The flag is set before `terminate_children()` takes its snapshot.
  - Registration and snapshot both happen under `proc_lock`.
  - So a process either appears in the snapshot, or sees the flag when it registers.
  - The killed lane is journaled through 71.10's terminated branch (`:496`): `cancelled`, with its observed exit code
    and `cancelled_by` set to `stop_trigger`.
- **No segment starts after a stop.** Before each segment (`:321`), and before the collection check, the segment
  loop checks `cancel` and `stop_on_red` (unless `--keep-going`).
- **A lane cut short is never `ok`.** When the segment loop stops before every segment has run, it records the
  remaining segments `not-run` and marks the lane terminated, so `_run_lane_in_pool` journals it `cancelled` with
  `cancelled_by` (the stop trigger, or `interrupt`). A reduced lane is `ok` only when every segment ran and passed,
  or selected nothing, and the collection check, if it ran, exited 0.
- **Test seams.** Two keyword-only hooks join `subprocess_argv_for_lane` (`:533`), for tests only and unused by
  `main()`:
  - `before_popen(ctx)`, called in `_run_pixi_argv` immediately before `Popen`, after every stop check;
  - `between_segments(ctx, index)`, called at the top of each segment iteration from the second segment on, before
    the loop's stop check.

Ledger key: `71-11-no-lane-process-outlives-a-stop-and-a-reduced-lane-cut-short-is-never-ok`.
Type / Effort / Deps: fix / S / S-71.10.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): the preflight "runs them concurrently", and "a red
  lane still refuses the push". It is built by:
  - Story 71.3: the run-and-cancel contract and its ACs quoted above;
  - Story 71.9: reduced lanes and their segments;
  - Story 71.10: the `cancelled` journal shape this story reuses.

  This fix closes the two windows those stories left open. It mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.10, which is `done`: PR #2009 merged as `047665dd1a`.
- **Epic.** Epic 71 is `done`. This backlog story reopens it (`epic-71` moves to `in-progress`), which
  `ledger-regression`'s `epic_reopened_by_new_story` admits when the new story arrives in the same change.

## Acceptance Criteria

- **(1) A lane released after the stop is killed at registration.**
  - Given:
    - three lanes run as real processes through `subprocess_argv_for_lane`: `fail` exits 1, `peer` sleeps 30 s, and
      `late` sleeps 30 s;
    - a `before_popen` hook that holds `late` until `terminate_children()` has returned (an event the test sets
      after the stop);
    - `--jobs 3`, without `--keep-going`.
  - When `run_preflight` runs.
  - Then:
    - the run exits 1 well under 30 s;
    - `late` is journaled `cancelled` with a negative exit code and `cancelled_by: "fail"`;
    - `red_lanes == ["fail"]`;
    - no process group of `late` or `peer` remains (`os.killpg(pgid, 0)` raises `ProcessLookupError`).
- **(2) An interrupt also reaches a late start.** Given the same hook holding a lane until SIGINT has been handled
  (`coord.cancel` is set). Then the run exits 130 and that lane is journaled `cancelled` with
  `cancelled_by: "interrupt"`, with no process left.
- **(3) A stop on red prevents the next segment.**
  - Given a reduced lane of two segments, the first a passing `sys.executable -c` process.
  - Given a `between_segments` hook that, before segment 2, waits until another lane has gone red and
    `terminate_children()` has returned.
  - When the run ends. Then:
    - segment 2 never started (no `Popen` for it);
    - segment 2 is journaled `not-run` with `exit_code` `null`;
    - the lane is `cancelled` with `cancelled_by` naming the failing lane;
    - the run exits 1.
- **(4) SIGINT between segments cancels the lane.** Given the same reduced lane, with the hook sending SIGINT before
  segment 2 and waiting until `coord.cancel` is set. Then:
  - the run exits 130 and the record's verdict is `interrupted`;
  - the lane is `cancelled` with `cancelled_by: "interrupt"`, never `ok`;
  - segment 1 is `passed` and segment 2 is `not-run`.
- **(5) `--keep-going` is unchanged.** Given a red lane and a reduced lane under `--keep-going`. Then the reduced
  lane runs every segment and keeps its own verdict.
- **(6) Existing tests pass.** The 71.1-71.10 preflight tests pass unchanged.
- **(7) Mutations fail the new tests.** Each is applied to a scratch copy of `preflight.py`, as Story 71.10's landing
  repair did:
  - dropping the registration check fails (1) and (2): `late` runs and is journaled from its own result;
  - dropping the `stop_on_red` check before segments fails (3): segment 2 starts, and is `cancelled`, not `not-run`;
  - restoring `lane_exit = 0` on the interrupted break fails (4): the lane is journaled `ok`.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- Do the stop check at registration under the same `proc_lock` that `terminate_children()` uses for its snapshot.
- Keep Story 71.10's journal shape: `cancelled`, the observed exit code and seconds, `cancelled_by`, and a
  never-started lane `cancelled` at exit 0.
- Test hooks block on events with timeouts, never on sleeps alone, and every test reaps what it starts.

**Never:**
- Never change which lanes run (Story 71.2), what a lane or segment runs (71.4, 71.6, 71.9), or stop-on-red without
  `--keep-going`.
- Never journal `ok` for a lane that did not run every segment, or `red` for a lane the coordinator stopped.
- Never let a hook default to anything but `None`, or let `main()` pass one.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` is in the surfaces of `spec-pyforge-steward` and `spec-pyforge-core`, and
`test_preflight_concurrency.py` in `spec-pyforge-steward`'s. Append the reconcile to each Spec
`spec-surface-check` names, then one scoped stamp each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Moment of the stop or interrupt | Today (`d377581be4`) | After |
|---|---|---|
| lane past `:474`, before `Popen` | process runs to completion; own result | killed at registration; `cancelled`, `cancelled_by` |
| lane's process running | `cancelled` (71.10) | unchanged |
| lane not yet started | `cancelled`, exit 0 (71.10) | unchanged |
| reduced lane between segments, stop on red | next segment starts | next segment `not-run`; lane `cancelled` |
| reduced lane between segments, SIGINT | lane `ok`, later segments `not-run` | lane `cancelled` (`interrupt`) |
| reduced lane before its collection check | check starts | check not run; lane `cancelled` |
| `--keep-going` | every lane and segment runs | unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-09 (preflight races) entry.
- Epic: Epic 71 (CAP-159, FR-32). It was `done`; this story reopens it to `in-progress`.
- Ledger key: `71-11-no-lane-process-outlives-a-stop-and-a-reduced-lane-cut-short-is-never-ok`.
- Ledger status at mint: `backlog`.
- Deps: S-71.10 (`done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched.
- Surface: `preflight.py` and its unit tests. Epic 71 declares no `[epic_surfaces]` entry in steward's
  `marshal-policy.toml`, so marshal's derived default (`src/shared/packages/pyforge-steward/**` among it) applies.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- On a branch where one selected lane fails, run `pixi run -e pyforge-guild pr-preflight` without `--keep-going`.
  Expected:
  - the run returns soon after that lane's failure, without waiting for a lane that was still starting;
  - the newest line of `.steward/preflight-runs.jsonl` journals no lane `ok` whose `suite_reduction_segments` hold a
    `not-run` segment;
  - no lane process remains.
- Press Ctrl-C during a run that has a reduced suite lane. Expected: exit 130; that lane is `cancelled` with
  `cancelled_by: "interrupt"` and its later segments `not-run`.
- Mutation checks for AC (7), against a scratch copy of `preflight.py`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
