"""Lazy Atlas MCP ASGI app — official SDK server plus supervisor start/get."""

from __future__ import annotations

from typing import Any

_APP: Any = None


def _atlas_run_pipeline(payload: dict[str, Any]) -> Any:
    from pyforge.atlas.mcp.tools import run_pipeline  # noqa: PLC0415

    return run_pipeline(payload["name"])


def build_atlas_mcp_asgi() -> Any:
    """Bring ``pyforge.atlas.mcp.server.build_server`` to the host POST face."""
    global _APP  # noqa: PLW0603
    if _APP is None:
        from django_pyforge.mcp_http import asgi_for_server  # noqa: PLC0415
        from django_pyforge.mcp_start_get import attach_start_get  # noqa: PLC0415
        from django_pyforge.supervisor import ATLAS_STATION  # noqa: PLC0415
        from django_pyforge.supervisor import RUN_PIPELINE_TOOL  # noqa: PLC0415
        from django_pyforge.supervisor import register_runner  # noqa: PLC0415
        from pyforge.atlas.mcp.server import build_server  # noqa: PLC0415

        register_runner(ATLAS_STATION, RUN_PIPELINE_TOOL, _atlas_run_pipeline)
        _APP = asgi_for_server(attach_start_get(build_server(), station=ATLAS_STATION))
    return _APP
