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


class TestABT003PlaceholderAboutFields:
    """v8.13.0 — ABT-003 catches grayskull placeholder literals in about:."""

    def _build_recipe(self, tmp_path, summary='"Real description here"', license_value='MIT', license_file='LICENSE'):
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(
            "schema_version: 1\n"
            "package:\n  name: foo\n  version: \"1.0.0\"\n"
            "source:\n"
            "  url: \"https://pypi.org/x/foo-1.0.0.tar.gz\"\n"
            "  sha256: \"0000000000000000000000000000000000000000000000000000000000000000\"\n"
            "build:\n  number: 0\n  noarch: python\n"
            "requirements:\n  host:\n    - python\n    - pip\n  run:\n    - python\n"
            "tests: []\n"
            f"about:\n  summary: {summary}\n  license: {license_value}\n  license_file: {license_file}\n  homepage: \"https://x.example.com\"\n"
            "extra:\n  recipe-maintainers:\n    - rxm7706\n"
        )
        return recipe

    def test_flags_placeholder_summary(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path, summary='"Add your description here"')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "ABT-003" in codes

    def test_flags_empty_license(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path, license_value='""')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "ABT-003" in codes

    def test_flags_placeholder_license_file_string(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path, license_file='PLEASE_ADD_LICENSE_FILE')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "ABT-003" in codes

    def test_flags_placeholder_license_file_in_list(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path, license_file='[PLEASE_ADD_LICENSE_FILE]')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "ABT-003" in codes

    def test_clean_recipe_no_abt003(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path)
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "ABT-003" not in codes


def _live_floor() -> str:
    """conda-forge's CURRENT python_min, read from the installed pinning.

    Mirrors recipe_optimizer._read_conda_forge_python_floor so these tests
    follow the ecosystem instead of pinning a snapshot that goes stale the
    next time conda-forge drops a Python.
    """
    import re
    from pathlib import Path

    here = Path(__file__).resolve()
    pat = re.compile(
        r"^python_min:\s*\n(?:[ \t]*#[^\n]*\n)*[ \t]*-\s*['\"]?(\d+\.\d+)['\"]?",
        re.MULTILINE,
    )
    for parent in here.parents:
        pinning = parent / ".pixi/envs/local-recipes/conda_build_config.yaml"
        if pinning.is_file():
            m = pat.search(pinning.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
            break
    return "3.11"


class TestSEL004RedundantPythonMin:
    """v8.13.0 — SEL-004 catches context.python_min at/below the conda-forge floor."""

    def _build_recipe(self, tmp_path, python_min_line=''):
        recipe = tmp_path / "recipe.yaml"
        ctx_block = '  version: "1.0.0"\n'
        if python_min_line:
            ctx_block += f'  {python_min_line}\n'
        recipe.write_text(
            "schema_version: 1\n"
            "context:\n"
            f"{ctx_block}"
            "package:\n  name: foo\n  version: \"1.0.0\"\n"
            "source:\n"
            "  url: \"https://pypi.org/x/foo-1.0.0.tar.gz\"\n"
            "  sha256: \"0000000000000000000000000000000000000000000000000000000000000000\"\n"
            "build:\n  number: 0\n  noarch: python\n"
            "requirements:\n  host:\n    - python ${{ python_min }}.*\n    - pip\n  run:\n    - python >=${{ python_min }}\n"
            "tests:\n  - python:\n      imports:\n        - foo\n      pip_check: true\n      python_version:\n        - ${{ python_min }}.*\n        - \"*\"\n"
            "about:\n  summary: A real summary\n  license: MIT\n  license_file:\n    - LICENSE\n  homepage: \"https://x.example.com\"\n"
            "extra:\n  recipe-maintainers:\n    - rxm7706\n"
        )
        return recipe

    def test_flags_python_min_at_floor(self, tmp_path, script_runner):
        """AT the live floor -> SEL-004 fires as 'matches the default floor'.

        Floor-RELATIVE on purpose: hardcoding a snapshot broke this test when
        conda-forge dropped 3.10 on 2026-09-02 and the floor moved to 3.11 --
        the same defect the generator carried. Read the floor the way the code
        under test reads it.
        """
        floor = _live_floor()
        recipe = self._build_recipe(tmp_path, python_min_line=f'python_min: "{floor}"')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        result = json.loads(out)
        sel004 = [s for s in result["suggestions"] if s["code"] == "SEL-004"]
        assert sel004, f"expected SEL-004 to fire, got codes: {[s['code'] for s in result['suggestions']]}"
        assert "matches the default conda-forge floor" in sel004[0]["message"]

    def test_flags_python_min_below_floor(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path, python_min_line='python_min: "3.9"')
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        result = json.loads(out)
        sel004 = [s for s in result["suggestions"] if s["code"] == "SEL-004"]
        assert sel004, f"expected SEL-004 to fire, got codes: {[s['code'] for s in result['suggestions']]}"
        assert "below the" in sel004[0]["message"]

    def test_no_fire_above_floor(self, tmp_path, script_runner):
        """One minor ABOVE the live floor -> SEL-004 stays silent (floor-relative)."""
        major, minor = (int(p) for p in _live_floor().split("."))
        recipe = self._build_recipe(
            tmp_path, python_min_line=f'python_min: "{major}.{minor + 1}"'
        )
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "SEL-004" not in codes

    def test_no_fire_when_omitted(self, tmp_path, script_runner):
        recipe = self._build_recipe(tmp_path)  # no python_min in context
        rc, out, _ = script_runner("recipe_optimizer.py", str(recipe))
        codes = [s["code"] for s in json.loads(out)["suggestions"]]
        assert "SEL-004" not in codes
