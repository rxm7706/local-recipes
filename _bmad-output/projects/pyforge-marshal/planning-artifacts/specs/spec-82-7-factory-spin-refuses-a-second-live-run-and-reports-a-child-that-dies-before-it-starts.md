---
title: '82.7: Factory spin refuses a second live run and reports a child that dies before it starts'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: 'ac91b861aa4ea00f976b370299461fd99f8bc487'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `adapters/harness_bmadloop.py::spin` spawns the `bmad-loop run` child and then polls the log for its
starting line with `_poll_for_harness_run_id(self, log_path)` (`adapters/harness_bmadloop.py:1526`, called at `:1588`),
which never asks whether the child is still alive. A child that exits at once (most often `cmd_run`'s `worktree_clean`
refusal, before its starting line) burns the whole poll window and is reported as a launch: `MRS-SPIN-004` WARN, exit 0,
the dead pid in the `outcome` entry, the real error unread in `harness.log` (DW-FU-3-3-4).

**Scope ruling (operator, 2026-10-02):** the title's first half, refusing a second spin while the project's run is
live, already ships. `cli/spin.py::run_spin` calls `cli/dispatch.py::spin_loop_home_in_flight_conflict` before a run id
is minted (the "Story 34.1" block, from Story 28.24's 2026-09-10 fix) and refuses with `MRS-DISP-021`, naming the run and
its pids; `tests/unit/test_spin.py` covers it. This story keeps that guard unchanged and adds no second gate and no
second liveness model. DW-FU-3-3-2 is closed as resolved by Stories 28.24 and 34.1. The first dispatch of this story
(run `pyforge-marshal-20261002T130706347Z-dc65b4d3`) found the guard, blocked on the intent gap and changed no code.

**Approach:** the poll takes the spawned child's liveness: each step asks whether the pid is still running (an exited
child that has not been reaped counts as exited). A child that exits before its starting line ends the poll at once and
raises the adapter's launch error with the tail of `harness.log`, so `spin` reports a failed launch (the existing
`MRS-SPIN-003` class, "never launched, safe to retry") with a non-zero exit and an `outcome` entry that says the process
exited. A slow but live child keeps today's `MRS-SPIN-004` WARN.

Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (launch returns a run identifier promptly; the run completes, escalates or stops with a
  named reason) with Story 3.3 (FR-9, FR-10, FR-52; AD-3, AD-22). Story 3.3's I/O row that counted an unconfirmed launch as
  a success "pid known" is the defect corrected here. No new CAP; no flag.

## Acceptance Criteria

- Given a spawned child that exits with status 1 before printing its starting line When spin runs Then the poll ends without waiting out its window and spin reports a failed launch (`MRS-SPIN-003`) quoting the log tail, with a non-zero exit and an `outcome` entry that says the process exited
- Given a child still alive when the poll window ends without a starting line When spin runs Then it reports `MRS-SPIN-004` WARN and exit 0 as today
- Given a loop home whose run is live When a second spin runs Then it still refuses with `MRS-DISP-021` (Story 34.1's guard, unchanged)
- Given the liveness check removed from the poll When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Reuse the existing `MRS-SPIN-003` launch-failure path; no new finding code. Close DW-FU-3-3-4 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolution:` line naming this story, a `verified:`
line citing `path:line` or a command with its exit code).

**Never:** Do not add a second spin-vs-spin gate, a lock file or a second liveness model; do not change Story 34.1's
guard or `MRS-DISP-021`. Do not change `marshal factory resume`. Do not touch retry escalation or the policy writes
(Story 82.6's surface).

</intent-contract>

## Code Map

All paths under `src/shared/packages/pyforge-marshal/` unless stated.

- `src/pyforge/marshal/adapters/harness_bmadloop.py:1526` -- `_poll_for_harness_run_id(self, log_path)`: the defect; polls
  `harness.log` for `_RUN_STARTING_RE` (`:1193`) in `_SPIN_LOG_POLL_INTERVAL_S` steps up to `_SPIN_LOG_POLL_TIMEOUT_S`
  (`:1185`), never asks about the child. `spin` (`:1549`) calls it at `:1588` with only `log_path`; `pid` is in scope there.
  `os`, `re`, `time` and `PosixProcess` are already imported at the top of the module.
- `../pyforge-core/src/pyforge/core/process.py:250` -- `spawn_detached` returns `process.pid` and drops the `Popen`, so an
  exited child stays an unreaped zombie. `:216` `PosixProcess.is_alive` is `os.kill(pid, 0)` and its own comment says a
  zombie reports alive: it cannot answer "exited" here. Read-only evidence; `pyforge-core` is not edited (its port contract
  and every supervisor reading depend on that zombie behaviour).
- `src/pyforge/marshal/cli/spin.py:1960-2000` -- consumer, unchanged: `except HarnessError` appends `MRS-SPIN-003`
  (`cannot launch bmad-loop run: {exc}`), journals a FAILED `outcome` entry with `"error": str(exc)` and `pid: None`, and
  `_emit` returns the non-zero exit. `:2004` `MRS-SPIN-004` WARN stays the live-but-slow path. The guard
  `spin_loop_home_in_flight_conflict` (`cli/dispatch.py`, called from `run_spin` before a run id is minted) is Story 34.1's
  and is not touched; `marshal factory resume` has no `harness.spin` call.
- `src/pyforge/marshal/ports/harness.py:662-672` -- `HarnessPort.spin` docstring: "Raises `HarnessError` only if the process
  could not be LAUNCHED at all"; widen to name the early exit.
- `src/pyforge/marshal/core/findings.py:169` and `src/pyforge/marshal/core/verdict.py:121` -- prose that defines
  `MRS-SPIN-003` as "NO harness process was started"; stale once an early-exit child maps here. Amend the sentence; no
  code, no new code, classification (`Verdict.ERROR`, `verdict.py:871`) unchanged.
- `tests/unit/test_harness_bmadloop_spin.py` -- `spin` tests; they fake `Popen` with fixed pids (`4242`, `999`, `555`, `1`) that
  are not real children, so the new liveness probe needs a stub in the autouse `_fast_poll` fixture. The `@pytest.mark.slow`
  real-subprocess test (`:236`) is the pattern for a real child.
- `tests/unit/test_spin.py` -- CLI-level `spin` tests (`MRS-DISP-021`, `MRS-SPIN-003/004` shapes); read-only here.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- `### DW-FU-3-3-4` (`status: open`);
  close it per Boundaries.

## Tasks & Acceptance

**Execution:**
- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- add module-level `_child_exited(pid) -> bool`: `os.waitpid(pid,
  os.WNOHANG)` (reaps an exited child, so a zombie counts as exited); `ChildProcessError` (not our child, or already
  reaped) falls back to `not PosixProcess().is_alive(pid)` -- one liveness model, no new gate -- and thread `pid` into
  `_poll_for_harness_run_id(self, log_path, pid)`. Each step reads `_child_exited` BEFORE reading the log, so output the child
  wrote before exiting is always seen; a match returns the run id, an exit with no match raises `HarnessError` naming the pid,
  that the process exited before its starting line, and the log tail (last lines, one line, bounded). A live child at the
  deadline still returns `None` -- AC2 unchanged.
- `src/pyforge/marshal/ports/harness.py` -- `HarnessPort.spin` docstring: the early exit is a `HarnessError` too.
- `src/pyforge/marshal/core/findings.py`, `src/pyforge/marshal/core/verdict.py` -- amend the `MRS-SPIN-003` prose: nothing is
  running, so a retry is safe, whether the process never started or started and exited before its starting line.
- `tests/unit/test_harness_bmadloop_spin.py` -- autouse stub `_child_exited` -> `False` for the fixed-pid fakes; new tests:
  (1) real child `sys.exit(1)` with no starting line -> `spin` raises `HarnessError` ("exited", log tail) well inside a
  poll window pinned long enough that a missing check shows (mutation: remove the probe from the poll and it fails);
  (2) a child that prints its starting line then exits -> the run id, not an error (log read after the exit observation);
  (3) a live child with no starting line -> `harness_run_id is None` (AC2, the existing fake test now pinned live);
  (4) `_child_exited` directly: running child `False`, exited-unreaped child `True`, already-reaped/foreign live pid by the
  `is_alive` fallback.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- close `DW-FU-3-3-4` (`status: closed`,
  `resolution:` naming Story 82.7, `verified:` citing the poll's `path:line` and the test command with its exit code).

**Acceptance Criteria:**
- The four criteria in the intent contract above; AC3 (`MRS-DISP-021`) is verified by running the existing
  `tests/unit/test_spin.py` guard tests unchanged.

## Spec Change Log

## Design Notes

Why `waitpid`, not `ProcessPort.is_alive`: the spec's own rule is "an exited child that has not been reaped counts as
exited", and `is_alive` documents the opposite for a zombie. `spawn_detached` is the one place the child's `Popen` lives and
it drops it, so the adapter, as the parent, is the only party that can reap. `waitpid` on a pid the parent already reaped
(or never had) raises `ChildProcessError`, which routes to the existing `is_alive` reading instead of a second model.
`subprocess.Popen`'s own deferred cleanup tolerates a child reaped from under it (`ECHILD` -> returncode 0).

Sequence per poll step: `exited = _child_exited(pid)`; read the log; match -> return; `exited` -> raise; deadline ->
`None`; sleep. Checking exit first closes the race where the child prints its line and exits between a log read and a
later probe.

## Binding

Parent: Story 3.3, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry and the 2026-10-02 (later) ruling.
Ledger key: `82-7-factory-spin-refuses-a-second-live-run-and-reports-a-child-that-dies-before-it-starts`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-3-4 (DW-FU-3-3-2 closed by the 2026-10-02 ruling).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
