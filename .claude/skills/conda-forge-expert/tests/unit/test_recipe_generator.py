"""Unit tests for recipe-generator.py (hyphenated → script_runner only)."""
from __future__ import annotations

import pytest

import yaml


class TestRecipeGenerator:
    def test_smoke_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "--help")
        assert rc == 0
        assert "pypi" in out.lower()
        assert "template" in out.lower()
        assert "github" in out.lower()

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
