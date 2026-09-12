---
spec: mcp-era-isolation
# Flipped ready -> shipped 2026-08-27 (chain reconciliation): CAP-1..3 were
# delivered direct-to-SPEC as slice 1 (commit cb87d8c352, CRC-proven same day
# per .memlog.md); CAP-4 via Epic 35 / Story 35.1 (ledger done). See the dated
# evidence map at the end of this file. Slice 2 stays with
# spec-mcp-factory-stdio-translator; slice 3 stays parked (retire-skip.md).
status: shipped
created: "2026-08-26"
updated: "2026-08-27"
owner-dream: docs/dreams/mcp-era-isolation.md
surface:
  - docs/dreams/mcp-era-isolation.md
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/platform/config/asgi.py
  - src/platform/deploy/charts/platform/
  - pixi.toml
  - "[feature.mcp-host]"
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/platform/config/asgi.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
companions:
  - architecture-diagrams.md
  - retire-skip.md
  - cluster-required.md
sources:
  - ../../../../../../docs/dreams/mcp-era-isolation.md
  - spec-21-2-atlas-mcp-on-the-host-dual-era.md
  - spec-21-4-the-other-seven-mcp-faces.md
open_questions: []
---

> **Canonical contract.** Slice 1 isolates the mcp 1.x / 2.x **pin**.
> CAP-4 (2026-08-26) fail-louds the **cluster** overlay so mcp-host cannot
> be omitted. Dual-era wire is already in `mcp_http.py`. Factory stdio
> (slice 2) and retiring the ImportError skip (slice 3) are **not** this
> increment.

# SPEC — MCP era isolation (slice 1)

## Why

**A pain to solve.** CRC gunicorn skips `/stations/<name>/mcp` because
`python-agent-platform` ships mcp 1.x (Langflow + FastMCP 3 `mcp<2`) and
cannot import `mcp.server.mcpserver`. Dual-era code already exists; the
operator cannot reach it on the live image without a second interpreter.

## Capabilities

- **CAP-1 — dual-era atlas face on the host path**
  - **intent:** An agent can POST to `/stations/atlas/mcp` on the live host
    and receive dual-era MCP (handshake echo and modern header) while the
    web image still imports Langflow.
  - **success:** CRC `/ht/` is 200. POST initialize `protocolVersion`
    `2025-06-18` echoes that revision. `MCP-Protocol-Version: 2026-07-28`
    is accepted. Unsupported revision returns JSON-RPC `-32022` with
    `data.supported`. GET returns 405 and `Allow: POST`.
  - **verified:** 2026-09-11 — code-level re-check: `mcp_dual_era.py` carries `"2025-06-18"`,
    `UNSUPPORTED_PROTOCOL_VERSION = -32022`, and the non-POST 405/`Allow` rejection, matching
    the claim. The live CRC handshake proof itself (this spec's own evidence map, `.memlog.md`,
    2026-08-26) is not re-run in this pass — needs a live CRC cluster.

- **CAP-2 — isolated mcp-host env**
  - **intent:** A pixi environment exists that materializes mcp 2.x and the
    official SDK server without FastMCP 3 or Langflow.
  - **success:** `pixi install --frozen -e mcp-host` solves. That env's
    `python -c "from mcp.server.mcpserver import MCPServer"` succeeds.
    `rg -n fastmcp pixi.toml` under `[feature.mcp-host]` is empty.
    `[feature.python-agent-platform]` is not lifted to mcp 2.x.
  - **verified:** 2026-09-11 — live: `pixi install --frozen -e mcp-host` solves;
    `pixi run -e mcp-host python -c "from mcp.server.mcpserver import MCPServer"` succeeds;
    `[feature.mcp-host.dependencies]` carries no `fastmcp`; `pixi list -e python-agent-platform`
    resolves `mcp 1.28.1`, confirming it is NOT lifted to 2.x.

- **CAP-3 — host proxies; sidecar down is loud**
  - **intent:** The host ASGI process keeps the `/stations/<name>/mcp`
    pattern and forwards the request to the mcp-host process when
    `MCP_HOST_SIDECAR_BASE_URL` is set.
  - **success:** With the URL set, dispatch does not import `MCPServer` in
    the web interpreter. When the sidecar is unreachable, the host logs at
    error and returns HTTP 502 — not a silent skip.
  - **verified:** 2026-09-11 — code-level re-check: `mcp_http.py:432`'s docstring and
    implementation match exactly ("Stream the request to the mcp-host sidecar. Unreachable →
    502 + error log"); `MCP_HOST_SIDECAR_URL_ENV` gates the forward path. `test_mcp_host_
    sidecar.py`'s Django-backed test suite not re-run in this pass (needs Postgres+Redis via
    the `platform-ci-test` env — disproportionate to a doc-hygiene sweep).

- **CAP-4 — cluster overlay cannot omit mcp-host**
  - **intent:** A Helm install / `helm template` of the platform chart (vanilla
    or OCP overlay) always emits mcp-host and always sets
    `MCP_HOST_SIDECAR_BASE_URL` on web and worker. An operator cannot
    forget the sidecar and still get a green chart. Laptop /
    `platform-ci-test` may leave the URL unset and load faces in-process
    (mcp 2.x) or skip (mcp 1.x).
  - **success:** `helm template` fails if `mcpHost.image.repository` is empty.
    There is no `mcpHost.enabled` knob. Chart tests still require exactly one
    mcp-host Deployment + ClusterIP and the internal Service URL on web/worker.
    Production/cluster Django check fails if the URL is unset. Sidecar not
    Ready is 502 on `/stations/<name>/mcp`, not a web CrashLoop. ImportError
    skip is **not** deleted (`retire-skip.md`).
  - **verified:** 2026-09-11 — code-level re-check: `mcp-host-deployment.yaml:3`'s `required`
    directive cites this exact CAP ("mcpHost.image.repository is required — cluster overlay
    cannot omit mcp-host (spec-mcp-era-isolation CAP-4)"); `test_chart_invariants.py` carries
    `test_helm_template_fails_when_mcp_host_repository_empty` and
    `test_mcp_host_values_have_no_enabled_knob` by name. No `helm` binary available in this
    environment to re-run `helm template` live — code-level match only.

## Constraints

- Do not fold `mcp-types` / `httpx2` into `python-agent-platform`.
- Do not lift FastMCP 4 from PyPI. Do not wait on SEP-2663 Tasks.
- Do not remint unifying-strategy architecture. `lane1-serves-dw-h3` stays no.
- Write under `_bmad-output/projects/pyforge-steward/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-steward`. No `bmad-switch` from a parallel agent.
- Same-process JSON translator is forbidden (cannot load both SDKs).
- Invert (sidecar Langflow) only if this hop fails CAP-1 identity or latency.

## Non-goals

- Implementing BMAD-SPEC-2026-MCP (factory stdio) in this slice.
- 12-7 Route/SCC re-prove.
- Libro.
- One lockfile for mcp 2.0 and Langflow.
- Retiring the ImportError skip while the sidecar is the isolation mechanism
  (see `retire-skip.md`).
- Epic 34 / CAP-19 (query plane). This SPEC does not ATTACH Postgres.

## Success signal

On CRC, `/ht/` 200 and `POST /stations/atlas/mcp` dual-era proofs pass, while
`python -c "import langflow"` still works in the **web** image and the
mcp-host env has no FastMCP 3. A chart that omits mcp-host or blanks the
proxy URL does not template.

## Assumptions

- Official `mcp` 2.x Streamable HTTP plus existing `DualEraPostOnlyASGI` is
  sufficient once it runs in a process that can import `MCPServer`.
- httpx is already on the web image for the proxy hop.

## Open Questions

- None for slice 1. Invert vs sidecar is decided: sidecar first.
- The SEP-2663 Tasks scheduled re-check is **not** carried here (this SPEC's
  constraint is "do not wait on Tasks"); it lives in
  `spec-pyforge-unifying-strategy`'s answered `mcp-tasks-runtime` OQ
  (2026-08-24).

## Shipped — capability→story evidence map (2026-08-27)

Chain reconciliation pass. Every capability is delivered and verified; this
SPEC owes no residual work. Slice 2 (factory stdio) is owned by
`spec-mcp-factory-stdio-translator`; slice 3 (retiring the ImportError skip)
stays parked behind `retire-skip.md`'s trigger.

- **CAP-1 — dual-era atlas face on the host path.** Direct-to-SPEC (slice 1;
  the face/pattern itself was minted by Stories 21.2/21.4 under FR-11).
  Evidence: commit `cb87d8c352` (`mcp_dual_era.py`, `mcp_http.py` rework,
  `src/platform/mcp_host/app.py`); CRC proof 2026-08-26 recorded in
  `.memlog.md` — `/ht/` 200, initialize `2025-06-18` echoed, header
  `2026-07-28` accepted, unsupported revision → `-32022`, GET 405
  `Allow: POST`, `import langflow` still green in the web image.
- **CAP-2 — isolated mcp-host env.** Direct-to-SPEC (slice 1). Evidence:
  `pixi.toml` `[feature.mcp-host]` (mcp `>=2.1.0`, mcp-types, uvicorn,
  starlette; no FastMCP, no Langflow) + the `mcp-host` env; `.memlog.md`
  records the env solving at mcp 2.1.1 with `MCPServer` importable while the
  `python-agent-platform` lock stays mcp 1.28.1;
  `tests/packaging/test_mcp_era_isolation.py`.
- **CAP-3 — host proxies; sidecar down is loud.** Direct-to-SPEC (slice 1).
  Evidence: `django_pyforge/mcp_http.py` forwards on
  `MCP_HOST_SIDECAR_BASE_URL` without importing `MCPServer` in the web
  interpreter; unreachable sidecar → error log + HTTP 502;
  `src/platform/tests/test_mcp_host_sidecar.py`.
- **CAP-4 — cluster overlay cannot omit mcp-host.** Decomposed: Epic 35 /
  Story 35.1 (`spec-35-1-cluster-requires-mcp-host.md`, status done
  2026-08-26; ledger `35-1-cluster-requires-mcp-host: done`). Evidence:
  `mcp-host-deployment.yaml` `required` guard on empty
  `mcpHost.image.repository`; `test_chart_invariants.py` — empty-repository
  render fails, no `mcpHost.enabled` knob, exactly one mcp-host Deployment +
  ClusterIP, `MCP_HOST_SIDECAR_BASE_URL` wired on web/worker;
  `stage_one.py` production/cluster required-setting check (laptop /
  `platform-ci-test` stay URL-unset); sidecar down is 502, not a web
  CrashLoop; the ImportError skip is retained per `retire-skip.md`.
