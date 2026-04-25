"""Unit tests for github_updater.py (GitHub autotick)."""
from __future__ import annotations

import pytest


class TestGithubUpdater:
    def test_help(self, script_runner):
        rc, out, _ = script_runner("github_updater.py", "--help")
        assert rc == 0
        assert "--dry-run" in out

    @pytest.mark.network
    def test_dry_run_live_against_actionlint(self, script_runner, tmp_path):
        """Live test against rhysd/actionlint. Flaky if rate-limited."""
        # Build a minimal fixture pointing at the real repo so the script
        # can auto-detect.
        recipe_dir = tmp_path / "actionlint"
        recipe_dir.mkdir()
        (recipe_dir / "recipe.yaml").write_text(
            "schema_version: 1\n"
            "context:\n"
            "  version: 1.7.7\n"
            "package:\n"
            "  name: actionlint\n"
            "  version: ${{ version }}\n"
            "source:\n"
            "  url: https://github.com/rhysd/actionlint/archive/refs/tags/v${{ version }}.tar.gz\n"
            "  sha256: " + "0" * 64 + "\n"
            "build:\n  number: 0\n"
            "about:\n  homepage: https://github.com/rhysd/actionlint\n"
            "  license: MIT\n  summary: x\n"
            "extra:\n  recipe-maintainers:\n    - rxm7706\n"
        )
        rc, out, err = script_runner(
            "github_updater.py", "--dry-run", str(recipe_dir),
            timeout=60,
        )
        # Should report either "would update" or "already current"
        combined = out + err
        assert "would update" in combined.lower() or "current" in combined.lower(), (
            f"out={out}\nerr={err}"
        )
