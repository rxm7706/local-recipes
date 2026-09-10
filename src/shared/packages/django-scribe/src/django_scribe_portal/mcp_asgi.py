"""Lazy Scribe MCP ASGI app — start_recall / get_recall over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import build_station_mcp_asgi

SCRIBE_STATION = "scribe"
RUN_RECALL_TOOL = "run_recall"
START_RECALL_TOOL = "start_recall"
GET_RECALL_TOOL = "get_recall"

_CACHE: dict[str, Any] = {}


def run_recall(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised recall. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_scribe_runner() -> None:
    from django_pyforge.supervisor import register_runner  # noqa: PLC0415

    register_runner(SCRIBE_STATION, RUN_RECALL_TOOL, run_recall)


def build_scribe_mcp_asgi() -> Any:
    """Host POST face at ``/stations/scribe/mcp``."""
    return build_station_mcp_asgi(
        station=SCRIBE_STATION,
        server_label="pyforge-scribe",
        start_tool=START_RECALL_TOOL,
        get_tool=GET_RECALL_TOOL,
        run_tool=RUN_RECALL_TOOL,
        runner=run_recall,
        cache=_CACHE,
    )
