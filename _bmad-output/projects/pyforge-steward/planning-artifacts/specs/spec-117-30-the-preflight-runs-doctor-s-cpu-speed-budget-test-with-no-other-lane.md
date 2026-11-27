---
title: "117.30: The preflight runs doctor's CPU speed-budget test with no other lane"
type: 'fix'
created: '2026-11-27'
status: 'done'
story: 117-30-the-preflight-runs-doctor-s-cpu-speed-budget-test-with-no-other-lane
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_alone_tail.py'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_preflight_alone_tail_tasks.py'
  - 'docs/how-to/run-and-read-pr-preflight.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** On 2026-11-27, two full `pr-preflight --keep-going` runs went red on one test:
doctor's `test_doctor_check_completes_within_the_five_second_budget`. One run measured a median
of 5.05 s of CPU at a load average of 12.5. The other measured 5.03 s at 13.7. The budget is
5.0 s. Both times, `pyforge-doctor-live-test` passed when run alone.

The test already judges CPU, not wall time. It already runs as its own pytest call after the
lane's xdist segment, so no worker in its own lane competes with it. What it lacks is time away
from the preflight's other lanes. Their load raises the CPU a run spends, through shared SMT cores
and a lower clock. The preflight has mutexes, but no way to run a lane alone.

Measured on the 16-core reference laptop, the lane takes 47 s when run alone: 31 s for its xdist
segment and 11.5 s for the speed test. Running the whole lane alone would add about 47 s to every
full run that selects it. Running only its last segment alone adds about 12 s.

**Approach:** `ALONE_TAIL_TASKS` in `preflight.py` names each task whose last `&&` segment must run
alone. Today it names only `pyforge-doctor-live-test`.

1. `alone_tail_plan` splits such a task's `cmd` at `&&` into head segments and a tail. Each
   segment becomes one argv, and the plan keeps the task's own `env`.
2. The lane runs its head beside the other lanes. Each head segment runs as
   `pixi run --frozen -e <env> -- <argv>`.
3. When the head passes, the lane waits. The scheduler starts its tail only when admission leaves
   nothing in flight, which means no pending lane can start. While the tail runs, only the tail
   can finish, so no lane becomes ready and none starts.
4. When the tail finishes, the lane completes, and its dependents then run.

The journal keeps one row per lane. Its seconds are the head and tail summed. Its `alone_tail`
entry gives the tail's own seconds, start offset, exit code and status.

If the head fails, the tail never runs, as `&&` would not run it. If a stop or an interrupt comes
before the tail starts, the lane is recorded `cancelled`, like any unstarted lane.

A run refuses, with exit 2, before any install when a selected lane's declared task has no tail it
can run as argv.

Ledger key: `117-30-the-preflight-runs-doctor-s-cpu-speed-budget-test-with-no-other-lane`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change): the serial remainder a task
  names runs alone.
- A fix under spec-pyforge-steward CAP-159 / FR-32: concurrent lanes never decide each other's
  verdicts.
- No AD moves.

## Boundaries & Constraints

**Always:**
- The test, its median and its 5.0 s budget stay as they are.
- CI's jobs and `pixi.toml` stay as they are. CI runs the task whole on a runner of its own.
- A lane outside the declared set runs whole, as before.

**Never:**
- Never run a declared task whole when its tail cannot be split. Refuse the run instead.
- Never weaken an assertion to green a run.

## Acceptance Criteria

**Given** a run in which an alone-tail lane is selected beside other lanes
**When** its head passes
**Then** its tail starts only after every other lane has ended, no lane overlaps the tail, and
the journal keeps one row for the lane with `alone_tail` named.

- **AC1 — The scheduler and the subprocess parts.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_alone_tail.py -q
  ```

- **AC2 — The declared set holds a serial tail in the real `pixi.toml`.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_preflight_alone_tail_tasks.py -q
  ```

- **AC3 — A full preflight that selects doctor's live half runs its tail last and passes.**
  Expected: the run exits 0. Its journal row for `pyforge-doctor-live-test` has
  `alone_tail.status == "ok"`, with a start offset after every other lane's end.

</intent-contract>
