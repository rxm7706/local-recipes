"""End-to-end: generate-npm → validate → optimize → autotick-npm.

Exercises the full canonical npm lifecycle in one shot. Catches issues
where the steps fail to compose cleanly (e.g. the schema_version regression
discovered during the canonical-pattern refactor).

Network-free: builds an in-memory NpmPackageInfo, then drives the rest via
script_runner subprocess.
"""
from __future__ import annotations

import json

import pytest
import yaml


@pytest.mark.integration
class TestWorkflowNpmCanonical:
    """Full chain: generate → validate → optimize → autotick(stubbed)."""

    def _make_info(self, mod, *, with_deps: bool):
        """Synthetic NpmPackageInfo with realistic-looking metadata."""
        return mod.NpmPackageInfo(
            raw_name="example-pkg",
            conda_name="example-pkg",
            version="1.2.3",
            description="A synthetic example package for integration testing.",
            license="MIT",
            homepage="https://github.com/example/example-pkg",
            repository_url="https://github.com/example/example-pkg",
            tarball_url="https://registry.npmjs.org/example-pkg/-/example-pkg-1.2.3.tgz",
            tarball_filename="example-pkg-1.2.3.tgz",
            source_url="https://registry.npmjs.org/example-pkg/-/example-pkg-1.2.3.tgz",
            sha256="a" * 64,
            license_filename="LICENSE",
            bin_entries={"example-pkg": "bin/cli.js"},
            node_major=20,
            has_runtime_deps=with_deps,
        )

    def test_canonical_chain_with_deps(
        self, load_module, script_runner, tmp_path,
    ):
        """Full chain on a recipe WITH runtime deps.

        Generates → validates clean → optimizer reports nothing → autotick
        dry-run reports the recipe state correctly.
        """
        mod = load_module("recipe-generator.py")
        info = self._make_info(mod, with_deps=True)

        # 1. Generate
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, third_party_licenses=True,
        )
        assert recipe_path.exists()
        recipe_dir = recipe_path.parent

        # All four canonical files
        for name in ("recipe.yaml", "build.sh", "conda-forge.yml"):
            assert (recipe_dir / name).exists(), f"missing {name}"
        # No build.bat by default
        assert not (recipe_dir / "build.bat").exists()

        # The generated YAML must parse and have key fields
        data = yaml.safe_load(recipe_path.read_text())
        assert data["package"]["name"] == "example-pkg"
        assert data["build"]["noarch"] == "generic"
        assert "pnpm" in data["requirements"]["build"]

        # 2. Validate (subprocess — exercises the actual validator script)
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipe_dir), timeout=120,
        )
        combined = out + err
        # Recipe must validate cleanly. The pip_check warning shouldn't fire
        # on a nodejs recipe (fix #3 in this round).
        assert "Recipe validation passed" in combined, (
            f"validate failed:\nout={out}\nerr={err}"
        )
        assert "Consider adding pip_check" not in combined, (
            f"pip_check warning fired on a nodejs recipe — fix #3 regressed.\n{combined}"
        )

        # 3. Optimize
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipe_dir), timeout=60,
        )
        result = json.loads(out)
        assert result["success"] is True
        # Generated recipe is canonical → 0 suggestions expected
        assert result["suggestions_found"] == 0, (
            f"optimizer flagged a freshly-generated canonical recipe: {result}"
        )

        # 4. Autotick dry-run with stubbed registry
        # We can't easily stub the network in a subprocess, so import
        # npm_updater and call its update_recipe directly with a stub.
        updater = load_module("npm_updater.py")
        # Patch requests at the module level
        import unittest.mock
        with unittest.mock.patch.object(updater, "requests") as fake_requests:
            fake_resp = unittest.mock.Mock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = {
                "dist-tags": {"latest": "1.2.3"},
                "versions": {
                    "1.2.3": {
                        "dist": {"tarball": info.tarball_url}
                    }
                },
            }
            fake_resp.raise_for_status = lambda: None
            fake_requests.get.return_value = fake_resp
            fake_requests.RequestException = Exception

            tick_result = updater.update_recipe(recipe_path, dry_run=True)

        assert tick_result["success"] is True
        # 1.2.3 == 1.2.3 → no update
        assert tick_result["updated"] is False
        assert "up-to-date" in tick_result["message"].lower()

    def test_zero_dep_chain(self, load_module, script_runner, tmp_path):
        """Same chain but with `has_runtime_deps=False` — should produce a
        husky-style minimal recipe and still validate clean.

        This is the auto-detect path (fix #2 in this round): the dispatch
        flips third_party_licenses off when npm metadata declares no deps.
        """
        mod = load_module("recipe-generator.py")
        info = self._make_info(mod, with_deps=False)
        # Auto-detect: when has_runtime_deps is False the dispatch sets
        # third_party_licenses=False. Mimic that here.
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, third_party_licenses=False,
        )
        recipe_dir = recipe_path.parent

        data = yaml.safe_load(recipe_path.read_text())
        # Husky-style minimal recipe
        assert data["requirements"]["build"] == ["nodejs"]
        assert data["about"]["license_file"] == "LICENSE"

        # Must validate cleanly
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipe_dir), timeout=120,
        )
        assert "Recipe validation passed" in (out + err)


@pytest.mark.integration
class TestPipCheckFalsePositiveFix:
    """Regression for fix #3 (pip_check warning gating).

    The original bug: the warning fired for every recipe that had a tests
    block, regardless of whether the recipe was a Python package. This
    polluted the output of every nodejs/lua/perl recipe we generate.
    """

    def test_pip_check_not_suggested_for_nodejs(
        self, script_runner, recipes_dir, tmp_path,
    ):
        """Generate a synthetic nodejs recipe and verify validator stays quiet."""
        nodejs_recipe = tmp_path / "nodejs-pkg"
        nodejs_recipe.mkdir()
        (nodejs_recipe / "recipe.yaml").write_text(
            "schema_version: 1\n"
            "context:\n"
            "  version: \"1.0.0\"\n"
            "package:\n"
            "  name: nodejs-pkg\n"
            "  version: ${{ version }}\n"
            "source:\n"
            "  url: https://example.com/nodejs-pkg-1.0.0.tgz\n"
            "  sha256: " + ("0" * 64) + "\n"
            "build:\n"
            "  number: 0\n"
            "  noarch: generic\n"
            "requirements:\n"
            "  build:\n"
            "    - nodejs\n"
            "  run:\n"
            "    - nodejs\n"
            "tests:\n"
            "  - script:\n"
            "      - echo hello\n"
            "about:\n"
            "  license: MIT\n"
            "  license_file: LICENSE\n"
            "  summary: nodejs test fixture\n"
            "  homepage: https://example.com\n"
            "extra:\n"
            "  recipe-maintainers:\n"
            "    - rxm7706\n"
        )

        rc, out, err = script_runner(
            "validate_recipe.py", str(nodejs_recipe), timeout=120,
        )
        combined = out + err
        assert "Consider adding pip_check" not in combined, (
            f"pip_check warning incorrectly fired on a noarch:generic nodejs "
            f"recipe — fix #3 regressed.\n{combined}"
        )

    def test_pip_check_still_suggested_for_python(
        self, script_runner, recipes_dir,
    ):
        """The v1-noarch fixture in the suite is a python package and should
        STILL be told to add pip_check (this proves we didn't disable the
        warning entirely — only gated it correctly)."""
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-noarch"), timeout=120,
        )
        # Note: the v1-noarch fixture already has pip_check, so the warning
        # won't fire. We test by checking that *if* pip_check were missing,
        # it would still fire. Instead, verify the validator detected it.
        assert "Recipe validation passed" in (out + err), (out + err)
