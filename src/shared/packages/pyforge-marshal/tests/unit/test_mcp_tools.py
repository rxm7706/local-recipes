"""Story 18.1 — named typed Marshal MCP tools (FR-153).

Story 115.3 (CAP-23 amended 2026-11-10) adds the three preserve tools' argv and their refusal while
``pyforge.marshal.preserve_refs`` is off: push and retire run the real CLI, which reads the flag.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.marshal.cli.preserve import PRESERVE_FLAG_KEY
from pyforge.marshal.core.verdict import EXIT_USAGE
from pyforge.marshal.mcp import tools
from pyforge.marshal.mcp.tools import (
    TOOL_SPECS,
    list_marshal_tools,
    marshal_check,
    marshal_homes,
    marshal_preflight,
    marshal_preserve_list,
    marshal_preserve_push,
    marshal_preserve_retire,
    marshal_refresh,
    marshal_status,
    marshal_upstream,
    marshal_watch,
    run_marshal,
)

_RETIRE_TAG = "refs/tags/preserve/pyforge-marshal/115.3/x"
_RETIRE_EVIDENCE = "story pyforge-marshal 115.3 done deadbeef"


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


def test_marshal_watch_forwards_project_run_and_fleet():
    seen: list[list[str]] = []

    def fake_main(argv):
        seen.append(list(argv))
        print('{"command":"watch","data":{"sections":{}}}')
        return 0

    out = marshal_watch(project="herald", run="run-1", fleet=True, main=fake_main)
    assert out["ok"] is True
    assert out["command"] == "watch"
    assert seen == [
        [
            "watch",
            "--format",
            "json",
            "--project",
            "herald",
            "--run",
            "run-1",
            "--fleet",
        ]
    ]


def test_mcp_server_registration_spec_is_path_relative():
    spec = tools.mcp_server_registration_spec()
    command = spec["marshal"]["command"]
    assert isinstance(command, str)
    tools.assert_no_absolute_command(command)
    with pytest.raises(ValueError):
        tools.assert_no_absolute_command("/abs/marshal-mcp")


# --- Story 115.3: the preserve tools ------------------------------------------------------------------------------


def _capture(seen: list[list[str]]):
    def fake_main(argv):
        seen.append(list(argv))
        print("{}")
        return 0

    return fake_main


def test_marshal_preserve_list_forwards_its_filters():
    seen: list[list[str]] = []
    out = marshal_preserve_list(station="pyforge-marshal", state="open", main=_capture(seen))
    assert out["ok"] is True
    assert seen == [["preserve", "list", "--format", "json", "--station", "pyforge-marshal", "--state", "open"]]


def test_marshal_preserve_push_forwards_pending():
    seen: list[list[str]] = []
    assert marshal_preserve_push(pending=True, main=_capture(seen))["ok"] is True
    assert marshal_preserve_push(main=_capture(seen))["ok"] is True
    assert seen == [["preserve", "push", "--pending"], ["preserve", "push"]]


def test_marshal_preserve_retire_requires_tag_and_evidence():
    with pytest.raises(ValueError, match="evidence"):
        marshal_preserve_retire(tag=_RETIRE_TAG, evidence="", main=lambda argv: 0)
    seen: list[list[str]] = []
    assert marshal_preserve_retire(tag=_RETIRE_TAG, evidence=_RETIRE_EVIDENCE, main=_capture(seen))["ok"] is True
    assert seen == [["preserve", "retire", _RETIRE_TAG, "--evidence", _RETIRE_EVIDENCE]]


@pytest.fixture
def preserve_flag_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``pyforge.marshal.preserve_refs`` reads OFF, as it does in every environment."""
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PRESERVE_FLAG_KEY: "off"})))


def _assert_refused_by_the_flag(result: dict) -> None:
    assert result["ok"] is False
    assert result["exit_code"] == EXIT_USAGE
    assert f"flag {PRESERVE_FLAG_KEY} is off" in result["stderr"]


def test_marshal_preserve_push_refuses_with_the_flag_off(preserve_flag_off):
    _assert_refused_by_the_flag(marshal_preserve_push(pending=True))


def test_marshal_preserve_retire_refuses_with_the_flag_off(preserve_flag_off):
    _assert_refused_by_the_flag(marshal_preserve_retire(tag=_RETIRE_TAG, evidence=_RETIRE_EVIDENCE))


@pytest.mark.parametrize(
    "tool_name, arguments",
    [
        ("marshal_preserve_push", {"pending": True}),
        ("marshal_preserve_retire", {"tag": _RETIRE_TAG, "evidence": _RETIRE_EVIDENCE}),
    ],
)
def test_registered_preserve_tool_refuses_through_the_server_with_the_flag_off(preserve_flag_off, tool_name, arguments):
    """The registered tool, called the way an MCP client calls it, reaches the CLI's flag refusal."""
    from pyforge.marshal.mcp import server as server_mod

    outcome = asyncio.run(server_mod.build_server().call_tool(tool_name, arguments))
    assert outcome.is_error is False
    _assert_refused_by_the_flag(json.loads(outcome.content[0].text))
