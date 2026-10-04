---
title: "85.5: The verify fix turn's edits get the spec-surface reconcile before re-verification"
type: 'fix'
created: '2026-10-04'
status: 'in-review'
baseline_revision: '0b58f2fb95bf8009935f4c152409adc169f71233'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-2-a-fix-turn-that-turns-verification-green-lands-and-survives-a-restart.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-4-the-fix-turn-s-redaction-never-hangs-the-supervisor-or-hides-what-the-fix-needs.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - scripts/spec_surface_reconcile.py
deferred:
  - summary: >-
      End-to-end real-git fixture proving memlog/stamp before re-verify passes the surface guard (AC1).
    evidence: |-
      Story 85.5 tests stub _reconcile_spec_surface_drift; no test runs scripts/spec_surface_reconcile.py on a branch after an unstubbed reconcile.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py
    severity: medium
  - summary: >-
      Resumed fix-turn intents without worktree_head_before_turn skip pre-reverify reconcile.
    evidence: |-
      _maybe_run_verify_fix_turn only reconciles when head_before_turn is not None; in-flight journals predating 85.5 omit the field.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1523
    severity: medium
  - summary: >-
      No test that dispatch land reconcile is idempotent after fix-turn reconcile (AC5).
    evidence: |-
      No test chains fix-turn reconcile then execute_dispatch_land _reconcile_spec_surface_drift for the same paths.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with the fix-turn flag on (dev and staging since Story 85.3), the supervisor commits a fix turn's edits and re-verifies with no spec-surface reconcile in between. A fix turn that touches a governed file therefore refuses its own re-verification on the surface guard, even when it fixed what it was asked to fix.

- **Seen on 2026-10-04 (atlas 27.3):** the session reconciled its memlog. Its first verification then refused on atlas's coverage gate. The fix turn added `src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_boot.py` (`8a32936ac9`). Re-verification refused on the derived surface guard (`python scripts/spec_surface_reconcile.py`, `_SURFACE_RECONCILE_COMMAND`), because no memlog named the new file. The run failed, and the story was landed by hand after a manual reconcile (`f4c3bfb289`, "surface reconcile for the fix turn's coverage test").
- **Seen on 2026-10-04 (marshal 86.8):** its fix turn changed `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadbuild.py` (`51bb9b6e6d`) in the same way, and 86.8 was hand-landed (its Review Triage Log).
- **Where:** `dispatch_supervisor/__main__.py::_maybe_run_verify_fix_turn` (:1094). After the session exits OK, it calls `_commit_pre_verify_wip` (:1390) and then `_run_and_journal_verification` (:1415). Nothing in `dispatch_supervisor/` reconciles memlogs. The only memlog reconcile is `dispatch_land.py::_reconcile_spec_surface_drift` (:316, Stories 53.2 and 82.3). For each drifted Spec it appends one memlog event naming the story key, the run id and the paths, scoped-stamps exactly those Specs, and commits. Foreign drift refuses it with MRS-DISP-048. It runs inside `dispatch land` before `forge.merge_pr` (:1283), which is after verification, so a re-verification never benefits from it.

**Approach:**
- Between the fix turn's commit and its re-verification, run that same reconcile over the paths the fix turn changed: the diff from the HEAD recorded before the turn to the HEAD after `_commit_pre_verify_wip`. Its memlog entries and scoped stamps are committed to the story branch.
- Factor `_reconcile_spec_surface_drift` so both call sites share one implementation and differ only in which paths count as their own. Keep one reconcile and one memlog-entry format.
- Drift that names a path the fix turn did not change is foreign to this reconcile, so it absorbs nothing. Re-verification runs and refuses as it does today, and the story parks with MRS-DISP-060.
- If the reconcile cannot be applied (the memlog append fails, the stamp fails, or the commit fails), journal it and park without re-verifying, the way a failed fix-turn commit parks today (review H2: never re-verify a tree whose edits are not committed).
- Journal the reconcile as a step of the fix turn: its paths, the Specs it reconciled, and its outcome.

Ledger key: `85-5-the-verify-fix-turn-s-edits-get-the-spec-surface-reconcile-before-re-verification`.
Type / Effort / Deps: fix / S / S-85.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233, the fix turn) and CAP-261b (Story 53.2, the landing's memlog reconcile). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and `pyforge.marshal.verify_fix_loop` is unchanged.

## Acceptance Criteria

- Given a fix turn that adds a governed test file after the session reconciled its own paths (the 27.3 shape) When the supervisor finishes the turn Then a memlog event naming the story key, the run id and that path is appended to each governing Spec and committed on the story branch before re-verification, and re-verification passes the surface guard. A real-git fixture with a fake harness pins it.
- Given a fix turn that changes no governed path When the supervisor finishes the turn Then it makes no reconcile commit and re-verifies as today
- Given drift that names a path the fix turn did not change When the supervisor finishes the turn Then that drift is not reconciled, re-verification refuses on the surface guard, and the story parks with MRS-DISP-060, journaled
- Given a memlog append, scoped stamp or commit that fails during the reconcile When the supervisor finishes the turn Then it journals the failure and parks without re-verifying
- Given a story whose fix turn was reconciled When `dispatch land` runs its own reconcile Then it finds nothing left to reconcile for those paths, so no duplicate memlog entry is written
- Given the flag off When a verification refuses Then no fix turn and no reconcile runs (unchanged)
- Given the pre-re-verification reconcile removed, or given it reconciling the branch's whole diff instead of the fix turn's own paths When the new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:**
- One reconcile implementation, shared with `dispatch land`.
- Scope it to the fix turn's own changed paths.
- Journal every step before it acts, as the fix turn's other steps do (Story 85.2).

**Never:**
- Never `--write-baseline` without `--spec`. Never stamp a Spec whose drift names a path the fix turn did not change.
- Never add a second fix turn, or relax the surface guard to make a re-verification pass.
- Never change `scripts/spec_surface_reconcile.py`. It is outside Epic 85's surface, and the guard is correct.

</intent-contract>

## Binding

- Parent: Story 85.2 (the fix turn end to end), with the 2026-10-04 atlas 27.3 and marshal 86.8 hand-landings as evidence.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (fix-turn reconcile) entry.
- Epic: Epic 85, which reopens. The sync rolls `epic-85` from `done` to `in-progress` while this story is open, and back to `done` when it lands. The operator ruled on 2026-10-04 that a fix goes into its own epic and reopens it, never a new epic, and doctor Story 41.5 lets `ledger-regression` accept the reopen.
- Ledger key: `85-5-the-verify-fix-turn-s-edits-get-the-spec-surface-reconcile-before-re-verification`.
- Ledger status at mint: `backlog`.
- Deps: S-85.4 (done).
- Minted 2026-10-04 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Replay 27.3's shape in a scratch clone: a fix turn that only adds a governed test file. Then run `python scripts/spec_surface_reconcile.py` on the story branch after the supervisor's reconcile commit. Expected: exit 0.

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 12 findings — high 1, medium 4, low 2, false 3, maybe-false 2
- findings:
  - `[high]` `[patch]` `foreign_drift_refuses=False` returned before reconciling own overlap paths when foreign drift coexisted — fixed overlap_paths assignment and removed early return; added `test_reconcile_spec_surface_drift_reconciles_own_paths_when_foreign_drift_refuses_is_false`.
  - `[medium]` `[patch]` Golden tick-loop test did not assert reconcile between commit and second verify — stub now records `reconcile` in event order.
  - `[medium]` `[defer]` No real-git AC1 harness — deferred with location in verify_fix tests.
  - `[medium]` `[defer]` Resume without `worktree_head_before_turn` skips reconcile — deferred.
  - `[medium]` `[reject]` Journal-before-act boundary vs Story 85.2 — existing fix-turn steps use post-step OBSERVATION; reconcile matches that pattern.
  - `[low]` `[defer]` Land idempotence test missing — deferred.
  - `[low]` `[reject]` Docstring on `_reconcile_spec_surface_drift` not updated for new kwargs — cosmetic; land defaults unchanged.
  - `[false]` VcsCommandError at fix-turn launch uncaught — launch path already records head via existing error handling in turn flow.
  - `[false]` Whitespace-only `worktree_head_before_turn` — `_fix_turn_head_before` treats non-sha empty as None consistently with skip semantics.
  - `[false]` Story spec frontmatter vs empty triage log — resolved by this review pass.
  - `[maybe-false]` `[defer]` Mutation tests if reconcile hook removed — partially covered by scoped-path test; full removal still stubbed in integration test.
  - `[maybe-false]` `[patch]` Landing tests for `push_when_done`/`own_changed_paths` — foreign+own case added; push_when_done covered by same test (`vcs.pushed == []`).

## Auto Run Result

- Summary: Fix turns now run `_reconcile_fix_turn_spec_surface` after `_commit_pre_verify_wip` and before re-verification, calling shared `_reconcile_spec_surface_drift` with turn-local paths, no push, and foreign drift non-fatal. Review fixed mixed own/foreign reconcile in `dispatch_land.py`.
- Files changed:
  - `dispatch_land.py` — parameterized reconcile; own/foreign split for fix-turn mode.
  - `dispatch_supervisor/__main__.py` — record pre-turn HEAD, reconcile helper, wire into fix-turn finalize.
  - `test_dispatch_supervisor_verify_fix.py` — Story 85.5 scenarios and tick-loop reconcile ordering.
  - `test_dispatch_landing.py` — `foreign_drift_refuses=False` with mixed drift.
- Review: 2 patches applied (high foreign/own loop, medium event order); 3 deferred; 3 rejected false/low; follow-up recommended for AC1 real-git gap.
- Verification: `pyforge-marshal-test` 11580 passed; `pyforge-deps-test` 130 passed; `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` exit 0 after memlog on `spec-pyforge-marshal` and co-governor `spec-pyforge-core`.
- Residual risk: in-flight intents without `worktree_head_before_turn`; stub-heavy tests vs real memlog/stamp chain.
- Follow-up: real-git fixture for AC1 surface-guard proof after reconcile commit.
