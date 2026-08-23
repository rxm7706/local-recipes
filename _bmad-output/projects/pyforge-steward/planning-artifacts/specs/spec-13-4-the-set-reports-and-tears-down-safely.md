---
title: The set reports and tears down safely
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
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

### 2026-08-23 — Review pass 1 (pre-merge Code Map)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Code Map said "status/remove verbs"; updated to status/clean routing that matches the shipped CLI surface.

### 2026-08-23 — Review pass 2 (bmad-build-auto four-layer)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 2, low 1)
- defer: 6: (high 0, medium 4, low 2)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` Re-check member dirty/error immediately before each archive (TOCTOU after set-wide gate)
  - `[medium]` `[patch]` Test: refuse clean when member status is unassessable (path missing); no partial archive
  - `[low]` `[patch]` Assert coordinated `.code-workspace` retained after partial `--merged-only`; include `member/` in text `format_clean`
- deferred: silent skip of missing registered members; set vs single-repo slug shadowing; mid-loop archive compensation; CAP numbering doc drift; interactive confirm uses branch slug; parent CAP-2 success prose not updated

## Auto Run Result

- **Summary:** `steward workspace status <feature>` reports dirty/unpushed across every open repo-set member; `steward workspace clean <feature>` refuses while any member is dirty (names them); `--merged-only` archives each member via 13.1 archive-not-delete. Own-worktrees-only holds set-wide (foreign loop homes fixture-proven invisible).
- **Files changed:** `workspace.py` (set status/teardown + TOCTOU re-check + format_clean member prefix), `cli.py` (set routing help), `test_workspace_repo_set_status_teardown.py`, this spec.
- **Review findings:** patches applied 3 (0 high, 2 medium, 1 low); deferred 6; rejected 5 (remove-vs-clean verb, CAP renumber, UX polish, empty-set no-op UX, speculative full rollback).
- **Follow-up review recommendation:** true (patched score 3×2 + 1×1 = 7 ≥ 5).
- **Verification:** story tests 7 passed; full steward suite previously 765 passed; PR #662 CI green on pre-patch commit — re-check after this patch push.
- **Residual risks:** set clean without `--merged-only` still requires interactive confirm per member (same as single-repo 13.1); concurrent bookkeeping races remain deferred from 13.1; missing registered members are omitted from the open set without an explicit warning.
