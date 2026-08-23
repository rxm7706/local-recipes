---
title: One command refreshes the fleet's homes
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 52fbe2fac3
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

- `src/shared/packages/pyforge-marshal/cli/factory.py` or `cli/refresh.py`
- `core/context.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
