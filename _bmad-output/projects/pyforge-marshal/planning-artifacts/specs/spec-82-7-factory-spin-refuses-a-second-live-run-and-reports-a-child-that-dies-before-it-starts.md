---
title: '82.7: Factory spin refuses a second live run and reports a child that dies before it starts'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'ac91b861aa4ea00f976b370299461fd99f8bc487'
review_loop_iteration: 0
followup_review_recommended: true
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

### 2026-10-02 — Review pass
- verdicts: 28 findings — high 0, medium 6, low 15, false 7, maybe-false 0
- findings:
  - `[low]` `[reject]` (Blind Hunter) `_child_exited` discards the `waitpid` status, so exit 0, exit 1 and a signal death read alike, and an exit 0 before the starting line would read as "cannot launch" — a real child exiting 0 before `cmd_run`'s starting line is not reachable (the line is printed before any work, and the only early exits are refusals with status 1); the log tail already carries the cause. A status field needs a changed return type for a private probe; not worth the extra surface. Rejected with EH3.
  - `[medium]` `[patch]` (Blind Hunter) the quoted log tail is neither redacted nor control-character-safe, and the one-line test pins only `"\n"` — verified: `HarnessError` text lands in the `MRS-SPIN-003` finding, stdout and the durable journal `error` field, and `BmadLoopHarness._redact_text` (AD-34) was not applied; `\x1b` survived `_log_tail`. The `log_path` quoting claim is false (the path is Marshal's own `run_dir` path, and `cannot open spin log {log_path}` quotes it the same way). Fix applied: `_poll_for_harness_run_id` redacts the whole log text before `_log_tail`, quoting `(withheld: redaction failed)` on a `None`; `_log_tail` collapses control-character runs to one space; real-child tests pin both (a `ghp_` token and `\x1b[31m`).
  - `[low]` `[reject]` (Blind Hunter) an unreadable `harness.log` reads as an empty one (`tail: (empty)`) — the parent opened and truncated that file itself in `spawn_detached`, so an `OSError` on the read after the child exited is not reachable in practice, and a distinct wording adds a branch. Rejected with EH4.
  - `[low]` `[patch]` (Blind Hunter) `test_spin_bounds_the_quoted_log_tail` never reaches the 500-character cap and its `+ 400` bound passes with the cap deleted — verified by the verification-gap layer's mutations. Fix applied: the test is replaced by `test_spin_quotes_the_end_of_the_log_not_its_head`, and direct `_log_tail` tests pin 5 lines, 500 characters (503 with the marker), the exact-500 boundary, empty text and control-character collapse with literal numbers.
  - `[low]` `[patch]` (Blind Hunter) `test_spin_returns_the_run_id_of_a_child_that_prints_its_line_and_exits` runs under the autouse 0.2 s window while a real interpreter starts — a loaded CI box can pass the deadline first. Fix applied: the test pins `_SPIN_LOG_POLL_TIMEOUT_S` to 10.0, as the sibling real-child tests do.
  - `[low]` `[reject]` (Blind Hunter) Story 3.3's spec still states the old exit-0 contract for an unconfirmed launch — a done story spec is the historical record (DW-FU-3-3-4's own evidence quotes it); this story's Binding, the memlog entry and the ledger resolution record the superseding behaviour. Rewriting a closed contract is not a direct correction.
  - `[low]` `[patch]` (Blind Hunter) the memlog reconcile entry is silent on the baseline stamp and on co-governors, unlike its 82.13 neighbours — the guard passes, but a reader cannot tell. Fix applied: a review-pass addendum event appended with `memlog.py` names the three paths of this round, states that no other Spec's surface names them as a glob and that no baseline was stamped.
  - `[medium]` `[patch]` (Blind Hunter) no test runs the real adapter through `run_spin`, so AC1's command-surface claim rests on composition — verified: every CLI-level test raises a fake `HarnessError("bmad-loop binary not found")`. Fix applied: `tests/unit/test_spin.py::test_spin_a_child_that_exits_before_its_starting_line_is_a_failed_launch` drives the real `BmadLoopHarness.spin` through `run_spin` and asserts the non-zero exit, `MRS-SPIN-003` with the tail, no `MRS-SPIN-004`, and a FAILED outcome whose `error` says the process exited. Shared with EH11 and IA1.
  - `[false]` `[reject]` (Blind Hunter) `_child_exited` is unguarded for `pid <= 0`, POSIX-only and untested against `subprocess`'s deferred cleanup — the pid is `Popen.pid` from `spawn_detached`, always positive; marshal is already POSIX-only (`adapters/fs_local.py` imports `fcntl`, `PosixProcess.spawn_detached` uses `start_new_session`); a child reaped from under `Popen` is tolerated by `_internal_poll` (`ECHILD` -> returncode 0) and, if another reaper wins the race, the `ChildProcessError` branch answers through `is_alive`.
  - `[medium]` `[patch]` (Edge Case Hunter) child stderr in the tail may hold secrets and is quoted raw — same root cause and fix as the redaction row above.
  - `[false]` `[reject]` (Edge Case Hunter) a child that printed its starting line and then exited is still reported as a clean launch — the contract names "before its starting line": a child that printed it began a run, which the supervisor sidecar tracks to its own end (Story 3.4); the test `test_spin_returns_the_run_id_of_a_child_that_prints_its_line_and_exits` pins that deliberately.
  - `[low]` `[reject]` (Edge Case Hunter) `waitpid` status lost, so a signal or OOM death shows only `tail: (empty)` — same as the first row: the exit cause is in the log when there is one, and a silent kill is rare.
  - `[low]` `[reject]` (Edge Case Hunter) an unreadable log reads as empty — same as the third row.
  - `[low]` `[reject]` (Edge Case Hunter) no final re-probe at the deadline, so a child dying in the last step reads as `MRS-SPIN-004` — the probe is read at the top of the final iteration, microseconds before the deadline check; the exposure is one 0.2 s step and falls back to today's behaviour; a re-probe adds a branch.
  - `[false]` `[reject]` (Edge Case Hunter) a recycled pid after another reaper took the zombie makes the `is_alive` fallback see a live process — the fallback runs only when `waitpid` raised `ChildProcessError` within the same poll step, a milliseconds window in which Linux pid allocation (sequential to `pid_max`) cannot reach a live recycled pid.
  - `[false]` `[reject]` (Edge Case Hunter) `os.WNOHANG` is missing on win-64 — same POSIX-only evidence as the `pid <= 0` row; `spin`'s detached launch cannot run there before this code is reached.
  - `[low]` `[patch]` (Edge Case Hunter) control characters survive in the tail — same fix as the redaction row (`_CONTROL_RUN_RE` collapse in `_log_tail`).
  - `[low]` `[patch]` (Edge Case Hunter) the 0.2 s autouse window makes the prints-its-line test intermittent — same fix as the Blind Hunter row.
  - `[low]` `[patch]` (Edge Case Hunter) the `_log_tail` truncation branch is untested — same fix as the tail-bounds row.
  - `[medium]` `[patch]` (Edge Case Hunter) AC1's second half has no command-level test — same fix as the Blind Hunter command-surface row.
  - `[low]` `[reject]` (Edge Case Hunter) surviving "never launched" wording in `verdict.py:135` and `findings.py:187` — those sentences quote a past review finding to explain why `MRS-SPIN-006` was split off `003`; the defining sentence of `MRS-SPIN-003` is amended, and the contrast still holds (nothing is running vs a live process). Cosmetic.
  - `[false]` `[reject]` (Edge Case Hunter) "retry is safe" is wrong because the policy write, run directory and intent persist — the early exit happens at the same point as the existing `cannot launch` failure (after the intent and policy write, before the supervisor sidecar), journals a FAILED outcome the same way, and returns before any sidecar spawns; the state left is identical to the already-shipped `MRS-SPIN-003` path.
  - `[medium]` `[patch]` (Verification Gap) the "exit probe before log read" ordering is not pinned — verified by the layer's mutation (probe moved after the read, 25/25 passes on the real-child tests); a reorder would report a started run as `MRS-SPIN-003`, "safe to retry". Fix applied: `test_poll_reads_the_exit_probe_before_the_log` uses a stub probe that writes the starting line when called and returns `True`.
  - `[low]` `[patch]` (Verification Gap) the two `_log_tail` bounds are unpinned — same fix as the tail-bounds row (mutations: no 500-character cut and no 5-line cap each caught).
  - `[medium]` `[patch]` (Intent Alignment) the intent's expectations live at the command surface (`run_spin`'s finding, exit code and outcome entry) while the diff's tests stop at the adapter — same fix as the command-surface row.
  - `[low]` `[reject]` (Intent Alignment) no test covers a silent exit 0 before the starting line — not reachable per the first row; every early-exit test uses status 1, matching AC1's own wording.
  - `[false]` `[reject]` (Intent Alignment) the autouse `_child_exited` stub means the old fake-`Popen` tests do not exercise the probe, and production timing constants are overridden — by design: the fixed-pid fakes are not real children, and the probe is exercised by the real-child tests and by five mutation runs (each caught); production constants are untouched in the source.
  - `[false]` `[reject]` (Intent Alignment) the failed outcome entry carries `pid: None`, so the dead pid appears only in the message — that is the existing failed-launch outcome shape (`cli/spin.py` writes `pid: None` on every `HarnessError`), and AC1 asks for an entry that says the process exited, which `error` does.

## Auto Run Result

Status: done

**Summary.** `spin`'s bounded `harness_run_id` poll now asks whether the spawned child has exited. `_child_exited(pid)` uses `os.waitpid(pid, WNOHANG)` (which reaps the unreaped zombie `spawn_detached` leaves) and falls back to `PosixProcess.is_alive` on `ChildProcessError`; the poll reads it at each step before the log. A child that exited without printing its starting line ends the poll at once and raises `HarnessError` naming the pid and quoting a redacted, control-character-free, one-line tail of `harness.log`; `cli/spin.py` already reports that as `MRS-SPIN-003`, non-zero exit, with a FAILED `outcome` entry. A live child at the deadline still returns `None` (`MRS-SPIN-004` WARN, exit 0). Story 34.1's `MRS-DISP-021` guard, `marshal factory resume` and `pyforge-core` are untouched. `DW-FU-3-3-4` is closed.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — `_child_exited`, `_log_tail`, redaction and the pid-aware poll.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py` — `HarnessPort.spin` docstring names the early exit.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — `MRS-SPIN-003` prose only.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_spin.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` — real-child, ordering, tail-bound, redaction and command-surface tests.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` — `DW-FU-3-3-4` closed with `resolution:` and `verified:`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — two surface-reconcile events (implementation, review pass); no baseline stamped.

**Review findings.** 28 reported: 7 patch entries applied (redaction and control characters; tail-bound tests; probe-before-log ordering test; flaky-window pin; command-surface test; memlog addendum), none deferred, 15 rejected with the reasons recorded above (7 `false`, 8 `low` not worth the added branches or edit to a closed contract). Patched entries at entry verdict: 3 medium (redaction, ordering, command surface), 4 low.

**Follow-up review recommendation: `true`.** Three medium entries were patched on a first pass. Unverified risk: the patch round's new code and ten tests were checked by the implementer's own five mutation runs and the full suite, but no independent reviewer read them — chiefly the redaction call (`_redact_text` over a whole log blob: over-redaction of a useful tail, or the `None` path never exercised outside the one patched test) and the new `test_spin.py` real-child test's timing under a loaded runner.

**Verification performed** (exit codes read from files, never a pipe).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — exit 0, 10823 passed, 1 skipped, 14 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0 ("every tracked file governed or allowlisted; no drift"), re-run after the last memlog append.
- `pixi run -e pyforge-guild spec-surface-check` and `deferred-work-check` — exit 0.
- Mutation (implementer, five runs): probe after log, no redaction, no control-character collapse, no 500-character cap, no 5-line cap — each caught by its intended test; removing the probe from the poll fails 8 tests across the two test files.

**Residual risks.**
- The harness auto-checkpoint committed the mutated line `exited = False` into branch history (`d037147146` and neighbours) while a mutation run was live; the final tree and HEAD hold the real line (`exited = _child_exited(pid)`, verified by `git show HEAD:` and the working tree), but the wip commits remain in history until landing.
- `pr-preflight` was not run in this session, nor was the spec-surface baseline stamped (the landing flow stamps, scoped, from a clean tree).
- `MRS-SPIN-003` now also covers a child that started and exited; callers that treat every `MRS-SPIN-003` as "no process was ever spawned" should read its message.
