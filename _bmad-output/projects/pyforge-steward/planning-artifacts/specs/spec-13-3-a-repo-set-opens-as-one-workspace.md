---
title: A repo set opens as one workspace
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 16cef86c06
---

<intent-contract>

## Intent

**Problem:** Multi-repo features still require hand-cut worktrees per repo; there is no declarative set that opens as one workspace (spec-multi-repo-workspaces CAP-1).

**Approach:** Extend steward workspace so `steward workspace start <feature>` against a declarative `[projects.<slug>]` repo set cuts one worktree per registered repo on branch `f-<feature>`, generates a `.code-workspace`, names missing members (never guesses), and records a dated Spec Change Log entry resolving the registry-location open question.

## Acceptance Criteria

- Declarative `[projects.<slug>]` repo set supported.
- `steward workspace start <feature>` creates one worktree per registered repo on `f-<feature>`.
- Generates a `.code-workspace` file.
- Missing members are named, never guessed.
- Registry-location open question resolved with a dated Spec Change Log entry.

## Boundaries & Constraints

**Never:** Implement 13.4 teardown/reporting. Own-worktrees-only HARD rule still holds. Never `scripts/bmad-switch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` workspace duty + CLI
- Registry config for `[projects.<slug>]`

## Verification

- Unit/integration tests for multi-repo start + missing-member naming
- `pixi run --frozen -e pyforge-steward` (or established package test task)
