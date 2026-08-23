---
title: Status and the feed-mirror decision
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 686de783c4
---

<intent-contract>

## Intent

**Problem:** `steward workspace ls` deliberately avoids per-worktree git cost; operators still need dirty/ahead/behind/merged status, and two open questions from spec-scratch-worktree-lifecycle CAP-3 remain unresolved (Tier-3 feed rsync-mirror verb vs join `start`; whether `workspace update` exists).

**Approach:** Add `steward workspace status [<slug>]` that pays the per-worktree git-subprocess cost. Record dated Spec Change Log decisions for the two open questions — decisions recorded, not silently implemented beyond status.

## Acceptance Criteria

- `steward workspace status [<slug>]` reports dirty/clean, ahead/behind, merged? (JSON + human).
- Dated Spec Change Log entries resolve: (1) Tier-3 feed rsync-mirror as own verb vs join `start`; (2) whether `workspace update` exists at all.
- Own-worktrees-only HARD rule still holds (foreign Marshal loop homes invisible).

## Boundaries & Constraints

**Never:** Implement multi-repo set (13.3–13.4). Never `scripts/bmad-switch`. Do not silently invent `workspace update` without the logged decision.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` — workspace duty + CLI status
- Spec Change Log on related planning spec / this story spec

## Verification

- Unit/integration tests for status fields + foreign-worktree invisibility
- `pixi run --frozen -e pyforge-steward` (or established package test task)
