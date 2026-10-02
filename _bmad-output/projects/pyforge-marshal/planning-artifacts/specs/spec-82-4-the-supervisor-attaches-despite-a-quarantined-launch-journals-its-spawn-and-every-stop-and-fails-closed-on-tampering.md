---
title: '82.4: The supervisor attaches despite a quarantined launch, journals its spawn and every stop, and fails closed on tampering'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: '7e2939beebd2a78fff6c0f962dc2aed85954bb64'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The supervisor's journal can read healthy while a live run goes unsupervised. Re-verified at HEAD a7cdb91fe4:

- `supervisor/__main__.py::run_supervisor` (`:754`) decides attach-or-inert from one `fold` (`:916`): `started_by_marshal`
  (`:928-932`) looks for a launch or resume entry in `fold_result.by_kind`. A quarantined `run-launch` line never appears
  there, so a run Marshal did start reads as "not ours" and the supervisor returns 0 inert (`:933-967`), with one stderr
  line and no journal write (DW-FU-3-4-3; `tests/unit/test_supervisor.py:5200` pins exactly this).
- No `signal` handler exists anywhere in the package. `supervisor-detach` is written only when the tick loop ends
  (`:2625-2629`), so SIGTERM, SIGHUP or an operator's `pkill` leave an open `supervisor-attach` that reads like a healthy
  supervisor (DW-FU-3-4-6).
- `cli/spin.py::_spawn_supervisor_sidecar` (`:1102`, called from launch at `:1831` and resume at `:2400`) spawns the
  sidecar at `:1280` and reports the outcome only as `data["supervisor_pid"]` (`:1332`) or an `MRS-SPIN-007` (`:1306`); the
  run journal never records that supervision was attempted, succeeded or failed (DW-FU-3-4-7). `_writer_id`'s docstring
  (`:855-863`) pins "never appends a third entry".
- The agent session can write the run's `journal.jsonl` through the Tier-3 backlink. Making it unwritable or replacing it
  sends every later append into the `(FsError, ValueError)` branch (`:2649-2667`), which prints one stderr line and returns
  1, leaving the live run unsupervised with a journal byte-identical to a healthy one mid-tick (DW-FU-3-4-8).

**Approach:**

- When `fold` finds no launch or resume entry but quarantined at least one line, the supervisor attaches and supervises;
  its `supervisor-attach` carries the quarantine count and a new MRS-SUPV WARN saying ownership could not be proven from the
  journal. A journal with neither a launch entry nor a quarantined line stays inert, as today.
- SIGTERM, SIGHUP and SIGINT handlers journal `supervisor-detach` with a reason naming the signal, then exit. SIGKILL and a
  host crash stay detectable by heartbeat absence, as the module docstring already says.
- `_spawn_supervisor_sidecar` journals one observation per spawn, the sidecar's pid or the spawn error, for launch and
  resume alike; `_writer_id`'s docstring is corrected.
- The supervisor opens the journal once for appending at attach and writes every later entry through that descriptor
  (an `FsPort` handle; `LocalFs` implements it). Each tick it compares the path's identity and size with what it last
  wrote. A replaced, truncated or removed journal, or an append that fails, makes it stop the watched run through
  `HarnessPort.stop` and record why on its own log and, when the held descriptor still accepts it, in a final
  `supervisor-detach`. With no harness run id to stop against it keeps watching and reports that it cannot act, the
  `MRS-SUPV-003` / `MRS-SUPV-005` precedent, rather than exiting.

Ledger key: `82-4-the-supervisor-attaches-despite-a-quarantined-launch-journals-its-spawn-and-every-stop-and-fails-closed-on-tampering`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-2 (a run is watched from outside by something the session cannot disable) with Story 3.4
  (FR-11; NFR-4, NFR-5; AD-9, AD-20). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a run directory whose only `run-launch` line is unparseable and whose watched pid is alive When the supervisor starts Then it journals a `supervisor-attach` carrying the quarantine count and an MRS-SUPV WARN, and keeps heartbeating
- Given a journal with no launch entry and no quarantined line When the supervisor starts Then it stays inert with no journal write, as today
- Given a running supervisor When it receives SIGTERM, SIGHUP or SIGINT Then its last journal entry is a `supervisor-detach` whose reason names the signal
- Given `marshal factory spin` or `resume` When the sidecar spawn succeeds or raises Then the run journal holds one entry recording the sidecar pid or the error
- Given a supervised run When the journal is replaced, truncated, or made read-only between ticks Then the supervisor stops the watched run through `HarnessPort.stop` and records why, and never exits leaving the run alive and unwatched
- Given each fix removed in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The journal stays the supervisor's only durable write target besides its own log. Every new reason and code is
registered in `core/findings.py` and `core/verdict.py`. Close DW-FU-3-4-3, DW-FU-3-4-6, DW-FU-3-4-7 and DW-FU-3-4-8 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not run the supervisor under a different uid or add IPC; AD-9's import and IPC bans stay. Do not attach to a
journal that proves the run is someone else's. Do not change the idle ladder or the budget ceilings (Story 82.5's surface).

</intent-contract>

## Code Map

Paths are under `src/shared/packages/pyforge-marshal/` (`M/`) unless rooted. Lines are at HEAD `7e2939beeb`.

- `M/src/pyforge/marshal/supervisor/__main__.py` -- the whole supervisor. `run_supervisor` (`:754`); journal read + `fold` (`:883-916`);
  `started_by_marshal` (`:928-932`) and the inert branch with its quarantine stderr line (`:933-967`); `_write_entry` (`:976-1000`, the one
  path every journal write takes, `fs.append_line` at `:999`); `supervisor-attach` append (`:1033`); `harness_run_id` MRS-SUPV-003 branch
  (`:1056-1079`); the tick loop head (`:1647-1657`, `sleep(_TICK_SECONDS)` at `:1649`); heartbeat append (`:2407-2414`); post-loop
  `retry_verify_pending` check (`:2418`), flushes (`:2462-2494`), escalation detection (`:2504`, skipped when `detach_reason` is set); final
  `supervisor-detach` (`:2623-2629`); the `except (FsError, ValueError)` that prints one line and returns 1 (`:2649-2668`); `finally` that
  completes the publisher (`:2669-2675`). The stop idiom to mirror is `_act_on_budget_transition` (`:1589-1610`: `harness.stop`, `HarnessError`
  -> `MRS-SUPV-005`). Module docstring (`:1-322`) describes the inert-check and the detach reasons; update it.
- `M/src/pyforge/marshal/ports/fs.py` -- `FsPort` Protocol; `AdvisoryLock` (`:85-96`) is the opaque-handle precedent (`path` + adapter-owned
  `handle`), `append_line` (`:195-212`) the AD-30 write protocol to reuse.
- `M/src/pyforge/marshal/adapters/fs_local.py` -- `LocalFs.append_line` (`:296-344`, `O_WRONLY|O_APPEND|O_CREAT`, one `os.write`, short-write and
  embedded-newline guards); `acquire_advisory_lock`/`release_advisory_lock` (`:360-410`) are the held-descriptor precedent. This file is the only
  place `os.open`/`os.write` may live (`tests/meta/test_p01_write_primitives_only_in_fs.py`, `test_ad11_write_boundary.py`).
- `M/src/pyforge/marshal/cli/spin.py` -- `_writer_id` docstring (`:855-863`, pins "never appends a third entry"); `_append_entry` (`:952-963`, the one write
  path); `_spawn_supervisor_sidecar` (`:1102-1332`, spawn at `:1279-1298`, `ProcessError` -> `MRS-SPIN-007` at `:1299-1330`, success sets
  `data["supervisor_pid"]` at `:1332`); callers `run_spin` (`:1831`) and `run_resume` (`:2400`, `launched_via="bmad-loop resume"`). Launch writes
  counters 0 (intent) and 1 (outcome) under `_writer_id()`; resume the same.
- `M/src/pyforge/marshal/core/findings.py` (`REGISTERED_CODES` tuple around `:1466-1478`; the long docstring above it narrates each story's codes)
  and `M/src/pyforge/marshal/core/verdict.py` (`:867-880` table, `MRS-SUPV-010` last in the SUPV family; highest `MRS-SPIN` is `-017`).
- `M/src/pyforge/marshal/core/journal.py` -- read-only. `fold` quarantines a line it cannot evaluate (`FoldResult.quarantined`); `by_kind`;
  `build_entry` / `prepare_for_write`; observation kinds are free-form strings validated against `schemas/journal.json`.
- Tests: `M/tests/unit/test_supervisor.py` (`FakeFs` `:68-117`, `FakeProcess`, `FakeHarness` `:287-350` records `stop_calls`, `_launch_outcome_line`
  `:474`; pins to change: `:922` missing sidecar blob, `:1119` and `:1156` append failure, `:5200` quarantined journal);
  `M/tests/unit/test_publisher.py:329` (a second `FsPort` fake that drives `run_supervisor`, `:358`); `M/tests/unit/test_spin.py` (spawn tests,
  `_fake_run_supervisor` at `:1604`); `M/tests/unit/test_fs_local.py`; `M/tests/unit/test_findings.py` (`:65` exact registry set);
  `M/tests/meta/test_ad9_supervisor_no_control_channel.py` (bans only `socket` and `multiprocessing`, so `import signal` is allowed).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- rows `DW-FU-3-4-3` (`:3545`), `DW-FU-3-4-6` (`:3585`),
  `DW-FU-3-4-7` (`:3599`), `DW-FU-3-4-8` (`:3613`); each is `status: open`. Copy the closed-row shape from the rows Story 82.3 closed (`DW-5-9-2`).

## Tasks & Acceptance

**Execution:**
- `M/src/pyforge/marshal/ports/fs.py` -- add frozen dataclasses `AppendHandle(path, handle)` and `HeldFileState(present, same_file, size, writable)`, and four
  `FsPort` methods: `open_append(path) -> AppendHandle`, `append_held(handle, line, *, fsync)`, `held_file_state(handle) -> HeldFileState`,
  `close_append(handle)`; document them next to `append_line` and update the module docstring -- fix 4.
- `M/src/pyforge/marshal/adapters/fs_local.py` -- implement them per Design Notes D4 on one descriptor held for the handle's life; `append_held` keeps
  `append_line`'s guards (embedded newline, short write) and raises `FsError` on `OSError` -- fix 4.
- `M/src/pyforge/marshal/supervisor/__main__.py` -- fix 1 (D1), fix 2 (D2), fix 4 (D4, D5): attach on a quarantined launch with the new payload and
  `MRS-SUPV-011`; install and restore the three signal handlers around the run and break the tick loop on a signal; open the journal once, route
  `_write_entry` through the handle, check journal integrity each tick, and fail closed per D5. Rewrite the inert-check paragraph of the module
  docstring and add the signal and tamper paragraphs. Do not touch the idle ladder or the budget ceilings (Story 82.5).
- `M/src/pyforge/marshal/cli/spin.py` -- fix 3 (D3): journal one `supervisor-spawn` observation from `_spawn_supervisor_sidecar` for launch and resume;
  a failure to journal it adds `MRS-SPIN-018` (WARN) and never changes the launch outcome; correct `_writer_id`'s docstring.
- `M/src/pyforge/marshal/core/findings.py`, `M/src/pyforge/marshal/core/verdict.py` -- register `MRS-SUPV-011`, `MRS-SUPV-012`, `MRS-SUPV-013`,
  `MRS-SPIN-018`, all `Verdict.WARN`; extend the narrating docstring/comments in both files the way Story 3.9 and 33.4 did.
- `M/tests/unit/test_supervisor.py`, `M/tests/unit/test_publisher.py` -- give both `FsPort` fakes the four new methods (the supervisor fake delegates
  `append_held` to `append_line` so `appended_lines` and `fail_append_line_on_call` keep working, and computes `held_file_state` from its journal text
  plus appended bytes with an override for a tampered state). Pass an explicit `FakeHarness` to every test that reaches a failing append, since a
  fail-closed stop now calls it. Rewrite the pins at `:922` and `:5200` (a quarantined launch now attaches) and extend `:1119` / `:1156` (a failed append
  now also stops the run).
- `M/tests/unit/test_supervisor.py` -- one new test per acceptance criterion below, each named for its criterion; signal tests drive the real handlers with
  `signal.raise_signal` from inside the injected `sleep` and assert the previous handlers are restored afterwards.
- `M/tests/unit/test_spin.py` -- spawn success and `ProcessError` each journal exactly one `supervisor-spawn` entry for `run_spin` and for `run_resume`; a
  failing journal append for it yields `MRS-SPIN-018` and an unchanged exit code.
- `M/tests/unit/test_fs_local.py` -- `LocalFs` handle behaviour on a real `tmp_path`: append through the handle, same-file after other writers append,
  not-same-file after a rename-over, `present=False` after unlink, size shrink after truncate, `writable=False` after `chmod 0o444` while the held
  descriptor still accepts an append.
- `M/tests/unit/test_findings.py` -- add the four codes to the exact-set assertion.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- close `DW-FU-3-4-3`, `DW-FU-3-4-6`, `DW-FU-3-4-7`, `DW-FU-3-4-8`
  (`status: closed`, a `resolved:` line naming Story 82.4 and the pinning test).
- Surface reconcile -- run `python scripts/spec_surface_reconcile.py`; for every Spec it names, append an `event` memlog entry naming each governed path you
  changed (`python _bmad/scripts/memlog.py append --workspace <spec-folder> --type event --text "..."`). Never pass `--write-baseline`.

**Acceptance Criteria:**
- Given the contract's six criteria, when the new tests run, then each fails with its own fix reverted and passes with it applied (revert one at a time by
  editing the fix out, then restore it; never `git stash`).
- Given a journal holding a valid `run-launch` for a different run id plus one quarantined line, when the supervisor starts, then it stays inert (the journal
  proves the run is someone else's).
- Given a quarantined launch and a watched pid that dies after one tick, when the run ends, then the journal reads attach (with `quarantined` and the
  `MRS-SUPV-011` finding), heartbeat, detach; the `MRS-SUPV-003` entry is journaled because no harness run id is recoverable.
- Given SIGTERM arrives while a tick's work is running (not while sleeping), when that tick finishes, then the loop ends with the signal's detach reason.
- Given an append that fails with a harness run id resolved, when the failure surfaces, then `HarnessPort.stop` is called once, the stderr line still reads
  `supervisor: cannot append to journal <path>: <error>`, and `run_supervisor` returns 1.
- Given a replaced, truncated, removed or read-only journal and no harness run id, when ticks continue, then the supervisor reports once on stderr, keeps
  heartbeating (through the held descriptor), and returns 0 when the watched process exits.

## Spec Change Log

## Design Notes

**D1 -- unproven attach (fix 1).** Collect the run-launch and run-resume entries once. `started_by_marshal` is unchanged. Attach unproven only when
`not started_by_marshal`, no launch or resume entry exists for ANY run id, and `fold_result.quarantined` is non-empty. A launch or resume entry that
names another run id is proof the run is someone else's, so quarantine does not rescue it and it stays inert with the plain "not a run Marshal started"
line; the old "N line(s) were unevaluable -- staying inert" line is deleted. The attach payload then carries `quarantined: <count>` and
`finding: MRS-SUPV-011` (WARN, "ownership could not be proven from the journal"); a proven attach keeps today's two-field payload byte for byte.
`harness_run_id` resolves to `None`, so the existing `MRS-SUPV-003` branch and heartbeat-only supervision apply unchanged.

**D2 -- signals (fix 2).** `signal` is not an AD-9 control channel (the meta-test bans `socket` and `multiprocessing` only), but a handler must never act
mid-tick. A small `_SignalState` holds `name: str | None` and `sleeping: bool`. The handler records `signal.Signals(signum).name`; it raises a private
`_SupervisorSignal` only while `sleeping` is true, because `time.sleep` resumes after a handler that returns and because raising inside
`subprocess.run` (a `harness.stop` or `push` call) would kill the child half-way. The loop sets `sleeping` only around `sleep(_TICK_SECONDS)`, breaks on
the exception, and re-checks `state.name` in its `while` condition. After the loop, `detach_reason` becomes `"signal-" + name` (concatenation, per
the AD-23 guard's precedent) when it is still `None` and the watched pid is still alive; a natural exit keeps `watched-process-exited`. Install SIGTERM,
SIGHUP and SIGINT immediately before the attach append and restore the previous handlers in `finally`; `signal.signal` raises `ValueError` off the main
thread, in which case skip installing and carry on. `run_supervisor` returns 0 after a signal detach, like every other deliberate detach reason. A
signal that arrives before the handlers exist kills the process before any attach is written, so nothing dangles.

**D3 -- spawn observation (fix 3).** After the spawn attempt, append one `Phase.OBSERVATION` entry of kind `supervisor-spawn` with
`JournalEntryId(_writer_id(), 2)` through `_append_entry(fs, run_dir, entry, fsync=False)`. Payload: `{"supervisor_pid": <pid>, "watched_pid": <pid>,
"launched_via": <str>}` on success; the same with `"supervisor_pid": None` plus `"error": str(exc)` on `ProcessError`. The entry is written after the
sidecar may already be running, so the two writers' order is undefined; they are distinct writer ids and `append_line` is line-atomic, which is the
property the journal relies on. Update `_writer_id`'s docstring and the "spawn stays last" comments in `run_spin` accordingly.

**D4 -- held handle and integrity (fix 4).** `LocalFs.open_append` opens `O_WRONLY | O_APPEND` with no `O_CREAT`, so a removed journal is never silently
recreated; it raises `FsError` on `OSError` and lets `ValueError` (NUL path) through like the other methods. `held_file_state` does `os.fstat(fd)` and
`os.stat(path)`: `present=False` on `FileNotFoundError`; `same_file` compares `(st_dev, st_ino)`; `size` is the path's `st_size`; `writable` is
`os.access(path, os.W_OK)`. A held descriptor keeps accepting appends after `chmod 0o444`, so read-only is detected by `writable`, not by a failing write.
The supervisor keeps `expected_size`: initially `len(journal_text.encode("utf-8"))` plus the attach line's bytes plus one newline, then `+= len(line) + 1`
per own append, and each tick `expected_size = max(expected_size, state.size)` after the check. Other writers (a `supervisor-spawn` entry, a landing)
only grow the file, so a legitimate journal always satisfies `state.size >= expected_size`. A pure module-level function
`_classify_journal_state(state, expected_size) -> str | None` returns `removed`, `replaced` (not `same_file`), `truncated` (`size < expected_size`),
`read-only` (not `writable`) or `None`, in that order.

**D5 -- fail closed (fix 4).** `_write_entry` wraps the sidecar write and the handle append. With a harness run id it re-raises, so `(FsError,
ValueError)` reaches the existing handler, which now runs `_fail_closed` instead of only printing. Without one it records the fault once, prints it, and
swallows (no stop is possible, so nothing is lost by continuing; a swallowed intent is safe because with no run id the only intent written is the
`budget-stop` pseudo-action that stops nothing). `_fail_closed(kind, detail)` does, in this order and without a second `is_alive` call: `harness.stop`
(a `HarnessError` or a `False` result is recorded, never raised); print `supervisor: cannot append to journal <path>: <detail>` for an append fault, or
`supervisor: journal <kind>: <detail>` otherwise, plus the stop outcome; a best-effort final `supervisor-detach` through `append_held` with
`reason: "journal-tampered"`, `journal_fault`, `stopped` and an `MRS-SUPV-012` finding, ignoring any failure; return 1. A fault with no harness run id
reports `MRS-SUPV-013` ("cannot act: no harness run id") once and keeps watching. The per-tick check runs right after the liveness reading, only while the
watched process is alive, and not again once reported. Without a harness run id the handler keeps its print-and-return-1 for any other `FsError`. Close the handle in `finally`.

**Golden examples.** Quarantined launch, pid alive for one tick: journal reads `supervisor-attach {pid, watched_pid, quarantined: 1, finding}` ->
`idle-harness-run-id-unavailable` -> `supervisor-heartbeat` -> `supervisor-detach {reason: "watched-process-exited"}`. SIGTERM during the sleep: the last
line is `supervisor-detach {pid, reason: "signal-SIGTERM"}` and the return is 0. Journal renamed over between ticks with a harness run id: `stop_calls ==
[(home, run_id)]`, stderr names `replaced`, return 1.

## Binding

Parent: Story 3.4, `spec-pyforge-marshal` CAP-2; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-4-the-supervisor-attaches-despite-a-quarantined-launch-journals-its-spawn-and-every-stop-and-fails-closed-on-tampering`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-3-4-3, DW-FU-3-4-6, DW-FU-3-4-7, DW-FU-3-4-8.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (ruff, `ruff format --check`, mypy over the touched packages).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 once every governed path you changed is named on its Spec's `.memlog.md` (never `--write-baseline`).

**Manual checks (if no CLI):**
- Mutation proof, one fix at a time: remove the fix, run its new test, confirm it fails, restore the fix, confirm it passes. Record the four results in the
  story's Auto Run Result.

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 39 findings — high 0, medium 4, low 25, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` (Intent Alignment 1) Fix 4 trigger is broader than "an append that fails": every `FsError`/`ValueError` reaching the final handler (sidecar-blob write, an aggressiveness-file write, a failed `open_append`) now calls `_fail_closed` — Shares a root cause with Blind Hunter 1, Verification Gap 2 and Edge Case Hunter 1. Real but a diagnostic label only (the stderr line carries the actual exception text) over a path that already ended the supervisor with exit 1; stopping the run satisfies the intent's "never exits leaving the run alive and unwatched"; D5 designed it and the implementer's risk note records it; reaching it needs a bug elsewhere, and narrowing adds a private exception class plus branches.
  - `[low]` `[reject]` (Intent Alignment 2) "Never exits leaving the run alive" has exceptions (no run id; a failed `open_append` at attach; `stop` failing) — With a run id the stop is attempted and its outcome journaled as `stopped` plus `MRS-SUPV-012`; with no run id the intent itself says keep watching and report; a failing `stop` is the same recorded shape as `budget-stop` and the `defer` rung. The one residual (failed `open_append`, no run id) is Edge Case Hunter 5.
  - `[false]` `[reject]` (Intent Alignment 3) An unproven attach has no harness run id, so a later tamper takes the `MRS-SUPV-013` report-and-keep-watching path and cannot stop the run — Refuted as a defect: the intent's AC for fix 1 says "keeps heartbeating", and the intent says that with no harness run id the supervisor keeps watching and reports it cannot act.
  - `[low]` `[reject]` (Intent Alignment 4) After a replace or removal, heartbeats and the `supervisor-journal-fault` entry go to the orphaned inode — Inherent in holding a descriptor (the intent's design) and stated in the spec's risk notes; the stderr line in `supervisor.log` is the durable record. Nothing in the intent asks for a second write target (its Boundaries forbid one).
  - `[low]` `[reject]` (Intent Alignment 5) A signal that lands mid-tick is acted on when that tick finishes — Shares a root cause with Blind Hunter 4 and Edge Case Hunter 3. Designed (D2: raising inside `subprocess.run` would kill a child half-way); every subprocess call in the tick is bounded by a timeout (`PosixProcess.run` takes `timeout_s`, `bmad-loop stop` has `_STOP_TIMEOUT_S`), so the deferral is bounded; the fix adds a branch.
  - `[false]` `[reject]` (Intent Alignment 6) The new detach reasons and journal kinds are not registered in `core/findings.py` or `core/verdict.py` — Refuted: neither file registers detach reasons or journal kinds (`idle-deferred`, `budget-*` and `escalation-paused` appear in neither, verified by grep); "every new reason and code" is met by registering the four new finding codes, which `test_findings.py` pins.
  - `[low]` `[reject]` (Intent Alignment 7) Read-only detection uses `os.access`, which is true for root, and the test skips under root — A root supervisor can write a mode-0444 file anyway, so there is no write to stop; the skip is documented in the test.
  - `[false]` `[reject]` (Intent Alignment 8) The mutation criterion is proved as prose in the Auto Run Result, not by a repeatable artifact — Refuted: the criterion is a verification procedure ("each fix removed in turn, its new test fails"), each fix has its own named test, and Story 82.3 closed the same criterion the same way.
  - `[low]` `[reject]` (Blind Hunter 1) A `ValueError` from `build_entry`/`prepare_for_write` (outside the try in `_write_entry`) reaches the handler and stops a healthy run, labelled `cannot append to journal` — Same root cause and verdict as Intent Alignment 1.
  - `[false]` `[reject]` (Blind Hunter 2) One transient append failure (ENOSPC/EIO) stops the run — Refuted as a defect: the intent says an append that fails makes the supervisor stop the watched run; tolerating transient write faults is the opposite of that criterion.
  - `[false]` `[reject]` (Blind Hunter 3) A signal detach is fail-open: a same-uid agent can silence the supervisor with `kill -TERM`, no finding code is emitted, and `_MARSHAL_INITIATED_DETACH_REASONS` omits it — Refuted: the intent requires a journaled detach naming the signal and keeps SIGKILL detectable by heartbeat absence, with a different uid out of scope; `is_marshal_initiated_stop` is fed only by the dispatch journal's `stop_reason` (`cli/dispatch.py:1283-1284`), never by this supervisor's detach reasons.
  - `[low]` `[reject]` (Blind Hunter 4) No escalation on a second signal, and signals are deferred during long work — Same root cause and verdict as Intent Alignment 5.
  - `[medium]` `[patch]` (Blind Hunter 5) A signalled sleep skips the fresh liveness reading, so a watched process that exited during the sleep is detached as `signal-<NAME>` — Verified at the `break` after the sleep: `watched_alive` was last tick's `True`, so the post-loop `signal-` reason won and escalation detection (skipped when `detach_reason` is set) never ran. Fixed: one fresh `process.is_alive` reading before the `break`; new test `test_a_signal_during_the_sleep_after_the_watched_process_exited_keeps_the_natural_exit_reason`.
  - `[false]` `[reject]` (Blind Hunter 6) The unproven-ownership attach is heartbeat-only; pass the harness run id on argv to supervise it fully — Refuted: the intent's AC for fix 1 reads "keeps heartbeating"; a new argv positional changes the ten-positional contract the intent never asks to change.
  - `[low]` `[reject]` (Blind Hunter 7) The residual risks (same-size in-place rewrite, same-uid SIGKILL, root `os.access`, one-tick latency) sit in prose while DW-FU-3-4-8 is closed; the closed rows' `verified:` text cites a renamed test — SIGKILL and the same-size rewrite are the intent's stated limits; the `verified:` lines are dated history of a closed row.
  - `[low]` `[reject]` (Blind Hunter 8) `MRS-SPIN-018` collides with Story 47.1's spec — Shares a root cause with Verification Gap 4. No collision exists on `main`; 47.1 never landed and its only mention is a triage-log row of a reverted attempt, so whichever story lands second takes the next free code under the registry's normal rule.
  - `[low]` `[patch]` (Blind Hunter 9) `test_every_entry_goes_through_the_one_held_descriptor` fills `used_append_line_directly` and never asserts it — Shares a root cause with Verification Gap 1 and Edge Case Hunter 10. Fixed: `FakeFs.direct_append_line_calls` counts only direct `append_line` calls (held appends use a private helper), and the test asserts it is 0 and that entries were appended.
  - `[false]` `[reject]` (Blind Hunter 10) `_fail_closed` can leave the run alive when `stop` fails or raises something other than `HarnessError` — Refuted: a `False` or `HarnessError` result is recorded (`stopped: false`, `MRS-SUPV-012`) in the same shape as the existing `budget-stop` and `defer` stops; `LocalHarness.stop` converts every launch failure and timeout to `HarnessError` (`harness_bmadloop.py:1727-1733`), so nothing else escapes.
  - `[low]` `[reject]` (Blind Hunter 11) Stringly-typed tamper kinds, a handle with no closed marker, a port docstring that says "at most once" beside a double-close test — No caller can reach the `KeyError` (the four kinds are closed in one function), `close_append` runs once in the outermost `finally`, and the double-close test pins the documented never-raises behaviour.
  - `[low]` `[patch]` (Blind Hunter 12) The module docstring sentence ends "which exits 1) and exit 0" — Verified at the opening paragraph. Fixed: reworded to say every detach reason exits 0 except `journal-tampered`, which exits 1.
  - `[low]` `[reject]` (Blind Hunter 13) Test gaps: second signal, partial handler installation, restoring a `None` previous handler, `NotADirectoryError`, a non-`HarnessError` from `stop` — Each would test behaviour rejected above or a one-line mapping; the touched modules pass the station coverage floor.
  - `[low]` `[patch]` (Verification Gap, other 1) The held-descriptor test claims more than it asserts — Same root cause and fix as Blind Hunter 9 (shares its route).
  - `[low]` `[reject]` (Verification Gap, other 2) A non-journal `ValueError` stops the watched run and no test drives it — Same root cause and verdict as Intent Alignment 1.
  - `[medium]` `[patch]` (Verification Gap, other 3) A signal during the sleep while the watched process exits in the same sleep is labelled `signal-<NAME>` — Same defect as Blind Hunter 5; one fix.
  - `[low]` `[reject]` (Verification Gap, other 4) `MRS-SPIN-018` is claimed by two specs with no guard — Same root cause and verdict as Blind Hunter 8.
  - `[low]` `[reject]` (Edge Case Hunter 1) A non-journal `ValueError`/`FsError` stops a healthy run, labelled `journal-tampered` — Same root cause and verdict as Intent Alignment 1.
  - `[medium]` `[patch]` (Edge Case Hunter 2) The signal `break` precedes the liveness re-read, so `watched_alive` is stale — Same defect as Blind Hunter 5; one fix.
  - `[low]` `[reject]` (Edge Case Hunter 3) A second signal is ignored while a blocking call hangs — Same root cause and verdict as Intent Alignment 5.
  - `[low]` `[reject]` (Edge Case Hunter 4) A `SIG_IGN` inherited for SIGHUP/SIGINT is overwritten — The sidecar runs under `start_new_session=True`, so it has no controlling terminal and no terminal-driven SIGHUP/SIGINT; only an explicit `kill` reaches it, and the fix adds a guard for a case no caller has shown.
  - `[low]` `[reject]` (Edge Case Hunter 5) `open_append` failing at attach with no harness run id exits 1 while the same fault later keeps watching — That exit is the pre-existing print-and-exit behaviour; with no run id the supervisor has nothing to act on, and with no journal handle its "keep watching" would write nowhere.
  - `[medium]` `[patch]` (Edge Case Hunter 6) A torn last line with no trailing newline swallows the attach entry, so the `quarantined` count and `MRS-SUPV-011` are lost in exactly the case fix 1 targets — Verified: `fold` quarantines `fragment + attach-json` as one line. Fixed: right after `open_append`, a lone terminator goes through the held handle only when the attach-time text is non-empty and lacks a trailing newline (`fold` skips blank lines); new tests `test_real_fs_a_torn_last_line_is_terminated_so_the_attach_entry_is_not_swallowed` and the no-extra-line control.
  - `[false]` `[reject]` (Edge Case Hunter 7) Any single quarantined line makes ownership unproven, with no check that it is a launch line — Refuted: the intent states the rule literally ("no launch or resume entry but quarantined at least one line"); `fold` cannot say which kind a quarantined line was, and a launch/resume entry for another run id already keeps it inert.
  - `[low]` `[reject]` (Edge Case Hunter 8) `journal_fault_reported` stops the per-tick check after one swallowed append with no run id — With no run id nothing is actionable, and the intent asks for one report that it cannot act; later reports would add no action.
  - `[low]` `[reject]` (Edge Case Hunter 9) A transient `held_file_state` error is classified `unverifiable` and stops a healthy run — An un-statable path is also what a parent directory made inaccessible looks like, a real tamper, so continuing would open a hole; a transient stat failure on a local filesystem is rare.
  - `[low]` `[patch]` (Edge Case Hunter 10) The held-descriptor test asserts nothing about `append_line` — Same root cause and fix as Blind Hunter 9.
  - `[low]` `[patch]` (Edge Case Hunter 11) No test for a signal interrupting the sleep after the watched process exited — Shares Blind Hunter 5's route. Fixed with `test_a_signal_during_the_sleep_after_the_watched_process_exited_keeps_the_natural_exit_reason` (`FakeProcess(alive_for=1)`; the last detach reason is `watched-process-exited`).
  - `[false]` `[reject]` (Edge Case Hunter 12, claim) The AC says the supervisor never exits leaving the run alive, but a failed `stop` exits 1 with the run alive — Refuted: the criterion is that the supervisor stops the run through `HarnessPort.stop` and records why; a stop that fails is recorded with `stopped: false` and `MRS-SUPV-012`, as the existing terminal stops do.
  - `[low]` `[reject]` (Edge Case Hunter 13, claim) `open_append` follows a symlink swapped in before attach — The supervisor reads the same swapped path first and the per-tick check follows it too; before-attach tampering is outside the intent's "between ticks" model, `O_NOFOLLOW` would need care because the run directory is reached through the Tier-3 symlink, and the fix adds a branch.
  - `[false]` `[reject]` (Edge Case Hunter 14, deletion) `_MARSHAL_INITIATED_DETACH_REASONS` lacks `journal-tampered` and `signal-*` — Refuted: its only consumer, `is_marshal_initiated_stop`, is fed by the dispatch journal's `stop_reason` (`cli/dispatch.py:1283-1284`), which this supervisor never writes.

## Auto Run Result

Status: done

**Summary.** The four defects of shipped behaviour in Story 3.4's supervisor are fixed, and DW-FU-3-4-3, -6, -7 and -8 are closed in the deferred-work ledger.

1. A journal with no run-launch or run-resume entry for any run id but at least one quarantined line now attaches. `supervisor-attach` carries `quarantined: <n>` and `MRS-SUPV-011`, and supervision is heartbeat-only because no harness run id is recoverable. A launch or resume entry naming only another run id, or a journal with no quarantined line, stays inert.
2. SIGTERM, SIGHUP and SIGINT journal a final `supervisor-detach` whose reason is `signal-<NAME>` and exit 0. The handlers raise only while the loop is sleeping, are restored on every exit, and are skipped off the main thread.
3. `marshal factory spin` and `resume` journal one `supervisor-spawn` observation (counter 2) carrying the sidecar pid, or `supervisor_pid: None` plus the error. A failure to journal it is `MRS-SPIN-018` (WARN) and never changes the launch outcome.
4. The supervisor opens its journal once through a new `FsPort` held-descriptor family and checks it every tick for a removed, replaced, truncated or read-only file. A tamper or a failed append stops the watched run through `HarnessPort.stop`, records why on stderr and in a best-effort final `supervisor-detach` (`journal-tampered`, `MRS-SUPV-012`), and exits 1. With no harness run id it reports `MRS-SUPV-013` once and keeps watching.

**Files changed** (under `src/shared/packages/pyforge-marshal/` unless rooted):

- `src/pyforge/marshal/ports/fs.py` -- `AppendHandle`, `HeldFileState` and the four held-descriptor methods on `FsPort`.
- `src/pyforge/marshal/adapters/fs_local.py` -- the `LocalFs` implementation: `O_WRONLY | O_APPEND`, no `O_CREAT`, `append_line`'s newline and short-write guards, `fstat` compared with `stat`.
- `src/pyforge/marshal/supervisor/__main__.py` -- unproven attach, signal handling, held descriptor, per-tick integrity check, `_fail_closed`, torn-tail terminator, module docstring.
- `src/pyforge/marshal/cli/spin.py` -- `_journal_supervisor_spawn` for launch and resume, and the corrected `_writer_id` docstring.
- `src/pyforge/marshal/core/findings.py`, `src/pyforge/marshal/core/verdict.py` -- `MRS-SUPV-011`, `MRS-SUPV-012`, `MRS-SUPV-013` and `MRS-SPIN-018`, all WARN.
- `tests/unit/test_supervisor.py`, `test_publisher.py`, `test_spin.py`, `test_fs_local.py`, `test_findings.py` and `tests/meta/test_ad11_write_boundary.py` -- one test per acceptance criterion, real-`LocalFs` tamper tests, and the pins that counted two spin appends (now three).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- four rows closed with `resolved:` lines.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `.../spec-pyforge-core/.memlog.md` -- surface-reconcile `event` entries naming every governed path changed. No baseline was stamped.

**Review findings.** Four layers reported 39 findings: high 0, medium 4, low 25, false 10. There was no intent gap and no bad spec. Nine rows were triaged `patch`, in four grouped entries, and applied. None were deferred. Thirty were rejected, each with its reason in the Review Triage Log.

- Patched, by entry verdict (2 medium, 2 low):
  - medium: a signal that cut the sleep short skipped the liveness re-read, so a watched process that had already exited was detached as `signal-<NAME>` and escaped escalation detection. One fresh `is_alive` reading now precedes the `break`.
  - medium: a torn last line with no trailing newline swallowed the `supervisor-attach` entry together with its `quarantined` count and `MRS-SUPV-011`. A lone terminator is now written first, only in that case.
  - low: `test_every_entry_goes_through_the_one_held_descriptor` asserted nothing about `append_line`. `FakeFs.direct_append_line_calls` now backs a real assertion.
  - low: one module docstring sentence contradicted itself about exit codes.
- Rejected, grouped:
  - A non-journal `ValueError` or `FsError` also fails closed. That changes a diagnostic label only, satisfies the intent's invariant, and D5 designed it.
  - A mid-tick signal waits for the tick, which is bounded by subprocess timeouts.
  - `MRS-SPIN-018` also appears in Story 47.1's never-landed review log. There is no collision on `main`.
  - Findings that restate an intent requirement: a heartbeat-only unproven attach, any quarantined line counting, a signal detach, and a failed `stop` recorded rather than retried.

**Follow-up review recommendation:** `followup_review_recommended: true`. Two medium entries were patched. The unverified risk no layer could settle is that no test delivers a real signal to a separate supervisor process or races a live sidecar's `supervisor-spawn` append against the parent's: signals are raised in-process against sentinel handlers, and the held-descriptor tamper tests run `LocalFs` in-process with a fake process and harness.

**Verification** (exit codes read directly, never through a pipe), on the patched tree:

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 9930 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0 (ruff, `ruff format --check`, mypy, target-version, precommit-config).
- `python scripts/spec_surface_reconcile.py` -- exit 0, "no drift". `--write-baseline` was never run.
- The marshal unit coverage gate passed with every touched module at or above 80% (`supervisor/__main__.py` 89%). That was measured before the review patches and not repeated after them.

**Mutation proof** (each fix edited out in place, its tests run, then restored; `git stash` was never used). Fix 1: `unproven_ownership = False`, and widening the rescue over another run's launch entry. Fix 2: handlers not installed, the `signal-<NAME>` reason dropped, and the post-sleep liveness re-read removed. Fix 3: the success call and the error call each removed. Fix 4: per-tick check removed, `HarnessPort.stop` removed from `_fail_closed`, a failed append back to print-and-exit, the no-run-id swallow removed, the `max(expected_size, state.size)` floor raise removed, and the torn-tail terminator removed. Every removal failed its named test.

**Residual risks:**

- A same-size, same-inode in-place rewrite of the journal is not detectable by this check. Privilege separation stays out of scope per Boundaries.
- The final `supervisor-detach` and the `supervisor-journal-fault` observation are best-effort and may land on an unlinked or truncated file. The stderr line in `supervisor.log` is the durable record, and detection lags up to one 60 s tick.
- `MRS-SPIN-018` is also named in blocked Story 47.1's review log. Whichever story lands second takes the next free code.
- A tamper that leaves the journal replaced while no harness run id is known is reported but cannot be acted on.
