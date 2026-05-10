"""Unit tests for post-processors invoked by ``generate_recipe_from_pypi``.

The MCP server in ``.claude/tools/conda_forge_server.py`` post-processes every
recipe grayskull writes. These tests exercise the helpers directly so a
refactor that breaks them fails fast — independent of the meta test that
enforces the artifacts in ``recipes/*/recipe.yaml`` carry the schema header.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
TOOLS_DIR = REPO_ROOT / ".claude" / "tools"


@pytest.fixture(scope="module")
def srv():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    try:
        import conda_forge_server  # pyright: ignore[reportMissingImports]
    except ImportError as e:
        pytest.skip(f"conda_forge_server not importable (missing fastmcp?): {e}")
    return conda_forge_server


def test_ensure_yaml_language_server_header_prepends_when_missing(srv, tmp_path):
    recipe = tmp_path / "recipe.yaml"
    recipe.write_text("schema_version: 1\ncontext:\n  version: \"1.0.0\"\n")
    assert srv._ensure_yaml_language_server_header(recipe) is True
    text = recipe.read_text()
    assert text.startswith("# yaml-language-server: $schema=")
    assert "schema_version: 1" in text


def test_ensure_yaml_language_server_header_idempotent(srv, tmp_path):
    recipe = tmp_path / "recipe.yaml"
    original = (
        "# yaml-language-server: "
        "$schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json\n"
        "schema_version: 1\n"
    )
    recipe.write_text(original)
    assert srv._ensure_yaml_language_server_header(recipe) is False
    assert recipe.read_text() == original


def test_ensure_yaml_language_server_header_handles_missing_file(srv, tmp_path):
    missing = tmp_path / "does-not-exist.yaml"
    assert srv._ensure_yaml_language_server_header(missing) is False
