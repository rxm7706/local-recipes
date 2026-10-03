---
title: "83.8: Dispatch hands a session a story status bmad-build-auto recognizes"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: abbb7ba05f5ce65e54b320b4d30e2c9e7d916c90
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A story spec is minted at `status: 'backlog'` to match its ledger row, but `backlog` is not a status bmad-build-auto recognizes (`step-01-clarify-and-route.md`: draft, ready-for-dev, in-progress, in-review, blocked, done; "status missing or unrecognized: HALT with status `blocked`"). Claude sessions have fallen through to planning; on 2026-10-03 a Cursor session for 83.5 followed the rule literally, halted before any work and set the spec `blocked` (run `pyforge-marshal-20261003T020120169Z-d937e761`).

**Approach:** Before it launches the session, dispatch rewrites a worktree spec whose frontmatter status is `backlog` to `ready-for-dev`, in the worktree copy only, and journals the rewrite on the launch. Any other status is left as it is.

Ledger key: `83-8-dispatch-hands-a-session-a-story-status-bmad-build-auto-recognizes`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 22.11 / Story 28.20 (the dispatch launch path). A defect at the seam with bmad-build-auto, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a worktree spec at `status: 'backlog'` When dispatch launches Then the session reads `ready-for-dev` and the launch journal records the rewrite
- Given a worktree spec at any other status (`ready-for-dev`, `in-progress`, `done`, `blocked`, ...) When dispatch launches Then the status is unchanged and nothing is journaled
- Given a spec with no frontmatter status When dispatch launches Then it is unchanged and dispatch behaves as today
- Given the rewrite removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where dispatch prepares the worktree, and pin it with a test that fails without the fix. Rewrite only the frontmatter `status:` line.

**Never:** Never edit the spec on `main` or in the primary checkout. Never change the ledger. Never edit `.claude/skills/bmad-build-auto/` (installer-owned).

</intent-contract>

## Binding

Parent: Story 22.11 / Story 28.20 (the dispatch launch path).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 entry.
Ledger key: `83-8-dispatch-hands-a-session-a-story-status-bmad-build-auto-recognizes`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request (the ninth defect from landing Phase 2 and Epic 83).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches acceptance criteria)

## Auto Run Result

Status: done

Summary: Before launching `bmad-build-auto`, dispatch rewrites a worktree story spec whose frontmatter reads `status: backlog` to `ready-for-dev`, persists the change only in the worktree copy, and records `spec_status_rewrite` on the `dispatch-launch` INTENT journal entry.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — pure `rewrite_worktree_spec_status_for_bmad_build_auto`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — apply rewrite and journal before harness launch
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — unit, integration, and mutation tests
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile entry

Review: no patches, deferrals, or rejections.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 10834 passed, 5 skipped
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `pixi run -e pyforge-guild python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile

Residual risk: none identified; primary-checkout spec and ledger remain untouched by design.
