"""Regression guard: every script's resolved data directory must agree.

Rule-2 retro (Story 5.5) found `feedstock_context.py` and
`feedstock_lookup.py` computing `.claude/skills/data/conda-forge-expert`
(one level shallow) while every other script resolved the correct
`.claude/data/conda-forge-expert` — a live divergence: the wrong directory
had actually been created on disk at some point and gitignored rather than
root-caused (`.gitignore` carried a stray `.claude/skills/data/` entry).
Both now import the shared `_paths.get_data_dir()` helper; this test
proves they agree with a known-correct sibling.
"""
from __future__ import annotations


class TestDataDirConsistency:
    def test_feedstock_context_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        feedstock_context = load_module("feedstock_context.py")
        assert feedstock_context._DATA_DIR == paths.get_data_dir()
        assert "skills" not in feedstock_context._DATA_DIR.parts

    def test_feedstock_lookup_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        feedstock_lookup = load_module("feedstock_lookup.py")
        assert feedstock_lookup._DATA_DIR == paths.get_data_dir()
        assert "skills" not in feedstock_lookup._DATA_DIR.parts

    def test_bootstrap_data_repo_root_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        bootstrap_data = load_module("bootstrap_data.py")
        assert bootstrap_data.REPO_ROOT == paths.get_repo_root()
        assert bootstrap_data.DATA_DIR == paths.get_data_dir()
        # Regression guard for the specific off-by-one this module fixes:
        # REPO_ROOT must contain .claude/, not be its own parent.
        assert (bootstrap_data.REPO_ROOT / ".claude").is_dir()
