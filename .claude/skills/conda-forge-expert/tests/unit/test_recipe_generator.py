"""Unit tests for recipe-generator.py (hyphenated → script_runner only)."""
from __future__ import annotations

import pytest

import yaml


class TestRecipeGenerator:
    def test_smoke_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "--help")
        assert rc == 0
        for ecosystem in ("pypi", "template", "github", "cran", "cpan", "luarocks"):
            assert ecosystem in out.lower(), f"missing {ecosystem} in --help"

    def test_cran_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "cran", "--help")
        assert rc == 0
        assert "cran" in out.lower()
        assert "--universe" in out or "-u" in out

    def test_cpan_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "cpan", "--help")
        assert rc == 0
        assert "cpan" in out.lower()
        assert "--version" in out

    def test_luarocks_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "luarocks", "--help")
        assert rc == 0
        assert "luarocks" in out.lower() or "rock" in out.lower()

    def test_template_python_noarch(self, script_runner, tmp_path):
        rc, out, err = script_runner(
            "recipe-generator.py",
            "template", "python-noarch",
            "--name", "smoke-test",
            "--version", "1.0.0",
            "--output", str(tmp_path),
        )
        assert rc == 0, f"out={out}\nerr={err}"
        recipe_file = tmp_path / "recipe.yaml"
        assert recipe_file.exists()
        data = yaml.safe_load(recipe_file.read_text())
        assert data is not None

    @pytest.mark.network
    def test_pypi_live(self, script_runner, tmp_path):
        """Generate a real recipe from PyPI (network)."""
        rc, out, err = script_runner(
            "recipe-generator.py",
            "pypi", "click",
            "--output", str(tmp_path),
            "--format", "v1",
            timeout=120,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        assert (tmp_path / "recipe.yaml").exists()

    @pytest.mark.network
    def test_github_live(self, script_runner, tmp_path):
        rc, out, err = script_runner(
            "recipe-generator.py",
            "github", "rhysd/actionlint",
            "--output", str(tmp_path),
            timeout=120,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        assert (tmp_path / "recipe.yaml").exists()

    @pytest.mark.network
    def test_cran_live(self, script_runner, tmp_path):
        """Live CRAN scaffolder. Picks a small fast package (`cli`)."""
        rc, out, err = script_runner(
            "recipe-generator.py",
            "cran", "cli",
            "--output", str(tmp_path),
            timeout=180,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        # rattler-build writes to <output>/r-<package>/recipe.yaml
        recipe = tmp_path / "r-cli" / "recipe.yaml"
        assert recipe.exists(), (
            f"Expected {recipe} to exist after CRAN scaffold."
        )
        # Sanity: the file is valid YAML with a package.name starting with r-
        content = yaml.safe_load(recipe.read_text())
        assert content["package"]["name"].startswith("r-")
