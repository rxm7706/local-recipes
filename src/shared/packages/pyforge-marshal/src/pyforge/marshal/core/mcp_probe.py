"""Pure MCP probe verdict mapping (Story 103.1, AD-4)."""

from __future__ import annotations

from pyforge.marshal.core.egress import redact_raw_text
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.ports.mcp_probe import McpProbeResult


def evaluate_mcp_probe(result: McpProbeResult, *, mcp_json_path: str) -> tuple[bool, list[Finding]]:
    """Map a probe result to ``(startable, findings)`` for preflight."""
    if result.outcome == "started" and result.tool_count is not None:
        return True, []

    tail = redact_raw_text(result.stderr_tail) if result.stderr_tail else ""
    detail = f"outcome={result.outcome}"
    if result.exit_code is not None:
        detail += f", exit_code={result.exit_code}"
    if tail:
        detail += f", stderr={tail!r}"
    message = f"MCP server {result.server_name!r} failed startup handshake ({detail})"
    finding = Finding(
        code="MRS-PREFLIGHT-012",
        severity=Severity.ERROR,
        message=message,
        path=mcp_json_path,
    )
    return False, [finding]
