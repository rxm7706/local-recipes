"""Unit tests for v8.12.0 grayskull post-processors in conda_forge_server.py.

The post-processors live in the MCP server module because that's where
`generate_recipe_from_pypi` shells out to grayskull. The tests import them
directly via importlib so the MCP server doesn't actually bind.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_cfs():
    """Load conda_forge_server.py with a stubbed fastmcp module so @mcp.tool
    decorators are no-ops."""
    if "cfs_under_test" in sys.modules:
        return sys.modules["cfs_under_test"]

    fake = types.ModuleType("fastmcp")

    class _FakeMCP:
        def tool(self, *_a, **_k):
            def deco(fn):
                return fn
            return deco

    fake.FastMCP = lambda *_a, **_k: _FakeMCP()  # type: ignore[attr-defined]
    fake.Context = object  # type: ignore[attr-defined]
    sys.modules["fastmcp"] = fake

    # parents[0]=unit, [1]=tests, [2]=conda-forge-expert, [3]=skills, [4]=.claude
    path = Path(__file__).resolve().parents[4] / "tools" / "conda_forge_server.py"
    spec = importlib.util.spec_from_file_location("cfs_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cfs_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cfs():
    return _load_cfs()


class TestNormalizeTestMatrix:
    def test_emits_canonical_list_indent(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "tests:\n  - python:\n      python_version: ${{ python_min }}.*\n"
        )
        assert cfs._normalize_grayskull_test_matrix(p) is True
        out = p.read_text()
        # Canonical: list items 2 spaces deeper than parent key.
        assert "      python_version:\n        - ${{ python_min }}.*\n        - \"*\"" in out

    def test_idempotent(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "tests:\n  - python:\n      python_version:\n        - ${{ python_min }}.*\n        - \"*\"\n"
        )
        assert cfs._normalize_grayskull_test_matrix(p) is False


class TestStripBeltAndSuspendersHost:
    def test_removes_wheel_setuptools_when_pep517_present(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "requirements:\n"
            "  host:\n"
            "    - python <4.0\n"
            "    - poetry-core\n"
            "    - wheel\n"
            "    - setuptools >=42.0.0\n"
            "    - pip\n"
            "  run:\n"
            "    - python\n"
        )
        assert cfs._strip_belt_and_suspenders_host(p) is True
        out = p.read_text()
        assert "- wheel" not in out
        assert "- setuptools" not in out
        assert "- poetry-core" in out
        assert "- pip" in out

    def test_keeps_setuptools_when_no_pep517_backend(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "requirements:\n"
            "  host:\n"
            "    - python\n"
            "    - setuptools >=42.0.0\n"
            "    - wheel\n"
            "    - pip\n"
            "  run:\n"
            "    - python\n"
        )
        # No PEP-517 backend declared → setuptools/wheel are the actual backend.
        assert cfs._strip_belt_and_suspenders_host(p) is False
        assert "- setuptools" in p.read_text()


class TestClampRunPythonFloor:
    def test_clamps_below_floor(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("requirements:\n  run:\n    - python >=3.9,<4.0\n")
        assert cfs._clamp_run_python_floor(p) is True
        assert "- python >=3.10" in p.read_text()

    def test_uses_python_min_template_when_declared(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "context:\n  python_min: \"3.10\"\n  version: \"1.0\"\n"
            "requirements:\n  run:\n    - python >=3.9,<4.0\n"
        )
        assert cfs._clamp_run_python_floor(p) is True
        assert "- python >=${{ python_min }}" in p.read_text()

    def test_leaves_floor_alone(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("requirements:\n  run:\n    - python >=3.10\n")
        assert cfs._clamp_run_python_floor(p) is False


class TestNormalizeSummary:
    def test_strips_trailing_version_tag(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo SDK (V1.0)\n")
        assert cfs._normalize_summary(p) is True
        assert p.read_text() == "about:\n  summary: Foo SDK\n"

    def test_strips_readme_comment(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo\n  # readme\n  license: MIT\n")
        assert cfs._normalize_summary(p) is True
        assert "# readme" not in p.read_text()
        assert "license: MIT" in p.read_text()

    def test_idempotent(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Clean\n  license: MIT\n")
        assert cfs._normalize_summary(p) is False
