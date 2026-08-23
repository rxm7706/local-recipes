---
title: The set reports and tears down safely
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 0c5002f42f705b43582e677a1b0db5f1f7915cc1
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

- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — `status_repo_set` / `clean_repo_set` / `open_repo_set_members`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `workspace status|clean <feature>` routes registered repo sets
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace_repo_set_status_teardown.py` — dirty refusal naming, `--merged-only` archive-not-delete, own-worktrees-only set-wide
- Parent: [spec-multi-repo-workspaces/SPEC.md](./spec-multi-repo-workspaces/SPEC.md) CAP-2

## Verification

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` — **765 passed**

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Code Map said "status/remove verbs"; updated to status/clean routing that matches the shipped CLI surface.

## Auto Run Result

- **Summary:** `steward workspace status <feature>` reports dirty/unpushed across every open repo-set member; `steward workspace clean <feature>` refuses while any member is dirty (names them), and with `--merged-only` archives each member via 13.1 archive-not-delete. Own-worktrees-only holds set-wide (foreign loop homes fixture-proven invisible).
- **Files changed:** `workspace.py` (set status/teardown), `cli.py` (optional clean slug + set routing), `test_workspace_repo_set_status_teardown.py`, this spec.
- **Review findings:** 1 low patch applied (Code Map wording); 0 deferred; rejects dropped (naming "remove" vs existing `clean` verb is outside AC).
- **Follow-up review recommendation:** false (patched: high 0, medium 0, low 1 → score 1).
- **Verification:** full steward suite 765 passed.
- **Residual risks:** set clean without `--merged-only` still requires interactive confirm per member (same as single-repo 13.1); concurrent bookkeeping races remain deferred from 13.1.
