"""Regression guard for DW-2-10-2: recipe_updater.py's bare "python" subprocess call.

Found during the pyforge-mason effort (Story 2.10, Blind Hunter review,
2026-08-12) and flagged for this closing CFE retrospective, since AD-15
forbade a Mason-side fix: `update_recipe`'s real-write path spawned
`["python", ...]` — a bare PATH lookup — while its sibling
`github_updater.py` correctly resolves
`os.environ.get("CONDA_PYTHON_EXE") or sys.executable` for the identical
internal call to `recipe_editor.py`. An environment with only `python3` on
PATH (no `python` alias) would fail this call.
"""
from __future__ import annotations

import inspect


class TestRecipeUpdaterInterpreterResolution:
    def test_apply_path_resolves_interpreter_like_github_updater(self, load_module):
        """Static check: the source no longer hardcodes a bare "python" argv0
        for the recipe_editor.py subprocess call, and instead mirrors
        github_updater.py's CONDA_PYTHON_EXE-or-sys.executable resolution."""
        updater = load_module("recipe_updater.py")
        source = inspect.getsource(updater)
        assert '["python", str(RECIPE_EDITOR_SCRIPT)' not in source
        assert "CONDA_PYTHON_EXE" in source

    def test_github_updater_and_recipe_updater_agree_on_resolution_pattern(
        self, load_module
    ):
        updater_source = inspect.getsource(load_module("recipe_updater.py"))
        github_updater_source = inspect.getsource(load_module("github_updater.py"))
        pattern = 'os.environ.get("CONDA_PYTHON_EXE") or sys.executable'
        assert pattern in updater_source
        assert pattern in github_updater_source
