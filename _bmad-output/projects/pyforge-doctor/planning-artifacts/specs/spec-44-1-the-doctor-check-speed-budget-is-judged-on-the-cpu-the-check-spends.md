---
title: "44.1: The doctor check speed budget is judged on the CPU the check spends"
type: 'fix'
created: '2026-10-12'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py
  - .claude/memory/feedback/the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py::test_doctor_check_completes_within_the_five_second_budget`
runs `doctor check` on the live repo root. It does one warm-up, then five timed runs, and requires the median wall
time to be under 5.0 s (PRD SM-C1, NFR-4). The `pyforge-doctor-test` task runs it in its own serial segment after
the parallel suite. In local `pr-preflight` on 2026-10-12 it failed on three branches, with medians of 7.26 s,
5.19 s and 5.76 s. It passes when run alone. Line numbers below are at `c447946b3f`.

**The evidence (where a `doctor check` run goes):**
- **CPU-bound and single-threaded.** On an idle machine one run takes 2.73 s of wall time and 2.75 s of CPU, measured
  with `os.times()` (self plus reaped children). Children account for only about 0.4 s. A `subprocess.run` trace
  shows `deptry --version` 0.18 s, `git ls-files` 0.18 s, `osv-scanner --version` 0.03 s, and a few `git` reads.
- **The time is doctor's own work.** About 95% is the `env_hygiene` scan (`checks/env_hygiene.py:866`, `gather`):
  - discovery takes 0.33 s and finds 2720 `.py` files (`_discover_python_files`, `:240`);
  - scanning takes 2.24 s (`_scan_file`, `:810`). It reads every file, parses the 178 that mention `environ` or
    `getenv`, and walks their ASTs, `_resolve_os_aliases` (`:298`) included.
  - The cost is spread across files: the largest single file costs 0.15 s.
- **So the budget measures what it claims to.** What fails is the clock. About twenty preflight lanes on sixteen
  cores stretch a CPU-bound run's wall time 2-2.7x, so the same work reads 5.2-7.3 s.
- **The work is also growing.** The same doctor code costs 2.31 s of CPU on the 2026-10-04 tree (`26a298ed12`) and
  2.75 s on today's. Tracked `.py` files went from 2562 to 2801. The test's docstring recorded about 1.8 s a run on
  2026-10-04.

**Approach:** judge the budget on the CPU each run spends, not on its wall time. Take the per-run delta of
`os.times()`: user plus system, for the process and for its reaped children. For a CPU-bound, single-threaded run
that equals the idle wall time the budget promises, and it does not stretch when other processes share the cores.
Keep the warm-up, the median of five, the 5.0 s budget and the non-vacuous findings guard. Report each run's wall
time beside its CPU time when the test fails. Record the scan's growth with the repo as a deferral row that carries
the numbers.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-1 (the fast `doctor check` pre-flight) and NFR-4 (`doctor
  check`'s default run stays within the five-second pre-flight promise, and a benchmark test guards it). Story 1.5
  shipped the benchmark, and Story 41.4 moved it to a warm median. No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** This is a test-only `fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-12 (the speed budget under preflight load),
  and the operator's ask the same day: "yes, chain the doctor budget test fix too".

## Acceptance Criteria

- **AC1 — The budget is judged on CPU.** For each of the five timed runs, the test records the CPU the run spent:
  the delta of `os.times()` user plus system, for the process and its reaped children. It asserts that the median
  CPU is under `_BUDGET_SECONDS` (5.0, unchanged). The warm-up count (1), the timed count (5) and the
  `findings_count >= engines_suite_size` guard are unchanged.
- **AC2 — A failure shows both clocks.** The failure message lists each timed run's CPU and wall seconds and names
  CPU as the judged measure.
- **AC3 — The measure means what it says.** One helper takes a callable and returns its `(wall, cpu)` seconds, and
  the budget test uses it. Three unit tests pin it:
  - a callable that burns about 0.3 s of CPU in-process reads at least 0.25 s of CPU;
  - one that sleeps 0.3 s reads under 0.1 s of CPU;
  - one that runs a child process burning about 0.3 s of CPU, and waits for it, reads at least 0.25 s of CPU.
- **AC4 — Holds under load.** With one busy-loop process per CPU running beside it, the budget test passes 3 of 3
  runs. The load processes are killed by exact PID afterwards. This is a Verification command.
- **AC5 — The growth is on record.** A deferral row in `deferred-work-ledger.md`, `DW-doctor-44-1`, records the scan
  cost: 2.31 s CPU on the 2026-10-04 tree and 2.75 s at `c447946b3f`, with the file counts and where the time goes.
  It names the product options (resolve `os` aliases in the same pass as the visit; skip files git does not track)
  without choosing one.
- **AC6 — Mutation.** Each change below makes a named test fail:
  - Return wall time as the helper's CPU figure: AC3's sleep test.
  - Drop the children's CPU from the helper: AC3's child-process test.
  - Judge the budget on wall time again: AC4's load run. This one is a Verification command, so record its result in
    the Spec Change Log.

## Boundaries & Constraints

**Always:**
- Keep the test real and unmocked against the live repo root, as its docstring promises.
- Update the docstring: CPU is now the measure, with the reason and this story's numbers.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never raise the 5.0 s budget, and never scale it by load.
- Never skip, `xfail` or `slow`-mark the test, and never move it out of `pyforge-doctor-test`'s serial segment.
- Never change `doctor check`'s behaviour in this story. A speed-up is the deferral row's to choose.

**Residual risk:**
- Time a run spends blocked (a network wait, a sleep) is not CPU, so this measure would not see it. `doctor check` is
  offline by design (NFR-1), and the child processes it waits for are counted.

## I/O & Edge-Case Matrix

| Run | Before (wall median) | After (CPU median) |
|---|---|---|
| idle machine | about 2.7 s, passes | about 2.75 s, passes |
| preflight, about 20 lanes | 5.2-7.3 s, fails | about 2.8 s, passes |
| a real regression (doctor's own work over 5 s of CPU) | fails | fails |
| a degraded run (sentinel findings only) | fails the guard | fails the guard |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-doctor` CAP-1 and NFR-4. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-12 (the speed budget under preflight load)
  entry.
- Epic: Epic 44 (new), minted with this story.
- Ledger key: `44-1-the-doctor-check-speed-budget-is-judged-on-the-cpu-the-check-spends`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-doctor` memlog records the evidence, the design and this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with AC1-AC3's tests (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- AC4's load run: start `nproc` copies of `python3 -c "while True: pass"`, then run `pixi run --frozen -e pyforge-doctor python -m pytest -q src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py` three times, then kill the load processes by exact PID — expected: 3 of 3 exit 0.
- The doctor lane under the preflight's conditions: the Guild environment's `bin` on `PATH`, and `TMPDIR` and `--basetemp` under a directory named `pyforge-doctor-test` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The three mutations of AC6 — expected: each fails its named test or command. Restore each.

## Named, not fixed here

- **The scan's cost.** It grows with the repository's Python files, and it is `DW-doctor-44-1`.

## Spec Change Log

- 2026-10-12: minted at the operator's ask "yes, chain the doctor budget test fix too". The evidence comes from
  measurements at `c447946b3f`: `os.times()`, a `subprocess.run` trace, cProfile, per-file scan timing, and the same
  code run on the 2026-10-04 tree.

## Review Triage Log

- No review has run yet.
