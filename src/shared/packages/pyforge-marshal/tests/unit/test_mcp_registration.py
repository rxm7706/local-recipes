"""Story 18.1 — per-home `.mcp.json` registration (FR-154 / AD-43)."""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.cli.init import _render_mcp_json
from pyforge.marshal.core import policy as policy_mod
from pyforge.marshal.mcp.tools import assert_no_absolute_command, mcp_server_registration_spec


class _MemFs:
    """Minimal FsPort stand-in for render-only tests."""

    def __init__(self) -> None:
        self.texts: dict[Path, str] = {}
        self.dirs: set[Path] = set()

    def exists(self, path: Path) -> bool:
        return path in self.texts or path in self.dirs

    def write_text_atomic(self, path: Path, text: str) -> None:
        self.texts[path] = text


def _effective_with_marshal_server():
    reg = mcp_server_registration_spec()["marshal"]
    return policy_mod.compose(
        project_slug="pyforge-marshal",
        project={"mcp_servers": {"marshal": dict(reg)}},
        flags={},
    )


def test_render_mcp_json_marshal_server_path_relative(tmp_path):
    """Policy-shaped marshal MCP server renders PATH-relative into `.mcp.json`."""
    reg = mcp_server_registration_spec()["marshal"]
    assert_no_absolute_command(str(reg["command"]))

    effective, findings = _effective_with_marshal_server()
    assert not any(f.severity.value == "ERROR" for f in findings)

    home = tmp_path / "home"
    fs = _MemFs()
    status, render_findings = _render_mcp_json(effective, home, fs)  # type: ignore[arg-type]
    assert status == "done"
    assert render_findings == []

    rendered = json.loads(fs.texts[home / ".mcp.json"])
    server = rendered["mcpServers"]["marshal"]
    assert server["command"] == "marshal-mcp"
    assert server["args"] == []
    assert_no_absolute_command(server["command"])
    dumped = json.dumps(rendered)
    assert "/home/" not in dumped
    assert str(Path.cwd()) not in dumped


def test_render_skips_when_mcp_json_already_present(tmp_path):
    effective, _ = _effective_with_marshal_server()
    home = tmp_path / "home"
    fs = _MemFs()
    fs.texts[home / ".mcp.json"] = '{"mcpServers": {"hand": {"command": "x"}}}'
    status, _ = _render_mcp_json(effective, home, fs)  # type: ignore[arg-type]
    assert status == "skipped"
    assert fs.texts[home / ".mcp.json"] == '{"mcpServers": {"hand": {"command": "x"}}}'


def test_project_policy_declares_marshal_mcp_server():
    """This station's tracked marshal-policy.toml declares the marshal server."""
    pkg_root = Path(__file__).resolve().parents[2]  # .../pyforge-marshal
    policy = (
        pkg_root.parents[3]
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "marshal-policy.toml"
    )
    assert policy.is_file(), policy
    text = policy.read_text(encoding="utf-8")
    assert "[mcp_servers.marshal]" in text
    assert 'command = "marshal-mcp"' in text


def test_render_write_failure_reports_failed(tmp_path):
    class _FailFs(_MemFs):
        def write_text_atomic(self, path: Path, text: str) -> None:
            raise FsError(f"boom writing {path}")

    effective, _ = _effective_with_marshal_server()
    status, findings = _render_mcp_json(effective, tmp_path / "home", _FailFs())  # type: ignore[arg-type]
    assert status == "failed"
    assert findings
