"""Lazy Warden MCP ASGI app — start_audit / get_audit over the supervisor."""

from __future__ import annotations

from typing import Any

from django_pyforge.supervisor import get_run as supervisor_get_run
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import start_bounded

WARDEN_STATION = "warden"
RUN_AUDIT_TOOL = "run_audit"

_SERVER: Any = None


def run_audit(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Complete one supervised audit. Returns a payload dict only."""
    data = payload if isinstance(payload, dict) else {}
    target = data.get("target")
    if not isinstance(target, str) or not target.strip():
        target = "."
    else:
        target = target.strip()
    return {"target": target, "completed": True}


def ensure_warden_runner() -> None:
    register_runner(WARDEN_STATION, RUN_AUDIT_TOOL, run_audit)


def attach_warden_start_get(server: Any, *, station: str = WARDEN_STATION) -> Any:
    """Register ``start_audit`` and ``get_audit``. Do not reuse Atlas tool names."""

    @server.tool()
    def start_audit(target: str, assertion: str) -> dict[str, str]:
        """Return a handle immediately; work publishes through the supervisor.

        Story 42.2: ``start_bounded``, so a run bound reaches the agent as the
        same projected refusal the portal renders (status, retry_after,
        run_ids) instead of a flattened sentence.
        """
        handle = start_bounded(
            station=station,
            assertion=assertion,
            tool=RUN_AUDIT_TOOL,
            payload={"target": target},
        )
        return {"handle": handle}

    @server.tool()
    def get_audit(handle: str, assertion: str) -> dict[str, Any]:
        """Fetch a supervisor run by handle. Assertion required."""
        return supervisor_get_run(station=station, handle=handle, assertion=assertion)

    return server


def build_warden_mcp_asgi() -> Any:
    """Host POST face at ``/stations/warden/mcp``."""
    global _SERVER  # noqa: PLW0603
    from django_pyforge.mcp_http import asgi_for_server  # noqa: PLC0415

    if _SERVER is None:
        from mcp.server.mcpserver import MCPServer  # noqa: PLC0415

        ensure_warden_runner()
        _SERVER = attach_warden_start_get(MCPServer("pyforge-warden"), station=WARDEN_STATION)
    return asgi_for_server(_SERVER)
