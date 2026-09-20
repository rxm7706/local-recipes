---
title: Atlas MCP on the host, dual-era
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 844a4ff461376678408bba63fbed19dfeb29f91c
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
warnings: []
deferred:
  - summary: >-
      local-recipes keeps mcp>=1.24,<2.0 because FastMCP 3.x cannot solve
      with mcp 2.x. Platform-ci-test and pyforge-atlas take mcp 2.0.0.
    evidence: |-
      pixi.toml comments on both pins; FastMCP 4 is not on conda-forge.
    location: pixi.toml
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Atlas's MCP face still registers on FastMCP and is not on the host ASGI process, so handshake-era and modern clients cannot share `POST /stations/atlas/mcp`.

**Approach:** Wrap atlas's existing `build_server` tool surface with the official `mcp` SDK Streamable HTTP app, mount it on the host ASGI dispatcher as a `/stations/<name>/mcp` pattern (atlas supplies the app), and dual-era-gate revisions `2025-03-26`–`2026-07-28`.

## Boundaries & Constraints

**Always:** Official `mcp` SDK (not FastMCP) for the host face. Echo requested handshake revision on `initialize`. Unsupported revision → JSON-RPC `-32022` with `supported` list. Discovery/mount is a pattern via AppConfig MCP token, not a host roster. Parent AD-2: no `import pyforge` under `src/platform/`. Atlas `tools.py` stays the tool bodies; do not duplicate them. Physical writes under `_bmad-output/projects/pyforge-steward/` plus the listed Code Map. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** Satisfying dual-era would require FastMCP 4 from PyPI (conda-forge cannot accept) as the host face, or a fifth PostgreSQL schema / MinIO / Liquibase 27-1.

**Never:** Story 21.3 `start`/`get`. Story 21.4 other stations' MCP apps. Epic 30 console deletion. `pyforge.*` under `src/platform/`. MinIO. Dual-endpoint SSE (`/sse` + `/messages`). Branching on client name or User-Agent. Hardcoded `atlas` in host dispatch.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Handshake echo | POST initialize `protocolVersion` in `2025-03-26`,`2025-06-18`,`2025-11-25` | Result `protocolVersion` equals the request | No error expected |
| Modern revision | POST with MCP-Protocol-Version `2026-07-28` (no initialize required for that era) | Request is accepted by the same POST path | No error expected |
| Unsupported revision | initialize or header revision outside the supported list (incl. `2024-11-05`, `2099-01-01`) | JSON-RPC error `-32022` with `data.supported` listing the four revisions | HTTP error body carries the code |
| GET not SSE | GET `/stations/atlas/mcp` | `405` and `Allow: POST`; no `text/event-stream` body | Method not allowed |
| No UA branch | Source of mount/gate/server | No `User-Agent` / client-name dispatch | Test fails on a match |
| Existing tools | `build_server` wrappers | Still call `pyforge.atlas.mcp.tools` 1:1; no second tool module | AST/import failure |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` -- switch lazy FastMCP to lazy `mcp.server.mcpserver.MCPServer`; keep `@mcp.tool()` wrappers calling `tools.py`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/__init__.py` -- docstring: official SDK, still do not import `.server` at package import
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` -- **new** supported-revision constants, POST-only ASGI wrap, initialize/`MCP-Protocol-Version` `-32022` gate, `asgi_for_server(MCPServer)`, `match_station_mcp(path)`, `iter_station_mcp_apps()`
- `src/shared/packages/django-pyforge/src/django_pyforge/portals.py` -- optional `mcp_asgi_app()` defaulting to `None`
- `src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py` -- **new** lazy `build_atlas_mcp_asgi()` → `asgi_for_server(build_server())`
- `src/shared/packages/django-atlas/src/django_atlas_portal/apps.py` -- `mcp_asgi_app` method
- `src/platform/config/asgi.py` -- pattern-dispatch `/stations/<name>/mcp` via `match_station_mcp` + discovered apps; enter MCP Starlette lifespans; no station name literals; no `pyforge` import
- `src/platform/tests/test_atlas_mcp_host.py` -- I/O matrix on a composed host dispatcher (dummy official-SDK server as atlas); AST no-UA / no-roster / atlas `build_server` import
- `src/shared/packages/pyforge-atlas/tests/mcp/test_official_sdk_server.py` -- `build_server` is `MCPServer`; wrappers still call `tools`
- `pixi.toml` -- `[feature.platform-ci-test.pypi-dependencies]` (and image-pip if the same pins are required) `mcp==2.0.0` + `mcp-types==2.0.0`; `[feature.pyforge-atlas.dependencies]` `mcp>=2.0.0`; do **not** lift `local-recipes` `mcp>=1.24,<2.0` while `fastmcp>=3.4.7,<4` remains (unsolvable pair). Update the stopgap comment.
- Read-only: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py`, `src/platform/tests/meta/test_no_pyforge_import.py`, `src/platform/config/urls.py` (Django portals stay HTML; MCP is ASGI)
- Do not edit: Helm/Liquibase, `start_*`/`get_*`, other stations' `mcp_asgi_app`, Epic 30 console

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` -- official SDK registration -- canopy:FR-11 bring-not-duplicate
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` -- dual-era POST face helpers -- canopy:AD-5
- `src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py` -- lazy atlas server mount -- host must not import `pyforge.*`
- `src/platform/config/asgi.py` -- pattern dispatch + lifespan -- one ASGI process
- `pixi.toml` -- platform/atlas `mcp` 2.x -- dual-era needs `mcp` 2
- `src/platform/tests/test_atlas_mcp_host.py` + `src/shared/packages/pyforge-atlas/tests/mcp/test_official_sdk_server.py` -- I/O matrix

**Acceptance Criteria:**
- Given the host ASGI process, when a client POSTs to `/stations/atlas/mcp`, then the face speaks MCP revisions `2025-03-26` through `2026-07-28` using the official `mcp` SDK
- Given handshake `initialize`, when the client requests a supported handshake revision, then the result echoes that revision; when unsupported, then `-32022` with the supported list
- Given mount/gate/server sources, when scanned, then no path branches on client name or user-agent, and deprecated dual-endpoint SSE is not served
- Given atlas `build_server`, when registered, then it is the existing tools module brought to this spec, not a second server

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Implementation pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (high 0, medium 1, low 0)
- reject: 0
- addressed_findings: []

## Design Notes

The four supported revisions are `2025-03-26`, `2025-06-18`, `2025-11-25`, `2026-07-28`. The SDK also knows `2024-11-05`; this face must reject it with `-32022`. The SDK's initialize fallback-to-latest is not the echo rule — intercept unsupported initialize before the SDK.

`local-recipes` cannot lift `mcp` to 2.x while FastMCP 3.x factory servers remain: every conda-forge FastMCP 3.x build declares `mcp<2`. Platform-ci-test has no FastMCP and can take `mcp==2.0.0`. That is the lift this story performs.

Use `json_response=True`, `stateless_http=True`, and DNS-rebinding protection off (ingress terminates TLS). GET returns 405 with `Allow: POST`.

Host tests compose the same `asgi.py` helpers with a dummy `MCPServer` yielded as station `atlas` so platform-ci-test need not import Kedro. AST on `django_atlas_portal/mcp_asgi.py` proves it calls `pyforge.atlas.mcp.server.build_server`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `24f670472b` (2026-08-25, "Merge pull request #764 from rxm7706/steward/21-2-ledger-finalize"); also `716a8d236e` (2026-08-25, "Merge pull request #763 from rxm7706/steward/21-2-atlas-mcp-on-the-host-dual-era"). Ledger row `21-2-atlas-mcp-on-the-host-dual-era: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.cursor/pyforge-fleet-drain/queues.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-2-atlas-mcp-on-the-host-dual-era.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
