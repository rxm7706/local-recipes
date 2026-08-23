---
title: Coverage gates that name the module
type: test
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 15c004c4c2
---

<intent-contract>

## Intent

**Problem:** Coverage failures report a bare percentage; operators cannot see which module dropped below the station threshold (FR-131).

**Approach:** Wire CI so a PR that drops a touched package below its station threshold fails naming the uncovered module — unit >80% / integration >70% — not just printing a percentage.

## Acceptance Criteria

- CI fails when a touched package falls below the station's unit (>80%) or integration (>70%) threshold.
- Failure output names the uncovered module(s), not only an aggregate percentage.
- Thresholds are per-station (or documented station defaults) and fixture-covered where practical.
- Does not implement 19.4 test-architecture drift re-run.

## Boundaries & Constraints

**Never:** Implement 19.4. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward #675 / 15-1.

</intent-contract>

## Code Map

- CI workflow(s) under `.github/workflows/`
- Per-station coverage config / thresholds
- Coverage reporter that emits module names on fail
- Meta or unit fixture for named-module failure message

## Verification

- Fixture or local run shows named-module fail message below threshold
- `pixi run --frozen -e pyforge-marshal` related tests green
- CI: detectors, linter, package tests
