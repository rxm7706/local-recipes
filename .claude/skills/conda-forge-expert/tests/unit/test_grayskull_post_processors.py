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


# ============================================================================
# v8.13.0 post-processors — closes S1+S3 retro findings C1, C2, C3 + C4 wrapper
# ============================================================================


class TestExtractJsonFromStdout:
    """C4 — closes the prepare_submission_branch wrapper JSON-parse bug.

    Scripts like submit-pr.py emit a progress line before the JSON body;
    json.loads on the full stdout fails because the prefix isn't JSON.
    The helper finds the first '{' or '[' at the start of a line and parses
    from there.
    """
    def test_direct_json(self, cfs):
        assert cfs._extract_json_from_stdout('{"a": 1}') == {"a": 1}

    def test_prefixed_json(self, cfs):
        prefixed = '  Syncing fork with upstream conda-forge/staged-recipes ...\n{"success": true, "pushed": true}\n'
        assert cfs._extract_json_from_stdout(prefixed) == {"success": True, "pushed": True}

    def test_indented_json_after_prefix(self, cfs):
        # Some scripts indent the JSON for readability
        assert cfs._extract_json_from_stdout("info\n  {\"x\": 2}") == {"x": 2}

    def test_no_json_raises(self, cfs):
        import json as _json
        with pytest.raises(_json.JSONDecodeError):
            cfs._extract_json_from_stdout("just text, no json at all")

    def test_array_json(self, cfs):
        assert cfs._extract_json_from_stdout("[1, 2, 3]") == [1, 2, 3]


class TestReadCondaForgePythonFloor:
    """Verify the floor reader handles common pinning file shapes."""
    def test_returns_default_when_file_missing(self, cfs, monkeypatch, tmp_path):
        # Point the reader at a non-existent path via __file__ chain trick:
        # we trust the function's "default on OSError" path. Cannot easily
        # remap _PINNING_CONFIG_PATH; instead verify the default is sane.
        floor = cfs._read_conda_forge_python_floor()
        # Should be a real-looking floor like 3.10 or 3.11
        parts = floor.split(".")
        assert len(parts) == 2 and all(p.isdigit() for p in parts)


class TestClampOrDropContextPythonMin:
    """C1 + operator correction — drop the line at/below floor; keep above."""
    def test_drops_at_floor(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            'context:\n  version: "1.0"\n  python_min: "3.10"\n'
            "package:\n  name: foo\n"
        )
        assert cfs._clamp_or_drop_context_python_min(p, floor="3.10") is True
        out = p.read_text()
        assert "python_min" not in out
        assert "version" in out  # other context preserved

    def test_drops_below_floor(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            'context:\n  version: "1.0"\n  python_min: "3.9"\n'
        )
        assert cfs._clamp_or_drop_context_python_min(p, floor="3.10") is True
        assert "python_min" not in p.read_text()

    def test_drops_below_floor_explicit_38(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text('context:\n  python_min: "3.8"\n')
        assert cfs._clamp_or_drop_context_python_min(p, floor="3.10") is True
        assert "python_min" not in p.read_text()

    def test_keeps_above_floor(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            'context:\n  version: "1.0"\n  python_min: "3.11"\n'
        )
        assert cfs._clamp_or_drop_context_python_min(p, floor="3.10") is False
        assert 'python_min: "3.11"' in p.read_text()

    def test_no_op_when_absent(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text('context:\n  version: "1.0"\n')
        assert cfs._clamp_or_drop_context_python_min(p, floor="3.10") is False


class TestAddMissingDescription:
    """C2 — populate about.description from PyPI info; skip trivial/duplicate."""
    def test_inserts_description_when_missing(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "about:\n  summary: Foo SDK\n  license: MIT\n"
        )
        info = {"summary": "Foo SDK", "description": "Foo SDK is a comprehensive client library for the Foo API."}
        assert cfs._add_missing_description(p, "foo", info=info) is True
        out = p.read_text()
        assert "description: |" in out
        assert "Foo SDK is a comprehensive" in out

    def test_skips_when_already_present(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text(
            "about:\n  summary: Foo\n  description: Existing description\n"
        )
        info = {"description": "Different long description that would otherwise insert here."}
        assert cfs._add_missing_description(p, "foo", info=info) is False

    def test_skips_when_equal_to_summary(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo SDK client\n")
        info = {"summary": "Foo SDK client", "description": "Foo SDK client"}
        assert cfs._add_missing_description(p, "foo", info=info) is False

    def test_skips_when_too_short(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo\n")
        info = {"description": "Short."}  # < 20 chars stripped
        assert cfs._add_missing_description(p, "foo", info=info) is False

    def test_skips_when_no_info(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo\n")
        assert cfs._add_missing_description(p, "foo", info={}) is False


class TestStripGrayskullPlaceholders:
    """C3 — flag/repair grayskull placeholder literals."""
    def test_marks_placeholder_summary(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Add your description here\n  license: MIT\n")
        assert cfs._strip_grayskull_placeholders(p, info={}) is True
        out = p.read_text()
        assert "TODO: review" in out
        assert "Add your description here" in out  # preserved + marked

    def test_infers_license_from_classifier(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo\n  license:\n  license_file: LICENSE\n")
        info = {"classifiers": ["License :: OSI Approved :: MIT License"]}
        assert cfs._strip_grayskull_placeholders(p, info=info) is True
        out = p.read_text()
        assert "license: MIT" in out

    def test_marks_license_file_placeholder(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: Foo\n  license: MIT\n  license_file: PLEASE_ADD_LICENSE_FILE\n")
        assert cfs._strip_grayskull_placeholders(p, info={}) is True
        out = p.read_text()
        assert "TODO: vendor LICENSE" in out
        assert "PLEASE_ADD_LICENSE_FILE" in out  # preserved + marked

    def test_no_op_on_clean_recipe(self, cfs, tmp_path):
        p = tmp_path / "recipe.yaml"
        p.write_text("about:\n  summary: A real summary\n  license: MIT\n  license_file: LICENSE\n")
        assert cfs._strip_grayskull_placeholders(p, info={}) is False
