"""Story 19.3: deck-qa pixi task is the gate's first non-test caller."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

# Story 52.1 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


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
