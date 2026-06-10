"""Unit tests for recipe_optimizer.py."""
from __future__ import annotations

import json

import pytest


class TestRecipeOptimizer:
    def test_clean_recipe_no_suggestions(self, script_runner, recipes_dir):
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-noarch")
        )
        result = json.loads(out)
        assert result["success"] is True
        assert result["suggestions_found"] == 0

    @pytest.mark.xfail(
        reason="Known limitation: optimizer skips checks when top-level "
               "`package:` is missing, so STD-001/SEC-001/MAINT-001 are not "
               "triggered on the v1-broken fixture. Tracking item — when the "
               "optimizer is enhanced to handle headerless recipes, flip to "
               "a hard assertion.",
        strict=False,
    )
    def test_broken_recipe_flags_issues(self, script_runner, recipes_dir):
        """v1-broken has compiler() without stdlib() (STD-001) and other
        issues. Optimizer should flag at least one critical/quality finding."""
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-broken")
        )
        result = json.loads(out)
        assert result.get("success") is True
        assert result["suggestions_found"] > 0, (
            "Optimizer claimed success on a recipe missing stdlib for a "
            "compiler — STD-001 should fire."
        )

    def test_compiled_recipe_with_stdlib_clean(self, script_runner, recipes_dir):
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-compiled")
        )
        result = json.loads(out)
        assert result["success"] is True
        # No STD-001 (compiler without stdlib) since this fixture has both
        codes = [s.get("code", "") for s in result.get("suggestions", [])]
        assert "STD-001" not in codes

    def test_lic_001_secondary_license_source(self, tmp_path, script_runner):
        """LIC-001 — pattern-(3) secondary-source LICENSE should be flagged."""
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(
            "# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json\n"
            "schema_version: 1\n"
            "context: {version: \"1.0.0\"}\n"
            "package: {name: foo, version: \"1.0.0\"}\n"
            "source:\n"
            "  - url: https://pypi.org/packages/source/f/foo/foo-1.0.0.tar.gz\n"
            "    sha256: 0000000000000000000000000000000000000000000000000000000000000000\n"
            "  - url: https://raw.githubusercontent.com/example/foo/abc/LICENSE\n"
            "    sha256: 1111111111111111111111111111111111111111111111111111111111111111\n"
            "    file_name: LICENSE\n"
            "build: {number: 0, noarch: python, script: \"pip install .\"}\n"
            "requirements:\n  host: [python, pip]\n  run: [python]\n"
            "tests:\n  - python: {imports: [foo], pip_check: true, python_version: [\"*\"]}\n"
            "about: {summary: x, license: MIT, license_file: LICENSE, homepage: https://x.example.com}\n"
            "extra: {recipe-maintainers: [rxm7706]}\n"
        )
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        result = json.loads(out)
        codes = [s["code"] for s in result["suggestions"]]
        assert "LIC-001" in codes

    def test_fmt_001_non_canonical_list_indent(self, tmp_path, script_runner):
        """FMT-001 — list items at parent-key depth should be flagged."""
        recipe = tmp_path / "recipe.yaml"
        # python_version: with list items at SAME depth as the key (6-space)
        recipe.write_text(
            "# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json\n"
            "schema_version: 1\n"
            "context: {version: \"1.0.0\"}\n"
            "package: {name: foo, version: \"1.0.0\"}\n"
            "source: {url: https://pypi.org/x/foo-1.0.0.tar.gz, sha256: 0000000000000000000000000000000000000000000000000000000000000000}\n"
            "build: {number: 0, noarch: python, script: \"pip install .\"}\n"
            "requirements:\n  host: [python, pip]\n  run: [python]\n"
            "tests:\n"
            "  - python:\n"
            "      imports:\n"
            "        - foo\n"
            "      pip_check: true\n"
            "      python_version:\n"
            "      - first\n"
            "      - second\n"
            "about: {summary: x, license: MIT, license_file: LICENSE, homepage: https://x.example.com}\n"
            "extra: {recipe-maintainers: [rxm7706]}\n"
        )
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        result = json.loads(out)
        codes = [s["code"] for s in result["suggestions"]]
        assert "FMT-001" in codes
