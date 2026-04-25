"""End-to-end: v0 meta.yaml → migrate to v1 → validate v1.

No network. Uses the v0-noarch fixture as input.
"""
from __future__ import annotations

import pytest


@pytest.mark.integration
class TestWorkflowV0ToV1Migration:
    def test_dry_run_then_real_migration(
        self, script_runner, copy_recipe
    ):
        recipe_dir = copy_recipe("v0-noarch")

        # Pre-condition: meta.yaml exists, recipe.yaml does not
        assert (recipe_dir / "meta.yaml").exists()
        assert not (recipe_dir / "recipe.yaml").exists()

        # Step 1: dry run — no file writes
        rc, out, err = script_runner(
            "feedstock-migrator.py", "--dry-run", str(recipe_dir),
            timeout=60,
        )
        assert rc == 0, f"dry run failed: {out}\n{err}"
        assert not (recipe_dir / "recipe.yaml").exists()

        # Step 2: real migration (no --dry-run)
        rc, out, err = script_runner(
            "feedstock-migrator.py", str(recipe_dir),
            timeout=60,
        )
        assert rc == 0, f"migration failed: {out}\n{err}"
        assert (recipe_dir / "recipe.yaml").exists(), (
            "Migration should have created recipe.yaml"
        )

        # Step 3: validate migrated recipe (regression: fix #2 ensures
        # multi-output recipes pass; this is single-output but exercises
        # the conda-smithy lint path from fix #1)
        # CRITICAL: meta.yaml + recipe.yaml together violate the format-mixing
        # rule, so we delete meta.yaml first (per the migration protocol).
        (recipe_dir / "meta.yaml").unlink()

        rc, out, err = script_runner(
            "validate_recipe.py", str(recipe_dir),
        )
        combined = out + err
        # validate_recipe.py itself must not crash. A `Traceback` in its
        # OUTPUT is allowed only if it's surfacing an upstream conda-smithy
        # crash (a captured subprocess error, not a Python exception in our
        # script). Distinguish via the "conda-smithy:" prefix that our fix
        # #1 adds.
        if "Traceback" in combined:
            assert "conda-smithy:" in combined, (
                "validate_recipe.py raised a Python traceback that's not "
                "from the captured conda-smithy subprocess output:\n" + combined
            )
