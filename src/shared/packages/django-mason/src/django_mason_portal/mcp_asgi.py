"""Lazy Mason MCP ASGI app — start_build / get_build over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi

MASON_STATION = "mason"
RUN_BUILD_TOOL = "run_build"
START_BUILD_TOOL = "start_build"
GET_BUILD_TOOL = "get_build"

_CACHE: dict[str, Any] = {}


def run_build(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised build. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_mason_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(MASON_STATION, RUN_BUILD_TOOL, run_build)


def build_mason_mcp_asgi() -> Any:
    """Host POST face at ``/stations/mason/mcp``."""
    return build_station_mcp_asgi(
        station=MASON_STATION,
        server_label="pyforge-mason",
        start_tool=START_BUILD_TOOL,
        get_tool=GET_BUILD_TOOL,
        run_tool=RUN_BUILD_TOOL,
        runner=run_build,
        cache=_CACHE,
    )
