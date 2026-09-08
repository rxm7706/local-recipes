---
title: The other seven MCP faces
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 4b88f3f1245e770b9427447991f7d0510b640fca
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Only atlas speaks MCP on the host. Agents must learn a second transport for doctor, herald, marshal, mason, scribe, steward, and warden.

**Approach:** Each remaining station's `PortalConfig` supplies an MCP ASGI app via the existing AppConfig hook. Host dispatch stays the `/stations/<name>/mcp` pattern from 21.2; every face reuses the same dual-era POST wrapper.

## Boundaries & Constraints

**Always:** Official `mcp` SDK Streamable HTTP via `django_pyforge.mcp_http.asgi_for_server` / `asgi_for_station`. Same revisions as atlas (`2025-03-26` through `2026-07-28`). Handshake `initialize` echoes the requested revision; unsupported → JSON-RPC `-32022` with `data.supported`. Discovery is `iter_station_mcp_apps()` / `mcp_asgi_app()` — host `asgi.py` stays a pattern (no station-name roster). `mcp_token` already on each portal (`mcp:<name>`). Parent AD-2: no `import pyforge` under `src/platform/`. Physical writes under `_bmad-output/projects/pyforge-steward/` plus the Code Map. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** Dual-era would require FastMCP 4 from PyPI as the host face, a fifth PostgreSQL schema, MinIO, or Liquibase 27-1.

**Never:** Story 21.5 front-door supervisor UI. Epic 30 console deletion. `pyforge.*` under `src/platform/`. MinIO. Liquibase 27-1. Dual-endpoint SSE. User-Agent / client-name branching. Hardcoded seven-name list in `config/asgi.py`. Converting marshal FastMCP stdio (`pyforge.marshal.mcp.server`) in this story. Attaching `start_*`/`get_*` to these seven faces (21.3 atlas-only). Probe portals (`chrome-probe`, `infra-probe`) must not gain a production MCP face.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Seven faces POST | POST `/stations/<name>/mcp` initialize for each of doctor, herald, marshal, mason, scribe, steward, warden with handshake revision | Same dual-era echo as atlas | No error expected |
| Modern header | POST with `MCP-Protocol-Version: 2026-07-28` on any of the seven | Accepted on the same POST path | No error expected |
| Unsupported | initialize or header outside the four revisions (incl. `2024-11-05`) | `-32022` with `data.supported` listing the four | HTTP error body carries the code |
| GET not SSE | GET `/stations/<name>/mcp` for a remaining station | `405` and `Allow: POST`; no `text/event-stream` | Method not allowed |
| Pattern dispatch | `config/asgi.py` source | No literals of the seven station names; still `dispatch_station_mcp` | AST fail |
| Tokens registered | Each remaining `PortalConfig` | `mcp_token == "mcp:<station_name>"` and `mcp_asgi_app()` is not `None` | Probe configs still return `None` |
| No UA / no SSE | Mount/gate/face sources | No User-Agent or client-name branch; no dual-endpoint SSE | Test fails on a match |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` -- add `asgi_for_station(name)` (cached official `MCPServer` identity face + `asgi_for_server`); keep `match_station_mcp` / `iter_station_mcp_apps` as the only host dispatch
- `src/shared/packages/django-{doctor,herald,marshal,mason,scribe,steward}/src/django_*_portal/apps.py` -- override `mcp_asgi_app` to `asgi_for_station(self.station_name)`
- `src/shared/packages/django-warden/src/django_warden_fabric/apps.py` -- same override (warden naming triple unchanged)
- `src/shared/packages/django-pyforge/src/django_pyforge/portals.py` -- default hook stays `None` (probes inherit)
- `src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py` -- read-only; atlas face already landed
- `src/platform/config/asgi.py` -- read-only unless a comment-only clarification; do not add station names
- `src/platform/tests/test_seven_mcp_faces.py` -- **new** I/O matrix on composed dispatcher using `asgi_for_station`; Django discovery that the seven `mcp_asgi_app`s are non-None; AST no roster / no UA / no SSE; probes stay None
- Read-only: `test_atlas_mcp_host.py`, `mcp_start_get.py`, marshal FastMCP `pyforge.marshal.mcp.server`, `test_no_pyforge_import.py`
- Do not edit: Epic 30 console, Helm/Liquibase, Wagtail front-door run board (21.5), `src/platform/` packages named `pyforge`

## Tasks & Acceptance

**Execution:**
- `django_pyforge/mcp_http.py` -- `asgi_for_station` pattern -- one dual-era wrapper for seven faces
- seven station `apps.py` -- register MCP ASGI via AppConfig -- canopy:AD-1
- `src/platform/tests/test_seven_mcp_faces.py` -- I/O matrix

**Acceptance Criteria:**
- Given the atlas face, when the remaining seven stations register MCP tokens, then `POST /stations/<name>/mcp` conforms to the same dual-era checks
- Given host dispatch, when a new station supplies `mcp_asgi_app`, then routing is the path pattern, not a per-station list in `asgi.py`
- Given handshake and modern clients, when they speak revisions `2025-03-26` through `2026-07-28`, then initialize echoes; unsupported returns `-32022`; GET is not SSE; no user-agent branching

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 16
- addressed_findings:
  - `[medium]` `[patch]` Dual-era HTTP tests now POST/GET through each portal `mcp_asgi_app()`, not a test-local `asgi_for_station` call
  - `[low]` `[patch]` ruff I001/E501/COM812 on the new platform test; PLC0415 noqa on lazy portal/MCP imports

## Design Notes

The seven host faces are identity MCP servers (`station_face` tool returning the station name) wrapped by the 21.2 dual-era ASGI helper. Atlas keeps its brought-over `build_server`. Marshal's FastMCP stdio entry stays for CLI; the host face is official SDK. Do not attach supervisor `start`/`get` here.

`asgi_for_station` must not live as a name roster in `asgi.py`. Portal AppConfigs are the registration surface. Fixture portals keep `mcp_asgi_app` default `None`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Remaining seven stations register official-SDK identity MCP faces via `PortalConfig.mcp_asgi_app` → `asgi_for_station`. Host dispatch stays the `/stations/<name>/mcp` pattern. Dual-era handshake matches atlas.

**Files:**
- `django_pyforge/mcp_http.py` — `asgi_for_station` identity server + DualEra wrap
- seven station `apps.py` — `mcp_asgi_app` registration
- `src/platform/tests/test_seven_mcp_faces.py` — I/O matrix through portal hooks
- tracked spec `spec-21-4-the-other-seven-mcp-faces.md`

**Review:** 2 patches applied; 0 deferred; 16 rejected (bring marshal FastMCP; start/get on seven; live `config.asgi.application`; AD-7 on identity faces; concurrent cache; 21.5/Epic 30). Follow-up recommended: false (score 4).

**Verification:** 75 passed under `platform-ci-test`. ruff clean on the new test and seven `apps.py` files.

**Residual risks:** Identity faces only (`station_face`). Marshal FastMCP stdio unchanged. DualEra ASGI wrapper is rebuilt per `mcp_asgi_app()` call; discovery binds one instance into `_mcp_apps`.
