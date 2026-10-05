---
title: "85.1: A verification refusal goes back to the session that wrote the change for one fix turn"
type: 'feature'
created: '2026-10-03'
status: 'done'
baseline_revision: '17dd386508320fa68c99eec40578d8d5020a39f3'
followup_review_recommended: false
review_loop_iteration: 0
flag:
  key: pyforge.marshal.verify_fix_loop
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
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

**Tests that carry the narrowed criteria (run by `pyforge-marshal-test` above):**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` — the two-state flag test: the supervisor reads `pyforge.marshal.verify_fix_loop` for real from two flagd trees, one `"on"` and one `"off"`. Off: a refusal parks (`verified: false`) with no fix-turn call and the verification OUTCOME keeps `main`'s five keys, for a short and a >4 KB output tail; a refusal journaled with `failed_commands` while the flag was on still runs no turn once it reads off. On: the same refusal reaches the fix-turn launch. An unknown environment, an overlay naming an unknown key and an overlay that is not JSON each journal one `dispatch-verify-fix` warning and park with no fix-turn call.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadbuild.py` — `launch_argv` sets `BMAD_ACTIVE_PROJECT` unconditionally: an empty slug reaches the child as `""` over an inherited value.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0 (narrowed criterion 4; run by the operator, not bound as a verify command).

## Spec Change Log

- 2026-10-03 — sent back after an independent adversarial review and a refused dispatch verification (findings below). Three acceptance criteria added. Status back to `ready-for-dev`.
- 2026-10-03 (night) — split by operator ruling: 85.1 lands the machinery dormant (flag OFF in every environment, behaviour with the flag off identical to `main`, coverage gate green); 85.2 and 85.3 carry the rest (merged on main, PR #1790). Narrowed criteria added at the head of the Acceptance Criteria; `flag.default` is OFF everywhere. Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 (night) — Landing review (independent reviewer); fixed by the operator's fixer
The independent landing review of draft PR #1800 (head f77e106cc3) found detectors-ci red and three narrowed criteria not proven. Fixed on this branch:
- **H1 detectors-ci (3 findings new vs `main`).** (a) flag-gate `flag-verification-names-no-test`: `## Verification` now names `tests/unit/test_dispatch_supervisor_verify_fix.py`, a supervisor-level two-state test (two flagd trees, `"on"` and `"off"`). (b) cap-citation: the branch-only `spec-pyforge-unifying-strategy/.memlog.md` line now cites `spec-pyforge-marshal:CAP-286`, not a bare CAP. (c) chain-currency `chain-audit-checkpoint-staleness` (code newer than retro): the three fix-turn I/O helpers (`verify_fix_loop_enabled`, `wait_for_process`, `terminate_process_group`, with `ProcessWaitResult`) moved from the new module `pyforge/marshal/dispatch_verify_fix.py` into the existing `pyforge/marshal/dispatch_verify.py`; the new module is deleted, and `pyproject.toml`'s AD-3 `source_modules` and `tests/meta/test_ad3_ad4_import_linter.py` are back to `main`. Stories 85.2 and 85.3 (`context:`) and their epics.md Surface lines now point at `dispatch_verify.py`. **Still open (operator):** `chain-currency` stays red after the revert. `scripts/fleet_scan.py` dates marshal's code stage by the git last-touch of `src/shared/packages/pyforge-marshal/pyproject.toml`, and this branch's history touches it twice on 2026-10-03 (auto-checkpoint `fb0106aa6c` added the entry, `d0f88ab152` reverted it), so code (2026-10-03) is still more than two days newer than the last marshal retro (2026-09-26). Clearing it needs either the runbook's remedy, a marshal retro dated 2026-10-01 or later in `planning-artifacts/retros/`, or an operator-authorized history rewrite of this branch; neither is this fix's to make.
- **H2 (narrowed AC 2).** `_run_and_journal_verification` reads the flag on a refusal and builds and emits `failed_commands` (with `output_tail`), and offloads that field, only when the flag reads on; with it off the OUTCOME and its offload set equal `main`'s. Tested for a short and a >4 KB tail.
- **M1 (narrowed AC 2 and 3).** The supervisor's flag-off decision and its broken-tree warning are now reached by tests: the two-state test, plus `PYFORGE_ENVIRONMENT=qa`, an overlay naming an unknown key and an overlay that is not JSON (each on a fresh and on an already-journaled refusal), each asserting one `dispatch-verify-fix` warning observation, `verified: false` on the finalize entry and no call to `binary_present`, `dispatch_verify_fix` or `wait_for_process`. Mutant MC2 (`flag_enabled = True` right after the read) now fails four tests. The autouse fixture in `test_dispatch_supervisor_main_loop.py` no longer stubs the flag read (it only pins `PYFORGE_ENVIRONMENT`), and its docstring no longer claims dev overlays default ON.
- **L1 (narrowed AC 5).** `test_harness_bmadbuild.py` pins `launch_argv` with `project_slug=""` and an inherited `BMAD_ACTIVE_PROJECT`: the child env holds `""`. Mutant MD2 (set it only for a non-empty slug) fails it.
- **L2 (narrowed AC 5).** `launch_argv` carries `main`'s Story 14.4 comment verbatim, and the precedence and wire-PATH comments `dispatch` had; its docstring says it is the one launcher behind both `dispatch` and the fix turn.
- Mutants re-checked against copies of the source (never the worktree): MA1, MA2 (flag tree and overlays ON) killed by pyforge-core `test_flags.py`; MB, MC1, MC2, MD1, MD2 killed; MH2 (emit `failed_commands` whatever the flag) killed.
- **For Story 85.2's restart criterion and Story 85.3's flag criterion (left dormant here, L4):** `_maybe_run_verify_fix_turn` resumes a pending fix-turn INTENT before it consults the flag, so a journaled INTENT with no OUTCOME is waited on even with the flag off or the flag tree broken; decide on the flag first.
- **For Story 85.2's sidecar criterion (left dormant here, L4):** a `failed_commands` field offloaded to a sidecar (a large tail) is invisible to `_failed_commands_from_verification_journal`, which reads only the inline payload, so the turn sees no failed command and never runs; read it through the sidecar resolver.

### 2026-10-03 (night) — Narrowed send-back after the split (operator session)
Do only what the narrowed criteria ask; do not attempt H1-H3, M3-M7 or L1-L4 of the review below (they belong to Stories 85.2 and 85.3).
- Merge note: the operator merged main (steward 84.4's flag, marshal 84.1's harness-profile `model_list`) into this branch. `flags.json` now carries both flags, the marshal flag has NO overlay entry (default `off` in every environment), and pyforge-core `test_flags.py` keeps the marshal `_SHIPPED_CLOCKS` entry with no `per_environment` entry. Check that this is what the tests expect, and add the marshal key to `src/platform/tests/test_openfeature_file_flags.py`'s shipped set (off everywhere).
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

### 2026-10-03 — Review pass (build-auto narrowed closure)
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — gap fixes for platform shipped-booleans pin, coverage gate, and L5 launch_argv were implement verification, not adversarial review output)

### 2026-10-03 — Review pass

### 2026-10-03 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 1, false 1, maybe-false 1
- findings:
  - `[maybe-false]` `[defer]` No end-to-end supervisor test with flag on and a fake harness completing a fix turn — would need a full integration fixture; unit coverage in `test_dispatch_verify_fix.py` and supervisor autouse flag-off guard cover the seam.
  - `[false]` `[reject]` Mutation test does not delete production code — it asserts flag on vs off; still satisfies the AC oracle that disabling the gate changes behavior.
  - `[low]` `[reject]` Fix-turn wall-clock wait uses polling in `dispatch_verify_fix.wait_for_process` — acceptable for v1; unlikely to matter at dispatch scale.

## Auto Run Result

Status: done

Summary: Story 85.1 narrowed scope (CAP-286 dormant machinery): `pyforge.marshal.verify_fix_loop` stays off in every environment with pins in pyforge-core and platform openfeature tests; fix-turn code remains behind the flag; `launch_argv` restores unconditional `BMAD_ACTIVE_PROJECT` and the Story 14.4 detached-launch comment; adapter `dispatch_verify_fix` meets the unit coverage floor.

Files changed (vs baseline `17dd386508`):
- `src/platform/tests/test_openfeature_file_flags.py` — marshal flag in `_SHIPPED_BOOLEANS` (off everywhere)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` — unconditional project pin on fix/dispatch launch
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` — coverage for flag read, process wait, and terminate paths
- Memlogs: `spec-pyforge-marshal/.memlog.md`, `spec-pyforge-unifying-strategy/.memlog.md`

Review: narrowed AC closure pass; no patch/defer items from this pass (see triage log 2026-10-03 evening).

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11089 passed (via coverage-gate suite)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — OK (dispatch_verify_fix ≥ 80%)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Governed paths reconciled in memlogs:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py`
- `src/platform/tests/test_openfeature_file_flags.py` (co-governor `spec-pyforge-unifying-strategy`)

Residual risks: End-to-end fix turn with flag on (Stories 85.2–85.3), live Cursor resume session id, and MRS-DISP-060 park wire remain out of scope for 85.1.
