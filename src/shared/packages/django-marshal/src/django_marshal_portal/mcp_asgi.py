"""Lazy Marshal MCP ASGI app — start_loop / get_loop / held-loop publish."""

from __future__ import annotations

from typing import Any

from django_pyforge.mcp_start_get import attach_supervised_start_get
from django_pyforge.supervisor import LOOP_COMPLETE_TOOL
from django_pyforge.supervisor import LOOP_HEARTBEAT_TOOL
from django_pyforge.supervisor import LOOP_PUBLISH_TOOL
from django_pyforge.supervisor import complete_held_run
from django_pyforge.supervisor import heartbeat_held_run
from django_pyforge.supervisor import list_published_story_tasks
from django_pyforge.supervisor import publish_held_loop_bounded
from django_pyforge.supervisor import register_runner

MARSHAL_STATION = "marshal"
RUN_LOOP_TOOL = "run_loop"
START_LOOP_TOOL = "start_loop"
GET_LOOP_TOOL = "get_loop"
LIST_STORY_TASKS_TOOL = "list_loop_story_tasks"

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


def _attach_held_loop_tools(server: Any) -> Any:
    @server.tool(name=LOOP_PUBLISH_TOOL)
    def publish_loop_run(assertion: str, **payload: Any) -> dict[str, str]:
        """Publish an externally owned loop run to the supervisor store."""
        handle = publish_held_loop_bounded(
            station=MARSHAL_STATION,
            assertion=assertion,
            payload=dict(payload),
        )
        return {"handle": handle}

    @server.tool(name=LOOP_HEARTBEAT_TOOL)
    def heartbeat_loop_run(handle: str, **payload: Any) -> dict[str, str]:
        """Keep a held loop run alive."""
        heartbeat_held_run(handle, payload=dict(payload) if payload else None)
        return {"handle": handle}

    @server.tool(name=LOOP_COMPLETE_TOOL)
    def complete_loop_run(
        handle: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Terminalize a held loop run."""
        complete_held_run(handle, status=status, result=result or {})
        return {"handle": handle}

    @server.tool(name=LIST_STORY_TASKS_TOOL)
    def list_loop_story_tasks(project_slug: str) -> dict[str, Any]:
        """Return published per-story task records for one loop home."""
        return list_published_story_tasks(
            station=MARSHAL_STATION,
            project_slug=project_slug,
        )

    return server


def build_marshal_mcp_asgi() -> Any:
    """Host POST face at ``/stations/marshal/mcp``."""
    from django_pyforge.mcp_http import asgi_for_server  # noqa: PLC0415

    if _CACHE.get("app") is None:
        from mcp.server.mcpserver import MCPServer  # noqa: PLC0415

        register_runner(MARSHAL_STATION, RUN_LOOP_TOOL, run_loop)
        server = attach_supervised_start_get(
            MCPServer("pyforge-marshal"),
            station=MARSHAL_STATION,
            start_tool=START_LOOP_TOOL,
            get_tool=GET_LOOP_TOOL,
            run_tool=RUN_LOOP_TOOL,
        )
        server = _attach_held_loop_tools(server)
        _CACHE["app"] = asgi_for_server(server)
    return _CACHE["app"]
