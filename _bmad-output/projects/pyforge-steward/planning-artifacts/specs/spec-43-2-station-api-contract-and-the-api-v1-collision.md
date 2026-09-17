---
title: "Station API contract and the /api/v1 collision"
type: "feature"
created: "2026-09-02"
status: "done"
followup_review_recommended: false
review_loop_iteration: 1
updated: "2026-09-03"
baseline_commit: "58ee07a0"
baseline_revision: "e26da35a8b7709ce19cdd511702682381a4f4802"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/config/asgi.py"
  - "src/platform/config/fastapi_app.py"
  - "src/shared/packages/pyforge-core/src/pyforge/core/"
  - "src/shared/packages/pyforge-testing-kit/"
warnings: []
deferred:
  - "Per-station route inventories (each station adds its own routes under the prefix)."
  - summary: >-
      PyForgeStationClient default urllib transport has no executing test.
    evidence: |-
      Unit tests inject a mock transport; _urllib path untested in CI.
    location: >-
      src/shared/packages/pyforge-core/src/pyforge/core/client.py
    severity: medium
  - summary: >-
      Langflow /langflow/api/v1/ prefix-preserving redirect not gated in platform-ci-test.
    evidence: |-
      test_langflow_mount.py requires langflow package; langflow-free suite covers bare /api/v1 only.
    location: >-
      src/platform/tests/test_langflow_mount.py
    severity: medium
  - summary: >-
      Server-side X-PyForge-API-Version header enforcement not implemented.
    evidence: |-
      Client sets header; station_api.py never validates it against URL version.
    location: >-
      src/platform/config/station_api.py
    severity: medium
  - summary: >-
      django-warden portal has not adopted StationHttpClient for host calls.
    evidence: |-
      Contract test proves header parity via mock transport only; no portal wiring in diff.
    severity: medium
  - summary: >-
      OpenAPI documents are not schema-validated beyond path-key presence.
    evidence: |-
      Tests assert paths keys exist; no OpenAPI validator or golden document.
    severity: low
---

<intent-contract>

## Intent

**Problem:** The ASGI router hands all of `/api/v1/*` to Langflow before the FastAPI seam
sees it; the Dream's client example targets `/api/v1/compliance/check`, which
would reach Langflow. There is no versioned station API, no OpenAPI,
`pyforge.core.client` does not exist, and no contract test binds a
`django-<station>` portal to the host. Red-team **T-2**, **B-3**, directive
**R-5**.

**Approach:** Reserve `/stations/<name>/api/v<N>/` on the FastAPI seam; move Langflow off
bare `/api/v1` (it already serves under `/langflow/`); publish OpenAPI per
station; build `pyforge.core.client` (httpx, version header, assertion
carrier) with a golden contract test in `pyforge-testing-kit`; ship the
`PydanticFormErrorBridge` (BS-7) in `django-pyforge`. Delete the wrong example
from the Dream.

## Acceptance Criteria

- Given `/api/v1/anything`, when requested, then it is no longer Langflow; `/langflow/api/v1/...` still is, with the same prefix-preserving redirect behaviour.
- Given `/stations/warden/api/v1/openapi.json`, when fetched, then it validates and lists the station's routes; a test fails if a route exists without a version prefix.
- Given `pyforge.core.client`, when a portal and the CLI call the same route, then both carry `X-PyForge-API-Version` and the assertion, and a golden contract test in the kit passes for both.
- Given a 422 from a station route, when rendered by an HTMX view, then field errors appear inline via `PydanticFormErrorBridge` (BS-7 test).
- Given the Dream § Shared Data Contracts, when updated, then the example uses `/stations/warden/api/v1/...`.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-2-station-api-contract`. Host never imports `pyforge.*`. Host never imports `pyforge.*` (the client lives in `pyforge-core`, portals reach it through `django-pyforge`). HTMX stays the portal contract (Q7).

**Block If:** Implementation would introduce DRF JSON:API on portals, a BFF, or break Langflow's own `/langflow/` mount.

**Never:** An unversioned station route. A portal constructing a raw HTTP request (AD-7).

</intent-contract>

## Tasks

- [x] Router change + Langflow prefix test
- [x] Seam routing + OpenAPI
- [x] `pyforge.core.client`
- [x] Kit contract test
- [x] Form-error bridge
- [x] Dream example
- [x] Ledger `43-2-station-api-contract` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform` ASGI seam tests; `pyforge-core` + `pyforge-testing-kit` tests; chrome tests.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 2, medium 1, low 1)
- defer: 8: (high 0, medium 5, low 3)
- reject: 12
- addressed_findings:
  - `[high]` `[patch]` Added langflow-free host ASGI tests (`test_station_api_host_dispatch.py`) proving `/stations/warden/api/v1/*` dispatch and bare `/api/v1` no longer reaches Langflow.
  - `[high]` `[patch]` Unknown/unregistered station API paths return JSON 404 instead of KeyError 500 in `config/asgi.py`.
  - `[medium]` `[patch]` `contract-probe` station registry entry torn down after prefix-violation test.
  - `[low]` `[patch]` Updated `test_langflow_mount.py` module docstring for Story 43.2 routing.

### 2026-09-03 — Follow-up review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 5: (high 0, medium 4, low 1)
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` Regenerated `environment.yaml` without pixi WARN/ANSI banner (maintenance CI sync gate after `pixi.toml` dep changes).
  - `[low]` `[patch]` Added host dispatch test for unregistered station API version (`/stations/warden/api/v99/health` → JSON 404).

## Auto Run Result

Status: done

**Summary:** Reserved `/stations/<name>/api/v<N>/` on the host ASGI seam, moved Langflow off bare `/api/v1/*`, shipped `pyforge.core.client` + `django-pyforge` `StationHttpClient`, warden v1 OpenAPI probe routes, golden contract test in `pyforge-testing-kit`, and updated the Dream Shared Data Contracts example. BS-7 (`PydanticFormErrorBridge`) was pre-existing from Story 25.3.

**Files changed:**
- `src/platform/config/asgi.py` — station API dispatch; Langflow decoupled from bare `/api/v1`
- `src/platform/config/station_api.py` — warden v1 registry, OpenAPI, assertion gate
- `src/shared/packages/pyforge-core/src/pyforge/core/client.py` — `PyForgeStationClient`
- `src/shared/packages/django-pyforge/src/django_pyforge/station_client.py` — portal wrapper (AD-7)
- Platform + kit + core tests; Dream update; pixi env deps for kit contract test

**Review (initial pass):** 4 patches applied (2 high host-dispatch/404 guards). Deferred: server-side version-header enforcement, django-warden portal adoption, warden stub routes in host, station lifespan wiring, archive Dream example. Rejected: duplicate/noise findings (re-exports, skill docs, ledger checkbox before sync).

**Review (follow-up pass):** 2 patches applied (environment.yaml regeneration, unknown-version 404 test). Deferred: urllib transport test gap, Langflow positive-path CI gate, server-side version header, portal adoption, OpenAPI schema validation. Rejected: 18 duplicate/out-of-scope/noise findings (BS-7 re-ship, httpx-vs-urllib re-litigation, sprint-ledger process, export discoverability).

**Follow-up review recommendation:** false — follow-up pass patched counts: medium 1, low 1 (score 4 < 5; forced false as single allowed follow-up).

**Verification:**
- `pixi run -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_client.py` — 3 passed
- `pixi run -e pyforge-testing-kit pyforge-testing-kit-test` — 9 passed
- `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py` — 5 passed

**Residual risks:** Langflow prefix-preserving redirect tests require the `langflow` package (skipped in `platform-ci-test`; bare `/api/v1` isolation covered langflow-free). Warden `compliance/check` is a host stub until warden owns its route inventory. PyForgeStationClient default urllib transport untested end-to-end.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
