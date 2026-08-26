---
title: Isolate MCP eras without one lockfile
type: dream
owner: steward
status: in-progress
---

# Isolate MCP eras without one lockfile

## The Dream

Station MCP faces speak official MCP 2.x (dual-era Streamable HTTP) on the live
host **without** forcing Langflow and FastMCP 3 to share that interpreter. A
modern Cursor/Codex client can still talk to factory FastMCP 3 stdio tools
through a **later** translator — not by rewriting JSON inside gunicorn.

Three problems stay named, never merged:

1. **Pin** — `python-agent-platform` cannot import `mcp.server.mcpserver`
   (mcp 2.x) while Langflow + conda FastMCP 3 declare `mcp>=1.24,<2`.
2. **Dual-era wire** — already coded in `django_pyforge.mcp_http` (revisions
   `2025-03-26`–`2026-07-28`). It lights up when (1) is isolated.
3. **Factory stdio** — modern clients vs FastMCP 3 / mcp 1.x local tools.
   That is a downgrade/upgrade proxy, not the CRC ImportError.

## What it looks like when real

- CRC `/ht/` stays 200. Langflow still imports in the **web** image.
- `POST /stations/atlas/mcp` initialize with `2025-06-18` echoes that revision.
- `MCP-Protocol-Version: 2026-07-28` is accepted on the same POST path.
- Unsupported revision → JSON-RPC `-32022` with `data.supported`.
- GET `/stations/<name>/mcp` → 405, `Allow: POST`.
- `[feature.python-agent-platform]` is **not** lifted to mcp 2.x.
- Sidecar env solve has **no** FastMCP 3.

## What is real

Story 21.2 / 21.4 mounted official-SDK faces; CRC 12.7 skipped them on
`ImportError` so gunicorn could boot. `spec-platform-image-one-pixi-env`
explicitly did not invent mcp 2.0 + Langflow in one lock. FastMCP 4 is beta
and not on conda-forge. SEP-2663 Tasks is not in mcp 2.0.0.

## Sequence

1. **Slice 1 (this Dream's build)** — Pattern B sidecar (`mcp-host`): mcp 2.x,
   no Langflow, no FastMCP 3. Host `dispatch_station_mcp` proxies
   `POST /stations/<name>/mcp` to that process. Identity and path pattern stay
   on the host.
2. **Slice 2 (later)** — factory stdio translator (BMAD-SPEC-2026-MCP as
   input). Own spec. Does not claim to fix CRC.
3. **Slice 3 (later)** — retire the ImportError skip when FastMCP 4 is on
   conda-forge **or** Langflow drops `mcp<2`. Until then the skip is a safety
   net only when the sidecar is down (loud log).

Invert (sidecar Langflow, lift mcp 2.x on the web image) only if the hop
fails CAP-4 identity or latency.

## Constraints

- Do not remint unifying-strategy architecture. `lane1-serves-dw-h3` stays no.
- Do not fold `mcp-types` / `httpx2` into `python-agent-platform`.
- Do not lift FastMCP 4 from PyPI. Do not wait on Tasks.
- Do not implement the pasted translator in-process (cannot load both SDKs).
- Write planning under `_bmad-output/projects/pyforge-steward/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-steward`. No `bmad-switch` from parallel agents.

## Non-goals

- 12-7 Route/SCC re-prove.
- Libro.
- One lockfile for mcp 2.0 and Langflow.
- Q5 scorecard.

## Realization log

- **2026-08-26** — Dream captured from the MCP era program plan. Spec:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/`.
- **2026-08-26** — Slice 1 landed: pixi env `mcp-host`, sidecar Containerfile,
  host proxy via `MCP_HOST_SIDECAR_BASE_URL`, CRC proofs in spec memlog.
  Slice 2 parked as `spec-mcp-factory-stdio-translator`. Slice 3 criteria in
  `retire-skip.md` (ImportError skip kept).
