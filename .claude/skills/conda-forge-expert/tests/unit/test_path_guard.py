"""Unit tests for _path_guard.py — AUD-CFE-001 / -002 / -006.

The guard exists because three MCP-reachable surfaces join a caller-supplied
slug or path onto the recipes tree and then write (``recipe_editor``), copy into
a public fork (``submit_pr``) or build it (``trigger_build``). Each test below
names the escape it prevents.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def guard(load_module, monkeypatch, tmp_path):
    """_path_guard with the confinement root pointed at a tmp recipes tree."""
    mod = load_module("_path_guard.py")
    root = tmp_path / "recipes"
    (root / "somepkg").mkdir(parents=True)
    (root / "somepkg" / "recipe.yaml").write_text("schema_version: 1\n")
    monkeypatch.setenv("CFE_RECIPES_ROOT", str(root))
    return mod, root


class TestValidateRecipeName:
    @pytest.mark.parametrize(
        "name",
        ["numpy", "ruamel.yaml", "tree_sitter", "pyobjc-framework-CoreText", "2to3"],
    )
    def test_accepts_real_recipe_slugs(self, guard, name):
        mod, _ = guard
        mod.validate_recipe_name(name)  # must not raise

    @pytest.mark.parametrize(
        "name",
        [
            "../../etc",          # traversal
            "..",                 # bare parent
            ".",                  # bare self
            "foo/bar",            # nested (posix)
            "foo\\bar",           # nested (windows)
            "/etc/passwd",        # absolute
            "",                   # empty
            "foo\0bar",           # null byte
            "foo bar",            # whitespace
            "$(id)",              # shell-looking
        ],
    )
    def test_rejects_traversal_and_separators(self, guard, name):
        mod, _ = guard
        with pytest.raises(ValueError):
            mod.validate_recipe_name(name)

    def test_rejects_non_string(self, guard):
        mod, _ = guard
        with pytest.raises(ValueError):
            mod.validate_recipe_name(None)


class TestResolveUnderRecipes:
    def test_accepts_path_inside_the_root(self, guard):
        mod, root = guard
        assert mod.resolve_under_recipes(root / "somepkg") == root / "somepkg"

    def test_accepts_the_root_itself(self, guard):
        mod, root = guard
        assert mod.resolve_under_recipes(root) == root

    def test_rejects_sibling_of_the_root(self, guard, tmp_path):
        """`recipes/../secrets` must not pass just because it starts inside."""
        mod, root = guard
        outside = tmp_path / "secrets"
        outside.mkdir()
        with pytest.raises(ValueError, match="must be under"):
            mod.resolve_under_recipes(root / ".." / "secrets")

    def test_rejects_absolute_path_outside(self, guard):
        mod, _ = guard
        with pytest.raises(ValueError, match="must be under"):
            mod.resolve_under_recipes("/etc")

    def test_rejects_symlink_escaping_the_root(self, guard, tmp_path):
        """A symlink INSIDE recipes/ pointing out is still an escape."""
        mod, root = guard
        outside = tmp_path / "outside"
        outside.mkdir()
        link = root / "escape"
        link.symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError, match="must be under"):
            mod.resolve_under_recipes(link)

    def test_prefix_collision_is_not_containment(self, guard, tmp_path):
        """`/tmp/x/recipes-evil` must not pass a `/tmp/x/recipes` root."""
        mod, root = guard
        evil = root.parent / (root.name + "-evil")
        evil.mkdir()
        with pytest.raises(ValueError, match="must be under"):
            mod.resolve_under_recipes(evil)


class TestValidateRecipeFilePath:
    def test_accepts_existing_recipe_file(self, guard):
        mod, root = guard
        target = root / "somepkg" / "recipe.yaml"
        assert mod.validate_recipe_file_path(target) == target

    def test_accepts_new_file_in_existing_recipe_dir(self, guard):
        mod, root = guard
        target = root / "somepkg" / "conda-forge.yml"
        assert mod.validate_recipe_file_path(target) == target

    def test_rejects_non_yaml_suffix(self, guard):
        mod, root = guard
        with pytest.raises(ValueError, match="must be a .yaml/.yml file"):
            mod.validate_recipe_file_path(root / "somepkg" / "build.sh")

    def test_rejects_yaml_outside_the_root(self, guard, tmp_path):
        """The bug AUD-CFE-002 names: a suffix check alone let ANY repo yaml through."""
        mod, _ = guard
        target = tmp_path / "pixi-like.yaml"
        target.write_text("nope\n")
        with pytest.raises(ValueError, match="must be under"):
            mod.validate_recipe_file_path(target)

    def test_rejects_traversal_out_of_the_root(self, guard, tmp_path):
        mod, root = guard
        outside = tmp_path / "workflows"
        outside.mkdir()
        (outside / "ci.yml").write_text("on: push\n")
        with pytest.raises(ValueError, match="must be under"):
            mod.validate_recipe_file_path(root / ".." / "workflows" / "ci.yml")

    def test_rejects_directory_masquerading_as_yaml(self, guard):
        mod, root = guard
        d = root / "somepkg" / "weird.yaml"
        d.mkdir()
        with pytest.raises(ValueError, match="not a file"):
            mod.validate_recipe_file_path(d)

    def test_rejects_new_file_in_missing_dir(self, guard):
        mod, root = guard
        with pytest.raises(ValueError, match="directory does not exist"):
            mod.validate_recipe_file_path(root / "nope" / "recipe.yaml")


class TestRootResolution:
    def test_env_override_wins(self, load_module, monkeypatch, tmp_path):
        mod = load_module("_path_guard.py")
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(tmp_path))
        assert mod.recipes_root() == tmp_path.resolve()

    def test_defaults_to_repo_recipes_dir(self, load_module, monkeypatch):
        mod = load_module("_path_guard.py")
        monkeypatch.delenv("CFE_RECIPES_ROOT", raising=False)
        assert mod.recipes_root() == (mod.REPO_ROOT / "recipes").resolve()

    def test_root_is_read_per_call_not_at_import(self, load_module, monkeypatch, tmp_path):
        """An already-imported module must still see a later env change.

        Capturing the root at import time is what would make the test-suite
        override silently ineffective.
        """
        mod = load_module("_path_guard.py")
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(a))
        assert mod.recipes_root() == a.resolve()
        monkeypatch.setenv("CFE_RECIPES_ROOT", str(b))
        assert mod.recipes_root() == b.resolve()
