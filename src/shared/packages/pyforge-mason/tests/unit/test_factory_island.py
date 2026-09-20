"""Story 44.7 — factory island path resolution and build env wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason.errors import FactoryIslandMissingError
from pyforge.mason.recipe import build
from pyforge.mason.resolve import (
    is_factory_recipe_path,
    resolve_factory_island,
    resolve_foundry_root,
)


def _seed_foundry(root: Path) -> Path:
    factory = root / "factory"
    (factory / "recipes" / "click-help-colors").mkdir(parents=True)
    (factory / "recipes" / "click-help-colors" / "recipe.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    (factory / "pixi.toml").write_text('[workspace]\nname = "factory"\n', encoding="utf-8")
    (factory / "pixi.lock").write_text("version: 6\n", encoding="utf-8")
    return root


def test_is_factory_recipe_path():
    assert is_factory_recipe_path("factory/recipes/click-help-colors")
    assert is_factory_recipe_path("./factory/recipes/foo")
    assert not is_factory_recipe_path("recipes/click-help-colors")


def test_resolve_foundry_root_walk(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    start = foundry / "src" / "packages"
    start.mkdir(parents=True)
    assert resolve_foundry_root(None, {}, start) == foundry.resolve()


def test_resolve_factory_island_maps_recipe(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    resolved = resolve_factory_island(
        "factory/recipes/click-help-colors",
        foundry_root_arg=str(foundry),
        environ={},
        start_directory=tmp_path,
    )
    assert resolved is not None
    assert resolved.foundry_root == foundry.resolve()
    assert resolved.factory_root == (foundry / "factory").resolve()
    assert resolved.recipe_path == (foundry / "factory/recipes/click-help-colors").resolve()


def test_resolve_factory_island_missing_lock_raises(tmp_path):
    foundry = tmp_path / "python-foundry"
    (foundry / "factory").mkdir(parents=True)
    (foundry / "factory/pixi.toml").write_text("x", encoding="utf-8")
    with pytest.raises(FactoryIslandMissingError, match="factory island lock missing"):
        resolve_factory_island(
            "factory/recipes/x",
            foundry_root_arg=str(foundry),
            environ={},
            start_directory=tmp_path,
        )


def test_build_injects_factory_env_for_factory_recipe_path(fake_cfe_root, tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    captured: dict[str, object] = {}

    def _fake_native(recipe_path, *, root, timeout=None, stderr_sink=None, env=None):
        captured["recipe_path"] = recipe_path
        captured["env"] = env
        from pyforge.mason.models import BuildResult

        return BuildResult(mode="native", config="linux64", returncode=0, stdout="", artifact_dir=None)

    with patch("pyforge.mason.cfe.build_native", side_effect=_fake_native):
        build(
            "factory/recipes/click-help-colors",
            docker=False,
            config=None,
            cfe_root_arg=str(fake_cfe_root),
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={"MASON_FOUNDRY_ROOT": str(foundry)},
            start_directory=tmp_path,
        )

    assert captured["env"]["MASON_FACTORY_ROOT"] == str((foundry / "factory").resolve())
    assert captured["recipe_path"] == str((foundry / "factory/recipes/click-help-colors").resolve())
