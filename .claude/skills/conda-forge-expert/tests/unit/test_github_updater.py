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


class TestHeadModeBuildNumber:
    """G113 — a HEAD advance never changes context.version, so it must bump build.number."""

    _RECIPE = (
        'context:\n  version: "1.0.0.dev0"\n'
        "  commit: 088a427df8b0f7065f5270104933064c2627d63a\n\n"
        "package:\n  name: demo\n  version: ${{ version }}\n\n"
        "source:\n  url: https://github.com/o/r/archive/${{ commit }}.tar.gz\n"
        "  sha256: 0000000000000000000000000000000000000000000000000000000000000000\n\n"
        "build:\n{build_body}  noarch: generic\n"
    )

    @staticmethod
    def _head(_owner: str, _repo: str) -> dict[str, str]:
        return {"sha": "81fe19ede7ad5c40191267fe455248eed0a06f97", "branch": "main"}

    def _actions(self, load_module, monkeypatch, tmp_path, build_body: str) -> dict:
        gu = load_module("github_updater.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(self._RECIPE.format(build_body=build_body), encoding="utf-8")
        monkeypatch.setattr(gu, "_fetch_default_branch_head", self._head)
        result = gu.update_recipe_head(recipe, github_repo="o/r", dry_run=True)
        assert result["success"] is True and result["updated"] is True, result
        return {a["path"]: a for a in result["actions"]}

    def test_head_advance_increments_existing_build_number(self, load_module, monkeypatch, tmp_path):
        actions = self._actions(load_module, monkeypatch, tmp_path, "  number: 1\n")
        assert actions["build.number"]["value"] == 2
        assert "context.version" not in actions  # HEAD mode never invents a version

    def test_head_advance_from_absent_build_number_yields_one(self, load_module, monkeypatch, tmp_path):
        actions = self._actions(load_module, monkeypatch, tmp_path, "")
        assert actions["build.number"]["value"] == 1
