"""``McpProbePort`` -- stdio MCP startup handshake for preflight (Story 103.1).

A Protocol definition and frozen value types only (Structural Seed);
implemented solely by ``adapters/mcp_stdio_probe.py``. Classified non-egress
in ``core.egress`` (AD-34's process-spawn carve-out: the port hands argv and
an environment to a child process, never a payload to a sink).
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
    """Frozen outcome of one declared MCP server handshake attempt.

    ``server_name`` is the policy's key for the server; ``reported_server_name``
    is what the server itself answered in ``initialize``'s ``serverInfo.name``.
    ``tool_names`` are the ``name`` fields of ``tools/list``'s reply (``tool_count``
    counts every entry, named or not). ``stderr_tail`` is the child's own last
    2 KiB of stderr, raw; ``detail`` is the probe's own one-line reason for a
    non-``started`` outcome (the offending line, the exception). Both are
    redacted by ``core.mcp_probe`` before they reach a finding.
    """

    outcome: McpProbeOutcome
    server_name: str
    tool_count: int | None = None
    exit_code: int | None = None
    stderr_tail: str = ""
    reported_server_name: str | None = None
    tool_names: tuple[str, ...] = ()
    detail: str = ""


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
        """Run the initialize -> notifications/initialized -> tools/list lifecycle.

        Never raises; every failure is one of the six outcomes. Every process the
        probe starts is stopped (the child's whole process group) and the child is
        reaped before this returns, whatever happened.
        """
        ...
