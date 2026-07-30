"""Unit tests for submit_pr.py.

CRITICAL: these tests must NEVER actually submit a PR. We only ever invoke
with --dry-run, and we don't rely on the gh CLI mutating remote state.
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestForkSyncIsNotDestructive:
    """AUD-CFE-011: `_sync_fork` force-pushed the fork's main with a bare
    `--force`, silently discarding any commit on it that upstream does not have.
    """

    @pytest.fixture
    def fake_git(self, load_module, monkeypatch):
        mod = load_module("submit_pr.py")
        calls: list[list[str]] = []
        failing: set[str] = set()

        def _fake_run(cmd, cwd=None, check=True):
            calls.append(list(cmd))
            joined = " ".join(cmd)
            if any(token in joined for token in failing):
                if check:
                    raise RuntimeError("simulated git failure")
                return (1, "", "stale info: refusing to lose commits")
            if "rev-list" in cmd:
                return (0, "3", "")
            return (0, "", "")

        monkeypatch.setattr(mod, "_run", _fake_run)
        return mod, calls, failing

    def test_push_uses_force_with_lease(self, fake_git):
        mod, calls, _ = fake_git
        mod._sync_fork(Path("/tmp/fake-fork"))
        pushes = [c for c in calls if c[:2] == ["git", "push"]]
        assert pushes, "no push issued"
        assert all("--force-with-lease" in c for c in pushes), pushes
        assert not any("--force" in c and "--force-with-lease" not in c
                       for c in pushes), pushes

    def test_origin_is_fetched_before_the_lease_is_evaluated(self, fake_git):
        """A lease compared against a stale tracking ref proves nothing."""
        mod, calls, _ = fake_git
        mod._sync_fork(Path("/tmp/fake-fork"))
        fetch_origin = next(
            (i for i, c in enumerate(calls) if c[:3] == ["git", "fetch", "origin"]),
            None,
        )
        push = next(i for i, c in enumerate(calls) if c[:2] == ["git", "push"])
        assert fetch_origin is not None, "origin never fetched"
        assert fetch_origin < push

    def test_returns_the_behind_count_on_success(self, fake_git):
        mod, _, _ = fake_git
        assert mod._sync_fork(Path("/tmp/fake-fork")) == 3

    def test_lease_rejection_raises_instead_of_clobbering(self, fake_git):
        mod, _, failing = fake_git
        failing.add("push")
        with pytest.raises(RuntimeError, match="Refusing to overwrite"):
            mod._sync_fork(Path("/tmp/fake-fork"))

    def test_rejection_message_tells_the_operator_how_to_inspect(self, fake_git):
        mod, _, failing = fake_git
        failing.add("push")
        with pytest.raises(RuntimeError) as exc:
            mod._sync_fork(Path("/tmp/fake-fork"))
        assert "log origin/main ^upstream/main" in str(exc.value)


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
