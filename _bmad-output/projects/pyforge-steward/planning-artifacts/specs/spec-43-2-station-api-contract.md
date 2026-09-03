---
title: "Station API contract and the /api/v1 collision"
type: "feature"
created: "2026-09-02"
status: "in-progress"
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

- [ ] Router change + Langflow prefix test
- [ ] Seam routing + OpenAPI
- [ ] `pyforge.core.client`
- [ ] Kit contract test
- [ ] Form-error bridge
- [ ] Dream example
- [ ] Ledger `43-2-station-api-contract` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform` ASGI seam tests; `pyforge-core` + `pyforge-testing-kit` tests; chrome tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
