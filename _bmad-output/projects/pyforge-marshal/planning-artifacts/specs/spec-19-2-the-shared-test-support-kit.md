---
title: The shared test-support kit
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 89896c9458
---

<intent-contract>

## Intent

**Problem:** Marshal's CLI-runner / page-object / DB-factory / auth-HTTP-time mocks are station-local; other stations reimplement them (FR-130). Q-26 (own leaf vs pyforge-core module) must be decided here.

**Approach:** Ship Marshal's four real mocks as a shared kit (`pyforge-testing-kit` or `pyforge.core.testing`), seeded not rewritten, and have at least one other station import from it. Record the Q-26 leaf-vs-core decision in a dated Spec Change Log entry.

## Acceptance Criteria

- Shared kit exposes Marshal's four mock families (CLI-runner, page-object, DB-factory, auth-HTTP-time), seeded from existing Marshal tests.
- At least one other station imports from the kit (not a copy).
- Q-26 decided with a dated Spec Change Log entry (own leaf vs `pyforge.core.testing`).
- Fixture-covered; does not implement 19.3 coverage gates.

## Boundaries & Constraints

**Never:** Rewrite mocks from scratch when seeding is possible. Never implement 19.3/19.4. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- New package or module: `pyforge-testing-kit` / `pyforge.core.testing`
- Marshal tests that currently own the four mocks — become seed / re-export
- One other station's tests import the kit
- Spec Change Log for Q-26

## Verification

- Kit importable; second-station import test green
- `pixi run --frozen -e pyforge-marshal` (+ consumer station env) relevant tests green
- CI: detectors, linter, package tests
