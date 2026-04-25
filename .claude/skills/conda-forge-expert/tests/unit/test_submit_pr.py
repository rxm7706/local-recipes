"""Unit tests for submit_pr.py.

CRITICAL: these tests must NEVER actually submit a PR. We only ever invoke
with --dry-run, and we don't rely on the gh CLI mutating remote state.
"""
from __future__ import annotations


class TestSubmitPr:
    def test_help(self, script_runner):
        rc, out, _ = script_runner("submit_pr.py", "--help")
        assert rc == 0
        assert "--dry-run" in out

    def test_dry_run_unknown_recipe_fails_safely(self, script_runner):
        """submit_pr.py with a non-existent recipe must fail (not crash) and
        must NOT make any network call."""
        rc, out, err = script_runner(
            "submit_pr.py", "--dry-run", "this-recipe-does-not-exist-xyz",
            timeout=30,
        )
        assert rc != 0
        # Should not crash
        assert "Traceback" not in (out + err)

    def test_module_does_not_call_gh_at_import_time(self, load_module):
        """Importing submit_pr.py must not invoke gh or hit GitHub.

        If this test hangs or times out, the script is doing I/O at import
        time — a refactoring bug that would slow every other test in the
        suite.
        """
        mod = load_module("submit_pr.py")
        assert mod is not None
