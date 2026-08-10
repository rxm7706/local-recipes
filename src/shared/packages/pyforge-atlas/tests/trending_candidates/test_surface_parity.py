"""CAP-3 surface parity (Story 13.3, FR-66) — the CLI and the MCP tool must not drift.

The story's central claim is that identical filters yield identical output BY
CONSTRUCTION, because both surfaces delegate to the one
``query.query_trending_candidates``. Delegation alone does not deliver that: the filter
DEFAULTS are declared FOUR separate times — in ``query.py``'s signature, in
``mcp/tools.py``'s signature, in ``mcp/server.py``'s ``@mcp.tool()`` signature, and in
``__main__.py``'s argparse — and each forwards its own literals unconditionally, so
``query.py``'s defaults are dead code on every other path (follow-up review finding,
Story 13.3).

The gap that leaves: change a default in ``query.py`` alone and
``test_json_output_matches_query_trending_candidates`` still passes (both CLI sides move
together), while the MCP tool keeps sending the old value — so a DEFAULT invocation of
the two surfaces returns different results, which is precisely what CAP-3's success
signal forbids. These tests pin all four declarations to one source of truth.

``server.py`` is read via AST rather than FastMCP internals, mirroring
``tests/mcp/test_no_business_logic_in_tool_bodies.py``'s approach.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from pyforge.atlas.mcp import audit, server, tools
from pyforge.atlas.trending_candidates import query
from pyforge.atlas.trending_candidates.__main__ import _build_parser

TOOL_NAME = "query_trending_candidates"

# The 6th flag, --json, is an output-format choice with no query-seam counterpart.
FILTERS = ("period", "tier", "top", "not_on_cf", "min_stars")


def _signature_defaults(func) -> dict:
    params = inspect.signature(func).parameters
    return {name: params[name].default for name in FILTERS}


def _server_tool_defaults() -> dict:
    tree = ast.parse(Path(inspect.getfile(server)).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == TOOL_NAME:
            args = node.args.args
            defaults = node.args.defaults
            # defaults align to the TAIL of args
            paired = dict(
                zip((a.arg for a in args[len(args) - len(defaults):]), defaults)
            )
            return {name: ast.literal_eval(paired[name]) for name in FILTERS}
    raise AssertionError(f"{TOOL_NAME} is not defined in server.py")


def test_mcp_tool_defaults_match_the_query_seam():
    assert _signature_defaults(tools.query_trending_candidates) == _signature_defaults(
        query.query_trending_candidates
    )


def test_server_tool_defaults_match_the_query_seam():
    assert _server_tool_defaults() == _signature_defaults(query.query_trending_candidates)


def test_cli_defaults_match_the_query_seam():
    parsed = _build_parser().parse_args([])
    cli_defaults = {name: getattr(parsed, name) for name in FILTERS}
    assert cli_defaults == _signature_defaults(query.query_trending_candidates)


def test_the_trending_tool_is_recorded_in_the_mcp_audit_surface():
    """``mcp/audit.py`` is this package's declared, tested record of its MCP surface.
    The tool shipped registered on the server but absent from EVERY bucket there
    (follow-up review finding, Story 13.3) — the same omission Story 13.1 avoided by
    adding ``run_upstream_discovery_pipeline`` to ``PIPELINE_TRIGGER_TOOLS``, and
    ``query_vizro_ai`` avoided via ``NL_INTERFACE_TOOLS``. Nothing detected it, so this
    pins it."""
    assert audit.TRENDING_SURFACE_TOOLS == (TOOL_NAME,)
    assert callable(getattr(tools, TOOL_NAME))

    recorded = set(audit.TRENDING_SURFACE_TOOLS)
    # Recorded in exactly ONE bucket — it is a new capability, not one of THE_23.
    assert not recorded & set(audit.ATLAS_TOOL_AUDIT)
    assert not recorded & set(audit.NL_INTERFACE_TOOLS)
    assert not recorded & set(audit.PIPELINE_TRIGGER_TOOLS)
    assert not recorded & set(audit.CLI_ONLY_TOOLS)


def test_every_audit_recorded_surface_tool_is_registered_on_the_server():
    """The registry is only honest if it tracks the real server surface."""
    tree = ast.parse(Path(inspect.getfile(server)).read_text(encoding="utf-8"))
    registered = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool"
            for d in node.decorator_list
        )
    }
    missing = set(audit.TRENDING_SURFACE_TOOLS) - registered
    assert not missing, f"recorded in audit.py but not registered on the server: {missing}"
