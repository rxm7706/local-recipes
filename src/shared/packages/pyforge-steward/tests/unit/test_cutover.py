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
