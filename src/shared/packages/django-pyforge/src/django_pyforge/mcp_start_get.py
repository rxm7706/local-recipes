"""Atlas start/get MCP tools over the supervisor (FR-12 / canopy AD-6).

Story 42.2: ``start`` goes through ``start_bounded``, not ``publish_start``.
The SDK keeps the text of its own ``ToolError`` and withholds everyone else's,
so a bare ``RunBoundExceeded`` would reach an agent as ``Error executing tool
start_run_pipeline`` and nothing more -- no status, no ``Retry-After``, no
``run_ids`` -- and this tool is precisely the agent surface the bounds exist
for. ``supervisor._tool_refusal`` is where that contract is spelled out.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_pyforge.supervisor import ATLAS_STATION
from django_pyforge.supervisor import RUN_PIPELINE_TOOL
from django_pyforge.supervisor import get_run as supervisor_get_run
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import start_bounded


def attach_start_get(server: Any, *, station: str = ATLAS_STATION) -> Any:
    """Register ``start_run_pipeline`` and ``get_run`` on an official MCPServer."""

    @server.tool()
    def start_run_pipeline(name: str, assertion: str) -> dict[str, str]:
        """Return a handle immediately; work publishes through the supervisor."""
        handle = start_bounded(
            station=station,
            assertion=assertion,
            tool=RUN_PIPELINE_TOOL,
            payload={"name": name},
        )
        return {"handle": handle}

    @server.tool()
    def get_run(handle: str, assertion: str) -> dict[str, Any]:
        """Fetch a supervisor run by handle. Assertion required."""
        return supervisor_get_run(station=station, handle=handle, assertion=assertion)

    return server


def attach_supervised_start_get(
    server: Any,
    *,
    station: str,
    start_tool: str,
    get_tool: str,
    run_tool: str,
) -> Any:
    """Register station-scoped ``start_*`` / ``get_*`` tools over the supervisor."""

    @server.tool(name=start_tool)
    def _start(target: str, assertion: str) -> dict[str, str]:
        """Return a handle immediately; work publishes through the supervisor."""
        handle = start_bounded(
            station=station,
            assertion=assertion,
            tool=run_tool,
            payload={"target": target},
        )
        return {"handle": handle}

    @server.tool(name=get_tool)
    def _get(handle: str, assertion: str) -> dict[str, Any]:
        """Fetch a supervisor run by handle. Assertion required."""
        return supervisor_get_run(station=station, handle=handle, assertion=assertion)

    return server


def build_station_mcp_asgi(
    *,
    station: str,
    server_label: str,
    start_tool: str,
    get_tool: str,
    run_tool: str,
    runner: Callable[[dict[str, Any] | None], dict[str, Any]],
    cache: dict[str, Any],
) -> Any:
    """Lazy MCP ASGI app for a station face with supervisor start/get."""
    from django_pyforge.mcp_http import asgi_for_server  # noqa: PLC0415

    if cache.get("app") is None:
        from mcp.server.mcpserver import MCPServer  # noqa: PLC0415

        register_runner(station, run_tool, runner)
        server = attach_supervised_start_get(
            MCPServer(server_label),
            station=station,
            start_tool=start_tool,
            get_tool=get_tool,
            run_tool=run_tool,
        )
        cache["app"] = asgi_for_server(server)
    return cache["app"]
