---
title: A repo set opens as one workspace
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 89724f0a70
---

<intent-contract>

## Intent

**Problem:** Fleet work spans multiple repos but workspace verbs (13.1/13.2) are single-repo. Operators need one command to open every repo a feature touches on a coordinated branch with a generated `.code-workspace`.

**Approach:** Implement declarative `[projects.<slug>]` repo sets per `spec-multi-repo-workspaces` CAP-1. `steward workspace start <feature>` cuts one worktree per registered repo on branch `f-<feature>`, generates `.code-workspace`, names missing members (never guesses). Resolve the registry-location open question with a dated Spec Change Log entry.

## Acceptance Criteria

- Declarative repo-set registry (location decided and logged — not silently invented).
- `steward workspace start <feature>` creates one worktree per registered repo on `f-<feature>`.
- Generates a `.code-workspace` binding the set.
- Missing/unregistered members are named explicitly — never guessed.
- Own-worktrees-only HARD rule still holds (foreign loop homes invisible).

## Boundaries & Constraints

**Never:** Multi-repo teardown/status (13.4). Never `scripts/bmad-switch`. Do not implement 12-7 (live OCP skip). Substrate: 13.1/13.2 single-repo verbs must remain intact.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` — workspace duty, CLI, repo-set registry
- `spec-multi-repo-workspaces/SPEC.md` — CAP-1 binding + Spec Change Log entry for registry location

## Verification

- Unit/integration tests for start across a fixture repo set (missing member named)
- `pixi run --frozen -e pyforge-steward` (or established package test task)
