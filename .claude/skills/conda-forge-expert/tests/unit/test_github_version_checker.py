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


class TestExtractGithubRepo:
    """v8.90.6 — the detector must read the v1 ``about:`` field names (G2), not only v0 ``home``."""

    _HEAD = (
        "schema_version: 1\n"
        'context:\n  version: "2.1.0"\n'
        "package:\n  name: demo\n  version: ${{ version }}\n"
        "source:\n  url: {source_url}\n"
        "  sha256: " + "0" * 64 + "\n"
        "build:\n  number: 0\n  noarch: generic\n"
        "about:\n  license: MIT\n  summary: x\n{about_extra}"
    )

    def _extract(self, load_module, tmp_path, *, source_url: str, about_extra: str):
        gvc = load_module("github_version_checker.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(self._HEAD.format(source_url=source_url, about_extra=about_extra), encoding="utf-8")
        return gvc.extract_github_repo(recipe)

    def test_npm_source_with_v1_repository_is_detected(self, load_module, tmp_path):
        # The live miss (2026-09-25): recipes/bmad-module-skill-forge — npm tarball source,
        # GitHub URLs only under v1 about.homepage / about.repository → "No GitHub URL detected".
        found = self._extract(
            load_module, tmp_path,
            source_url="https://registry.npmjs.org/demo/-/demo-${{ version }}.tgz",
            about_extra=(
                "  homepage: https://demo.example.org/\n"
                "  repository: https://github.com/acme/demo-repo\n"
            ),
        )
        assert found == ("acme", "demo-repo")

    def test_v1_homepage_alone_is_detected(self, load_module, tmp_path):
        found = self._extract(
            load_module, tmp_path,
            source_url="https://pypi.org/packages/source/d/demo/demo-${{ version }}.tar.gz",
            about_extra="  homepage: https://github.com/acme/demo.git\n",
        )
        assert found == ("acme", "demo")

    def test_v0_home_still_detected_and_source_url_wins(self, load_module, tmp_path):
        found = self._extract(
            load_module, tmp_path,
            source_url="https://github.com/acme/from-source/archive/refs/tags/v${{ version }}.tar.gz",
            about_extra="  home: https://github.com/other/from-home\n",
        )
        assert found == ("acme", "from-source")
        found = self._extract(
            load_module, tmp_path,
            source_url="https://pypi.org/packages/source/d/demo/demo-${{ version }}.tar.gz",
            about_extra="  home: https://github.com/other/from-home\n",
        )
        assert found == ("other", "from-home")

    def test_no_github_url_anywhere_returns_none(self, load_module, tmp_path):
        found = self._extract(
            load_module, tmp_path,
            source_url="https://registry.npmjs.org/demo/-/demo-${{ version }}.tgz",
            about_extra="  homepage: https://demo.example.org/\n  repository: https://gitlab.com/acme/demo\n",
        )
        assert found is None
