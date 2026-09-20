"""Story 21.2 — atlas ``build_server`` is the official ``mcp`` SDK, same tools."""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.atlas.mcp import tools
from pyforge.atlas.mcp.server import build_server

SERVER_PATH = Path(__file__).resolve().parents[3] / "src" / "pyforge" / "atlas" / "mcp" / "server.py"


def test_build_server_is_official_mcp_server():
    server = build_server()
    assert type(server).__name__ == "MCPServer"
    assert type(server).__module__.startswith("mcp.server")


def test_wrappers_still_delegate_to_tools_module():
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "tools"
    ]
    names = {node.attr for node in calls}
    assert "run_pipeline" in names
    assert "read_dataset" in names
    assert "list_pipelines" in names
    assert "query_trending_candidates" in names
    assert tools.PIPELINE_NAMES  # surface still imported without the SDK
