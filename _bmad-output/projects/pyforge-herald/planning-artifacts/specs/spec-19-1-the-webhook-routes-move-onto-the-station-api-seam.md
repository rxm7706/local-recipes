---
title: 'The webhook routes move onto the station API seam'
type: 'fix'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Herald's webhook routes (`webhook.ON_SHIP_PATH = "/api/herald/webhooks/on-ship"` and
`ON_PR_CLOSE_PATH = "/api/herald/webhooks/on-pr-close"`, `webhook.py:183-184`) sit on the bare
`/api/` namespace the platform FastAPI seam owns: `config/asgi.py:149-150` routes every `/api/*`
path to `fastapi_application`, and only `_STATION_API_RE` paths are diverted to a station
sub-app (`config/asgi.py:132-144`, `config/station_api.py:24-32`). This contradicts
`spec-pyforge-unifying-strategy` SPEC.md:497's Always rule that station routes are
`/stations/<name>/api/v<N>/`, and herald is not registered on the station API seam the way
warden already is (`station_api.py:146`).

**Approach:** Re-point the two path literals onto `/stations/herald/api/v1/webhooks/on-ship` and
`/stations/herald/api/v1/webhooks/on-pr-close`, register herald v1 on `station_api.py` beside
warden, and move every caller (the `herald-live-demo.yml` workflow, herald's CI-caller
documentation) onto the new path in the same PR — because the surface is a documented,
contract-visible CI-caller contract, fixing it later means changing that contract a second time.

## Boundaries & Constraints

**Always:**
- Herald v1 is registered on the station API seam beside warden (`station_api.py:146`).
- The HMAC verification path stays unchanged — this is a routing fix, not a security change.
- Every caller (workflow, runbook, CLI doc) names the new path in the same PR as the route move.
- A test asserts the bare `/api/herald/...` form is no longer served.

**Never:**
- Leave any caller still referencing the old bare `/api/herald/...` path.
- Change HMAC verification logic itself.
- Add a second public port or standalone service — the routes ride the existing station API seam
  only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Request to the old bare path | `POST /api/herald/webhooks/on-ship` | no longer served by the herald listener | a test names the old path and asserts it is not served |
| Request to the new station-scoped path (on-ship) | `POST /stations/herald/api/v1/webhooks/on-ship` | reaches `webhook_host:application` | HMAC verification unchanged |
| Request to the new station-scoped path (pr-close) | `POST /stations/herald/api/v1/webhooks/on-pr-close` | reaches `webhook_host:application` | HMAC verification unchanged |
| Caller inventory sweep | `herald-live-demo.yml`, herald's CI-caller docs | every caller names the new path | none outstanding referencing the old form |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py` — `ON_SHIP_PATH` /
  `ON_PR_CLOSE_PATH` literals, `:183-184`
- `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py` — the listener the new
  path must route to
- `src/platform/config/station_api.py` — herald v1 registration beside warden, `:146`
- `.github/workflows/herald-live-demo.yml` — caller paths only
- herald's CI-caller documentation — caller paths only

## Tasks & Acceptance

**Execution:**
- fix: re-point `ON_SHIP_PATH`/`ON_PR_CLOSE_PATH` in `webhook.py` to
  `/stations/herald/api/v1/webhooks/on-ship` and `/stations/herald/api/v1/webhooks/on-pr-close`
- fix: register herald v1 on `station_api.py` beside warden (`:146`)
- fix: update `.github/workflows/herald-live-demo.yml` caller paths
- docs: update herald's CI-caller documentation to the new path
- test: assert the bare `/api/herald/...` form is no longer served

**Acceptance Criteria:**
- Given `webhook.ON_SHIP_PATH = "/api/herald/webhooks/on-ship"` and
  `ON_PR_CLOSE_PATH = "/api/herald/webhooks/on-pr-close"`, which sit on the bare `/api/`
  namespace the platform FastAPI seam owns — `config/asgi.py:149-150` routes every `/api/*` path
  to `fastapi_application`, and only `_STATION_API_RE` paths are diverted to a station sub-app
  (`config/asgi.py:132-144`, `config/station_api.py:24-32`) — when the literals are re-pointed
  onto `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}` and herald v1 is registered on
  the seam beside warden, then a request to the new path reaches `webhook_host:application`
  rather than the platform stub, the HMAC verification path is unchanged, every caller (workflow,
  runbook, CLI doc) names the new path, and a test asserts the bare `/api/herald/...` form is no
  longer served.
- And the change is contract-visible: the Spec's `surface:` block and `docs/` callers move in the
  same PR, because fixing this later means changing a documented CI-caller contract.

## Spec Change Log

## Review Triage Log
