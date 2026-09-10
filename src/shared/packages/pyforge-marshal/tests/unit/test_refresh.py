"""Story 15.1 -- ``marshal refresh``: one command refreshes the fleet's homes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import refresh as refresh_mod
from pyforge.marshal.cli.refresh import run_refresh
from pyforge.marshal.core.context import slug_from_loop_branch
from pyforge.marshal.core.refresh import (
    STEP_FAST_FORWARD,
    STEP_PUSH,
    STEP_RENDER_POLICY,
    STEP_SYNC_STATUS,
    RefreshStep,
    is_incomplete_refresh,
    ordered_steps,
)
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.vcs import WorktreeEntry


def test_slug_from_loop_branch():
    assert slug_from_loop_branch("loop/acme") == "acme"
    assert slug_from_loop_branch("loop/pyforge-marshal") == "pyforge-marshal"
    assert slug_from_loop_branch("main") is None
    assert slug_from_loop_branch(None) is None
    assert slug_from_loop_branch("loop/") is None


def test_is_incomplete_when_ff_done_and_render_failed():
    steps = ordered_steps(
        fast_forward=RefreshStep(STEP_FAST_FORWARD, "done"),
        push=RefreshStep(STEP_PUSH, "done"),
        render_policy=RefreshStep(STEP_RENDER_POLICY, "failed", "boom"),
        sync_status=RefreshStep(STEP_SYNC_STATUS, "done"),
    )
    assert is_incomplete_refresh(steps) is True


def test_not_incomplete_when_ff_skipped():
    steps = ordered_steps(
        fast_forward=RefreshStep(STEP_FAST_FORWARD, "skipped", "already current"),
        push=RefreshStep(STEP_PUSH, "done"),
        render_policy=RefreshStep(STEP_RENDER_POLICY, "failed"),
        sync_status=RefreshStep(STEP_SYNC_STATUS, "done"),
    )
    assert is_incomplete_refresh(steps) is False


class _FakeVcs:
    def __init__(
        self,
        *,
        worktrees: tuple[WorktreeEntry, ...] = (),
        worktrees_raise: bool = False,
        fetch_raise: bool = False,
        behind: dict[str, int] | None = None,
        behind_raise: set[str] | None = None,
        dirty: set[str] | None = None,
        ff_raise: set[str] | None = None,
        push_raise: set[str] | None = None,
        head_sha: str = "headsha012345",
    ) -> None:
        self.worktrees = worktrees
        self.worktrees_raise = worktrees_raise
        self.fetch_raise = fetch_raise
        self.behind = behind or {}
        self.behind_raise = behind_raise or set()
        self.dirty = dirty or set()
        self.ff_raise = ff_raise or set()
        self.push_raise = push_raise or set()
        self.head_sha = head_sha
        self.fetch_calls: list[tuple[Path, str, str]] = []
        self.ff_calls: list[tuple[Path, str]] = []
        self.push_calls: list[tuple[Path, str]] = []

    def repo_common_root(self, start):
        return Path("/fake-repo")

    def list_worktrees(self, repo_root):
        if self.worktrees_raise:
            raise VcsCommandError("list failed")
        return self.worktrees

    def fetch(self, repo_root, remote, ref):
        self.fetch_calls.append((repo_root, remote, ref))
        if self.fetch_raise:
            raise VcsCommandError("fetch failed")

    def commits_behind(self, worktree_path, tip_ref):
        if worktree_path.name in self.behind_raise:
            raise VcsCommandError("unreadable")
        return self.behind.get(worktree_path.name, 0)

    def worktree_head_sha(self, worktree_path):
        if worktree_path.name in self.behind_raise:
            raise VcsCommandError("unreadable")
        return self.head_sha

    def has_uncommitted_changes(self, worktree_path):
        return worktree_path.name in self.dirty

    def fast_forward(self, worktree_path, ref):
        self.ff_calls.append((worktree_path, ref))
        if worktree_path.name in self.ff_raise:
            raise VcsCommandError("not a fast-forward")
        return "newsha1234567890"

    def push(self, repo_root, branch):
        self.push_calls.append((repo_root, branch))
        slug = branch.removeprefix("loop/")
        if slug in self.push_raise:
            raise VcsCommandError("push failed")


def _ns(**kwargs):
    defaults = {"project": None, "format": "json", "base": "main"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture(autouse=True)
def _stub_policy_write(monkeypatch):
    def _fake_compose(slug):
        from pyforge.marshal.core import policy as policy_mod

        effective, _ = policy_mod.compose(
            project_slug=slug if policy_mod._is_valid_project_slug(slug) else "acme",
            project={},
            flags={},
        )
        return effective

    def _fake_write(effective, home, **kwargs):
        path = Path(home) / ".bmad-loop" / "policy.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# stub\n", encoding="utf-8")
        return path

    monkeypatch.setattr(refresh_mod, "_compose_effective", _fake_compose)
    monkeypatch.setattr(refresh_mod, "write_policy_toml", _fake_write)


def test_refresh_reports_behind_for_all_loop_homes(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    homes = (
        WorktreeEntry(path=tmp_path / "a", branch="loop/alpha"),
        WorktreeEntry(path=tmp_path / "b", branch="loop/beta"),
        WorktreeEntry(path=tmp_path / "main-checkout", branch="main"),
    )
    vcs = _FakeVcs(worktrees=homes, behind={"a": 3, "b": 0})
    code = run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    by_slug = {h["slug"]: h for h in out["data"]["homes"]}
    assert set(by_slug) == {"alpha", "beta"}
    assert by_slug["alpha"]["behind_count"] == 3
    assert by_slug["beta"]["behind_count"] == 0
    assert vcs.fetch_calls and vcs.fetch_calls[0][1:] == ("origin", "main")


def test_unreadable_home_is_reported_not_skipped(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "broken"
    home.mkdir()
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/broken"),),
        behind_raise={"broken"},
    )
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert len(out["data"]["homes"]) == 1
    row = out["data"]["homes"][0]
    assert row["readable"] is False
    assert row["behind_count"] is None
    assert any(f["code"] == "MRS-REFRESH-002" for f in out["findings"])


def test_dirty_home_refused_by_name_no_ff(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "dirty"
    home.mkdir()
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/dirty"),),
        behind={"dirty": 5},
        dirty={"dirty"},
    )
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    row = out["data"]["homes"][0]
    assert "dirty" in (row["refused_reason"] or "")
    steps = {s["name"]: s for s in row["steps"]}
    assert steps["fast_forward"]["status"] == "failed"
    assert vcs.ff_calls == []
    assert steps["push"]["status"] == "skipped"
    assert any(f["code"] == "MRS-REFRESH-003" for f in out["findings"])


def test_clean_behind_home_fast_forwards_and_pushes_loop_slug_only(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "acme"
    home.mkdir()
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        behind={"acme": 2},
    )
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    row = out["data"]["homes"][0]
    steps = {s["name"]: s for s in row["steps"]}
    assert steps["fast_forward"]["status"] == "done"
    assert steps["push"]["status"] == "done"
    assert vcs.ff_calls == [(home, "origin/main")]
    assert vcs.push_calls == [(Path("/fake-repo"), "loop/acme")]
    assert row["incomplete"] is False
    assert steps["render_policy"]["status"] == "done"


def test_ff_without_render_marks_incomplete(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "acme"
    home.mkdir()
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        behind={"acme": 1},
    )

    def _boom(effective, home_path, **kwargs):
        from pyforge.marshal.adapters.harness_bmadloop import HarnessPolicyWriteError

        raise HarnessPolicyWriteError("cannot write")

    monkeypatch.setattr(refresh_mod, "write_policy_toml", _boom)
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    row = out["data"]["homes"][0]
    assert row["incomplete"] is True
    steps = {s["name"]: s for s in row["steps"]}
    assert steps["fast_forward"]["status"] == "done"
    assert steps["render_policy"]["status"] == "failed"
    codes = {f["code"] for f in out["findings"]}
    assert "MRS-REFRESH-006" in codes
    assert "MRS-REFRESH-007" in codes


def test_cli_wired_through_main(tmp_path, monkeypatch):
    from pyforge.marshal.cli.main import main

    monkeypatch.chdir(tmp_path)
    assert main(["refresh", "--help"]) == 0


def test_sync_status_step_skips_when_no_epics_md(tmp_path):
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "skipped"
    assert "epics.md" in result.detail


def test_sync_status_step_skips_when_script_missing(tmp_path):
    epics = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    )
    epics.parent.mkdir(parents=True)
    epics.write_text("# Epic 1\n", encoding="utf-8")
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "skipped"
    assert "sprint_plan.py" in result.detail


def _seed_epics_and_script(tmp_path: Path) -> None:
    epics = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    )
    epics.parent.mkdir(parents=True)
    epics.write_text("# Epic 1\n", encoding="utf-8")
    script = (
        tmp_path
        / ".claude"
        / "skills"
        / "bmad-sprint-planning"
        / "scripts"
        / "sprint_plan.py"
    )
    script.parent.mkdir(parents=True)
    script.write_text("# stub\n", encoding="utf-8")


def test_sync_status_step_reports_done_with_new_entries(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    class _Result:
        returncode = 0
        stdout = json.dumps({"ok": True, "new_entries": ["epic-2", "2-1-x"]})
        stderr = ""

    monkeypatch.setattr(
        refresh_mod.subprocess, "run", lambda argv, **kw: _Result()
    )
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "done"
    assert "2 new entries" in result.detail
    assert findings == []


def test_sync_status_step_reports_in_sync_with_no_new_entries(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    class _Result:
        returncode = 0
        stdout = json.dumps({"ok": True, "new_entries": []})
        stderr = ""

    monkeypatch.setattr(
        refresh_mod.subprocess, "run", lambda argv, **kw: _Result()
    )
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "done"
    assert result.detail == "in sync"


def test_sync_status_step_reports_failure_and_finding(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(
        refresh_mod.subprocess, "run", lambda argv, **kw: _Result()
    )
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert any(f.code == "MRS-REFRESH-008" for f in findings)


def test_sync_status_step_reports_failure_when_launch_raises(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    def _boom(argv, **kw):
        raise OSError("no uv on PATH")

    monkeypatch.setattr(refresh_mod.subprocess, "run", _boom)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert any(f.code == "MRS-REFRESH-008" for f in findings)


def test_run_refresh_includes_sync_status_step(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "acme"
    home.mkdir()
    vcs = _FakeVcs(
        worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        behind={"acme": 2},
    )
    monkeypatch.setattr(vcs, "repo_common_root", lambda start: tmp_path)
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    row = out["data"]["homes"][0]
    steps = {s["name"]: s for s in row["steps"]}
    assert "sync_status" in steps
    assert steps["sync_status"]["status"] == "skipped"  # no epics.md under tmp_path
