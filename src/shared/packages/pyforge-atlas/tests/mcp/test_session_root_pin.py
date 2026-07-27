"""AUD-ATLAS-018 — MCP sessions refuse arbitrary Kedro project roots."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.atlas.mcp.session import PROJECT_ROOT, _resolve_mcp_project_root


def test_resolve_mcp_project_root_defaults_to_package_root():
    assert _resolve_mcp_project_root(None) == PROJECT_ROOT


def test_resolve_mcp_project_root_accepts_exact_package_root():
    assert _resolve_mcp_project_root(PROJECT_ROOT) == PROJECT_ROOT
    assert _resolve_mcp_project_root(str(PROJECT_ROOT)) == PROJECT_ROOT


def test_resolve_mcp_project_root_rejects_foreign_tree(tmp_path):
    foreign = tmp_path / "other-kedro"
    foreign.mkdir()
    with pytest.raises(ValueError, match="atlas package root"):
        _resolve_mcp_project_root(foreign)
