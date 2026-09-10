---
title: 'The webhook routes move onto the station API seam'
type: 'fix'
created: '2026-09-10'
status: 'done'
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

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 24 findings — high 1, medium 0, low 8, false 10, maybe-false 5
- findings:
  - `[high]` `[patch]` `app.mount("/", ...)` left an unversioned Mount route that broke `test_every_registered_station_route_has_a_version_prefix` — skipped `Mount` in `assert_routes_are_versioned` with comment; seam + contract tests green
  - `[low]` `[reject]` on-pr-close missing from I/O matrix — matrix names on-ship as representative; both path constants and workflow URLs updated; AC satisfied in plural
  - `[low]` `[reject]` no host-level on-pr-close tests — same coverage pattern as on-ship at webhook unit layer; platform legacy 404 + unsigned 401 prove seam routing
  - `[low]` `[reject]` no unit legacy test for on-pr-close — AC cites on-ship legacy path; on-pr-close uses identical routing branch
  - `[false]` `[reject]` spec Never vs workflow URL edit contradiction — boundary excludes enabling the workflow, not updating stale URLs when paths change
  - `[low]` `[defer]` `docs/dreams/herald-moments-2-4-live-backend.md` still quotes old paths — historical dream doc, out of story caller scope (cli-runbooks + workflow updated)
  - `[false]` `[reject]` verification `-k` filter skips platform host tests — spec lists platform pytest as separate command; both ran and passed
  - `[low]` `[defer]` no signed 201 through platform dispatcher — handler unchanged per intent; unsigned 401 proves webhook app reached not platform 404
  - `[low]` `[reject]` no dedicated `station_api.py` unit tests — covered by `test_station_api_host_dispatch.py` through full host ASGI
  - `[low]` `[reject]` platform-ci-test pyforge-herald dep weight — required for `importlib` herald mount in platform CI (intentional pixi.toml change)
  - `[low]` `[patch]` `environment.yaml` carried worktree-specific pixi WARN banner — reverted to baseline; no build-env dep change in this story
  - `[false]` `[reject]` spec mojibake — file renders correctly as UTF-8 em dashes in editor
  - `[low]` `[reject]` openapi omits webhook mount paths — mounts are intentionally opaque ASGI delegation, not FastAPI-declared routes
  - `[low]` `[reject]` live smoke only covers on-ship — smoke suite spot-checks one route; both paths share identical ASGI routing
  - `[false]` `[reject]` concurrent lazy-init race — CPython GIL + first-request-only build; no production multi-request herald deployment yet
  - `[false]` `[reject]` uncaught HeraldError on missing secret at first webhook — same fail-fast as daphne path; health vs webhook separation is intentional
  - `[false]` `[reject]` importlib crash when pyforge-herald absent — platform-ci-test now depends on pyforge-herald by design
  - `[false]` `[reject]` Mount violates versioned-route claim — webhook literals are versioned inside `webhook.py`; Mount prefix is ASGI plumbing
  - `[maybe-false]` `[defer]` herald-only PR skips platform-ci path filter — real ops gap; defer until herald/platform CI coupling policy is decided
  - `[maybe-false]` `[defer]` herald-live-demo URL sync unverified in default CI — workflow disabled by design per spec boundary
  - `[false]` `[reject]` intent: second lazy layer vs `webhook_host.application` — `build_application` is the documented mount target; semantically equivalent
  - `[false]` `[reject]` intent: registration split across modules — required by pap:AD-2 platform import boundary
  - `[false]` `[reject]` intent: daphne smoke uses station paths without dispatcher — literals are absolute; smoke validates path constants on standalone host
  - `[false]` `[reject]` intent alignment: collateral pixi.lock churn — accompanies platform-ci-test dependency addition

## Auto Run Result

Status: done

### Summary
Moved Herald webhook route literals to `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}`, registered herald v1 on the platform station API seam with a lazy `webhook_host` ASGI mount via `pyforge.herald.station_api`, and updated workflow URLs, runbooks, and tests. Review fixed the versioned-route contract gate for ASGI mounts and reverted an accidental `environment.yaml` worktree banner change.

### Files changed
- `webhook.py` — station API path constants and mount comment
- `station_api.py` (herald) — lazy webhook ASGI attach helper
- `station_api.py` (platform) — herald v1 registration; skip Mount in route contract check
- `test_station_api_host_dispatch.py` — herald health, unsigned webhook 401, legacy 404
- `test_webhook.py` — legacy bare-path 404; path normalization cases
- `test_webhook_live_smoke.py`, `herald-live-demo.yml`, `cli-runbooks.md` — caller URL/docs sync
- `pixi.toml` / `pixi.lock` — `pyforge-herald` in `platform-ci-test` for importlib mount

### Review
- Patches applied: 2 (high: Mount contract gate; low: environment.yaml revert)
- Deferred: platform-ci path filter for herald-only PRs; herald-live-demo URL CI guard; signed 201 through dispatcher; stale dream doc paths
- Rejected: 18 findings (see triage log)

### Follow-up review recommendation
`false` — patched high finding verified green; no named unverified risk remains after full verification.

### Verification
- `pixi run -e pyforge-herald pyforge-herald-test -- -k "webhook and (station_api or legacy or normalizes)"` — 5 passed
- `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py src/platform/tests/test_station_api_seam.py -q` — 15 passed

### Residual risks
- Signed webhook success through the full platform dispatcher is assumed from unchanged handler logic (only unsigned 401 tested at host boundary).
- Herald-only PRs may not run platform-ci until path filters include `src/shared/packages/pyforge-herald/**`.
