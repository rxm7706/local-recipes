---
title: '71.12: Every cancelled lane names what stopped the run'
type: 'fix'
created: '2026-10-23'
status: 'in-review'
baseline_revision: '9fc4cb1c2b04c5746b92b7c0931eea8d82e6b729'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1), and pr-preflight is a gate, as 105.1, 106.1 and 107.1 recorded
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-11-no-lane-process-outlives-a-stop-and-a-reduced-lane-cut-short-is-never-ok.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-88-1-the-preflight-runs-each-task-once-after-its-dependencies.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_lane_identity.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_docs_site_mutex.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-105-1-the-preflight-never-runs-two-docs-site-lanes-at-once.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the preflight journals some cancelled lanes with no `cancelled_by`, and which ones depends on how the
scheduler interleaved. So `test_red_dependency_cancels_dependents` fails under load. Atlas Story 37.11's full
`pr-preflight` (branch HEAD `63cb853a8a`, 2026-10-22) went red on that test alone: `KeyError: 'cancelled_by'` at
`assert by_task["a"]["cancelled_by"] == "d"`, 1 failed and 2901 passed. In isolation it passed 10 runs of 10.

Read at `9fc4cb1c2b` in `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`. Four places journal a
lane the stop keeps from running:

- `_run_lane_in_pool`'s red-stop checks (`:1001`, `:1024`) return `cancelled` with `cancelled_by` from
  `_stop_cause(coord, "red")`.
- Its interrupt checks (`:999`, `:1022`) return `cancelled` with no cause.
- `run_preflight`'s result assembly gives every lane with no result `cancelled`, exit 0, 0 s, with no cause: after an
  interrupt (`:1427`) and after a red stop (`:1456`).

Story 71.10 AC (4) pinned the last shape: "the two that never started are journaled `cancelled`, exit 0, 0 s, with no
`cancelled_by`".

**Why it is timing.** In the 88.1 fixture lane `a` depends on `b` and `c`, `b` depends on `d`, and `d` goes red.
`_mark_dependency_blocked` (`:1338`) journals a dependent only once every dependency has a result. The scheduler
offers a lane only while no red stop is set (`:1364`). Under load the pool thread can run `d` to its end while the main
thread is still filling slots, so `c` is never submitted. Then `a` keeps a dependency with no result, and `c` and `a`
reach `:1456` with no cause. A lane carries a cause when the scheduler submitted it before the stop (the pool names
`d`) and none when it did not; `a`, never submitted itself, carries one only when `c` was.

**Measured at `9fc4cb1c2b`** with the test's fixture and an injected runner (a session probe through the real `run_preflight`, not kept):

- `--jobs 1`, every run: only `d` starts; `b` reads `cancelled_by: d`; `c`, `a` and `e` read `cancelled` with no
  `cancelled_by`.
- `--jobs 4`, idle machine: `d` and `c` start; `a` reads `d`; `e`, never submitted, has no cause.

**Approach:** the four uncaused sites take the stop's cause from `_stop_cause`, as the red-stop checks and the
terminated-lane path already do. After a red stop the default is `red`; after an interrupt it is `interrupt`. The
first recorded cause wins, so after a red stop followed by SIGINT a never-started lane names the red lane, as the
lanes the interrupt terminated already do. A never-started lane is still told apart by exit 0 and 0 s. The SIGINT
handler records its cause before it sets `cancel`, as a red lane records its cause before `stop_on_red` (review
finding 4), so a pool thread that sees a stop flag always finds its cause.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): the preflight "runs them concurrently", and "a red
  lane still refuses the push". It is built by:
  - Story 71.10: the `cancelled` journal shape and `cancelled_by`, which this story completes;
  - Story 88.1: a dependent of a red lane is journaled `cancelled` with `cancelled_by` the red lane;
  - Story 103.5: `cancelled_by_environment`, the red lane's environment; an interrupt names none.

  This fix mints no CAP and changes no `SPEC.md` text.
- **Replaces Story 71.10 AC (4), and Story 105.1's matching clause.** A never-started lane now names the stop's
  cause. AC (4) held only for a lane the scheduler never submitted: the pool already named the cause for a lane it
  turned away. So one lane's journal differed by scheduling. Story 105.1 restated it for a deferred docs-site lane
  (`spec-105-1-…md:108`: "a lane that never started: … no `cancelled_by`, as Story 71.10 states"). `cancelled_by`
  stays additive (71.10's own constraint). `preflight.py` is its only reader in `src/` and `scripts/`; three tests
  pinned its absence and now pin the cause.
- **A dependent of a lane turned away on an interrupt now names `interrupt`** (review finding 2). After SIGINT the
  scheduler still submits ready lanes (`:1364` filters only a red stop), and the pool turns them away. Before, such a
  lane carried no cause, so `_dependency_blocker` (`:906`, `:910`-`:911`) fell through to the dependency's own task and
  environment; now it names `interrupt`, with no environment, in `cancelled_by` (and in `blocked_by` under
  `--keep-going`). The new value names the root cause, as a dependent of a lane cut off by a red stop already does.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.11, which is `done`.
- **Epic.** Epic 71 is `done`. This backlog story reopens it (`epic-71` moves to `in-progress`), which
  `ledger-regression`'s `epic_reopened_by_new_story` admits when the new story arrives in the same change.

## Acceptance Criteria

- **(1) A lane the stop kept from being submitted names the red lane.**
  - Given the 88.1 fixture (`a` depends on `b` and `c`, `b` on `d`, `e` independent, `d` exits 1), `--jobs 1`, an
    injected runner, without `--keep-going`.
  - When `run_preflight` runs.
  - Then:
    - only `d` starts, and the run exits 1;
    - `d` is `red` with no `cancelled_by`;
    - `b`, `c`, `a` and `e` are `cancelled`, exit 0, 0 s, with `cancelled_by: "d"` and
      `cancelled_by_environment` `d`'s environment;
    - on `9fc4cb1c2b` the same test fails (`c`, `a` and `e` carry no `cancelled_by`).
- **(2) The flaky test asserts every cause.** `test_red_dependency_cancels_dependents` asserts `cancelled_by: "d"`
  and `d`'s environment on every lane it reads `cancelled`, whatever the interleaving.
- **(3) The pool's interrupt checks name the cause.** A direct `_run_lane_in_pool` call with `cancel` set and the
  stop cause `("interrupt", None)` returns `cancelled` with `cancelled_by: "interrupt"` and no environment, and runs
  nothing. So does a call that sets `cancel` while the lane waits for its service lock (the second check).
- **(4) An interrupted run names `interrupt` for a never-started lane.** `--jobs 1`, two lanes, SIGINT while the first
  runs: `second` is `cancelled`, exit 0, 0 s, `cancelled_by: "interrupt"`, no `cancelled_by_environment`.
- **(5) The three tests that pinned 71.10 AC (4) assert the cause instead.**
  `test_jobs_one_never_started_lanes_have_no_cancelled_by` and
  `test_sigint_leaves_a_never_started_lane_cancelled_without_cancelled_by` are renamed for what they now pin;
  `test_after_a_red_stop_no_lane_starts_even_one_pending_lanes_depend_on` (Story 105.1) keeps its name. Each keeps
  its exit-0, 0-s assertions.
- **(6) A dependent of a lane turned away on an interrupt names `interrupt`.** Given lanes `x` and `w` running at
  `--jobs 2`, `w` running the installed SIGINT handler, `y` submitted afterwards and turned away, and `z` depending on `y`, every step
  ordered by events. Then `y` is `cancelled` with `cancelled_by: "interrupt"`; `z` is `cancelled` with
  `cancelled_by: "interrupt"` (`not-run` with `blocked_by: "interrupt"` under `--keep-going`); neither carries an
  environment key.
- **(7) Nothing else moves.** The scheduler, which lanes run and in what order, the exit codes, the verdicts,
  `red_lanes`, `--keep-going`'s `not-run` status and the journal of lanes that ran are unchanged. The other preflight
  tests pass unchanged; `pixi run --frozen -e pyforge-steward pyforge-steward-test` is green.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- Read the cause through `_stop_cause`, so a reader never sees a task without its environment.
- Every new test is deterministic: it orders lanes with `--jobs 1`, calls `_run_lane_in_pool` directly, or (AC (6))
  orders `--jobs 2` lanes by events and runs the installed SIGINT handler from a lane rather than sending a signal,
  and never sleeps to win a race.

**Never:**
- Never change which lanes run, the order they start in, or stop-on-red without `--keep-going`.
- Never add a journal key to the record or to a lane's schema. Only the cause fields of a cancelled lane or a
  blocked dependent change: `cancelled_by` and `cancelled_by_environment` appear on lanes that lacked them, and a
  dependent of a lane turned away on an interrupt names `interrupt` with no environment (AC (6)).
- Never restructure the scheduler loop or `_mark_dependency_blocked`.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` is in the surfaces of `spec-pyforge-steward` and `spec-pyforge-core`, and the preflight
tests in `spec-pyforge-steward`'s. Append the reconcile to each Spec `spec-surface-check` names, then one scoped stamp
each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Cancelled lane | Today (`9fc4cb1c2b`) | After |
|---|---|---|
| terminated by a red stop | `cancelled_by` the red lane (71.10) | unchanged |
| terminated by SIGINT | `cancelled_by: interrupt` (71.10) | unchanged |
| submitted, turned away by a red stop | `cancelled_by` the red lane (103.5 review) | unchanged |
| submitted, turned away by an interrupt | `cancelled`, no cause | `cancelled_by` the first stop cause (`interrupt`) |
| dependent `_mark_dependency_blocked` reached, dependency red or cut off by a red stop | `cancelled_by` its dependency's cause (88.1) | unchanged |
| dependent of a lane turned away on an interrupt | `cancelled_by` the dependency itself, with its environment | `cancelled_by: interrupt`, no environment |
| never submitted, red stop | `cancelled`, no cause | `cancelled_by` the red lane, with its environment |
| never submitted, interrupt | `cancelled`, no cause | `cancelled_by` the first stop cause (`interrupt`, or the red lane before it) |
| `--keep-going`, dependent of a red lane | `not-run`, `blocked_by` (88.1) | unchanged |
| `--keep-going`, dependent of a lane turned away on an interrupt | `not-run`, `blocked_by` the dependency, with its environment | `not-run`, `blocked_by: interrupt`, no environment |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-23 (a cancelled lane names no cause) entry.
- Epic: Epic 71 (CAP-159, FR-32). It was `done`; this story reopens it to `in-progress`.
- Ledger key: `71-12-every-cancelled-lane-names-what-stopped-the-run`.
- Ledger status at mint: `backlog`.
- Deps: S-71.11 (`done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the decision; `SPEC.md` untouched.
- Surface: `preflight.py` and its unit tests. Epic 71 declares no `[epic_surfaces]` entry in steward's
  `marshal-policy.toml`, so marshal's derived default (`src/shared/packages/pyforge-steward/**` among it) applies.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file.

**Manual checks (not a dispatch gate):**
- AC (1)'s test against `preflight.py` at `9fc4cb1c2b`: expected red, naming a cancelled lane with no `cancelled_by`.
- `test_red_dependency_cancels_dependents` repeated under load (several copies of the suite at once): expected green
  every run.

## Spec Change Log

- 2026-10-23, after the independent review (FAIL; its session report is not kept, and its findings are listed under
  Review Triage Log; read against this spec at `26ebdea86f`): AC (5) names three tests, not two (Story 105.1's docs-site test pinned the same shape); AC (6) is
  new (a dependent of a lane turned away on an interrupt); the old AC (6) is AC (7); the Never clause, the I/O
  matrix and the Approach say what the review found; the Problem's two imprecise sentences are corrected.

- 2026-10-23, after the re-review (FAIL): the Always clause admits AC (6)'s `--jobs 2`, event-ordered test, which
  now runs the installed SIGINT handler from a lane.

## Review Triage Log

### 2026-10-23 — Review pass 1 (FAIL: one must-fix, two should-fix, three nits)

1. **must-fix, fixed.** `test_preflight_docs_site_mutex.py::test_after_a_red_stop_no_lane_starts_even_one_pending_lanes_depend_on`
   asserted `"cancelled_by" not in install` and failed on every run (the full station suite: 1 failed, 2905 passed).
   It now asserts the red lane and its environment; Story 105.1's clause is recorded as superseded.
2. **should-fix, fixed.** A dependent of a lane the pool turned away on an interrupt changed from the dependency's
   name to `interrupt`, which this spec said could not happen. Kept (it names the root cause), recorded in AC (6),
   the matrix and the Never clause, and pinned by
   `test_a_dependent_of_a_lane_turned_away_on_an_interrupt_names_interrupt` (both `--keep-going` states, ordered by
   events), red on `9fc4cb1c2b`.
3. **should-fix, fixed.** The mint memlog entry said "No SPEC.md, PRD or spine change" and listed neither the PRD
   and spine re-stamps nor the TEA matrix; a later memlog entry corrects it (the memlog is append-only).
4. **nit, fixed.** `_on_sigint` set `cancel` before it recorded the cause; it now records the cause first, as the red
   path does.
5. **nit, fixed.** The second interrupt check's default is pinned: the test is parametrized like the first check's,
   with no cause recorded, `interrupt`, and a red lane recorded first.
6. **nit, fixed.** "offers a lane only while no stop is set" now says a red stop; "the cause on `a`, `c` and `e`"
   now says `a` depends on whether `c` was submitted. Same in the Dream entry.

### 2026-10-23 — Review pass 2 (FAIL: one must-fix, two should-fix, one nit; every round-1 finding resolved)

1. **must-fix, fixed.** AC (6)'s test sent a real SIGINT from lane `w`. Python runs the handler on the main thread at
   its next bytecode check; a signal that landed as the main thread entered `wait()` stayed pending until a lane's
   10 s timeout, so under 16 CPU burners and 8 parallel runs 2 of 32 failed (`keep_going=True`: `KeyError:
   'blocked_by'`), and `keep_going=False` passed by the assembly's path. `w` now calls the installed handler
   (`signal.getsignal(signal.SIGINT)`) itself, so the cause is recorded before `w` returns; the test asserts `x` and
   `w` are `ok` and that `z` was journaled, so a timeout inside a runner fails the test. Under the same load: 40 of
   40 runs green, slowest call 0.25 s; red on `9fc4cb1c2b` (`KeyError: 'cancelled_by'` on `y`).
2. **should-fix, fixed.** The Always clause excluded the `--jobs 2` `run_preflight` test AC (6) requires; amended.
3. **should-fix, fixed.** The Dream entry's Constraints still said only the cancelled lanes' two fields change; it now
   names the blocked dependent's `blocked_by` under `--keep-going`, as the Never clause does.
4. **nit, fixed here.** This spec cited session scratch files; it now says they are not kept. The memlog keeps its
   one such citation (append-only), as Story 107.1's entries do.
