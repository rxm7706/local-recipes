"""Unit tests for validate_recipe.py."""
from __future__ import annotations

import pytest


class TestValidateRecipe:
    def test_v1_noarch_passes(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-noarch")
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"
        assert rc == 0

    def test_v0_noarch_passes(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v0-noarch")
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"
        assert "meta.yaml (legacy format) detected" in out
        assert rc == 0

    def test_v1_compiled_passes_with_stdlib(self, script_runner, recipes_dir):
        """Recipe with compiler() and stdlib() should not be flagged."""
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-compiled")
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"

    def test_broken_recipe_fails(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-broken")
        )
        assert rc != 0, "broken recipe must fail validation"
        # Should report at least one of its known issues
        combined = (out + err).lower()
        assert "package" in combined or "checksum" in combined or "maintainer" in combined

    # ── Regression: fix #1 — conda-smithy lint replaces non-existent rattler-build lint ──

    def test_regression_fix_1_uses_conda_smithy_lint(
        self, script_runner, recipes_dir
    ):
        """validate_recipe.py used to invoke `rattler-build lint` which never
        existed as a subcommand. It now calls `conda-smithy recipe-lint`."""
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-noarch")
        )
        assert "conda-smithy lint:" in out, (
            "Expected validator to report a conda-smithy lint result; "
            "did it regress to the broken rattler-build lint path?\n"
            f"out={out}\nerr={err}"
        )
        # Negative: must NOT show the old "rattler-build lint: not available" string
        assert "rattler-build lint: not available" not in out

    # ── Regression: fix #2 — top-level `recipe:` is accepted for multi-output ──

    def test_regression_fix_2_multi_output_recipe_key(
        self, script_runner, recipes_dir
    ):
        """v1 multi-output recipes use top-level `recipe:` instead of
        `package:`. The validator used to reject this with `Missing package
        section`."""
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-multi-output")
        )
        assert "Missing package section" not in out, (
            "Validator regressed: rejected a multi-output recipe that uses "
            "top-level `recipe:` (rattler-build schema). "
            f"out={out}\nerr={err}"
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"

    # ── Direct module API (faster than subprocess) ──

    def test_run_external_lint_finds_conda_smithy(self, load_module):
        mod = load_module("validate_recipe.py")
        assert hasattr(mod, "run_external_lint")
        # Function must be the new name from fix #1
        assert not hasattr(mod, "run_rattler_lint"), (
            "validate_recipe.py still exposes the old `run_rattler_lint` "
            "function — fix #1 should have renamed it to `run_external_lint`."
        )

    def test_validate_recipe_yaml_accepts_recipe_key(self, load_module, copy_recipe):
        mod = load_module("validate_recipe.py")
        recipe_dir = copy_recipe("v1-multi-output")
        result = mod.validate_recipe_yaml(recipe_dir / "recipe.yaml")
        # The function returns a ValidationResult NamedTuple
        assert "Missing package or recipe section" not in result.errors
        assert "Missing package section" not in result.errors
