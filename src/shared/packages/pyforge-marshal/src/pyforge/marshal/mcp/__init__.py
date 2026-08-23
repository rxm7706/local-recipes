"""Marshal MCP surface (Story 18.1, FR-153 / FR-154; Story 18.2, FR-155 / FR-156).

Named, typed tools over Marshal's CLI capabilities. ``.server`` is
deliberately NOT imported here — ``fastmcp`` stays a lazy,
registration-time-only dependency (atlas pattern) so tool bodies import
without FastMCP installed.

Story 18.2 parity / coverage helpers live under ``.parity`` / ``.coverage``.
They are FastMCP-free. Coverage is *not* imported here so
``python -m pyforge.marshal.mcp.coverage`` does not hit a double-load
``RuntimeWarning`` from package ``__init__`` pre-importing the module.
"""

from __future__ import annotations

from pyforge.marshal.mcp.parity import (
    CLI_ONLY_VERBS,
    TOOL_ONLY_NAMES,
    assert_cli_tool_parity,
    parity_findings,
)
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
    "CLI_ONLY_VERBS",
    "TOOL_ONLY_NAMES",
    "TOOL_SPECS",
    "assert_cli_tool_parity",
    "list_marshal_tools",
    "marshal_check",
    "marshal_homes",
    "marshal_preflight",
    "marshal_refresh",
    "marshal_status",
    "marshal_upstream",
    "parity_findings",
    "run_marshal",
]
