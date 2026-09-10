"""Lazy Steward MCP ASGI app — start_duty / get_duty over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi

STEWARD_STATION = "steward"
RUN_DUTY_TOOL = "run_duty"
START_DUTY_TOOL = "start_duty"
GET_DUTY_TOOL = "get_duty"

_CACHE: dict[str, Any] = {}


def run_duty(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised duty. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_steward_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(STEWARD_STATION, RUN_DUTY_TOOL, run_duty)


def build_steward_mcp_asgi() -> Any:
    """Host POST face at ``/stations/steward/mcp``."""
    return build_station_mcp_asgi(
        station=STEWARD_STATION,
        server_label="pyforge-steward",
        start_tool=START_DUTY_TOOL,
        get_tool=GET_DUTY_TOOL,
        run_tool=RUN_DUTY_TOOL,
        runner=run_duty,
        cache=_CACHE,
    )
