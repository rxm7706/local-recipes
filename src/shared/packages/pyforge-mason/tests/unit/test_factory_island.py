"""Factory island path resolution and native build wiring.

Story 44.7 (steward, spec-python-foundry-cutover:CAP-4) wired the island;
Story 39.1 (spec-pyforge-mason CAP-36) covers every native branch: the walk,
the variable, the unresolved root and its message, the missing lock, the
empty slug, the missing recipe, the rejected path shapes, the native recipe
argument and child environment, the unchanged caller mapping, the artifact
directory, and the exit codes through ``main()``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason.cli import main
from pyforge.mason.errors import FactoryIslandMissingError
from pyforge.mason.exit_codes import EXIT_CFE_UNAVAILABLE, EXIT_FAILED
from pyforge.mason.models import BuildResult
from pyforge.mason.recipe import build
from pyforge.mason.resolve import (
    is_factory_recipe_path,
    resolve_factory_island,
    resolve_foundry_root,
)

_RECIPE = "click-help-colors"


def _seed_foundry(root: Path) -> Path:
    factory = root / "factory"
    (factory / "recipes" / _RECIPE).mkdir(parents=True)
    (factory / "recipes" / _RECIPE / "recipe.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    (factory / "pixi.toml").write_text('[workspace]\nname = "factory"\n', encoding="utf-8")
    (factory / "pixi.lock").write_text("version: 6\n", encoding="utf-8")
    return root


def _build(recipe_path: str, *, fake_cfe_root: Path, environ: dict[str, str], start_directory: Path) -> BuildResult:
    return build(
        recipe_path,
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=None,
        environ=environ,
        start_directory=start_directory,
    )


def _fake_native_capturing(captured: dict[str, object]):
    def _fake_native(recipe_path, *, root, timeout=None, stderr_sink=None, env=None):
        captured["recipe_path"] = recipe_path
        captured["env"] = env
        return BuildResult(mode="native", config="linux64", returncode=0, stdout="", artifact_dir=None)

    return _fake_native


# --- the path rule ----------------------------------------------------------


def test_is_factory_recipe_path_accepts_only_island_relative_spellings():
    assert is_factory_recipe_path(f"factory/recipes/{_RECIPE}")
    assert is_factory_recipe_path("./factory/recipes/foo")
    assert is_factory_recipe_path(".\\factory\\recipes\\foo")


@pytest.mark.parametrize(
    "recipe_path",
    ["../factory/recipes/x", "/factory/recipes/x", "..factory/recipes/x", "recipes/x"],
)
def test_is_factory_recipe_path_rejects_other_shapes(recipe_path):
    assert not is_factory_recipe_path(recipe_path)


def test_rejected_shape_is_not_resolved_even_with_a_foundry_present(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    assert (
        resolve_factory_island(
            f"../factory/recipes/{_RECIPE}",
            foundry_root_arg=str(foundry),
            environ={},
            start_directory=tmp_path,
        )
        is None
    )


# --- the foundry root: the walk and the variable ----------------------------


def test_resolve_foundry_root_walk(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    start = foundry / "src" / "packages"
    start.mkdir(parents=True)
    assert resolve_foundry_root(None, {}, start) == foundry.resolve()


def test_resolve_foundry_root_from_the_variable(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert resolve_foundry_root(None, {"MASON_FOUNDRY_ROOT": str(foundry)}, elsewhere) == foundry.resolve()


def test_resolve_factory_island_by_the_variable(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    resolved = resolve_factory_island(
        f"./factory/recipes/{_RECIPE}",
        foundry_root_arg=None,
        environ={"MASON_FOUNDRY_ROOT": str(foundry)},
        start_directory=elsewhere,
    )
    assert resolved is not None
    assert resolved.recipe_path == (foundry / "factory" / "recipes" / _RECIPE).resolve()


def test_resolve_factory_island_maps_recipe(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    resolved = resolve_factory_island(
        f"factory/recipes/{_RECIPE}",
        foundry_root_arg=str(foundry),
        environ={},
        start_directory=tmp_path,
    )
    assert resolved is not None
    assert resolved.foundry_root == foundry.resolve()
    assert resolved.factory_root == (foundry / "factory").resolve()
    assert resolved.recipe_path == (foundry / "factory/recipes" / _RECIPE).resolve()


# --- the typed error branches ------------------------------------------------


def test_unresolved_root_raises_and_names_only_knobs_that_exist(tmp_path):
    # Precondition: nothing above tmp_path carries the island marker.
    assert resolve_foundry_root(None, {}, tmp_path) is None
    with pytest.raises(FactoryIslandMissingError) as excinfo:
        resolve_factory_island(
            "factory/recipes/x",
            foundry_root_arg=None,
            environ={},
            start_directory=tmp_path,
        )
    exc = excinfo.value
    assert exc.identifier == "factory:missing-island"
    assert "MASON_FOUNDRY_ROOT" in exc.message
    assert "factory/pixi.toml" in exc.message
    assert "factory/pixi.lock" in exc.message
    # No flag is advertised: Mason has no foundry-root flag (AD-13's six-flag set is closed).
    assert "--" not in exc.message


def test_resolve_factory_island_missing_lock_raises(tmp_path):
    foundry = tmp_path / "python-foundry"
    (foundry / "factory").mkdir(parents=True)
    (foundry / "factory/pixi.toml").write_text("x", encoding="utf-8")
    with pytest.raises(FactoryIslandMissingError, match="factory island lock missing") as excinfo:
        resolve_factory_island(
            "factory/recipes/x",
            foundry_root_arg=str(foundry),
            environ={},
            start_directory=tmp_path,
        )
    assert excinfo.value.identifier == "factory:missing-island"


@pytest.mark.parametrize("recipe_path", ["factory/recipes/", "./factory/recipes/", "factory/recipes/x/"])
def test_empty_recipe_slug_raises(tmp_path, recipe_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    with pytest.raises(FactoryIslandMissingError, match="must name a recipe under factory/recipes/") as excinfo:
        resolve_factory_island(
            recipe_path,
            foundry_root_arg=str(foundry),
            environ={},
            start_directory=tmp_path,
        )
    assert excinfo.value.identifier == "factory:missing-island"


def test_missing_recipe_raises(tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    with pytest.raises(FactoryIslandMissingError, match="factory recipe not found") as excinfo:
        resolve_factory_island(
            "factory/recipes/no-such-recipe",
            foundry_root_arg=str(foundry),
            environ={},
            start_directory=tmp_path,
        )
    assert excinfo.value.identifier == "factory:missing-island"


# --- the native build: recipe argument, child environment, caller mapping ----


def test_build_injects_factory_env_for_factory_recipe_path(fake_cfe_root, tmp_path):
    # Resolved by the walk with an empty caller mapping, so both variables in the
    # child's environment can only have come from the injection.
    foundry = _seed_foundry(tmp_path / "python-foundry")
    start = foundry / "src"
    start.mkdir()
    captured: dict[str, object] = {}

    with patch("pyforge.mason.cfe.build_native", side_effect=_fake_native_capturing(captured)):
        _build(
            f"factory/recipes/{_RECIPE}",
            fake_cfe_root=fake_cfe_root,
            environ={},
            start_directory=start,
        )

    assert captured["recipe_path"] == str((foundry / "factory/recipes" / _RECIPE).resolve())
    assert captured["env"]["MASON_FACTORY_ROOT"] == str((foundry / "factory").resolve())
    assert captured["env"]["MASON_FOUNDRY_ROOT"] == str(foundry.resolve())


def test_build_leaves_the_callers_mapping_unchanged(fake_cfe_root, tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    environ = {"MASON_FOUNDRY_ROOT": str(foundry), "UNRELATED": "kept"}
    snapshot = dict(environ)
    captured: dict[str, object] = {}

    with patch("pyforge.mason.cfe.build_native", side_effect=_fake_native_capturing(captured)):
        _build(f"factory/recipes/{_RECIPE}", fake_cfe_root=fake_cfe_root, environ=environ, start_directory=tmp_path)

    assert environ == snapshot
    assert "MASON_FACTORY_ROOT" not in environ
    assert captured["env"] is not environ
    assert captured["env"]["UNRELATED"] == "kept"


def test_non_island_path_gets_no_factory_variable(fake_cfe_root, tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    environ = {"MASON_FOUNDRY_ROOT": str(foundry)}
    captured: dict[str, object] = {}

    with patch("pyforge.mason.cfe.build_native", side_effect=_fake_native_capturing(captured)):
        _build("../factory/recipes/x", fake_cfe_root=fake_cfe_root, environ=environ, start_directory=tmp_path)

    assert captured["recipe_path"] == "../factory/recipes/x"
    assert "MASON_FACTORY_ROOT" not in captured["env"]


def test_native_build_reports_the_artifact_directory_under_the_factory_root(fake_cfe_root, tmp_path):
    foundry = _seed_foundry(tmp_path / "python-foundry")
    factory_root = (foundry / "factory").resolve()

    with (
        patch("pyforge.mason.cfe.run_streamed", return_value=(0, "ok")) as mock_run_streamed,
        patch("pyforge.mason.cfe.detect_native_build_config", return_value="linux64"),
    ):
        result = _build(
            f"factory/recipes/{_RECIPE}",
            fake_cfe_root=fake_cfe_root,
            environ={"MASON_FOUNDRY_ROOT": str(foundry)},
            start_directory=tmp_path,
        )

    assert result.artifact_dir == f"{factory_root}/build_artifacts/linux64"
    args, kwargs = mock_run_streamed.call_args
    assert args[0][-1] == str(factory_root / "recipes" / _RECIPE)
    assert kwargs["env"]["MASON_FACTORY_ROOT"] == str(factory_root)


# --- exit codes through main() -----------------------------------------------


def test_main_exits_1_when_the_foundry_root_is_unresolved(fake_cfe_root, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MASON_FOUNDRY_ROOT", raising=False)
    monkeypatch.delenv("MASON_FORMAT", raising=False)

    with patch("pyforge.mason.cfe.build_native") as mock_native:
        rc = main(["recipe", "build", "factory/recipes/x", "--cfe-root", str(fake_cfe_root)])

    assert rc == EXIT_FAILED
    mock_native.assert_not_called()
    err = capsys.readouterr().err
    assert "factory:missing-island" in err
    assert "MASON_FOUNDRY_ROOT" in err
    assert "Traceback" not in err


def test_main_checks_the_cfe_root_first(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MASON_CFE_ROOT", raising=False)
    monkeypatch.delenv("MASON_FOUNDRY_ROOT", raising=False)
    monkeypatch.delenv("MASON_FORMAT", raising=False)

    with patch("pyforge.mason.cfe.build_native") as mock_native:
        rc = main(["recipe", "build", "factory/recipes/x"])

    assert rc == EXIT_CFE_UNAVAILABLE
    mock_native.assert_not_called()
    assert "factory:missing-island" not in capsys.readouterr().err
