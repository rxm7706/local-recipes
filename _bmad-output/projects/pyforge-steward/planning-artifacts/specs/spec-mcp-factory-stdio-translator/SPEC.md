---
spec: mcp-factory-stdio-translator
status: draft
created: "2026-08-26"
updated: "2026-08-26"
owner-dream: docs/dreams/mcp-era-isolation.md
surface:
  - docs/dreams/mcp-era-isolation.md
companions:
  - io-matrix.md
sources:
  - ../../../../../../docs/dreams/mcp-era-isolation.md
  - spec-mcp-era-isolation/SPEC.md
open_questions: []
---

> **Canonical contract.** Parked slice 2. This SPEC is **not** the CRC
> ImportError fix. Do not implement until slice 1 is shipped and a dedicated
> factory-stdio Dream/build is scheduled.

# SPEC — Factory stdio MCP translator (slice 2)

## Why

**A pain to solve.** Modern MCP clients (`2026-07-28`, `_meta` on every
call, no handshake) cannot speak FastMCP 3 / mcp 1.x stdio tools in this
factory (CFE, marshal). That is a **wire-format and session** problem.
CRC gunicorn failing to import `MCPServer` is a **different** problem
(slice 1 sidecar). Same-process translation cannot load both SDKs.

## Capabilities

- **CAP-1 — stdio wrap of a FastMCP 3 child**
  - **intent:** A modern client can start a factory tool over stdio and
    get MCP 1.x-legal traffic to the child.
  - **success:** Child sees `initialize` handshake when the client is
    modern-era; client `_meta` is stripped before the child; text results
    wrap as `content[{type,text}]`.

- **CAP-2 — explicit non-CRC claim**
  - **intent:** Operators never treat this process as the host-face pin fix.
  - **success:** Docs and CLI help state it does not change gunicorn
    `/stations/<name>/mcp` and does not lift `python-agent-platform`.

## Constraints

- Own process. Do not import mcp 1.x and mcp 2.x in one interpreter.
- Do not claim CRC `/ht/` or atlas POST proofs.
- Expand binary/image content types only if a factory tool actually returns them.
- No bash-mock harness until this SPEC's I/O matrix exists (companion).
- Physical writes under `_bmad-output/projects/pyforge-steward/`.
  `BMAD_ACTIVE_PROJECT=pyforge-steward`. No `bmad-switch` from parallel agents.

## Non-goals

- CRC / Langflow / FastMCP 3 pin isolation (slice 1).
- SEP-2663 Tasks.
- FastMCP 4 from PyPI.
- Reminting unifying-strategy architecture.

## Success signal

A modern client can call one named factory FastMCP 3 stdio server through
the translator and complete `tools/list` + one tool call; CRC host faces
are unchanged.

## Assumptions

- BMAD-SPEC-2026-MCP (`_meta` strip, fabricated handshake, `content[]`
  wrap) is the starting engine, not a copy-paste into gunicorn.
