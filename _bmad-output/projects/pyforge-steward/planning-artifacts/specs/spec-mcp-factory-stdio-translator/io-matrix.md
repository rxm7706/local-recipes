# I/O matrix (slice 2 — factory stdio translator)

Parked. Fill before implementation. Do not write a bash-mock harness until
every row here has Input / Expected / Error Handling.

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Modern client, no handshake | First JSON-RPC is `tools/list` with `_meta` | Translator fabricates `initialize` to FastMCP 3 child, then forwards `tools/list` without `_meta` | Child protocol error is surfaced to client |
| Handshake-era client | Client sends `initialize` `2025-06-18` | Pass through; do not double-handshake | Echo child's revision |
| `_meta` on request | Any method with `_meta` | Child payload has no `_meta` | Preserve other params |
| Text result wrap | Child returns bare `text` or mcp 1.x result | Client sees `content[{type,text}]` when modern | Binary/image types out of scope until a factory tool returns them |
| Unsupported revision | Client revision outside 1.x + modern set | JSON-RPC `-32022` with `supported` | Do not start child |
| Not CRC | Translator running | No change to gunicorn `/stations/*/mcp` | CAP-2 |

Source shape adapted from BMAD-SPEC-2026-MCP. Not a CRC fix.
