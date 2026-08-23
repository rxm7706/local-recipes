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

**Problem:** Operators refresh eight loop homes by hand — behind-counts, dirty trees, and harness policy re-render are easy to skip or do inconsistently (FR-133–FR-135, AD-21).

**Approach:** Add one CLI command that reports each home's behind-count (unreadable homes reported, never skipped), fast-forwards clean trees only (dirty homes refused by name; push targets `loop/<slug>` only), and re-renders harness policy as a checked step — each step `done | skipped | failed`; FF-without-render reports the home incompletely refreshed.

## Acceptance Criteria

- One command enumerates all 8 loop homes and reports behind-count per home.
- Unreadable homes are reported, never silently skipped.
- Clean trees fast-forward; dirty homes refused by name.
- Push targets `loop/<slug>` only.
- Harness policy re-render is a checked step; each step is `done | skipped | failed`.
- Fast-forward without successful render reports the home as incompletely refreshed.

## Boundaries & Constraints

**Never:** Touch another station's artifacts. Never `scripts/bmad-switch`. Surface: `cli/factory.py` or new `cli/refresh.py`, `core/context.py`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/` — refresh verb
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/context.py` — home enumeration
- Tests under package `tests/`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
