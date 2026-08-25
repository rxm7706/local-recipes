"""Atlas start/get MCP tools over the supervisor (FR-12 / canopy AD-6)."""

from __future__ import annotations

from typing import Any

from django_pyforge.supervisor import ATLAS_STATION
from django_pyforge.supervisor import RUN_PIPELINE_TOOL
from django_pyforge.supervisor import get_run as supervisor_get_run
from django_pyforge.supervisor import publish_start


def attach_start_get(server: Any, *, station: str = ATLAS_STATION) -> Any:
    """Register ``start_run_pipeline`` and ``get_run`` on an official MCPServer."""

    @server.tool()
    def start_run_pipeline(name: str, assertion: str) -> dict[str, str]:
        """Return a handle immediately; work publishes through the supervisor."""
        handle = publish_start(
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
