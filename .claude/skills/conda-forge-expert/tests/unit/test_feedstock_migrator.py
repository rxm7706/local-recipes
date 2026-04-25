"""Unit tests for feedstock-migrator.py (hyphenated → script_runner only)."""
from __future__ import annotations

import yaml


class TestFeedstockMigrator:
    def test_dry_run_v0_to_v1(self, script_runner, recipes_dir):
        """Dry run should print the converted recipe.yaml without writing."""
        rc, out, err = script_runner(
            "feedstock-migrator.py", "--dry-run",
            str(recipes_dir / "v0-noarch"),
            timeout=60,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        # Output should look like a v1 recipe
        assert "schema_version" in out or "package:" in out or "recipe:" in out

    def test_dry_run_does_not_write(
        self, script_runner, copy_recipe
    ):
        """Dry run must not create recipe.yaml in the source dir."""
        recipe_dir = copy_recipe("v0-noarch")
        # Confirm no recipe.yaml present pre-run
        assert not (recipe_dir / "recipe.yaml").exists()
        rc, _, _ = script_runner(
            "feedstock-migrator.py", "--dry-run", str(recipe_dir),
            timeout=60,
        )
        assert rc == 0
        assert not (recipe_dir / "recipe.yaml").exists(), (
            "Dry run wrote recipe.yaml to disk."
        )

    def test_help_lists_dry_run_flag(self, script_runner):
        rc, out, _ = script_runner("feedstock-migrator.py", "--help")
        assert rc == 0
        assert "--dry-run" in out
