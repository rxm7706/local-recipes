"""``McpProbePort`` -- stdio MCP startup handshake for preflight (Story 103.1).

A Protocol definition only (Structural Seed); implemented solely by
``adapters/mcp_stdio_probe.py``. Classified non-egress in ``core.egress``
(AD-34 process-spawn carve-out).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Protocol, runtime_checkable

McpProbeOutcome = Literal[
    "started",
    "exited",
    "timed-out",
    "bad-reply",
    "error-reply",
    "spawn-failed",
]


@dataclass(frozen=True)
class McpProbeResult:
    """Frozen outcome of one declared MCP server handshake attempt."""

    outcome: McpProbeOutcome
    server_name: str
    tool_count: int | None = None
    exit_code: int | None = None
    stderr_tail: str = ""


@runtime_checkable
class McpProbePort(Protocol):
    """Start one MCP server from a rendered ``.mcp.json`` entry and probe stdio."""

    def probe_server(
        self,
        *,
        server_name: str,
        command: str,
        args: tuple[str, ...],
        env: Mapping[str, str],
        cwd: str,
        timeout_s: float,
    ) -> McpProbeResult:
        """Run the initialize → notifications/initialized → tools/list lifecycle."""
        ...
