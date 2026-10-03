---
title: "85.2: A fix turn that turns verification green lands, and survives a supervisor restart"
type: 'feature'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
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
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify_fix.py
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

## Review Triage Log

- No review has run yet.
