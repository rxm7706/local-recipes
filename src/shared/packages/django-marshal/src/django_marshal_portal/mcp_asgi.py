"""Lazy Marshal MCP ASGI app — start_loop / get_loop / held-loop publish."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from django_pyforge.assertion.client import register_portal_job
from django_pyforge.mcp_start_get import attach_supervised_start_get
from django_pyforge.supervisor import (
    LOOP_COMPLETE_TOOL,
    LOOP_HEARTBEAT_TOOL,
    LOOP_PUBLISH_TOOL,
    complete_held_run,
    heartbeat_held_run,
    list_published_story_tasks,
    publish_held_loop_bounded,
    register_runner,
)

MARSHAL_STATION = "marshal"
RUN_LOOP_TOOL = "run_loop"
START_LOOP_TOOL = "start_loop"
GET_LOOP_TOOL = "get_loop"
LIST_STORY_TASKS_TOOL = "list_loop_story_tasks"
WATCH_TOOL = "marshal_watch"

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


def _marshal_watch_job(
    *,
    assertion: str,
    payload: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Portal/MCP job: same report shape as ``marshal watch`` (Story 44.2/44.4)."""
    del assertion
    data = payload if isinstance(payload, dict) else {}
    pyforge = shutil.which("pyforge")
    argv = (
        [pyforge, "marshal", "watch", "--format", "json"]
        if pyforge
        else ["marshal", "watch", "--format", "json"]
    )
    project = data.get("project")
    run = data.get("run")
    if project:
        argv.extend(["--project", str(project)])
    if run:
        argv.extend(["--run", str(run)])
    if data.get("fleet"):
        argv.append("--fleet")
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return {
        "ok": False,
        "exit_code": completed.returncode,
        "stderr": completed.stderr,
        "stdout": completed.stdout,
    }



def ensure_marshal_runner() -> None:
    from django_pyforge.supervisor import register_runner

    register_runner(MARSHAL_STATION, RUN_LOOP_TOOL, run_loop)
    register_portal_job(MARSHAL_STATION, WATCH_TOOL, _marshal_watch_job)


def attach_held_loop_tools(server: Any) -> Any:
    return _attach_held_loop_tools(server)


def _attach_held_loop_tools(server: Any) -> Any:
    @server.tool(name=LOOP_PUBLISH_TOOL)
    def publish_loop_run(
        assertion: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Publish an externally owned loop run to the supervisor store.

        `payload` is an explicit nested field, not `**kwargs` -- the MCP SDK's
        own schema generation turns a `**kwargs`-style parameter into a
        REQUIRED field named after it rather than "any extra keys allowed"
        (found live, spec-mcp-host-real-station-tools: the real HostPublisher
        client sent flat kwargs and every publish call failed schema
        validation the moment this tool became reachable at all).
        """
        handle = publish_held_loop_bounded(
            station=MARSHAL_STATION,
            assertion=assertion,
            payload=payload,
        )
        return {"handle": handle}

    @server.tool(name=LOOP_HEARTBEAT_TOOL)
    def heartbeat_loop_run(
        handle: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Keep a held loop run alive. Same explicit-`payload` shape as publish."""
        heartbeat_held_run(handle, payload=payload or None)
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

    @server.tool(name=WATCH_TOOL)
    def marshal_watch(
        project: str | None = None,
        run: str | None = None,
        fleet: bool = False,
    ) -> dict[str, Any]:
        """Return ``marshal watch``'s report (Story 44.2 / spec-marshal-run-watch CAP-3)."""
        return _marshal_watch_job(
            assertion="",
            payload={"project": project, "run": run, "fleet": fleet},
        )

    return server


def build_marshal_mcp_asgi() -> Any:
    """Host POST face at ``/stations/marshal/mcp``."""
    from django_pyforge.mcp_http import asgi_for_server

    if _CACHE.get("app") is None:
        from mcp.server.mcpserver import MCPServer

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
