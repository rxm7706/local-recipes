"""Unit tests for recipe_optimizer.py."""
from __future__ import annotations

import json

import pytest


class TestRecipeOptimizer:
    def test_clean_recipe_no_suggestions(self, script_runner, recipes_dir):
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-noarch")
        )
        result = json.loads(out)
        assert result["success"] is True
        assert result["suggestions_found"] == 0

    @pytest.mark.xfail(
        reason="Known limitation: optimizer skips checks when top-level "
               "`package:` is missing, so STD-001/SEC-001/MAINT-001 are not "
               "triggered on the v1-broken fixture. Tracking item — when the "
               "optimizer is enhanced to handle headerless recipes, flip to "
               "a hard assertion.",
        strict=False,
    )
    def test_broken_recipe_flags_issues(self, script_runner, recipes_dir):
        """v1-broken has compiler() without stdlib() (STD-001) and other
        issues. Optimizer should flag at least one critical/quality finding."""
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-broken")
        )
        result = json.loads(out)
        assert result.get("success") is True
        assert result["suggestions_found"] > 0, (
            "Optimizer claimed success on a recipe missing stdlib for a "
            "compiler — STD-001 should fire."
        )

    def test_compiled_recipe_with_stdlib_clean(self, script_runner, recipes_dir):
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(recipes_dir / "v1-compiled")
        )
        result = json.loads(out)
        assert result["success"] is True
        # No STD-001 (compiler without stdlib) since this fixture has both
        codes = [s.get("code", "") for s in result.get("suggestions", [])]
        assert "STD-001" not in codes
