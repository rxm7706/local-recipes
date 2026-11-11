"""Story 115.3 (CAP-23 amended 2026-11-10): ``marshal-mcp`` registers exactly the tools it lists.

``list_marshal_tools`` reports every ``TOOL_SPECS`` entry, so a spec the server does not register is a tool a
client is told about and cannot call (the three preserve tools, at ``82a2b18828``). The live server's registered
names must equal ``TOOL_SPECS``; the two mutations below -- a registration dropped from a built server, a spec
added to ``TOOL_SPECS`` -- each make the same check fail with a named finding.
"""

from __future__ import annotations

import asyncio

import pytest

from pyforge.marshal.mcp import server as server_mod
from pyforge.marshal.mcp import tools as tools_mod
from pyforge.marshal.mcp.parity import registration_findings


def _registered_names(server) -> frozenset[str]:
    return frozenset(tool.name for tool in asyncio.run(server.list_tools()))


def test_registered_tool_names_equal_tool_specs():
    registered = _registered_names(server_mod.build_server())
    assert registration_findings(registered) == []
    assert registered == frozenset(tools_mod.TOOL_SPECS)


def test_the_three_preserve_tools_are_registered():
    """The operator's ruling of 2026-11-10: register all three; the count is the inventory's, never typed."""
    registered = _registered_names(server_mod.build_server())
    assert {"marshal_preserve_list", "marshal_preserve_push", "marshal_preserve_retire"} <= registered
    assert len(registered) == len(tools_mod.TOOL_SPECS)


@pytest.mark.parametrize("dropped", sorted(tools_mod.TOOL_SPECS))
def test_mutation_a_dropped_registration_fails_the_check(dropped):
    server = server_mod.build_server()
    server.remove_tool(dropped)
    findings = registration_findings(_registered_names(server))
    assert [(f.code, dropped in f.detail) for f in findings] == [("tool_spec_unregistered", True)]


def test_mutation_an_added_spec_fails_the_check(monkeypatch):
    registered = _registered_names(server_mod.build_server())
    monkeypatch.setitem(
        tools_mod.TOOL_SPECS,
        "marshal_phantom",
        {"description": "fixture-only: a spec with no registration", "cli": ["status", "--format", "json"]},
    )
    findings = registration_findings(registered)
    assert [(f.code, "marshal_phantom" in f.detail) for f in findings] == [("tool_spec_unregistered", True)]


def test_a_registration_with_no_spec_fails_the_check():
    """The other direction CAP-23 names: a registered tool the inventory hides."""
    registered = _registered_names(server_mod.build_server()) | {"marshal_unlisted"}
    findings = registration_findings(registered)
    assert [(f.code, "marshal_unlisted" in f.detail) for f in findings] == [("tool_registered_without_spec", True)]
