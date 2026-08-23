---
title: Startup refuses misconfiguration, two-stage and named
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 6044d2bef4
---

<intent-contract>

## Intent

**Problem:** Platform boot can proceed past missing/invalid required settings into import side effects (CAP-3 / `spec-platform-fifteen-factors`). Operators get opaque mid-boot failures instead of a named setting + remedy.

**Approach:** Add a two-stage fail-fast validation contract before app import side effects: stage names each missing/invalid required setting and its remedy. Fixture-prove every required key. Borrow MIT django-15-factor-base patterns with notices if useful. Do not implement 16.3–16.5 (telemetry, policy-as-tests, OIDC).

## Acceptance Criteria

- Missing/invalid required setting → boot fails in a validation stage that **names the setting and its remedy** before app import side effects.
- Fixture coverage for each required key (absence / invalid cases as appropriate).
- Two-stage shape documented in code/docs (validation vs later boot).
- Related platform / steward tests green.
- Does not implement 16.3–16.5, steward 12-7, or Epic 17.

## Boundaries & Constraints

**Never:** AD-4/AD-17 topology or chart 12.1 rewrites (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/config/settings/` (base/local/production) — required env contract
- New or existing startup validation module (design decision this story)
- Platform boot entrypoints: `manage.py` / ASGI/WSGI / celery app import path
- Tests under `src/platform/tests/` proving each required key

## Verification

- Per-key fixtures: fail names setting + remedy; happy path boots
- `pixi run --frozen -e pyforge-steward` / platform test env related pytest green
- CI detectors / linter / package tests
