"""Story 44.12 — plan preserve-moved, apply idempotent, flip refuses loops."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pyforge.core.cutover_root import CutoverRootError, read_cutover_root

from pyforge.steward.cutover import (
    apply_phase,
    flip_root,
    loops_running,
    plan_append,
    plan_regenerate,
)


def _git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    pkg = root / "src/shared/packages/demo"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)
    return root


def test_regenerate_preserves_moved(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    first = plan_regenerate(root, manifest)
    assert first["rows"]
    first["rows"][0]["status"] = "moved"
    manifest.write_text(json.dumps(first), encoding="utf-8")
    second = plan_regenerate(root, manifest)
    moved = [r for r in second["rows"] if r["status"] == "moved"]
    assert moved
    assert moved[0]["path"] == first["rows"][0]["path"]


def test_append_preserves_moved(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    first = plan_regenerate(root, manifest)
    first["rows"][0]["status"] = "moved"
    manifest.write_text(json.dumps(first), encoding="utf-8")
    extra = root / "src/shared/packages/demo/extra.txt"
    extra.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "delta"], cwd=root, check=True, capture_output=True)
    second = plan_append(root, manifest)
    by_path = {r["path"]: r for r in second["rows"]}
    assert by_path[first["rows"][0]["path"]]["status"] == "moved"
    assert "src/shared/packages/demo/extra.txt" in by_path


def test_apply_is_idempotent(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    manifest = tmp_path / "manifest.json"
    dest = tmp_path / "foundry"
    plan_regenerate(root, manifest)
    once = apply_phase(root, manifest, "1a", dest)
    twice = apply_phase(root, manifest, "1a", dest)
    assert once["copied"] >= 1
    assert twice["copied"] == 0
    assert twice["skipped"] >= 1
    copied = dest / "src/packages/demo/pyproject.toml"
    assert copied.is_file()


def test_flip_refused_while_loop_running(tmp_path: Path) -> None:
    flags = tmp_path / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": "local-recipes",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    loops = tmp_path / "loops" / "x"
    loops.mkdir(parents=True)
    (loops / "state.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
    realization = tmp_path / "dream.md"
    realization.write_text("## Realization log\n", encoding="utf-8")
    assert loops_running(tmp_path / "loops")
    with pytest.raises(CutoverRootError, match="loop is running"):
        flip_root(flags, "foundry", realization, loop_home=tmp_path / "loops")
    assert read_cutover_root(flags) == "local-recipes"


# --- Story 76.1: a flip is not masked by the per-environment overlay -------------


def _flag_tree(directory: Path, overlays: object | None = None) -> Path:
    flags = directory / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
                        "defaultVariant": "local-recipes",
                    },
                    "pyforge.other": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    if overlays is not None:
        (directory / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    return flags


_PINNED = {
    "dev": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "off"},
    "staging": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "on"},
    "production": {"pyforge.cutover_root": "local-recipes"},
}


def test_the_reader_sees_the_overlay_pinned_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flags = _flag_tree(tmp_path, {**_PINNED, "staging": {"pyforge.cutover_root": "foundry"}})
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert read_cutover_root(flags) == "foundry"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert read_cutover_root(flags) == "local-recipes"


@pytest.mark.parametrize("target", ["foundry", "local-recipes"])
def test_flip_then_read_agree_in_every_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    from pyforge.core import flags as core_flags

    flags = _flag_tree(tmp_path, _PINNED)
    other = "foundry" if target == "local-recipes" else "local-recipes"
    flip_root(flags, other, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    flip_root(flags, target, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    for environment in core_flags.ENVIRONMENTS:
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        assert read_cutover_root(flags) == target, environment
        rendered = json.loads(core_flags.render(environment, flags_path=flags))
        assert rendered["flags"]["pyforge.cutover_root"]["defaultVariant"] == target, environment


def test_flip_touches_only_the_cutover_key_of_the_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path, _PINNED)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {
        "dev": {"pyforge.cutover_root": "foundry", "pyforge.other": "off"},
        "staging": {"pyforge.cutover_root": "foundry", "pyforge.other": "on"},
        "production": {"pyforge.cutover_root": "foundry"},
    }
    assert json.loads(flags.read_text(encoding="utf-8"))["flags"]["pyforge.cutover_root"]["defaultVariant"] == "foundry"


def test_flip_leaves_an_environment_that_does_not_name_the_flag_alone(tmp_path: Path) -> None:
    flags = _flag_tree(
        tmp_path, {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "local-recipes"}}
    )
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "foundry"}}


def test_flip_without_a_sibling_overlay_writes_no_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert not (tmp_path / "flag-overlays.json").exists()
    assert read_cutover_root(flags) == "foundry"


def test_flip_refuses_a_broken_overlay_before_writing_anything(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    (tmp_path / "flag-overlays.json").write_text("{not json", encoding="utf-8")
    before = flags.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused"):
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert flags.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("overlays", "named"),
    [
        ({"dev": {"pyforge.typo": "off"}}, "pyforge.typo"),
        ({"dev": {"pyforge.other": "maybe"}}, "maybe"),
        ({"qa": {"pyforge.other": "on"}}, "qa"),
        ({"dev": {"pyforge.other": {"variants": {}}}}, "pyforge.other"),
    ],
)
def test_flip_refuses_an_invalid_overlay_entry_before_writing_anything(
    tmp_path: Path, overlays: object, named: str
) -> None:
    flags = _flag_tree(tmp_path, overlays)
    overlays_path = tmp_path / "flag-overlays.json"
    tree_before = flags.read_text(encoding="utf-8")
    overlays_before = overlays_path.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused") as excinfo:
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert named in str(excinfo.value)
    assert flags.read_text(encoding="utf-8") == tree_before
    assert overlays_path.read_text(encoding="utf-8") == overlays_before
