"""Story 19.3: deck-qa pixi task is the gate's first non-test caller."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def test_deck_qa_pixi_task_is_registered() -> None:
    """The story's caller surface exists in pixi and forwards to herald deck qa."""
    pixi = tomllib.loads((_repo_root() / "pixi.toml").read_text(encoding="utf-8"))
    task = pixi["feature"]["pyforge-herald"]["tasks"]["deck-qa"]
    assert task["cmd"] == "herald deck qa"
    assert "cwd" not in task
