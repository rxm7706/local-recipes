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

    def test_calculate_hash_renders_an_expression_before_it_downloads(self, tmp_path, monkeypatch, load_module):
        editor = load_module("recipe_editor.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(
            'schema_version: 1\ncontext:\n  name: my-pkg\n  version: "1.2"\n'
            "source:\n  url: https://x/${{ name[0] }}/${{ name | replace('-', '_') }}-${{ version }}.tar.gz\n"
        )
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(tmp_path))
        seen = []
        monkeypatch.setattr(editor, "calculate_sha256_from_url", lambda url: seen.append(url) or "0" * 64)
        result = editor.execute_actions(recipe, [{"action": "calculate_hash", "path": "source"}])
        assert result["success"] is True and seen == ["https://x/m/my_pkg-1.2.tar.gz"]

    def test_calculate_hash_refuses_an_expression_that_does_not_render(self, tmp_path, monkeypatch, load_module):
        editor = load_module("recipe_editor.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(
            'schema_version: 1\ncontext:\n  version: "1.2"\nsource:\n  url: https://x/${{ missing }}-${{ version }}.tar.gz\n'
        )
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(tmp_path))
        seen = []
        monkeypatch.setattr(editor, "calculate_sha256_from_url", lambda url: seen.append(url) or "0" * 64)
        result = editor.execute_actions(recipe, [{"action": "calculate_hash", "path": "source"}])
        assert result["success"] is False and "does not render" in result["error"] and seen == []
