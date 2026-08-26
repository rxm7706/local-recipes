---
spec: mcp-era-isolation
status: ready
created: "2026-08-26"
updated: "2026-08-26"
owner-dream: docs/dreams/mcp-era-isolation.md
surface:
  - docs/dreams/mcp-era-isolation.md
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/platform/config/asgi.py
  - pixi.toml
  - "[feature.mcp-host]"
companions:
  - architecture-diagrams.md
  - retire-skip.md
sources:
  - ../../../../../../docs/dreams/mcp-era-isolation.md
  - spec-21-2-atlas-mcp-on-the-host-dual-era.md
  - spec-21-4-the-other-seven-mcp-faces.md
open_questions: []
---

> **Canonical contract.** Slice 1 only: isolate the mcp 1.x / 2.x **pin** so
> host station faces can load. Dual-era wire is already in `mcp_http.py`.
> Factory stdio translator is **not** this SPEC.

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

- **CAP-2 — isolated mcp-host env**
  - **intent:** A pixi environment exists that materializes mcp 2.x and the
    official SDK server without FastMCP 3 or Langflow.
  - **success:** `pixi install --frozen -e mcp-host` solves. That env's
    `python -c "from mcp.server.mcpserver import MCPServer"` succeeds.
    `rg -n fastmcp pixi.toml` under `[feature.mcp-host]` is empty.
    `[feature.python-agent-platform]` is not lifted to mcp 2.x.

- **CAP-3 — host proxies; sidecar down is loud**
  - **intent:** The host ASGI process keeps the `/stations/<name>/mcp`
    pattern and forwards the request to the mcp-host process when
    `MCP_HOST_SIDECAR_BASE_URL` is set.
  - **success:** With the URL set, dispatch does not import `MCPServer` in
    the web interpreter. When the sidecar is unreachable, the host logs at
    error and returns HTTP 502 — not a silent skip.

## Constraints

- Do not fold `mcp-types` / `httpx2` into `python-agent-platform`.
- Do not lift FastMCP 4 from PyPI. Do not wait on SEP-2663 Tasks.
- Do not remint unifying-strategy architecture. `lane1-serves-dw-h3` stays no.
- Write under `_bmad-output/projects/pyforge-steward/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-steward`. No `bmad-switch` from a parallel agent.
- Same-process JSON translator is forbidden (cannot load both SDKs).
- Invert (sidecar Langflow) only if this hop fails CAP-4 identity or latency.

## Non-goals

- Implementing BMAD-SPEC-2026-MCP (factory stdio) in this slice.
- 12-7 Route/SCC re-prove.
- Libro.
- One lockfile for mcp 2.0 and Langflow.
- Retiring the ImportError skip while the sidecar is the isolation mechanism
  (see `retire-skip.md`).

## Success signal

On CRC, `/ht/` 200 and `POST /stations/atlas/mcp` dual-era proofs pass, while
`python -c "import langflow"` still works in the **web** image and the
mcp-host env has no FastMCP 3.

## Assumptions

- Official `mcp` 2.x Streamable HTTP plus existing `DualEraPostOnlyASGI` is
  sufficient once it runs in a process that can import `MCPServer`.
- httpx is already on the web image for the proxy hop.

## Open Questions

- None for slice 1. Invert vs sidecar is decided: sidecar first.
