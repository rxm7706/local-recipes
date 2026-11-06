"""Lazy Herald MCP ASGI app — start_notice / get_notice over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi
from django_pyforge.supervisor import refuse_unwired_run

HERALD_STATION = "herald"
RUN_NOTICE_TOOL = "run_notice"
START_NOTICE_TOOL = "start_notice"
GET_NOTICE_TOOL = "get_notice"

_CACHE: dict[str, Any] = {}


def run_notice(_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Run nothing: no work is wired behind ``start_notice`` yet (Story 21.6)."""
    refuse_unwired_run(HERALD_STATION, RUN_NOTICE_TOOL)


def ensure_herald_runner() -> None:
    from django_pyforge.supervisor import register_runner

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
