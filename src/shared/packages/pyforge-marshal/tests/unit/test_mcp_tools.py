"""Story 18.1 — named typed Marshal MCP tools (FR-153)."""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.mcp import tools
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


def test_list_marshal_tools_structured_inventory():
    payload = list_marshal_tools()
    assert payload["ok"] is True
    assert payload["count"] == len(TOOL_SPECS)
    names = {t["name"] for t in payload["tools"]}
    assert names == set(TOOL_SPECS)
    for entry in payload["tools"]:
        assert "description" in entry
        assert "cli" in entry


def test_run_marshal_ok_parses_json():
    def fake_main(argv):
        assert argv == ["status", "--format", "json"]
        print(json.dumps({"homes": [], "verdict": "PASS"}))
        return 0

    result = run_marshal(["status", "--format", "json"], main=fake_main)
    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert result["homes"] == []
    assert result["verdict"] == "PASS"


def test_run_marshal_nonzero_envelope():
    def fake_main(argv):
        print(json.dumps({"findings": [{"code": "X"}]}))
        return 2

    result = run_marshal(["check", "--format", "json"], main=fake_main)
    assert result["ok"] is False
    assert result["exit_code"] == 2
    assert result["data"]["findings"][0]["code"] == "X"


def test_marshal_status_forwards_project():
    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    out = marshal_status(project="acme", main=fake_main)
    assert out["ok"] is True
    assert seen == [["status", "--format", "json", "--project", "acme"]]


def test_marshal_check_scope_and_project():
    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    out = marshal_check(scope="repo", project="acme", main=fake_main)
    assert out["ok"] is True
    assert seen[0][:3] == ["check", "--format", "json"]
    assert "--scope" in seen[0] and "repo" in seen[0]
    assert "--project" in seen[0] and "acme" in seen[0]


def test_marshal_homes_argv():
    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    assert marshal_homes(main=fake_main)["ok"] is True
    assert seen == [["homes", "--format", "json"]]


def test_marshal_preflight_requires_slug():
    with pytest.raises(ValueError, match="slug"):
        marshal_preflight(slug="", main=lambda argv: 0)

    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    assert marshal_preflight(slug="acme", main=fake_main)["ok"] is True
    assert seen == [["preflight", "acme", "--format", "json"]]


def test_marshal_upstream_and_refresh():
    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    assert marshal_upstream(main=fake_main)["ok"] is True
    assert marshal_refresh(project="acme", base="main", main=fake_main)["ok"] is True
    assert seen[0] == ["upstream", "--format", "json"]
    assert seen[1] == [
        "refresh",
        "--format",
        "json",
        "--project",
        "acme",
        "--base",
        "main",
    ]


def test_tools_import_without_fastmcp(monkeypatch):
    """FR-153 surface: tool bodies must not require fastmcp at import time."""
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "fastmcp" or name.startswith("fastmcp."):
            raise ImportError("fastmcp blocked for test")
        return real_import(name, *args, **kwargs)

    # Drop cached modules so re-import exercises the no-fastmcp path.
    for key in list(sys.modules):
        if key == "pyforge.marshal.mcp" or key.startswith("pyforge.marshal.mcp."):
            if key.endswith("server"):
                del sys.modules[key]
            elif key in ("pyforge.marshal.mcp", "pyforge.marshal.mcp.tools"):
                del sys.modules[key]

    monkeypatch.setattr(builtins, "__import__", blocked)
    mod = importlib.import_module("pyforge.marshal.mcp.tools")
    assert mod.list_marshal_tools()["count"] >= 1


def test_mcp_server_registration_spec_is_path_relative():
    spec = tools.mcp_server_registration_spec()
    command = spec["marshal"]["command"]
    assert isinstance(command, str)
    tools.assert_no_absolute_command(command)
    with pytest.raises(ValueError):
        tools.assert_no_absolute_command("/abs/marshal-mcp")
