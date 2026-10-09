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

    def test_v1_go_nocgo_passes_without_stdlib(self, script_runner, recipes_dir):
        """CFE retro G101: compiler("go-nocgo") does not link the C stdlib,
        so a recipe using only that compiler must not be flagged for a
        missing stdlib() -- mirrors recipe_optimizer.py's STD-001 exemption."""
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-go-nocgo")
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"
        assert "stdlib" not in out.lower(), f"out={out}"
        assert rc == 0

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


class TestValidateRecipeBadKeys:
    """Story 22.2 — non-string mapping keys and Python object repr leaks."""

    def test_sentinel_key_nested_in_tests(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-sentinel-key")
        )
        combined = out + err
        assert rc != 0
        assert "tests[1]" in combined
        assert "SentinelType" in combined or "object repr" in combined

    def test_sentinel_key_under_source(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-sentinel-key-source")
        )
        combined = out + err
        assert rc != 0
        assert "source" in combined

    def test_nonstring_int_key_under_extra(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-nonstring-key")
        )
        combined = out + err
        assert rc != 0
        assert "Non-string mapping key 1" in combined
        assert "extra" in combined

    def test_repr_as_whole_value_about_summary(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-repr-value")
        )
        combined = out + err
        assert rc != 0
        assert "about.summary" in combined

    def test_repr_in_prose_description_not_flagged(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-repr-in-prose")
        )
        combined = out + err
        assert "Python object repr" not in combined

    def test_clean_go_nocgo_fixture_unchanged(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "validate_recipe.py", str(recipes_dir / "v1-go-nocgo")
        )
        assert "Recipe validation passed" in out, f"out={out}\nerr={err}"
        assert rc == 0

    def test_sentinel_fixture_red_without_tree_walk(self, load_module, copy_recipe, monkeypatch):
        """Mutation guard: disabling the walk must drop the sentinel-key failure."""
        mod = load_module("validate_recipe.py")
        recipe = copy_recipe("v1-sentinel-key") / "recipe.yaml"
        with_walk = mod.validate_recipe_yaml(recipe)
        assert not with_walk.passed
        assert any("tests[1]" in e for e in with_walk.errors)

        monkeypatch.setattr(mod, "_find_bad_keys", lambda tree, path="": [])
        without_walk = mod.validate_recipe_yaml(recipe)
        assert not any("tests[1]" in e for e in without_walk.errors)

    def test_top_level_sentinel_key(self, load_module, tmp_path):
        mod = load_module("validate_recipe.py")
        path = tmp_path / "recipe.yaml"
        path.write_text(
            "schema_version: 1\n"
            '"<foo.Bar object at 0x1>": 1\n'
            "package:\n  name: x\n  version: \"1\"\n"
            "source:\n  url: https://example.com/x.tar.gz\n"
            "  sha256: 0000000000000000000000000000000000000000000000000000000000000000\n",
            encoding="utf-8",
        )
        result = mod.validate_recipe_yaml(path)
        assert any("root" in e for e in result.errors)

    def test_find_bad_keys_bool_and_date_keys(self, load_module):
        mod = load_module("validate_recipe.py")
        tree = {True: "x", "nested": {None: 1}}
        errors = mod._find_bad_keys(tree)
        assert any("Non-string mapping key True" in e for e in errors)
        assert any("Non-string mapping key None" in e for e in errors)
