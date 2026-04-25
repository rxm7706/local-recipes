"""Unit tests for npm_updater.py."""
from __future__ import annotations

import json

import pytest


HUSKY_RECIPE = """\
context:
  version: "9.0.0"

package:
  name: husky
  version: ${{ version }}

source:
  url: https://registry.npmjs.org/husky/-/husky-9.0.0.tgz
  sha256: 0000000000000000000000000000000000000000000000000000000000000000

build:
  number: 0
  noarch: generic

requirements:
  build:
    - nodejs
  run:
    - nodejs

about:
  license: MIT
  license_file: LICENSE
  summary: Modern native Git hooks
"""


SCOPED_RECIPE = """\
context:
  version: "1.0.0"

package:
  name: codex
  version: ${{ version }}

source:
  url: https://registry.npmjs.org/@openai/codex/-/codex-1.0.0.tgz
  sha256: 0000000000000000000000000000000000000000000000000000000000000000

build:
  number: 0
  noarch: generic

requirements:
  build:
    - nodejs
  run:
    - nodejs

about:
  license: Apache-2.0
  license_file: LICENSE
"""


GITHUB_SOURCE_RECIPE = """\
context:
  version: "1.2.3"

package:
  name: openspec
  version: ${{ version }}

source:
  url: https://github.com/Fission-AI/OpenSpec/archive/refs/tags/v1.2.3.tar.gz
  sha256: 0000000000000000000000000000000000000000000000000000000000000000

build:
  number: 0
  noarch: generic

requirements:
  build:
    - nodejs
  run:
    - nodejs

about:
  license: MIT
  license_file: LICENSE
"""


class TestNpmUpdater:
    def test_help(self, script_runner):
        rc, out, _ = script_runner("npm_updater.py", "--help")
        assert rc == 0
        assert "--dry-run" in out
        assert "--package" in out
        assert "--pre" in out

    def test_extract_npm_name_bare(self, load_module):
        mod = load_module("npm_updater.py")
        recipe = {"source": {"url": "https://registry.npmjs.org/husky/-/husky-9.0.0.tgz"}}
        assert mod._extract_npm_name(recipe) == "husky"

    def test_extract_npm_name_scoped(self, load_module):
        mod = load_module("npm_updater.py")
        recipe = {
            "source": {
                "url": "https://registry.npmjs.org/@openai/codex/-/codex-1.0.0.tgz"
            }
        }
        assert mod._extract_npm_name(recipe) == "@openai/codex"

    def test_extract_npm_name_github_source_returns_none(self, load_module):
        """Recipes with GitHub source URLs aren't npm-managed."""
        mod = load_module("npm_updater.py")
        recipe = {
            "source": {
                "url": "https://github.com/x/y/archive/refs/tags/v1.0.0.tar.gz"
            }
        }
        assert mod._extract_npm_name(recipe) is None

    def test_extract_npm_name_list_source(self, load_module):
        """Multi-source recipes (source: list-of-dicts) are also handled."""
        mod = load_module("npm_updater.py")
        recipe = {
            "source": [
                {"url": "https://example.com/extra.patch"},
                {"url": "https://registry.npmjs.org/husky/-/husky-9.0.0.tgz"},
            ]
        }
        assert mod._extract_npm_name(recipe) == "husky"

    def test_is_prerelease(self, load_module):
        mod = load_module("npm_updater.py")
        assert mod._is_prerelease("1.0.0-beta.1") is True
        assert mod._is_prerelease("1.0.0-rc.0") is True
        assert mod._is_prerelease("0.0.1-next-2024") is True
        assert mod._is_prerelease("1.0.0") is False
        assert mod._is_prerelease("9.1.7") is False

    def test_is_newer(self, load_module):
        mod = load_module("npm_updater.py")
        assert mod._is_newer("9.1.7", "9.0.0") is True
        assert mod._is_newer("9.0.0", "9.0.0") is False
        assert mod._is_newer("8.9.9", "9.0.0") is False

    def test_dry_run_already_up_to_date(
        self, load_module, tmp_path, stub_responses,
    ):
        """If npm reports the same version that's in the recipe, nothing
        is updated."""
        mod = load_module("npm_updater.py")
        recipe_dir = tmp_path / "husky"
        recipe_dir.mkdir()
        recipe_file = recipe_dir / "recipe.yaml"
        recipe_file.write_text(HUSKY_RECIPE)

        stub_responses.register(
            "GET",
            "https://registry.npmjs.org/husky",
            status=200,
            body={
                "dist-tags": {"latest": "9.0.0"},
                "versions": {
                    "9.0.0": {"dist": {"tarball": "https://registry.npmjs.org/husky/-/husky-9.0.0.tgz"}}
                },
            },
        )

        result = mod.update_recipe(recipe_file, dry_run=True)
        assert result["success"] is True
        assert result["updated"] is False
        assert "up-to-date" in result["message"].lower()

    def test_dry_run_new_version_emits_action_plan(
        self, load_module, tmp_path, stub_responses,
    ):
        """Newer registry version → dry-run returns the action plan without
        writing the file."""
        mod = load_module("npm_updater.py")
        recipe_dir = tmp_path / "husky"
        recipe_dir.mkdir()
        recipe_file = recipe_dir / "recipe.yaml"
        original = HUSKY_RECIPE
        recipe_file.write_text(original)

        stub_responses.register(
            "GET",
            "https://registry.npmjs.org/husky",
            status=200,
            body={
                "dist-tags": {"latest": "9.1.7"},
                "versions": {
                    "9.1.7": {"dist": {"tarball": "https://registry.npmjs.org/husky/-/husky-9.1.7.tgz"}}
                },
            },
        )

        result = mod.update_recipe(recipe_file, dry_run=True)
        assert result["success"] is True
        assert result["updated"] is True
        assert result["dry_run"] is True
        assert result["latest_version"] == "9.1.7"
        # Action plan must include version + build.number reset + hash recompute
        actions = {a["action"] for a in result["actions"]}
        assert actions == {"update", "calculate_hash"}
        # File must not have been modified
        assert recipe_file.read_text() == original

    def test_dry_run_scoped_package(
        self, load_module, tmp_path, stub_responses,
    ):
        """Scoped npm names (@scope/name) round-trip correctly."""
        mod = load_module("npm_updater.py")
        recipe_dir = tmp_path / "codex"
        recipe_dir.mkdir()
        recipe_file = recipe_dir / "recipe.yaml"
        recipe_file.write_text(SCOPED_RECIPE)

        stub_responses.register(
            "GET",
            "https://registry.npmjs.org/@openai/codex",
            status=200,
            body={
                "dist-tags": {"latest": "1.2.3"},
                "versions": {
                    "1.2.3": {
                        "dist": {"tarball": "https://registry.npmjs.org/@openai/codex/-/codex-1.2.3.tgz"}
                    }
                },
            },
        )

        result = mod.update_recipe(recipe_file, dry_run=True)
        assert result["success"] is True
        assert result["updated"] is True
        assert result["npm_package"] == "@openai/codex"

    def test_github_source_recipe_is_rejected(self, load_module, tmp_path):
        """Recipes with a GitHub source should fail with a clear error
        (use github_updater.py instead)."""
        mod = load_module("npm_updater.py")
        recipe_dir = tmp_path / "openspec"
        recipe_dir.mkdir()
        recipe_file = recipe_dir / "recipe.yaml"
        recipe_file.write_text(GITHUB_SOURCE_RECIPE)

        result = mod.update_recipe(recipe_file, dry_run=True)
        assert result["success"] is False
        assert "github" in result["error"].lower() or "npm registry url" in result["error"].lower()

    def test_pre_release_skipped_by_default(
        self, load_module, tmp_path, stub_responses,
    ):
        """Latest tag pointing at a pre-release should be ignored unless --pre."""
        mod = load_module("npm_updater.py")
        recipe_dir = tmp_path / "husky"
        recipe_dir.mkdir()
        recipe_file = recipe_dir / "recipe.yaml"
        recipe_file.write_text(HUSKY_RECIPE)

        stub_responses.register(
            "GET",
            "https://registry.npmjs.org/husky",
            status=200,
            body={
                "dist-tags": {"latest": "10.0.0-beta.1"},
                "versions": {
                    "9.0.0": {"dist": {"tarball": "https://registry.npmjs.org/husky/-/husky-9.0.0.tgz"}},
                    "10.0.0-beta.1": {"dist": {"tarball": "..."}},
                },
            },
        )

        result = mod.update_recipe(recipe_file, dry_run=True)
        # Stable fallback (9.0.0) matches the current version → no update
        assert result["success"] is True
        assert result["updated"] is False

    def test_update_all_recipes_categorises_results(
        self, load_module, tmp_path, stub_responses,
    ):
        """Bulk mode walks recipes/, classifies each into up_to_date /
        needs_update / not_npm / errors."""
        mod = load_module("npm_updater.py")
        # Build a tmp recipes/ tree with three recipes:
        # - husky (npm-source, up to date)
        # - codex (npm-source, needs update)
        # - openspec (github source — should be classified as not_npm)
        for name, body in (
            ("husky", HUSKY_RECIPE),
            ("codex", SCOPED_RECIPE.replace('"1.0.0"', '"1.0.0"')),
            ("openspec", GITHUB_SOURCE_RECIPE),
        ):
            (tmp_path / name).mkdir()
            (tmp_path / name / "recipe.yaml").write_text(body)

        # Stub the registry: husky stays at 9.0.0, codex bumps to 1.2.3
        stub_responses.register(
            "GET", "https://registry.npmjs.org/husky",
            status=200,
            body={
                "dist-tags": {"latest": "9.0.0"},
                "versions": {"9.0.0": {"dist": {"tarball": "x"}}},
            },
        )
        stub_responses.register(
            "GET", "https://registry.npmjs.org/@openai/codex",
            status=200,
            body={
                "dist-tags": {"latest": "1.2.3"},
                "versions": {"1.2.3": {"dist": {"tarball": "y"}}},
            },
        )

        result = mod.update_all_recipes(tmp_path)
        assert result["success"] is True
        assert result["scanned"] == 3
        assert result["summary"]["up_to_date"] == 1
        assert result["summary"]["needs_update"] == 1
        assert result["summary"]["not_npm"] == 1
        assert result["summary"]["errors"] == 0
        # Spot-check details
        details = result["details"]
        assert details["up_to_date"][0]["recipe"] == "husky"
        assert details["needs_update"][0]["recipe"] == "codex"
        assert details["needs_update"][0]["latest_version"] == "1.2.3"
        assert details["not_npm"][0]["recipe"] == "openspec"

    def test_update_all_recipes_rejects_non_directory(self, load_module, tmp_path):
        mod = load_module("npm_updater.py")
        # Pass a non-existent directory
        result = mod.update_all_recipes(tmp_path / "nonexistent")
        assert result["success"] is False
        assert "Not a directory" in result["error"]

    def test_help_includes_all_flag(self, script_runner):
        rc, out, _ = script_runner("npm_updater.py", "--help")
        assert rc == 0
        assert "--all" in out

    @pytest.mark.network
    def test_live_husky(self, script_runner, tmp_path):
        """Live: actually hit the npm registry for husky in dry-run mode."""
        recipe_dir = tmp_path / "husky"
        recipe_dir.mkdir()
        (recipe_dir / "recipe.yaml").write_text(HUSKY_RECIPE)

        rc, out, err = script_runner(
            "npm_updater.py", "--dry-run", str(recipe_dir),
            timeout=60,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        result = json.loads(out)
        assert result["success"] is True
        # Either it's up to date or there's a newer version — both are valid
        assert "current_version" in result
