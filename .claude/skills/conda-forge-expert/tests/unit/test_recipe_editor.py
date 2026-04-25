"""Unit tests for recipe_editor.py."""
from __future__ import annotations

import json

import yaml


class TestRecipeEditor:
    def test_update_context_version(self, script_runner, copy_recipe):
        recipe_dir = copy_recipe("v1-noarch")
        recipe_file = recipe_dir / "recipe.yaml"

        actions = json.dumps(
            [{"action": "update", "path": "context.version", "value": "9.9.9"}]
        )
        rc, out, err = script_runner(
            "recipe_editor.py", str(recipe_file), actions
        )
        assert rc == 0, f"out={out}\nerr={err}"
        result = json.loads(out)
        assert result["success"] is True

        # Content equivalence (assertion #5 from the design doc)
        data = yaml.safe_load(recipe_file.read_text())
        assert data["context"]["version"] == "9.9.9"

    def test_invalid_path_creates_keys(self, script_runner, copy_recipe):
        """Document current behavior: recipe_editor.py auto-creates missing
        keys rather than rejecting them. If we want strict-mode rejection,
        that's a separate enhancement, not a regression."""
        recipe_dir = copy_recipe("v1-noarch")
        recipe_file = recipe_dir / "recipe.yaml"
        actions = json.dumps(
            [
                {
                    "action": "update",
                    "path": "definitely.not.a.real.path",
                    "value": "x",
                }
            ]
        )
        rc, out, _ = script_runner(
            "recipe_editor.py", str(recipe_file), actions
        )
        # Current behavior: succeeds and creates the path. If this changes
        # to a rejection, update the assertion.
        assert rc == 0
        result = json.loads(out)
        assert result["success"] is True

    def test_malformed_actions_json_handled(self, script_runner, copy_recipe):
        recipe_dir = copy_recipe("v1-noarch")
        recipe_file = recipe_dir / "recipe.yaml"
        rc, out, err = script_runner(
            "recipe_editor.py", str(recipe_file), "not json"
        )
        # Should not crash; exit non-zero or produce error JSON
        assert rc != 0 or "error" in (out + err).lower()
