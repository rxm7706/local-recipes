---
title: Marshal's capabilities become named, typed tools
type: feature
created: '2026-08-23'
status: in-progress
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 0c9c17ecb5
---

<intent-contract>

## Intent

**Problem:** Marshal's factory capabilities are CLI-first and not exposed as a governed, typed tool surface (FR-153); clone-surviving registration exists via `marshal init`'s rendered `.mcp.json` (FR-154 mechanism already covered) but capabilities are not named tools with typed args and structured answers.

**Approach:** Add a `pyforge/marshal/mcp/` (or tools) module that exposes marshal CLI capabilities as named tools with typed arguments and structured answers, registered per-home via the existing rendered `.mcp.json` pattern — never a machine-absolute hand edit.

## Acceptance Criteria

- Marshal capabilities are exposed as named tools with typed arguments and structured answers (FR-153).
- Per-home registration uses the existing rendered `.mcp.json` pattern from `marshal init` — no machine-absolute hand edits (FR-154).
- Fixture-covered; does not claim FR-155/156 parity gates (Story 18.2).

## Boundaries & Constraints

**Never:** Implement Story 18.2 parity/coverage gates. Never hand-edit absolute paths into `.mcp.json`. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/` (or tools module) — named typed tools
- Existing `marshal init` rendered `.mcp.json` registration pattern
- Unit/meta tests under `pyforge-marshal/tests/`

## Verification

- `pixi run --frozen -e pyforge-marshal` relevant unit/meta tests green
- Tool registration survives clone pattern (fixture)
- CI: detectors, linter, package tests
