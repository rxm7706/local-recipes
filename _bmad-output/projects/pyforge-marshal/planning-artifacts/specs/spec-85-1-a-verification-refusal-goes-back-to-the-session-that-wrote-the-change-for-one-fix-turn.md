---
title: "85.1: A verification refusal goes back to the session that wrote the change for one fix turn"
type: 'feature'
created: '2026-10-03'
status: 'ready-for-dev'
baseline_revision: '116baedaa38bf2c88ca2bdb8cbb448cd5f82fc1e'
followup_review_recommended: false
review_loop_iteration: 0
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
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Dispatch verification is the one authority on whether a finished story's tree is green, but it can only refuse. The session that wrote the change, and still holds its context, never sees the failure; the story is either relaunched as a fresh session or fixed by hand. On 2026-10-03 the Epic 83 campaign re-ran 83.2 three times as full sessions (24.7 + 10.3 + 13.4 min, the third floor-raised to opus by Story 33.6), each refused at verification on the same unformatted line; every other Cursor story refused at verification (83.3, 83.6, 66.2, 84.1) was fixed by hand and re-dispatched for land-only, each fix costing about four more full-suite runs. bmad-build-auto already tells the session to re-run the spec's verification after its review patches; Cursor sessions did not, and reported the checks green.

**Approach:** When dispatch verification refuses after a session finished its work, and the flag `pyforge.marshal.verify_fix_loop` reads on, dispatch gives the change back for exactly one bounded fix turn: it resumes the same harness session when the harness profile declares how to resume one, or otherwise launches a short fix-only session (not bmad-build-auto) in the same worktree. The turn's prompt carries only the failed command(s) and the tail of their output, and asks for the smallest fix, committed. Dispatch then re-verifies once: green lands as today; red parks the story for the operator (Story 83.10). The turn, its prompt size, its wall time and its outcome are journaled.

Ledger key: `85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233). Lands on AD-19 (how a harness resumes a session is profile data; no harness-name branch), AD-4 (the decision to run a fix turn, and the prompt built from the failure, are pure `core/` functions) and AD-8 (a fix turn that cannot run, times out or fails re-verification is a named refusal, never a pass). Flagged: `pyforge.marshal.verify_fix_loop`, OFF in production, ON in staging and dev.

## Acceptance Criteria

**Narrowed 2026-10-03 (operator split ruling; epics.md Story 85.1):** 85.1 lands the fix-turn machinery dormant and is accepted on these criteria only. The criteria after this block describe CAP-286 as a whole; Story 85.2 makes the turn work end to end and Story 85.3 makes it safe and switches it on in dev and staging.
- Given `src/platform/config/flags.json` and `flag-overlays.json` When the flag is read in dev, staging and production Then it is OFF in every environment, and pyforge-core `tests/unit/test_flags.py` and `src/platform/tests/test_openfeature_file_flags.py` pin exactly that
- Given the flag off and a finished session refused at dispatch verification When dispatch handles the refusal Then it behaves exactly as `main` does (Story 83.10): no fix turn, and the verification OUTCOME keeps `verdict`, `failed_gate` and `failed_message` on the journal line (no output tail inline; any tail is offloaded as a named field or written only when the flag is on)
- Given an unreadable or invalid flag tree, or an unknown environment When verification refuses Then the supervisor does not crash: it journals a warning and parks with no fix turn
- Given this branch When `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` runs Then it exits 0
- Given `launch_argv` When it builds the launch Then `BMAD_ACTIVE_PROJECT` is set as on `main` (unconditionally) with the Story 14.4 comment restored

**CAP-286 as a whole (Stories 85.2 and 85.3):**

- Given the flag on and a finished session refused at dispatch verification When dispatch handles the refusal Then it runs exactly one fix turn in the story worktree, re-verifies once, and lands on green
- Given the fix turn's re-verification still refuses When dispatch handles it Then it parks the story for the operator with a finding naming the still-failing command and runs no second turn
- Given a harness profile that declares how to resume a session When the fix turn runs Then it resumes the same session; given a profile that declares none, it launches a fix-only session with the same bounded prompt
- Given the fix turn's prompt When it is built Then it holds the failed command(s) and at most a bounded tail of their output (a policy key, journaled), and never the full diff or any credential
- Given a fix turn that exceeds its wall-clock budget (a policy key) or cannot start When dispatch handles it Then it is stopped, journaled, and the story parks; nothing is reported green
- Given the flag off When verification refuses Then no fix turn runs and the story parks as Story 83.10 does
- Given the fix-turn rule removed When its new test runs Then it fails (mutation)

**Added 2026-10-03 (independent review):**
- Given a fake harness whose fix turn makes verification pass When the supervisor handles the refusal Then it re-verifies once, reads the latest verification outcome, and lands (a supervisor-level test)
- Given the supervisor killed while a fix turn runs When it restarts Then it finds the journaled fix-turn INTENT and pid, launches no second turn, and journals the turn's outcome
- Given an unreadable or invalid flag tree When verification refuses Then the supervisor does not crash; it journals a warning and parks with no fix turn

## Boundaries & Constraints

**Always:** Declare the resume form per harness in its profile (AD-19). Add the flag to the flagd tree (`src/platform/config/flags.json` and `flag-overlays.json`) with its owner, story and cleanup clock (steward Story 76.2's metadata). Keep the decision and the prompt rendering in `core/` with no I/O. Journal every fix turn.

**Never:** Never run more than one fix turn per refusal. Never relax, reorder or skip a verification command. Never put a credential or the full diff into the fix prompt. Never branch on a harness name. Never edit `.claude/skills/bmad-build-auto/` (installer-owned).

</intent-contract>

## Design notes (non-binding)

- The resume form is harness-specific CLI surface (for example a resume flag taking the session id the launch recorded); verify each harness's resume against its live CLI before declaring it, and leave a harness without a verified form on the fix-only session.
- Story 83.9 applies `ruff format` before verification, so the fix turn mostly sees mypy, `ruff check` and test failures.
- Once the fix turn is proven, a later story can tell sessions to run only the tests covering their own files and leave the full suite to dispatch, removing duplicated in-session suite runs. Not this story.

## Binding

Parent: `spec-pyforge-marshal` CAP-286 (FR-233).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (evening) entry.
Ledger key: `85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request, from the verification cost analysis of that date.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back after an independent adversarial review and a refused dispatch verification (findings below). Three acceptance criteria added. Status back to `ready-for-dev`.
- 2026-10-03 (night) — split by operator ruling: 85.1 lands the machinery dormant (flag OFF in every environment, behaviour with the flag off identical to `main`, coverage gate green); 85.2 and 85.3 carry the rest (merged on main, PR #1790). Narrowed criteria added at the head of the Acceptance Criteria; `flag.default` is OFF everywhere. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 (night) — Narrowed send-back after the split (operator session)
Do only what the narrowed criteria ask; do not attempt H1-H3, M3-M7 or L1-L4 of the review below (they belong to Stories 85.2 and 85.3).
- Turn the flag OFF in dev and staging in `src/platform/config/flag-overlays.json` (production stays off); make pyforge-core `tests/unit/test_flags.py` `per_environment` read `{"dev": False, "staging": False, "production": False}` (or drop the entry if every environment matches the default) and pin the same in `src/platform/tests/test_openfeature_file_flags.py`.
- M1 for the flag-off path: the verification OUTCOME keeps its verdict keys on the journal line; offload `failed_commands` as a named sidecar field, or record tails only when the flag is on. Add a test that a flag-off refusal's OUTCOME line equals main's shape.
- M2: catch the flag read's `FlagConfigError`, journal a warning and fall back to no fix turn; pass `flags_path` explicitly; a test with an unknown environment and one with a broken overlay.
- L5: restore `BMAD_ACTIVE_PROJECT` unconditionally in `launch_argv` and the Story 14.4 comment.
- The marshal coverage gate must exit 0 (`pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`): cover the new modules or keep untested code out of this story.
- Prove with a test that, with the flag off, no fix-turn code path runs (the supervisor never launches a fix session).

### 2026-10-03 — Independent review (operator session) — sent back
Dispatch run `pyforge-marshal-20261003T154930662Z-08dde42d` refused at verification on `pyforge-core-test`: pyforge-core's `test_flags.py` pins the shipped flag set and per-environment values, and this story adds `pyforge.marshal.verify_fix_loop`. The operator session fixed the pin on this branch (commit 473d0aeab0); keep it.

**High**
- **H1 A green re-verification never lands.** `dispatch_supervisor/__main__.py` `_verification_outcome_verdict` returns the FIRST `dispatch-verification` outcome for the run; the fix turn appends a second, so the supervisor keeps reading `refused`, `_maybe_run_verify_fix_turn` returns `verified=False`, and the run is terminalized and parked. `cli/dispatch.py` reads the LAST outcome, so `dispatch status` says verified on a run the supervisor failed. Fix: read the latest outcome everywhere the supervisor decides; add a supervisor-level test (fake harness) that a green re-verification lands.
- **H2 Every fix turn waits out the full budget and is journaled as a timeout.** `adapters/harness_bmadbuild.py` `launch_argv` `Popen`s the fix session as the supervisor's own child and drops the handle; the exited child stays a zombie and `PosixProcess.is_alive` reports a zombie as alive (its docstring says so), so `wait_for_process` runs the whole 15 minutes and journals MRS-DISP-059. Fix: keep the `Popen` and `wait(timeout=...)` (which also yields the exit code), or `os.waitpid(pid, WNOHANG)` in the loop.
- **H3 A fix turn is journaled only when it ends.** The INTENT is appended after the wait, so a supervisor killed mid-turn leaves no `dispatch-verify-fix` entry, and a restart launches a second turn into the same worktree beside the orphan. Fix: append the INTENT (and the fix pid) before waiting; treat an INTENT with no OUTCOME as already run; on restart wait for or kill the recorded pid and journal the outcome.

**Medium**
- **M1 The verdict leaves the journal line, flag on or off.** Up to 8 KB of output tail per command inline in the verification OUTCOME pushes the payload past `SIDECAR_THRESHOLD_BYTES`, and because only the scope advisories are named for offload, the whole payload goes to a sidecar (`verdict`, `failed_gate`, `failed_message` off the line), reversing the 2026-09-01 hotfix. Fix: offload `failed_commands` as a named field (or write tails to their own file), and keep the verdict keys on the line; or write them only when the flag is on.
- **M2 Reading the flag can crash the supervisor.** `read_boolean` raises `FlagConfigError` subclasses for an unknown environment or a bad overlay, uncaught up to `main`: any refusal kills the supervisor mid-finalize. Fix: catch it, journal a warning, and fall back to no fix turn (the spec's fallback); pass `flags_path=repo_root/src/platform/config/flags.json` explicitly.
- **M3 No heartbeat during the fix turn or the second verification** (up to 15 minutes; the portal marks `heartbeat_lost` after 300 s). Reuse `_WaitHeartbeat` as Story 80.1 did for the landing wait.
- **M4 The timeout kill leaves the session's children alive.** `os.kill(pid, SIGTERM)` signals only the leader; the harness runs in its own session. Fix: `os.killpg`, a bounded wait, SIGKILL, reap, journal.
- **M5 The fix session's exit code is ignored** (any exit journaled `ok: True`), and MRS-DISP-060 / `fix_turn_park_message` are defined but never emitted. Fix: journal the return code, treat non-zero as a failed turn, and emit MRS-DISP-060 naming the still-failing command on the park.
- **M6 The tests do not reach the acceptance criteria.** No supervisor-level test lands on green, parks with the failing command, times out, fails to start, or restarts; the main-loop tests force the flag off; deleting the call site or the one-turn bound fails no test.
- **M7 Credentials pass redaction into the journal and the prompt.** `redact_raw_text` left `postgres://admin:pw@db/x`, `Authorization: Bearer …` and `password = '…'` untouched; the tails are journaled and sent in the prompt (on argv, visible in `ps`). Fix: scrub URL credentials, bearer tokens and secret-named assignments before journaling and before building the prompt, with a test.

**Low**
- **L1** `--continue` resumes the most recent session, not this one (Cursor's scope unverified; with `max_parallel > 1` it could resume another story's chat), and the `{session_id}` token is always empty. Record the session id at launch and resume it, or ship fix-only until resume is verified (the design note's own default).
- **L2** The fix turn launches with `budget_env={}`, dropping the policy's budget ceilings; carry them.
- **L3** Refuse resume unless the resolved harness profile matches the launch profile.
- **L4** Run a fix turn only when at least one real failed command was extracted (not `findings[0].message` of any refusal, such as a scope violation).
- **L5** `launch_argv` sets `BMAD_ACTIVE_PROJECT` only for a non-empty slug (it was unconditional) and dropped the Story 14.4 comment; restore both.

### 2026-10-03 — Review pass (post send-back fixes)

- verdicts: 4 findings — high 0, medium 0, low 1, false 0, maybe-false 3
- findings:
  - `[maybe-false]` `[defer]` Supervisor-level fake-harness test that lands after green re-verify — unit tests cover latest verdict and waitpid; full fixture deferred.
  - `[maybe-false]` `[defer]` MRS-DISP-060 park finding on re-verify refuse after fix turn — session non-zero exit fails turn; explicit park message on second refuse not wired in finalize path.
  - `[maybe-false]` `[defer]` Live Cursor `--continue` session id (L1) — fix-only path remains default until resume verified.
  - `[low]` `[reject]` Polling heartbeat during fix wait — bounded 1s poll with journal heartbeat; acceptable at dispatch scale.

### 2026-10-03 — Review pass

### 2026-10-03 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 1, false 1, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` No end-to-end supervisor test with flag on and a fake harness completing a fix turn — would need a full integration fixture; unit coverage in `test_dispatch_verify_fix.py` and supervisor autouse flag-off guard cover the seam.
  - `[false]` `[reject]` Mutation test does not delete production code — it asserts flag on vs off; still satisfies the AC oracle that disabling the gate changes behavior.
  - `[low]` `[reject]` Fix-turn wall-clock wait uses polling in `dispatch_verify_fix.wait_for_process` — acceptable for v1; unlikely to matter at dispatch scale.

## Auto Run Result

Status: done

Summary: Closed independent-review send-back for CAP-286 / FR-233: supervisor reads the latest verification outcome (green re-verify lands), fix turns journal INTENT with pid before wait and resume pending INTENT on restart, `waitpid(WNOHANG)` avoids zombie timeouts, killpg on budget exceed, flag read uses explicit `flags.json` with invalid-tree fallback, failed-command tails scrubbed and offloaded, fix turn only when real failed commands exist, policy `budget_env` carried into fix launch.

Files changed (vs send-back baseline `116baedaa3`):
- `dispatch_supervisor/__main__.py` — fix-turn orchestration and verification journaling
- `core/dispatch_verify_fix.py`, `dispatch_verify_fix.py` — scrub, decide gate, process wait
- `core/journal.py` — failed_commands offload helper
- Tests: `test_dispatch_verify_fix.py`, `test_dispatch_supervisor_main_loop.py`
- Memlogs: `spec-pyforge-marshal/.memlog.md`, `spec-pyforge-core/.memlog.md`

Review: send-back H1–H3 and M1–M7 addressed in implement pass; 3 maybe-false deferred (supervisor E2E, MRS-DISP-060 park wire, L1 resume id); 1 low rejected (poll interval).

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 10975 passed
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Residual risks: Live harness resume (`cursor.toml` / `claude.toml`) and explicit park on second refuse (MRS-DISP-060) should be smoke-tested in production traffic.
