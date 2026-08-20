"""Regression guard: every script's resolved data directory must agree.

Rule-2 retro (Story 5.5) found `feedstock_context.py` and
`feedstock_lookup.py` computing `.claude/skills/data/conda-forge-expert`
(one level shallow) while every other script resolved the correct
`.claude/data/conda-forge-expert` — a live divergence: the wrong directory
had actually been created on disk at some point and gitignored rather than
root-caused (`.gitignore` carried a stray `.claude/skills/data/` entry).
Both now import the shared `_paths.get_data_dir()` helper.

Note what the equality assertions below can and cannot prove. Now that these
modules literally bind `_paths.get_data_dir()`, comparing them BACK to it is
near-tautological: it catches a module that stops delegating, which is the
regression that would reintroduce the divergence, but it cannot catch
`_paths` itself resolving wrongly — both sides would move together. (Verified
by mutation: pointing `_paths` at `parents[3]` leaves those assertions
passing.) The independent anchor assertions carry that half — they check the
resolved path against the repo's actual on-disk shape rather than against
another expression of the same computation.
"""
from __future__ import annotations


class TestDataDirConsistency:
    def test_feedstock_context_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        feedstock_context = load_module("feedstock_context.py")
        assert feedstock_context._DATA_DIR == paths.get_data_dir()
        # Independent anchor: the resolved dir must sit under the repo's real
        # `.claude/data/`, checked against the filesystem rather than against
        # another expression of the same computation.
        assert "skills" not in feedstock_context._DATA_DIR.parts
        assert feedstock_context._DATA_DIR.parent.name == "data"
        assert (feedstock_context._DATA_DIR.parent.parent / "skills").is_dir()

    def test_feedstock_lookup_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        feedstock_lookup = load_module("feedstock_lookup.py")
        assert feedstock_lookup._DATA_DIR == paths.get_data_dir()
        assert "skills" not in feedstock_lookup._DATA_DIR.parts
        assert feedstock_lookup._DATA_DIR.parent.name == "data"
        assert (feedstock_lookup._DATA_DIR.parent.parent / "skills").is_dir()

    def test_bootstrap_data_repo_root_agrees_with_paths_helper(self, load_module):
        paths = load_module("_paths.py")
        bootstrap_data = load_module("bootstrap_data.py")
        assert bootstrap_data.REPO_ROOT == paths.get_repo_root()
        assert bootstrap_data.DATA_DIR == paths.get_data_dir()
        # Regression guard for the specific off-by-one this module fixes:
        # REPO_ROOT must contain .claude/, not be its own parent.
        assert (bootstrap_data.REPO_ROOT / ".claude").is_dir()
