"""Atlas start/get MCP tools over the supervisor (FR-12 / canopy AD-6).

Story 42.2: ``start`` goes through ``start_bounded``, not ``publish_start``.
The SDK keeps the text of its own ``ToolError`` and withholds everyone else's,
so a bare ``RunBoundExceeded`` would reach an agent as ``Error executing tool
start_run_pipeline`` and nothing more -- no status, no ``Retry-After``, no
``run_ids`` -- and this tool is precisely the agent surface the bounds exist
for. ``supervisor._tool_refusal`` is where that contract is spelled out.
"""

from __future__ import annotations

from typing import Any

from django_pyforge.supervisor import ATLAS_STATION
from django_pyforge.supervisor import RUN_PIPELINE_TOOL
from django_pyforge.supervisor import get_run as supervisor_get_run
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
