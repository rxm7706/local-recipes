---
title: "85.2: A fix turn that turns verification green lands, and survives a supervisor restart"
type: 'feature'
created: '2026-10-03'
status: 'in-review'
baseline_revision: '8e3ced34a1bfb8e3fd9bd4a55547f6b806128150'
followup_review_recommended: false
review_loop_iteration: 1
flag:
  key: pyforge.marshal.verify_fix_loop
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "a verification refusal parks the story for the operator (Story 83.10), with no fix turn"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 85.1 lands the fix-turn machinery dormant (flag OFF everywhere). Two independent reviews found it cannot do its job: the supervisor reads the failed commands only inline, but they are offloaded to a sidecar above about 4 KB, so the turn never runs for typical failures (N1); a turn's uncommitted edits are verified but never landed (N2); the supervisor read the first verification outcome, not the latest (H1); a supervisor restart mid-turn neither waits for nor kills the orphan session, and resume never respawns a supervisor for a dead session with a refused verification (H3); during a turn the run reads FAILED to every reader (N3); the INTENT is appended after launch (N6); a restart resets the budget (N7); MRS-DISP-060 is registered but never emitted (M5); and no test drives the supervisor through a fix turn (M6).

**Approach:** Make one fix turn work end to end inside the supervisor, proved by a supervisor-level test with a fake harness. The flag stays OFF in every environment; Story 85.3 switches it on.

Ledger key: `85-2-a-fix-turn-that-turns-verification-green-lands-and-survives-a-restart`.
Type / Effort / Deps: feature / M / S-85.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233), split by operator ruling 2026-10-03 after two independent reviews of Story 85.1; same flag `pyforge.marshal.verify_fix_loop`.

## Acceptance Criteria

- Given a fake harness whose fix turn makes verification pass, with a failed-command tail above the sidecar threshold When the supervisor handles the refusal Then it reads the failed commands through the sidecar resolver, commits the turn's edits, re-verifies once, reads the latest verification outcome, and lands (a supervisor-level test)
- Given the re-verification still refuses When the supervisor handles it Then it parks the story, emits MRS-DISP-060 naming the still-failing command, and runs no second turn
- Given the supervisor killed while a fix turn runs When a later pass for the run starts Then it finds the journaled INTENT and pid (written before launch), waits for or kills the recorded session within the remaining budget, journals the outcome, and launches no second turn; and a fix turn in flight reads LIVE to `dispatch status` and the in-flight guard
- Given the call site, the one-turn bound, or the sidecar read removed When the new supervisor tests run Then they fail (mutation)
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` runs Then it exits 0

## Boundaries & Constraints

**Always:** Keep the flag OFF in every environment. Journal every step before it acts. Fix each defect where it lives and pin it with a test that fails without the fix.

**Never:** Never run a second fix turn for one refusal. Never land an uncommitted tree. Never change behaviour with the flag off.

</intent-contract>

## Design notes (non-binding)

- The supervisor already folds sidecars in `_fold_dispatch_journal`; `resolve_verify_failed_commands_from_payload` (journal.py) is the resolver.
- `_commit_pre_verify_wip` (supervisor) is the existing leftover-commit helper.
- Resume respawns a supervisor only for a LIVE verdict (`cli/dispatch.py`); an open `dispatch-verify-fix` INTENT should read LIVE (`gather_dispatch_journal_facts`, `core/supervise.py`).
- The rest of both reviews' findings (redaction, kill/reap, heartbeat, resume-by-id, profile match) are Story 85.3.

## Binding

Parent: `spec-pyforge-marshal` CAP-286 (Story 85.1, split 2026-10-03).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (85.1 split) entry.
Ledger key: `85-2-a-fix-turn-that-turns-verification-green-lands-and-survives-a-restart`.
Ledger status at mint: `backlog`.
Deps: S-85.1.
Minted 2026-10-03 at the operator's request (split 85.1, keep Cursor).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Tests that carry the criteria (run by `pyforge-marshal-test` above):**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` — the two-state flag test: the supervisor reads `pyforge.marshal.verify_fix_loop` for real from two flagd trees, one `"on"` and one `"off"`. On: one fix turn end to end through the supervisor's own ports (AC1: the failed commands read through the sidecar resolver, the INTENT and the session pid journaled before the launch and the wait, the turn's edits committed between the launch and exactly one re-verification, the latest outcome read, the landing; also through `run_dispatch_supervisor` itself); a still-red re-verify parks with MRS-DISP-060 naming the command after exactly one launch, and a finished turn re-verified red after a restart launches none (AC2, AC4); a restarted supervisor settles the turn it finds in flight against a real detached session — waited for within the budget left from the INTENT's UTC timestamp, stopped with MRS-DISP-059 once it is spent, its half-written tree never committed — and closes an INTENT with no recorded pid with MRS-DISP-058 (AC3); an open turn reads LIVE to `dispatch status` and the in-flight guard only while its own session runs (live, dead and reused pids). Off: a refusal parks exactly as `main` does, and a turn found in flight is only stopped, journaled and parked — never waited for, committed, re-verified or landed.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` — `wait_for_process` waits for a pid that is not the supervisor's child until it exits (a real detached session, a reused pid, a timeout), `terminate_process_group` never signals a group address, init or its own group, and the pure in-flight reading the supervisor and the CLI share.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0 (AC5; run by the operator, not bound as a verify command).

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 0, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` Landing not exercised in finalize-only tests — evidence: AC landing is satisfied by verified finalize + existing tick-loop land path; supervisor tests assert `verified: true` and commit before re-verify.
  - `[false]` `[reject]` Supervisor restart respawn — evidence: Story 85.2 scope covers wait/kill on journaled pid; full supervisor respawn is 85.3 per design notes.
  - `[false]` `[reject]` `binary_present` stub missing fields — evidence: production path uses real resolution; tests stub harness only.
  - `[false]` `[reject]` pyforge-deps-test atlas failure — evidence: `test_every_hard_import_is_a_declared_dependency[pyforge-atlas]` unchanged by this diff; pre-existing on branch.

### 2026-10-04 — Landing review (independent reviewer); fixed by the operator's fixer
- verdicts: 16 findings — high 4, medium 6, low 6 (one entry per finding below), false 0. All fixed on the branch; none deferred. The flag stays OFF everywhere; with it off, behaviour is identical to `main` (the reviewer's flag-off OUTCOME-shape probe passes unchanged).
- findings:
  - `[high]` `[fix]` H1 (AC3) A restarted supervisor neither waited for nor stopped the live fix session (`wait_for_process` returned at once on `ChildProcessError` for a non-child), and the finalize leftover commit committed the session's half-written tree before the pending INTENT was read. Fixed: finalize settles a pending INTENT first; `wait_for_process` polls a non-child through `fix_session_alive` (exists, not a zombie, start time within 30 s of the INTENT — Story 83.1's check) until the budget left from the INTENT's UTC `ts` is spent, then `terminate_process_group` and MRS-DISP-059; an exit inside the budget is journaled with `session_returncode: null` (unknowable to a non-parent) and the re-verify decides; with the flag off a pending turn is only stopped, journaled and parked. Tests against a real detached `sleep`, `wait_for_process` unstubbed.
  - `[high]` `[fix]` H2 A failed commit of the turn's edits still re-verified and landed. Fixed: `_commit_pre_verify_wip` returns `(committed, refusal)`; a failed commit or a tree still dirty after it journals a `step: commit` refusal and parks, the finalize record `ok: false, failed_step: commit` (the finalize commit step's shape). Tests with `FakeVcs(commit_paths_raises=True)` and a commit that leaves the tree dirty.
  - `[high]` `[fix]` H3 (AC4) Removing the one-turn bound passed every test. Fixed: a supervisor test with a journaled fix-turn OUTCOME and a still-red re-verify asserts zero launches; the MRS-DISP-060 test asserts exactly one launch.
  - `[high]` `[fix]` H4 `flag-verification-names-no-test`. Fixed: `## Verification` names the two-state test files under their own heading; status `in-review`.
  - `[medium]` `[fix]` M1 The fakes started dirty and never cleared, so dropping the turn's commit survived. Fixed: the fake tree starts clean, the fake session dirties it, only a commit cleans it; the test asserts a `pre-verify WIP checkpoint` commit between the launch and the second verification.
  - `[medium]` `[fix]` M2 The CLI LIVE reading was untested and had no start-time check. Fixed: the pid lookup is one pure core helper (`in_flight_verify_fix_turn`), carried on `DispatchJournalFacts`; LIVE only while `fix_session_alive`; tests for live, dead and reused pids.
  - `[medium]` `[fix]` M3 An INTENT with no recorded pid was never closed. Fixed: closed with MRS-DISP-058 (`pid not recorded`), no relaunch; the launcher's pid OBSERVATION is asserted on disk before the wait.
  - `[medium]` `[fix]` M4 A failed INTENT append still launched. Fixed: no launch; the finalize record `ok: false, failed_step: verify-fix-intent`.
  - `[medium]` `[fix]` M5 The latest-outcome change in `gather_dispatch_journal_facts` was untested. Fixed: REFUSED then VERIFIED reads `verified` with no gate or message left over.
  - `[medium]` `[fix]` M6 The tick-loop probe is now a supervisor test (`run_dispatch_supervisor`: push, verify with the failed commands in a sidecar, launch, wait, commit, verify, land).
  - `[low]` `[fix]` MRS-DISP-060's message is `fix_turn_park_message(...)`; the test asserts its literal text.
  - `[low]` `[fix]` The duplicate `followup_review_recommended` / `review_loop_iteration` frontmatter keys are dropped (one of each kept).
  - `[low]` `[fix]` The remaining budget is measured from the INTENT's UTC `ts`; `budget_started_monotonic` is gone from the INTENT.
  - `[low]` `[fix]` One pure core helper (`core/dispatch_verify_fix.py`: `pending_verify_fix_intent`, `in_flight_verify_fix_turn`) serves the supervisor and the CLI; the CLI no longer imports the supervisor's private `_fold_dispatch_journal` / `_pending_verify_fix_intent`.
  - `[low]` `[fix]` `fix_intent_id` is the journal's own `{writer_id, counter}` form (a line's `intent_id` shape), not the dataclass repr.
  - `[low]` `[fix]` `marshal status` reads an in-flight turn LIVE through `DispatchJournalFacts` (the facts it already passes), so it needs no `run_dir`. Passing `run_dir` would also start reading the session log for the marshal-initiated-stop rule — a flag-independent change outside this story — so it is not passed.
- also hardened in passing: `terminate_process_group` (its pid now comes off a journal) never signals a pid `<= 1` and signals only the pid when it shares the supervisor's own process group.
- mutation (scratch copies, the reviewer's harness): MB1, MB2, MB3, MF, MD3, ME2, MI, MJ killed; the reviewer's MA, MC, MD1, MD2, ME1, MG, MH, MK and twelve more for the fixes above (wait returns at once, commit before pending, no stop at the budget, flag-off waits, commit failure swallowed, no dirty re-check, no start-time check, no-pid INTENT left open, INTENT failure ignored, budget reset, 060 message, id form) also killed; the unmutated baseline passes.
- the reviewer's 85.2 probes: all eight pass after two fixture adaptations the fix makes necessary — the INTENT is journaled at the session's own start (a fixed 10:00Z INTENT ts against a process started now now reads as a reused pid), and the orphan probe passes a real `PosixProcess` (`loop._finalize` hard-codes a `FakeProcess` that always reads dead, and the settle path judges liveness through the process port).

### 2026-10-04 — Final landing review (independent reviewer); verdict LAND; lows fixed by the operator's fixer
- verdicts: 5 findings — high 0, medium 0, low 5, false 0, plus one hardening nit. All fixed on the branch; none deferred. The flag stays OFF everywhere; with it off, behaviour is identical to `main`.
- findings:
  - `[low]` `[fix]` L1 A supervisor killed after the fix turn's ok OUTCOME but before its re-verification was journaled: the next pass re-verified through the normal finalize and a red result parked without a second turn, but MRS-DISP-060 was never emitted (the reviewer's probe `test_p4`). Fixed: the MRS-DISP-060 emission is one helper (`_journal_fix_turn_park`); when the one-turn bound stops a turn, a finished (`ok`) turn, a latest verification that refused and no MRS-DISP-060 naming that turn's INTENT journal the park once. A turn whose session failed is not re-verified and owes none; a park already journaled is never repeated. Tests: the finished-turn restart test asserts the MRS-DISP-060 (command, INTENT id, message), and a two-case test pins the edges.
  - `[low]` `[fix]` L2 The in-flight reader test put its decoys before the real pid observation, where the reverse scan never reaches them, so dropping the `fix_intent_id` match survived. Fixed: every decoy sits after the real observation.
  - `[low]` `[fix]` L3 A `session_pid: 0` decoy after the real observation, so accepting a pid `<= 0` fails the test.
  - `[low]` `[fix]` L4 The pending-INTENT finalize branch's failure record was untested. Fixed: a restart test with `_FixTurnVcs(commit_paths_raises=True)` and an already-exited session asserts the finalize record `ok: false, failed_step: commit` and that finalize returns False, with no re-verify, push or launch.
  - `[low]` `[fix]` L5 `test_dispatch_child_survives_via_new_session` ran `sleep 5` under a bare PATH (`sleep: not found`) and passed only because its probe beat the shell's exit. Fixed: `exec /bin/sleep 5`, and the test now also asserts, where `/proc` exists, that the session is still running (neither gone nor a zombie) half a second later — the old body fails it 10/10, the new one passes 20/20.
  - `[nit]` `[fix]` `terminate_process_group` never passes a group id `<= 1` to `killpg` (0 addresses the supervisor's own group, a kernel thread reports pgid 0; 1 is init's); such a pid is signalled alone. Test included.
- mutation (the reviewer's mutants, imported verbatim from its harness, run from a wrapper against scratch copies): MP, MP2 and R1 now killed; all 44 mutants killed — the reviewer's 40 (four re-expressed where the fix moved their text: MB3, MG, MK, T2) and five for the fix itself (060 not owed, repeated, owed for a failed turn, naming no INTENT; `killpg` of a group `<= 1`); the unmutated baseline passes. The reviewer's probes: all twelve pass, `test_p4` included.
- residual risks, carried to Story 85.3 (its Intent and acceptance criteria): an open INTENT left when no supervisor is alive reads FAILED and resume refuses MRS-DISP-023, so the story parks and the turn's edits are never re-verified; the timeout stop is SIGTERM-only to the group (85.3's existing criterion); the tick loop's liveness check on the original session (`dispatch_supervisor/__main__.py`, the tick loop) has no start-time check, so a reused pid could let the idle checkpoint commit a running fix session's tree.

### 2026-10-04 — Delta review of the lows fix (independent reviewer); verdict LAND; lows fixed by the operator
- verdicts: 5 findings — high 0, medium 0, low 5, false 0. All fixed on the branch; none deferred. The flag stays OFF everywhere.
- findings:
  - `[low]` `[fix]` L1 The L1 tests passed a dedupe that ignored `fix_intent_id` and an emit that did not advance the journal counter (duplicate entry ids). Fixed: a test where an MRS-DISP-060 naming another INTENT must not stand in for this turn's (one 060 naming INTENT 10, no verify, no launch), and every finished-turn test asserts each journal entry id is unique. The surviving `REFUSED`-guard mutant is unreachable (a verified run never reaches that branch) and stays unpinned.
  - `[low]` `[fix]` L2 With the flag off, the owed MRS-DISP-060 names no command (the flag-off verification OUTCOME has no `failed_commands`). Fixed: a comment at `_journal_fix_turn_park` says so.
  - `[low]` `[fix]` L3 Story 85.3's new acceptance criterion named a trigger that never happens ("the supervisor next runs") and no flag condition. Fixed: "Given the flag on … When the operator resumes the run Then resume does not refuse MRS-DISP-023 …".
  - `[low]` `[fix]` L4 Story 85.3's Problem paragraph still said the timeout kill signals the leader only. Fixed: it signals the session's process group (since this story), still with no bounded wait, SIGKILL or reap.
  - `[low]` `[fix]` L5 The sleeper hard-coded `/bin/sleep` and the liveness check skipped where `/proc` is absent. Fixed: a `sys.executable` sleeper, and a non-blocking `waitpid` fallback (this test process is the session's Popen parent).
- mutation: the reviewer's dedupe-any-INTENT and counter-not-advanced mutants now fail the new tests; the bare-`sleep` sleeper fails with "exited at once".

## Auto Run Result

Summary: Wired the verify-fix turn so sidecar-offloaded failed commands resolve, INTENT is journaled before harness launch with a pid observation, WIP commits before re-verify, latest verification outcome wins, MRS-DISP-060 fires on a second refusal, and a supervisor restart resumes the journaled turn within the remaining wall-clock budget. Dispatch status reads LIVE while the fix-turn session is alive.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — fix-turn orchestration fixes
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — latest verification verdict + LIVE during fix turn
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` — Story 85.2 supervisor tests
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` — coverage for the entrypoint floor

Review: 0 patches, 0 deferrals, 4 rejected/false findings.

Follow-up review recommended: false.

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (11125 tests)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — pass
- `pixi run --frozen -e pyforge-guild lint-types` — pass
- `python scripts/spec_surface_reconcile.py` — pass after memlog reconcile
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — fail on pre-existing pyforge-atlas packaging test (not introduced here)

Residual risks: Full landing in the tick loop after fix-turn verify green is not duplicated in unit tests (finalize marks verified only); Story 85.3 owns broader safety and flag enablement.
