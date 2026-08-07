"""`dashboard_diff` + `commit_and_push_dashboard` + bare `deploy dashboard`
CLI reconciliation — Story 2.2 (FR-9).

Uses a REAL scratch git repo with a real bare `origin` remote (not mocked) —
this story's own spec calls this out explicitly: the zero-commit /
exactly-one-commit properties are about real git history, not a mock's
call-count.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.deploy import (
    build_dashboard,
    commit_and_push_dashboard,
    dashboard_diff,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _make_repo_with_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)

    work = tmp_path / "work"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    dashboard_dir = work / "docs" / "dashboard"
    dashboard_dir.mkdir(parents=True)
    (dashboard_dir / "data.js").write_text("window.DASHBOARD_DATA = {v: 1};\n")
    (work / "README.md").write_text("scratch repo\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


def _commit_count(cwd: Path) -> int:
    result = _git("rev-list", "--count", "HEAD", cwd=cwd)
    return int(result.stdout.strip())


def test_no_diff_produces_zero_commits_run_twice(tmp_path):
    work = _make_repo_with_origin(tmp_path)
    before = _commit_count(work)

    # A build that writes the exact same content the committed tree already has.
    same_cmd = [
        sys.executable, "-c",
        "from pathlib import Path; "
        "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 1};\\n')",
    ]

    for _ in range(2):
        build_dashboard(cwd=work, cmd=same_cmd)
        diff_text = dashboard_diff(cwd=work)
        assert diff_text.strip() == ""

    assert _commit_count(work) == before


def test_a_real_diff_produces_exactly_one_commit_containing_only_the_changed_files(tmp_path):
    work = _make_repo_with_origin(tmp_path)
    before = _commit_count(work)

    changed_cmd = [
        sys.executable, "-c",
        "from pathlib import Path; "
        "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 2};\\n')",
    ]
    build_dashboard(cwd=work, cmd=changed_cmd)
    diff_text = dashboard_diff(cwd=work)
    assert diff_text.strip() != ""

    sha = commit_and_push_dashboard(cwd=work)

    assert _commit_count(work) == before + 1
    changed_files = _git("show", "--name-only", "--format=", sha, cwd=work).stdout.split()
    assert changed_files == ["docs/dashboard/data.js"]

    # Pushed: the bare origin's main now points at the same SHA.
    origin_head = _git(
        "rev-parse", "refs/heads/main", cwd=tmp_path / "origin.git"
    ).stdout.strip()
    assert origin_head == sha


def test_deploy_dashboard_via_cli_reconciles_a_real_diff(tmp_path, monkeypatch):
    work = _make_repo_with_origin(tmp_path)
    before = _commit_count(work)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (
            sys.executable, "-c",
            "from pathlib import Path; "
            "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 3};\\n')",
        ),
    )

    rc = main(["deploy", "dashboard"])

    assert rc == EXIT_OK
    assert _commit_count(work) == before + 1


def test_deploy_dashboard_via_cli_is_a_zero_commit_noop_when_nothing_changed(tmp_path, monkeypatch):
    work = _make_repo_with_origin(tmp_path)
    before = _commit_count(work)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (
            sys.executable, "-c",
            "from pathlib import Path; "
            "Path('docs/dashboard/data.js').write_text('window.DASHBOARD_DATA = {v: 1};\\n')",
        ),
    )

    rc1 = main(["deploy", "dashboard"])
    rc2 = main(["deploy", "dashboard"])

    assert rc1 == EXIT_OK
    assert rc2 == EXIT_OK
    assert _commit_count(work) == before


def test_dashboard_diff_propagates_a_git_failure_outside_a_worktree(tmp_path):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(subprocess.CalledProcessError):
        dashboard_diff(cwd=not_a_repo)


def test_commit_and_push_reports_a_specific_failing_step_when_push_target_is_missing(tmp_path):
    """No `origin` remote configured: add+commit succeed, push fails — the
    failure is attributable to `git push` specifically via `exc.cmd`, and
    the commit made before the failure is NOT rolled back (documented
    accepted partial-completion state, this story's spec Design Notes)."""
    work = tmp_path / "work"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    (work / "docs" / "dashboard").mkdir(parents=True)
    (work / "docs" / "dashboard" / "data.js").write_text("window.DASHBOARD_DATA = {v: 1};\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)

    (work / "docs" / "dashboard" / "data.js").write_text("window.DASHBOARD_DATA = {v: 2};\n")
    before = _commit_count(work)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        commit_and_push_dashboard(cwd=work)

    assert exc_info.value.cmd[:2] == ["git", "push"]
    # The commit itself DID happen before the push failed.
    assert _commit_count(work) == before + 1
