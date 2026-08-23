---
title: Workspace verbs over git worktree
type: feature
created: '2026-08-23'
status: in-review
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 686de783c4cf20a8c1edd71b36e802b523c87265
---

<intent-contract>

## Intent

**Problem:** Scratch worktrees for steward work lack first-class CLI verbs — operators improvise git worktree commands without bookkeeping or an own-worktrees-only boundary (spec-scratch-worktree-lifecycle CAP-1/2/4/5).

**Approach:** Add `steward workspace start|ls|clean` under pyforge-steward: start creates a worktree from `origin/main` (or `--from`), prints path, records bookkeeping; ls enumerates cheaply without per-worktree subprocess; clean archives-not-deletes (bmad-loop discipline), optional `--merged-only`. All verbs emit `--json`. HARD: ls/clean never see Marshal loop-home worktrees (bookkeeping enforces; test plants foreign worktree and proves invisible).

## Acceptance Criteria

- `steward workspace start <slug> [--from <branch>]` creates worktree, prints path, records bookkeeping; default from `origin/main`.
- `steward workspace ls` cheap enumeration; `--json`.
- `steward workspace clean [--merged-only]` archive-not-delete; `--json`.
- Own-worktrees-only: foreign Marshal loop-home worktree invisible to ls/clean (tested).

## Boundaries & Constraints

**Never:** Touch Marshal loop homes. No `workspace status` / multi-repo set (13.2–13.4). Never `scripts/bmad-switch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` — workspace duty + CLI
- Tests proving foreign loop-home invisible

## Verification

- `pixi run --frozen -e pyforge-steward` (or platform-dev / package test task as established)
- Unit tests for start/ls/clean + foreign-worktree invisibility
