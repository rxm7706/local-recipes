---
title: Parity and coverage are gated numbers
type: test
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 933c734b7e
---

<intent-contract>

## Intent

**Problem:** After Story 18.1, CLI ⇄ tool parity and per-station tool-surface coverage are still review-time guesses (FR-155, FR-156). The 2-of-6-with-Marshal-at-zero finding is why coverage must be measured, not asserted.

**Approach:** Add a meta-test that fails when a capability is present on one surface (CLI or tools) and absent from the other, plus a per-station coverage report that reports tool-surface coverage as a number.

## Acceptance Criteria

- A capability present in CLI and absent from tools (or vice versa) fails a gated check (FR-155).
- Per-station tool-surface coverage is reported as a number (FR-156) — measured, not hard-asserted to 100%.
- Fixture-covered; builds on Story 18.1 `pyforge.marshal.mcp` surface.

## Boundaries & Constraints

**Never:** Re-implement 18.1 tool registration. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/tests/meta/` — CLI⇄tool parity meta-test
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/` — coverage inventory source
- Optional CLI/report for per-station coverage number

## Verification

- `pixi run --frozen -e pyforge-marshal` meta/unit tests green
- Parity failure case fixture-covered
- CI: detectors, linter, package tests
