---
title: Every process speaks structlog + OTel
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'b0782c48b4430d474bf23d9da228fb3d9c45433d'
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

**Never:** AD-4/pap:AD-17 topology or chart 12.1 rewrites (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal 20-4. Skip 12-7 forever.

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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `b0782c48b4` (2026-08-23, "Merge pull request #688 from rxm7706/steward/16-3-every-process-speaks-structlog-otel"). Ledger row `16-3-every-process-speaks-structlog-otel: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `pixi.lock`, `pixi.toml`, `src/platform/config/asgi.py`, `src/platform/config/celery_app.py`, `src/platform/config/observability/__init__.py`, `src/platform/config/observability/logging.py`, `src/platform/config/observability/telemetry.py`, `src/platform/config/settings/base.py`, `src/platform/config/settings/production.py`, `src/platform/config/wsgi.py`, `src/platform/manage.py`, `src/platform/platformapp/users/tasks.py` (+2 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
