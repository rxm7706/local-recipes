"""Lazy Herald MCP ASGI app — start_notice / get_notice over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi

HERALD_STATION = "herald"
RUN_NOTICE_TOOL = "run_notice"
START_NOTICE_TOOL = "start_notice"
GET_NOTICE_TOOL = "get_notice"

_CACHE: dict[str, Any] = {}


def run_notice(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised notice dispatch. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_herald_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(HERALD_STATION, RUN_NOTICE_TOOL, run_notice)


def build_herald_mcp_asgi() -> Any:
    """Host POST face at ``/stations/herald/mcp``."""
    return build_station_mcp_asgi(
        station=HERALD_STATION,
        server_label="pyforge-herald",
        start_tool=START_NOTICE_TOOL,
        get_tool=GET_NOTICE_TOOL,
        run_tool=RUN_NOTICE_TOOL,
        runner=run_notice,
        cache=_CACHE,
    )
