"""Lazy Marshal MCP ASGI app — start_loop / get_loop over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi

MARSHAL_STATION = "marshal"
RUN_LOOP_TOOL = "run_loop"
START_LOOP_TOOL = "start_loop"
GET_LOOP_TOOL = "get_loop"

_CACHE: dict[str, Any] = {}


def run_loop(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised loop run. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_marshal_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(MARSHAL_STATION, RUN_LOOP_TOOL, run_loop)


def build_marshal_mcp_asgi() -> Any:
    """Host POST face at ``/stations/marshal/mcp``."""
    return build_station_mcp_asgi(
        station=MARSHAL_STATION,
        server_label="pyforge-marshal",
        start_tool=START_LOOP_TOOL,
        get_tool=GET_LOOP_TOOL,
        run_tool=RUN_LOOP_TOOL,
        runner=run_loop,
        cache=_CACHE,
    )
