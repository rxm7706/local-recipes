"""Unit tests for _paths.py — the Rule-2 retro's canonical path helper.

Introduced to replace ~30 hand-rolled `Path(__file__)` parent-walk copies
that had drifted into three shapes across scripts/*.py, including two
(`feedstock_context.py`, `feedstock_lookup.py`) that resolved a data
directory one level shallow (`.claude/skills/data/...` instead of
`.claude/data/...`).
"""
from __future__ import annotations

from pathlib import Path


class TestPaths:
    def test_get_repo_root_is_the_monorepo_root(self, load_module):
        mod = load_module("_paths.py")
        root = mod.get_repo_root()
        # The repo root is the parent of .claude/, not .claude/ itself.
        assert (root / ".claude" / "skills" / "conda-forge-expert").is_dir()

    def test_get_data_dir_is_directly_under_claude(self, load_module):
        mod = load_module("_paths.py")
        data_dir = mod.get_data_dir()
        assert data_dir == mod.get_repo_root() / ".claude" / "data" / "conda-forge-expert"
        # Regression guard for the specific bug this module fixes: must NOT
        # be nested one level deeper under .claude/skills/.
        assert "skills" not in data_dir.parts
