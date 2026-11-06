"""Lazy Doctor MCP ASGI app — start_scan / get_scan over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi
from django_pyforge.supervisor import refuse_unwired_run

DOCTOR_STATION = "doctor"
RUN_SCAN_TOOL = "run_scan"
START_SCAN_TOOL = "start_scan"
GET_SCAN_TOOL = "get_scan"

_CACHE: dict[str, Any] = {}


def run_scan(_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Run nothing: no work is wired behind ``start_scan`` yet (Story 21.6)."""
    refuse_unwired_run(DOCTOR_STATION, START_SCAN_TOOL)


def ensure_doctor_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(DOCTOR_STATION, RUN_SCAN_TOOL, run_scan)


def build_doctor_mcp_asgi() -> Any:
    """Host POST face at ``/stations/doctor/mcp``."""
    return build_station_mcp_asgi(
        station=DOCTOR_STATION,
        server_label="pyforge-doctor",
        start_tool=START_SCAN_TOOL,
        get_tool=GET_SCAN_TOOL,
        run_tool=RUN_SCAN_TOOL,
        runner=run_scan,
        cache=_CACHE,
    )
