"""Pure MCP probe verdict mapping (Story 103.1, AD-4).

Only ``started`` with a tool list is startable. Every other outcome is one
``MRS-PREFLIGHT-012`` (ERROR, the code's existing tier -- the fourth
"not satisfiably recorded" sub-case) naming the server, the outcome, the exit
code when there is one, and the probe's detail and the server's stderr tail,
both redacted first: a finding's message flows through every ``Envelope``
consumer (AD-34).
"""

from __future__ import annotations

from pyforge.marshal.core.egress import redact_raw_text
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.ports.mcp_probe import McpProbeResult


def _redacted(text: str) -> str:
    if not text:
        return ""
    redacted = redact_raw_text(text)
    # ``None`` means the text could not be redacted; it never travels raw.
    return redacted if redacted is not None else "[unredactable]"


def evaluate_mcp_probe(result: McpProbeResult, *, mcp_json_path: str) -> tuple[bool, list[Finding]]:
    """Map a probe result to ``(startable, findings)`` for preflight."""
    if result.outcome == "started" and result.tool_count is not None:
        return True, []

    parts = [f"outcome={result.outcome}"]
    if result.exit_code is not None:
        parts.append(f"exit_code={result.exit_code}")
    detail = _redacted(result.detail)
    if detail:
        parts.append(f"detail={detail!r}")
    tail = _redacted(result.stderr_tail)
    if tail:
        parts.append(f"stderr={tail!r}")
    message = f"MCP server {result.server_name!r} failed the startup handshake ({', '.join(parts)})"
    finding = Finding(
        code="MRS-PREFLIGHT-012",
        severity=Severity.ERROR,
        message=message,
        path=mcp_json_path,
    )
    return False, [finding]
