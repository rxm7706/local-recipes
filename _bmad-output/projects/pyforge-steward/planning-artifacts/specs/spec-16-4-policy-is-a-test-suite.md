---
title: Policy is a test suite
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'PR #693 / b439626af4'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 0e1a41be0f
---

<intent-contract>

## Intent

**Problem:** CAP-4 (`spec-platform-fifteen-factors`) requires dependency / credential-surface / typing / coverage policies as executable tests that red on drift (15-factor policy-suite pattern). Docs-only policy drifts silently.

**Approach:** Encode each policy as a failing-on-drift test and wire the suite into platform CI lanes. Depend on 16.1 (pixi sole authority) already shipped. Borrow MIT django-15-factor-base policy-suite patterns with notices if useful. Do not implement 16.5 (OIDC).

## Acceptance Criteria

- Dependency, credential-surface, typing, and coverage policies each have at least one executable test that fails on deliberate drift.
- Suite is wired into platform CI lanes (not docs-only / manual).
- Related platform / steward tests green on the happy path.
- Does not implement 16.5, steward 12-7, or Epic 17.

## Boundaries & Constraints

**Never:** AD-4 / AD-17 topology or chart 12.1 rewrites (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal 20-6 / PR #691. Skip 12-7 forever.

</intent-contract>

## Code Map

- Platform policy surfaces (deps pins / credential leakage / typing / coverage floors)
- New or extended `tests/` policy suite under platform / steward
- Platform CI workflow / pixi task wiring
- Optional MIT notice if patterns are copied

## Verification

- Intentional drift fixtures/examples → red; clean tree → green
- CI lane invokes the policy suite
- `pixi run --frozen` related pytest green; CI detectors/linter/package tests

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/693
Merge SHA: b439626af427d784ae398728dfd2da34b161ea45
Note: merged with `--admin` (Actions billing blocked CI; local verification green).
Tests: `pytest tests/policy` → 28 passed
