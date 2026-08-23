---
title: One command refreshes the fleet's homes
type: feature
created: '2026-08-23'
status: in-review
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 53b166c161848e65a7acc8c0aed96223b81d99f4
---

<intent-contract>

## Intent

**Problem:** Operators lack a single command to refresh all eight BMAD loop homes — behind-counts, fast-forward, and harness policy re-render must be one governed verb (FR-133..135, AD-21).

**Approach:** Add a fleet refresh command (`cli/factory.py` or `cli/refresh.py` + `core/context.py`) that reports each home's behind-count (unreadable homes reported, never skipped), fast-forwards clean trees only (dirty refused by name; push targets `loop/<slug>` only), and re-renders harness policy as a checked step — each step `done | skipped | failed`.

## Acceptance Criteria

- One command reports behind-count for all 8 loop homes; unreadable homes reported, never skipped.
- Fast-forwards clean trees only; dirty homes refused by name; push targets `loop/<slug>` only.
- Re-renders harness policy as a checked step.
- Each step reports `done | skipped | failed`; FF-without-render reports home incompletely refreshed.

## Boundaries & Constraints

**Never:** Force-push. Never touch dirty homes. Never `scripts/bmad-switch` from the verb. No Story 15.2 ledger promotion scope.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/refresh.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/context.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py` (`commits_behind`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Auto Run Result

Status: in-review
Verification: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 5743 passed, 12 deselected.
Changed: `marshal refresh` CLI; `VcsPort.commits_behind`; `core/refresh` step types; `slug_from_loop_branch`; MRS-REFRESH-001..007.
Note: a peer agent briefly collided on this worktree then HALTed; this run completed implementation + verification.
