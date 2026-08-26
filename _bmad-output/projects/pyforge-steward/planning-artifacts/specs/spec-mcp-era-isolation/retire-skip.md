# Slice 3 — retire the ImportError skip

**Not slice 1.** `iter_station_mcp_apps` / `_install_flags_mcp` still catch
`ImportError` when `MCP_HOST_SIDECAR_BASE_URL` is **unset** (laptop /
`platform-ci-test` with mcp 2.x loads faces in-process).

## Retire when (any)

1. FastMCP 4 (or later) is on **conda-forge** and solves with mcp 2.x, **or**
2. Langflow (and langflow-base) drop the `mcp<2` / FastMCP 3 pin so
   `python-agent-platform` can take mcp 2.x without a second interpreter.

## Until then

- Sidecar down + URL set → HTTP 502 and an **error** log (not skip).
- URL unset + ImportError → skip face, log **warning** once per process
  (safety net so gunicorn still boots).
- Do not delete the skip in the same change that ships the sidecar.

## Re-check

`conda search -c conda-forge fastmcp` for a build that declares `mcp>=2` and
does not declare `mcp<2`. Then re-eval collapsing `mcp-host` into the web image.
