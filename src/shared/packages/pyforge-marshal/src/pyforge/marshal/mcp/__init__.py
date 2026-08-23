"""Marshal MCP surface (Story 18.1, FR-153 / FR-154).

Named, typed tools over Marshal's CLI capabilities. ``.server`` is
deliberately NOT imported here — ``fastmcp`` stays a lazy,
registration-time-only dependency (atlas pattern) so tool bodies import
without FastMCP installed.
"""

from __future__ import annotations

from pyforge.marshal.mcp.tools import (
    TOOL_SPECS,
    list_marshal_tools,
    marshal_check,
    marshal_homes,
    marshal_preflight,
    marshal_refresh,
    marshal_status,
    marshal_upstream,
    run_marshal,
)

__all__ = [
    "TOOL_SPECS",
    "list_marshal_tools",
    "marshal_check",
    "marshal_homes",
    "marshal_preflight",
    "marshal_refresh",
    "marshal_status",
    "marshal_upstream",
    "run_marshal",
]
