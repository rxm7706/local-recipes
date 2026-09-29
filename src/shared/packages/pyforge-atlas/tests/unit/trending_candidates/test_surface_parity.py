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


def _server_tree() -> ast.Module:
    return ast.parse(Path(inspect.getfile(server)).read_text(encoding="utf-8"))


def _server_tool_node() -> ast.FunctionDef:
    for node in ast.walk(_server_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == TOOL_NAME:
            return node
    raise AssertionError(f"{TOOL_NAME} is not defined in server.py")


def _server_tool_defaults() -> dict:
    node = _server_tool_node()
    args = node.args.args
    defaults = node.args.defaults
    # defaults align to the TAIL of args
    paired = dict(zip((a.arg for a in args[len(args) - len(defaults) :]), defaults))
    return {name: ast.literal_eval(paired[name]) for name in FILTERS}


def _is_tool_decorator(node: ast.expr) -> bool:
    """``@mcp.tool`` and ``@mcp.tool()`` alike (second follow-up review finding, Story
    13.3). FastMCP accepts both spellings, and this matcher used to require the CALL
    form — so a tool registered with the bare decorator was invisible to
    ``_registered_server_tools`` and the "every registered tool is recorded" assertion
    below passed over it (mutation-verified: appending a bare-decorated tool to
    ``server.py``'s source left the detected count unchanged at 13, while the same tool
    written ``@mcp.tool()`` took it to 14). A registry guard must not depend on how the
    decorator is spelled."""
    target = node.func if isinstance(node, ast.Call) else node
    return isinstance(target, ast.Attribute) and target.attr == "tool"


def _tools_in_source(source: str) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and any(_is_tool_decorator(d) for d in node.decorator_list)
    }


def _registered_server_tools() -> set[str]:
    """Every ``@mcp.tool``-decorated function in ``server.py``.

    Read via AST rather than by building the live server, mirroring
    ``tests/nl/test_query_vizro_ai_dryrun.py``: FastMCP is an OPTIONAL extra and is not
    installed in this environment, so nothing here can invoke a registered tool.
    """
    return _tools_in_source(Path(inspect.getfile(server)).read_text(encoding="utf-8"))


def test_mcp_tool_defaults_match_the_query_seam():
    assert _signature_defaults(tools.query_trending_candidates) == _signature_defaults(query.query_trending_candidates)


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
    assert TOOL_NAME in audit.TRENDING_SURFACE_TOOLS
    assert callable(getattr(tools, TOOL_NAME))

    recorded = set(audit.TRENDING_SURFACE_TOOLS)
    # Recorded in exactly ONE bucket — it is a new capability, not one of THE_23.
    assert not recorded & set(audit.ATLAS_TOOL_AUDIT)
    assert not recorded & set(audit.NL_INTERFACE_TOOLS)
    assert not recorded & set(audit.PIPELINE_TRIGGER_TOOLS)
    assert not recorded & set(audit.CLI_ONLY_TOOLS)
    assert not recorded & set(audit.GENERIC_SURFACE_TOOLS)


def test_every_audit_recorded_surface_tool_is_registered_on_the_server():
    """The registry is only honest if it tracks the real server surface."""
    missing = audit.registered_surface_tools() - _registered_server_tools()
    assert not missing, f"recorded in audit.py but not registered on the server: {missing}"


def test_every_registered_server_tool_is_recorded_in_the_audit_surface():
    """The CONVERSE direction — the one that actually catches the defect that prompted
    ``TRENDING_SURFACE_TOOLS`` (follow-up review finding, Story 13.3).

    The previous pass added only ``recorded ⊆ registered``, which a tool registered on
    the server and recorded in NO bucket satisfies trivially — i.e. exactly how
    ``query_trending_candidates`` shipped, and exactly how the next new tool would ship,
    with the whole suite green. This asserts the direction that fails for it."""
    unrecorded = _registered_server_tools() - audit.registered_surface_tools()
    assert not unrecorded, f"registered on the server but recorded in no mcp/audit.py bucket: {sorted(unrecorded)}"


def test_the_registry_guard_sees_a_bare_mcp_tool_decorator_too():
    """A mutation guard for the guard above (second follow-up review finding, Story
    13.3).

    ``_registered_server_tools`` matched only the CALL form, so a tool registered with
    the bare ``@mcp.tool`` — a spelling FastMCP accepts — was invisible to it, and
    ``test_every_registered_server_tool_is_recorded_in_the_audit_surface`` passed over
    it: the next unrecorded tool would ship exactly the way
    ``query_trending_candidates`` did, whole suite green, as long as it omitted two
    parentheses."""
    source = Path(inspect.getfile(server)).read_text(encoding="utf-8")
    baseline = _tools_in_source(source)
    for decorator in ("@mcp.tool", "@mcp.tool()"):
        probe = f"{source}\n\n{decorator}\ndef unrecorded_probe_tool() -> dict:\n    return {{}}\n"
        assert _tools_in_source(probe) - baseline == {"unrecorded_probe_tool"}, decorator


def test_the_server_tool_forwards_every_filter_to_the_same_named_keyword():
    """Guards the ONE hand-written forwarding hop in the whole surface (follow-up review
    finding, Story 13.3).

    ``server.py``'s ``@mcp.tool()`` wrapper re-declares all five filters and passes them
    on by hand, and NOTHING exercised it: the default-parity tests above compare only
    default VALUES, and ``tests/mcp/test_read_surface.py``'s delegation proof stops at
    ``tools.py``. Transposing two kwargs in the wrapper (``period=tier, tier=period``)
    left the entire suite green while an MCP client's ``period="daily"`` reached the
    query seam as its ``tier`` — the exact CLI/MCP drift CAP-3's success signal forbids
    (verified by mutation). Checked via AST for the same reason the rest of this module
    is: FastMCP is an optional extra, absent here, so the live tool cannot be called."""
    node = _server_tool_node()
    delegations = [
        call
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == TOOL_NAME
    ]
    assert len(delegations) == 1, "the wrapper must be a single delegate call"
    call = delegations[0]
    assert not call.args, "every filter must be forwarded BY KEYWORD, never positionally"
    forwarded = {kw.arg: kw.value.id for kw in call.keywords if isinstance(kw.value, ast.Name)}
    assert {name: name for name in FILTERS}.items() <= forwarded.items(), (
        f"server.py's {TOOL_NAME} does not forward each filter to its own name: {forwarded}"
    )
