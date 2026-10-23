---
title: "71.13: A second SIGINT never deadlocks the preflight's interrupt handler"
type: 'fix'
created: '2026-10-23'
status: 'in-progress'
baseline_revision: '884d7f1106'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1), and pr-preflight is a gate, as 105.1, 106.1, 107.1 and 71.12 recorded
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-11-no-lane-process-outlives-a-stop-and-a-reduced-lane-cut-short-is-never-ok.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-12-every-cancelled-lane-names-what-stopped-the-run.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a second Ctrl-C can hang an interrupted preflight for good. Story 71.12's third independent review found
it in a function 71.12 touched, outside 71.12's ACs. Read at `884d7f1106` (71.12 merged) in
`src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`:

- `run_preflight` installs `_on_sigint` (`:1316`-`:1323`). Python runs it on the main thread, between bytecodes.
- It records the cause under `stop_lock`, an `RLock` (`:593`), so that step can be re-entered.
- It then calls `coord.cancel.set()` (`:1320`). `threading.Event.set` holds the event's own `Lock` while it sets the
  flag and wakes waiters.
- It then calls `coord.terminate_children()` (`:1321`), which takes `proc_lock`, a plain `Lock` (`:586`), to copy the
  process list (`:646`) and again to mark each lane it signals (`:651`).

Python may run the handler again, on the same thread, while the first call holds either lock. The nested call
reaches the same lock and waits forever on the frame it interrupted. The handler swallows Ctrl-C, so only SIGKILL
ends the run. The window is a few bytecodes per lock: it takes a double Ctrl-C at the wrong instant.

**Measured at `884d7f1106`** with no real signal. Two tests run one green lane, keep the handler the run installed
(it closes over the run's coordinator), and call it on a daemon thread. Each replaces one lock with a stand-in that,
holding it, calls the handler once more:

- `cancel` replaced by a `threading.Event` subclass whose `set()` calls the handler inside `with self._cond`: still
  blocked when its 10 s join expired.
- `proc_lock` replaced by a lock that calls the handler from `__enter__`, with one sleeping lane registered: still
  blocked when its 20 s join expired.

**Approach:** a reentrancy guard local to `run_preflight`. A call that finds the handler already running returns at
once. The flag clears when the handler returns, so a SIGINT after that runs the handler again, as today. A nested
call that lands before the flag is set, or after it clears, runs the whole body while the outer call holds no lock,
and every step is idempotent: the first cause wins, `cancel` is already set, `terminate_children` skips an exited
process.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32): "a red lane still refuses the push", and Stories
  71.10-71.12's interrupt contract: a lane running at SIGINT is `cancelled` with `cancelled_by: interrupt`, a lane
  that never started names `interrupt` too, and the run exits 130. This fix keeps all of it and mints no CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-71.12, which is `done` (PR #2287, merged as `884d7f1106`).
- **Epic.** Epic 71 is `done`. This backlog story reopens it (`epic-71` moves to `in-progress`), which
  `ledger-regression`'s `epic_reopened_by_new_story` admits when the new story arrives in the same change.

## Acceptance Criteria

- **(1) A second SIGINT inside `cancel.set()` returns.**
  - Given the handler a one-lane run installed, and `cancel` replaced by an event whose `set()`, holding its lock,
    calls the handler once more.
  - When the handler is called on a daemon thread.
  - Then it returns within 10 s, `cancel` is set and the cause is `("interrupt", None)`.
  - And a further call after it returned also returns, with the cause unchanged.
- **(2) A second SIGINT while `proc_lock` is held returns.**
  - Given the same handler, one sleeping process registered for lane `("sleeper", "env")`, and `proc_lock` replaced
    by a lock that, once armed, calls the handler from inside the lock.
  - When the handler is called on a daemon thread.
  - Then it returns within 20 s, the nested call did land inside the lock, the process is terminated, the lane is in
    `terminated_lanes` and the cause is `("interrupt", None)`.
- **(3) Both tests fail on `884d7f1106`:** each handler call is still blocked when its join expires.
- **(4) Nothing else moves.** One SIGINT does what it did: the 71.10-71.12 interrupt tests pass unchanged (the cause,
  `cancel`, terminated lanes, `cancelled_by: interrupt`, exit 130). No lock type changes.
  `pixi run --frozen -e pyforge-steward pyforge-steward-test` is green.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- Tests send no real signal and never sleep to win a race: they call the installed handler, and every wait has a
  timeout so the old code fails instead of hanging the suite.

**Never:**
- Never make `proc_lock` or the `cancel` event reentrant, or replace either.
- Never change what one SIGINT does, the exit codes, the journal or the scheduler.
- Never ignore a SIGINT that arrives after the handler has returned.
- Never hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

**At landing:** `preflight.py` is in the surfaces of `spec-pyforge-steward` and `spec-pyforge-core`, and
`test_preflight_concurrency.py` in `spec-pyforge-steward`'s. Append the reconcile to each Spec `spec-surface-check`
names, then one scoped stamp each (AGENTS.md § Pre-PR item 5). Promote the story to `done` before the merge.

## I/O & Edge-Case Matrix

| Second SIGINT arrives | Today (`884d7f1106`) | After |
|---|---|---|
| while the first holds `cancel`'s lock | deadlock | returns at once; the first completes |
| while the first holds `proc_lock` | deadlock | returns at once; the first completes |
| during `_terminate_proc_group`'s 5 s wait (no lock held) | runs the whole handler again | returns at once |
| before the guard is set, or after it clears | runs the whole handler again | unchanged (no lock held; idempotent) |
| after the handler returned | runs the handler again | unchanged |
| one SIGINT only | cause, `cancel`, terminate, exit 130 | unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-23 (a second SIGINT deadlocks the
  handler) entry.
- Epic: Epic 71 (CAP-159, FR-32). It was `done`; this story reopens it to `in-progress`.
- Ledger key: `71-13-a-second-sigint-never-deadlocks-the-preflight-s-interrupt-handler`.
- Ledger status at mint: `backlog`.
- Deps: S-71.12 (`done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the decision; `SPEC.md` untouched.
- Surface: `preflight.py` and its unit tests. Epic 71 declares no `[epic_surfaces]` entry in steward's
  `marshal-policy.toml`, so marshal's derived default (`src/shared/packages/pyforge-steward/**` among it) applies.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file (on a
  host whose `/tmp` is tmpfs, with `TMPDIR` on the repository's filesystem).

**Manual checks (not a dispatch gate):**
- AC (1) and (2) against `preflight.py` at `884d7f1106`: expected red, each join expired.

## Spec Change Log

- No change yet.
