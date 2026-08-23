---
title: The set reports and tears down safely
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: df8c8a546f
---

<intent-contract>

## Intent

**Problem:** After Story 13.3, a multi-repo workspace can open, but there is no set-level status or safe teardown (spec-multi-repo-workspaces CAP-2).

**Approach:** Extend steward workspace so one command reports dirty/unpushed across the open set; removal refuses while any member is dirty (naming it); `--merged-only` honors 13.1's archive-not-delete discipline per member; own-worktrees-only HARD rule holds set-wide (loop homes invisible, test-planted).

## Acceptance Criteria

- One command reports dirty/unpushed across every member of an open repo-set workspace.
- Removal refuses while any member is dirty and names the dirty member.
- `--merged-only` honors archive-not-delete per member (13.1 discipline).
- Own-worktrees-only HARD rule holds set-wide (loop homes stay invisible; fixture-planted).

## Boundaries & Constraints

**Never:** Re-implement 13.3 start. Never delete foreign worktrees. Never `scripts/bmad-switch`. Single-repo 13.1/13.2 contracts remain the substrate per member.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — set-level status + teardown
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — status/remove verbs for sets
- Steward unit tests — dirty refusal naming, `--merged-only`, own-worktrees-only set-wide
- Parent: `spec-multi-repo-workspaces/SPEC.md` CAP-2

## Verification

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q`
