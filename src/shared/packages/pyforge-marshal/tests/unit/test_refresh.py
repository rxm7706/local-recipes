"""Story 15.1 -- ``marshal refresh``: one command refreshes the fleet's homes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

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

# Captured at import time, BEFORE the autouse fixture below replaces the
# module attribute -- so the real `_compose_effective` stays testable.
_REAL_COMPOSE_EFFECTIVE = refresh_mod._compose_effective


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
        dirty_raise: set[str] | None = None,
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
        self.dirty_raise = dirty_raise or set()
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
        if worktree_path.name in self.dirty_raise:
            raise VcsCommandError("status failed")
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


def test_clean_behind_home_fast_forwards_and_pushes_loop_slug_only(tmp_path, capsys, monkeypatch):
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
    epics = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    epics.parent.mkdir(parents=True)
    epics.write_text("# Epic 1\n", encoding="utf-8")
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "skipped"
    assert "sprint_plan.py" in result.detail


def _seed_epics_and_script(tmp_path: Path) -> None:
    epics = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "epics.md"
    epics.parent.mkdir(parents=True)
    epics.write_text("# Epic 1\n", encoding="utf-8")
    script = tmp_path / ".claude" / "skills" / "bmad-sprint-planning" / "scripts" / "sprint_plan.py"
    script.parent.mkdir(parents=True)
    script.write_text("# stub\n", encoding="utf-8")


# Story 52.1 (SPEC-pyforge-core CAP-6): `_sync_status_step` runs through
# `PosixProcess.run`, so these four stubs fake THAT seam (the
# `test_harness_bmadloop_engine_liveness.py` convention) -- never `subprocess`.


def test_sync_status_step_reports_done_with_new_entries(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)
    calls: list[tuple[list[str], Path, float | None]] = []

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        calls.append((list(argv), cwd, timeout_s))
        return ProcessResult(
            returncode=0,
            stdout=json.dumps({"ok": True, "new_entries": ["epic-2", "2-1-x"]}),
            stderr="",
        )

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "done"
    assert "2 new entries" in result.detail
    assert findings == []
    # The seam is handed the same argv shape, cwd and timeout as before.
    assert len(calls) == 1
    argv, cwd, timeout_s = calls[0]
    assert argv[:2] == ["uv", "run"]
    assert argv[3] == "generate"
    assert cwd == tmp_path
    assert timeout_s == refresh_mod._SYNC_STATUS_TIMEOUT_S


def test_sync_status_step_reports_in_sync_with_no_new_entries(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(
            returncode=0,
            stdout=json.dumps({"ok": True, "new_entries": []}),
            stderr="",
        )

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "done"
    assert result.detail == "in sync"


def test_sync_status_step_reports_failure_and_finding(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert result.detail == "boom"
    assert any(f.code == "MRS-REFRESH-008" for f in findings)


def test_sync_status_step_reports_failure_when_launch_raises(tmp_path, monkeypatch):
    """A launch failure (`PosixProcess.run` raising `ProcessError` -- the
    typed form of the raw `OSError`/`TimeoutExpired` the old clause caught)
    is the same caller-visible outcome as before: a `failed` step plus an
    `MRS-REFRESH-008` finding, never an escaped exception."""
    _seed_epics_and_script(tmp_path)

    def _boom(self, argv, *, cwd, timeout_s=None):
        raise ProcessError("executable not found: 'uv' (no uv on PATH)")

    monkeypatch.setattr(PosixProcess, "run", _boom)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert "no uv on PATH" in result.detail
    assert any(f.code == "MRS-REFRESH-008" for f in findings)
    assert any("failed to launch" in f.message for f in findings)


def test_sync_status_step_reports_failure_when_child_times_out(tmp_path, monkeypatch):
    """The timeout-shaped `ProcessError` (the message `PosixProcess.run`
    produces for a child exceeding `timeout_s` -- that mapping itself is
    pyforge-core's own tested contract, not pinned here) passes through
    `_sync_status_step` unchanged: the same `failed` step + `MRS-REFRESH-008`
    finding as any other launch failure, with the seam's message verbatim
    in `result.detail`."""
    _seed_epics_and_script(tmp_path)

    def _timeout(self, argv, *, cwd, timeout_s=None):
        raise ProcessError(f"command timed out after {timeout_s}s: {' '.join(argv)}")

    monkeypatch.setattr(PosixProcess, "run", _timeout)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert f"timed out after {refresh_mod._SYNC_STATUS_TIMEOUT_S}s" in result.detail
    assert "uv run" in result.detail
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


# --- Coverage of the remaining branches (Story 52.1 coverage gate) --------


def _one_home(tmp_path: Path, name: str = "acme", **vcs_kwargs) -> tuple[Path, _FakeVcs]:
    home = tmp_path / name
    home.mkdir()
    vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch=f"loop/{name}"),), **vcs_kwargs)
    return home, vcs


def _row(capsys) -> tuple[dict, dict, set[str]]:
    out = json.loads(capsys.readouterr().out)
    row = out["data"]["homes"][0]
    steps = {s["name"]: s for s in row["steps"]}
    codes = {f["code"] for f in out["findings"]}
    return row, steps, codes


# _compose_effective (the real one -- the autouse fixture stubs the module
# attribute, so it is reached through the import-time capture above).


def test_compose_effective_invalid_slug_never_probes_a_policy_path(monkeypatch):
    def _never(slug):
        raise AssertionError("conventional_project_policy_path must not be called")

    monkeypatch.setattr(refresh_mod, "conventional_project_policy_path", _never)
    effective = _REAL_COMPOSE_EFFECTIVE("bad/slug")
    assert type(effective).__name__ == "EffectivePolicy"


def test_compose_effective_valid_slug_without_a_policy_file(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh_mod, "conventional_project_policy_path", lambda slug: tmp_path / "absent.toml")
    effective = _REAL_COMPOSE_EFFECTIVE("acme")
    assert type(effective).__name__ == "EffectivePolicy"


def test_compose_effective_reads_a_present_policy_file(tmp_path, monkeypatch):
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text("landing_resync = true\n", encoding="utf-8")
    monkeypatch.setattr(refresh_mod, "conventional_project_policy_path", lambda slug: policy_path)
    read: list[Path] = []
    real_read = refresh_mod._read_project_policy

    def _spy(path):
        read.append(path)
        return real_read(path)

    monkeypatch.setattr(refresh_mod, "_read_project_policy", _spy)
    effective = _REAL_COMPOSE_EFFECTIVE("acme")
    assert read == [policy_path]
    # The value came from the PROJECT layer, i.e. the file really was read.
    assert effective.landing_resync.value is True
    assert effective.landing_resync.layer.value == "project"


def test_compose_effective_treats_a_malformed_policy_file_as_empty(tmp_path, monkeypatch):
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text("this is = not [valid toml\n", encoding="utf-8")
    monkeypatch.setattr(refresh_mod, "conventional_project_policy_path", lambda slug: policy_path)
    effective = _REAL_COMPOSE_EFFECTIVE("acme")
    assert type(effective).__name__ == "EffectivePolicy"


def test_compose_effective_unprobeable_path_falls_through_to_the_reader(monkeypatch):
    """`candidate.is_file()` raising `OSError` is treated as "present" so the
    reader (which wraps every I/O failure in `PolicyIOError`) gets the final
    word -- and its `PolicyIOError` degrades to an empty project layer."""

    class _Unprobeable:
        def is_file(self):
            raise OSError("EACCES")

    monkeypatch.setattr(refresh_mod, "conventional_project_policy_path", lambda slug: _Unprobeable())
    attempted: list[object] = []

    def _refuse(path):
        attempted.append(path)
        raise refresh_mod.PolicyIOError("unreadable")

    monkeypatch.setattr(refresh_mod, "_read_project_policy", _refuse)
    effective = _REAL_COMPOSE_EFFECTIVE("acme")
    assert len(attempted) == 1
    assert type(effective).__name__ == "EffectivePolicy"


# _sync_status_step: exit 0 but no JSON / not ok


def test_sync_status_step_exit_zero_without_ok_json_is_a_failure(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=0, stdout="not json at all", stderr="")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    findings: list = []
    result = refresh_mod._sync_status_step("acme", tmp_path, findings)
    assert result.status == "failed"
    assert result.detail == "not json at all"
    assert any(f.code == "MRS-REFRESH-008" for f in findings)


def test_sync_status_step_reports_the_scripts_own_error_field(tmp_path, monkeypatch):
    _seed_epics_and_script(tmp_path)

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=0, stdout=json.dumps({"ok": False, "error": "epics.md unparsable"}), stderr="")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    result = refresh_mod._sync_status_step("acme", tmp_path, [])
    assert result.status == "failed"
    assert result.detail == "epics.md unparsable"


# _refresh_one_home: the remaining failure branches


def test_dirt_probe_failure_fails_ff_and_skips_push_and_render(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 2}, dirty_raise={"acme"})
    run_refresh(_ns(), vcs=vcs)
    row, steps, codes = _row(capsys)
    assert row["readable"] is True
    assert row["refused_reason"] == "dirty-probe-failed"
    assert steps["fast_forward"]["status"] == "failed"
    assert "dirt probe failed" in steps["fast_forward"]["detail"]
    assert steps["push"]["status"] == "skipped"
    assert steps["render_policy"]["status"] == "skipped"
    assert steps["sync_status"]["status"] == "skipped"
    assert row["incomplete"] is False
    assert "MRS-REFRESH-003" in codes
    assert vcs.ff_calls == []


def test_fast_forward_failure_is_reported_and_push_skipped(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 4}, ff_raise={"acme"})
    run_refresh(_ns(), vcs=vcs)
    row, steps, codes = _row(capsys)
    assert row["refused_reason"].startswith("fast-forward failed:")
    assert steps["fast_forward"]["status"] == "failed"
    assert steps["push"]["status"] == "skipped"
    # Policy is still re-rendered on a failed FF (stubbed writer, "done").
    assert steps["render_policy"]["status"] == "done"
    assert row["incomplete"] is False
    assert "MRS-REFRESH-003" in codes
    assert vcs.push_calls == []


def test_push_failure_after_a_good_fast_forward_is_a_finding(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 1}, push_raise={"acme"})
    run_refresh(_ns(), vcs=vcs)
    row, steps, codes = _row(capsys)
    assert steps["fast_forward"]["status"] == "done"
    assert steps["push"]["status"] == "failed"
    assert "push failed" in steps["push"]["detail"]
    assert steps["render_policy"]["status"] == "done"
    assert row["incomplete"] is False
    assert row["refused_reason"] is None
    assert "MRS-REFRESH-003" in codes
    assert vcs.push_calls == [(Path("/fake-repo"), "loop/acme")]


def test_current_home_skips_ff_and_push_but_still_renders(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 0})
    run_refresh(_ns(), vcs=vcs)
    row, steps, codes = _row(capsys)
    assert steps["fast_forward"]["status"] == "skipped"
    assert "already current" in steps["fast_forward"]["detail"]
    assert steps["push"]["status"] == "skipped"
    assert steps["push"]["detail"] == "nothing new to push"
    assert steps["render_policy"]["status"] == "done"
    assert vcs.ff_calls == [] and vcs.push_calls == []


# run_refresh: argument and enumeration failures


def test_malformed_project_slug_is_an_error_finding(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vcs = _FakeVcs()
    code = run_refresh(_ns(project="../escape"), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert code != EXIT_OK
    assert out["data"]["homes"] == []
    assert "repo_root" not in out["data"]
    finding = next(f for f in out["findings"] if f["code"] == "MRS-REFRESH-001")
    assert finding["severity"] == "error"
    assert vcs.fetch_calls == []


def test_unresolvable_repo_root_is_reported(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vcs = _FakeVcs()
    monkeypatch.setattr(vcs, "repo_common_root", lambda start: (_ for _ in ()).throw(VcsCommandError("not a repo")))
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["homes"] == []
    assert any(f["code"] == "MRS-REFRESH-002" and "repo root" in f["message"] for f in out["findings"])


def test_worktree_enumeration_failure_is_reported(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vcs = _FakeVcs(worktrees_raise=True)
    run_refresh(_ns(), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["repo_root"] == "/fake-repo"
    assert out["data"]["homes"] == []
    assert any(f["code"] == "MRS-REFRESH-002" and "enumerate" in f["message"] for f in out["findings"])
    assert vcs.fetch_calls == []


def test_project_scope_filters_the_fleet_to_one_slug(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    vcs = _FakeVcs(
        worktrees=(
            WorktreeEntry(path=tmp_path / "a", branch="loop/alpha"),
            WorktreeEntry(path=tmp_path / "b", branch="loop/beta"),
        ),
        behind={"a": 1, "b": 1},
    )
    run_refresh(_ns(project="beta"), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert [h["slug"] for h in out["data"]["homes"]] == ["beta"]
    assert vcs.ff_calls == [(tmp_path / "b", "origin/main")]


def test_project_scope_with_no_matching_home_skips_the_fetch(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a").mkdir()
    vcs = _FakeVcs(worktrees=(WorktreeEntry(path=tmp_path / "a", branch="loop/alpha"),))
    code = run_refresh(_ns(project="nomatch"), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert out["data"]["homes"] == []
    assert vcs.fetch_calls == []


def test_fetch_failure_stops_before_any_home_is_touched(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 3}, fetch_raise=True)
    run_refresh(_ns(base="develop"), vcs=vcs)
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["base"] == "develop"
    assert out["data"]["homes"] == []
    assert any(f["code"] == "MRS-REFRESH-002" and "origin/develop" in f["message"] for f in out["findings"])
    assert vcs.ff_calls == []


# _render_text / _emit: the text format and a dead stdout


def test_text_format_renders_homes_steps_and_findings(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    home, vcs = _one_home(tmp_path, behind={"acme": 2}, dirty={"acme"})
    run_refresh(_ns(format="text"), vcs=vcs)
    out = capsys.readouterr().out
    assert "acme: behind=2 refused=dirty" in out
    assert "  fast_forward: failed (dirty working tree)" in out
    assert "  push: skipped (fast-forward refused)" in out
    assert "[warn] MRS-REFRESH-003:" in out


def test_text_format_with_no_homes(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_refresh(_ns(format="text"), vcs=_FakeVcs())
    assert capsys.readouterr().out.strip() == "no loop homes found"


def test_render_text_marks_incomplete_and_skips_non_dict_steps():
    homes = [
        {
            "slug": "acme",
            "behind_count": None,
            "incomplete": True,
            "refused_reason": None,
            "steps": [
                {"name": "fast_forward", "status": "done", "detail": ""},
                "not-a-step",
                {"name": "push", "status": "done"},
            ],
        }
    ]
    text = refresh_mod._render_text(homes, ())
    lines = text.splitlines()
    assert lines[0] == "acme: behind=? INCOMPLETE"
    assert lines[1] == "  fast_forward: done"
    assert lines[2] == "  push: done"
    assert len(lines) == 3


def test_emit_suppresses_a_dead_stdout(tmp_path, capsys, monkeypatch):
    """A closed downstream pipe while printing the envelope is not a refresh
    failure: `_emit` routes the `OSError` to `_suppress_downstream_pipe_close`
    and still returns the verdict-derived exit code."""
    monkeypatch.chdir(tmp_path)
    suppressed: list[bool] = []
    monkeypatch.setattr(refresh_mod, "_suppress_downstream_pipe_close", lambda: suppressed.append(True))

    def _dead_print(*args, **kwargs):
        raise OSError(32, "Broken pipe")

    # Shadow the builtin inside the module's own globals only.
    monkeypatch.setattr(refresh_mod, "print", _dead_print, raising=False)
    code = run_refresh(_ns(format="text"), vcs=_FakeVcs())
    assert code == EXIT_OK
    assert suppressed == [True]
    assert capsys.readouterr().out == ""
