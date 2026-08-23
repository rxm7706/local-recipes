---
title: Every process speaks structlog + OTel
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 40a7bf666b
---

<intent-contract>

## Intent

**Problem:** Platform web and Celery worker lack a shared structured-logging + tracing contract (CAP-2 / `spec-platform-fifteen-factors`). Request hops lose correlation; OTLP may be always-on or absent with no endpoint gate.

**Approach:** Wire structlog + OpenTelemetry so a request that fans into Celery carries `request_id` / `user_id` / `trace_id` across web and worker; OTLP export activates only when the endpoint is configured; one trace correlates the hop end-to-end — proven in tests. Borrow MIT django-15-factor-base patterns with notices if useful. Do not implement 16.4–16.5.

## Acceptance Criteria

- Structured logs on web and Celery worker include correlating `request_id` / `user_id` / `trace_id` for a fan-out request.
- OTLP export is off unless the endpoint setting is configured; on when configured.
- Tests assert end-to-end trace correlation across the web→worker hop.
- Related platform / steward tests green.
- Does not implement 16.4 (policy suite), 16.5 (OIDC), steward 12-7, or Epic 17.

## Boundaries & Constraints

**Never:** AD-4/AD-17 topology or chart 12.1 rewrites (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal 20-4. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/config/` — logging / OTel settings + endpoint gate
- Django / ASGI middleware or request context for ids
- Celery signal / task context propagation
- Tests proving correlation + OTLP gate

## Verification

- Fixture/request→Celery path: ids present on both sides; one correlated trace
- OTLP endpoint unset → no export; set → export path active (asserted)
- `pixi run --frozen -e platform-ci-test` / related pytest green; CI detectors/linter/package tests
