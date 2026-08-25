"""Lazy Atlas MCP ASGI app — official SDK server, not a second tool surface."""

from __future__ import annotations

from typing import Any

_APP: Any = None


def build_atlas_mcp_asgi() -> Any:
    """Bring ``pyforge.atlas.mcp.server.build_server`` to the host POST face."""
    global _APP
    if _APP is None:
        from django_pyforge.mcp_http import asgi_for_server
        from pyforge.atlas.mcp.server import build_server

        _APP = asgi_for_server(build_server())
    return _APP
