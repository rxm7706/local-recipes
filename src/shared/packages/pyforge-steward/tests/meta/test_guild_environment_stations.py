"""Story 72.1 / spec-pyforge-steward CAP-161 -- the Guild environment answers `pyforge mason`.

`pyforge-guild` is the session default (CAP-5); until this story it never installed
`pyforge-mason`, so `pyforge mason …` failed in the environment every harness runs.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


ROOT = _repo_root()


def _pixi() -> dict:
    return tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))


def test_mason_is_a_guild_feature_dependency() -> None:
    deps = _pixi()["feature"]["pyforge-guild"]["dependencies"]
    assert "pyforge-mason" in deps, "pyforge-mason must be a [feature.pyforge-guild.dependencies] member (CAP-161)"
    assert deps["pyforge-mason"] == {"path": "src/shared/packages/pyforge-mason"}


def test_guild_dependencies_comment_documents_atlas_exclusion() -> None:
    text = (ROOT / "pixi.toml").read_text(encoding="utf-8")
    guild_start = text.index("[feature.pyforge-guild.dependencies]")
    guild_block = text[guild_start : text.index("\n[feature.", guild_start + 1)]
    assert "pyforge-atlas is deliberately NOT here" in guild_block
    assert "spec-pyforge-steward/.memlog.md" in guild_block
