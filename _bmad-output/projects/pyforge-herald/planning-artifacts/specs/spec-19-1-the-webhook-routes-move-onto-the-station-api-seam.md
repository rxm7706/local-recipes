---
title: 'The webhook routes move onto the station API seam'
type: 'fix'
created: '2026-09-10'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'c83aafd3fcda9ebf3a8e03366646f49c3cb4c859'
context:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/platform/config/station_api.py
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `webhook.ON_SHIP_PATH` and `ON_PR_CLOSE_PATH` sit on the bare `/api/` namespace owned by the platform FastAPI seam, so Herald's webhook ASGI app cannot be reached through the versioned station API dispatcher — requests 404 silently.

**Approach:** Re-point the route literals onto `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}`, register herald v1 on `config.station_api` beside warden with a lazy mount of `webhook_host`'s ASGI application, and update every live caller (workflow, herald docs) in the same PR.

## Boundaries & Constraints

**Always:** HMAC verification and handler behavior stay unchanged; routes declare full `/stations/herald/api/v1/...` paths per the station API contract; bare `/api/herald/...` must not reach the webhook handler.

**Never:** Add Django or FastAPI imports to `webhook.py`; change webhook business logic; enable `herald-live-demo.yml` (out of scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| NEW_PATH_UNSIGNED | `POST /stations/herald/api/v1/webhooks/on-ship` without HMAC | 401 from webhook handler | Not platform 404 |
| LEGACY_PATH | `POST /api/herald/webhooks/on-ship` | Platform stub 404 | Webhook handler not invoked |
| SIGNED_ON_SHIP | Valid HMAC on new on-ship path | 201 + progress record | Unchanged from Story 13.4 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py:183-184` — `ON_SHIP_PATH` / `ON_PR_CLOSE_PATH` literals to update
- `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py` — lazy `application` / `build_application` mount target (unchanged shape)
- `src/platform/config/station_api.py:111-146` — warden v1 pattern; add `_register_herald_v1` + `register_station_api("herald", 1)`
- `src/platform/config/asgi.py:133-144` — station API dispatch (read-only; already routes `/stations/*/api/v*/`)
- `.github/workflows/herald-live-demo.yml:206,326` — CI caller URLs
- `src/shared/packages/pyforge-herald/docs/cli-runbooks.md:172-180` — operator-facing route docs
- `src/platform/tests/test_station_api_host_dispatch.py` — host-level dispatch tests to extend
- `src/shared/packages/pyforge-herald/tests/unit/test_webhook.py` — ASGI boundary tests (add legacy-path 404)

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py` — update path constants and mount comment — station seam contract
- `src/platform/config/station_api.py` — register herald v1 with health probe + lazy webhook ASGI mount — host dispatch
- `.github/workflows/herald-live-demo.yml` — update POST URLs — CI caller contract
- `src/shared/packages/pyforge-herald/docs/cli-runbooks.md` — document new paths — operator contract
- `src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py` — update daphne smoke URLs
- `src/shared/packages/pyforge-herald/tests/unit/test_webhook.py` — add legacy bare-path 404 test; fix normalization param
- `src/platform/tests/test_station_api_host_dispatch.py` — assert new path reaches webhook (401 unsigned), legacy path 404

**Acceptance Criteria:**
- Given the old `/api/herald/webhooks/*` literals, when they are replaced with `/stations/herald/api/v1/webhooks/*` and herald v1 is registered, then a POST to the new path is handled by the webhook ASGI app (401 without signature, not platform 404)
- Given the route move, when a client POSTs to `/api/herald/webhooks/on-ship`, then the bare path is not served by the webhook handler
- Given the change, when herald-live-demo and cli-runbooks are read, then they name only the new station API paths

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test -- -k "webhook and (station_api or legacy or normalizes)"` -- expected: all selected tests pass
- `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q` -- expected: all pass
