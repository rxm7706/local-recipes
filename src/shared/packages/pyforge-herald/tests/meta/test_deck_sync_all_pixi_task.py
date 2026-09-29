"""Story 23.6: deck-sync-all pixi task is the command's caller surface."""

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


def test_deck_sync_all_pixi_task_is_registered() -> None:
    """The story's caller surface exists in pixi and forwards to herald deck sync-all."""
    pixi = tomllib.loads((_repo_root() / "pixi.toml").read_text(encoding="utf-8"))
    task = pixi["feature"]["pyforge-herald"]["tasks"]["deck-sync-all"]
    assert task["cmd"] == "herald deck sync-all"
    assert "cwd" not in task


def test_deck_sync_proof_pixi_task_is_registered() -> None:
    """Story 24.3: the opt-in live idempotency-proof caller surface exists
    in pixi and forwards ``--proof-dir .herald/sync-proof``."""
    pixi = tomllib.loads((_repo_root() / "pixi.toml").read_text(encoding="utf-8"))
    task = pixi["feature"]["pyforge-herald"]["tasks"]["deck-sync-proof"]
    assert task["cmd"] == "herald deck sync-all --proof-dir .herald/sync-proof"
    assert "cwd" not in task
