"""Unit tests for github_version_checker.py."""
from __future__ import annotations

import pytest


class TestGithubVersionChecker:
    def test_help(self, script_runner):
        rc, out, _ = script_runner("github_version_checker.py", "--help")
        assert rc == 0

    @pytest.mark.network
    def test_live_against_actionlint(self, script_runner, tmp_path):
        recipe_dir = tmp_path / "actionlint"
        recipe_dir.mkdir()
        (recipe_dir / "recipe.yaml").write_text(
            "schema_version: 1\n"
            "context:\n  version: 1.7.7\n"
            "package:\n  name: actionlint\n  version: ${{ version }}\n"
            "source:\n  url: https://github.com/rhysd/actionlint/archive/refs/tags/v${{ version }}.tar.gz\n"
            "  sha256: " + "0" * 64 + "\n"
            "build:\n  number: 0\n"
            "about:\n  homepage: https://github.com/rhysd/actionlint\n"
            "  license: MIT\n  summary: x\n"
            "extra:\n  recipe-maintainers:\n    - rxm7706\n"
        )
        rc, out, _ = script_runner(
            "github_version_checker.py", str(recipe_dir),
            timeout=60,
        )
        # Either "Update available" or "no update" / "current"
        assert "actionlint" in out.lower() or "rhysd" in out.lower()
