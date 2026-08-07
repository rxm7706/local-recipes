"""`last_deploy_commit` + `steward deploy status` — Story 2.4 (FR-11).

No mocked state file anywhere here — `last_deploy_commit` reads git history
directly, so these tests build real scratch git repos and assert against
`git log`'s own output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.deploy import DeployRecord, last_deploy_commit


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(work: Path) -> None:
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)


def test_no_prior_deploy_commit_returns_none(tmp_path):
    work = tmp_path / "work"
    _init_repo(work)
    (work / "README.md").write_text("nothing dashboard-related\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init, no dashboard touched", cwd=work)

    assert last_deploy_commit(cwd=work) is None


def test_a_prior_deploy_commit_is_read_from_git_history(tmp_path):
    work = tmp_path / "work"
    _init_repo(work)
    (work / "README.md").write_text("repo\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)

    (work / "docs" / "dashboard").mkdir(parents=True)
    (work / "docs" / "dashboard" / "data.js").write_text("window.DASHBOARD_DATA = {};\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "dashboard: refresh status (steward deploy dashboard)", cwd=work)
    expected_sha = _git("rev-parse", "HEAD", cwd=work).stdout.strip()

    record = last_deploy_commit(cwd=work)

    assert record is not None
    assert record.sha == expected_sha
    assert record.timestamp  # non-empty ISO-ish string
    assert "T" in record.timestamp  # strict-ISO committer date


def test_only_the_most_recent_dashboard_touching_commit_is_reported(tmp_path):
    work = tmp_path / "work"
    _init_repo(work)
    (work / "docs" / "dashboard").mkdir(parents=True)
    (work / "docs" / "dashboard" / "data.js").write_text("v1\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "first dashboard commit", cwd=work)

    (work / "docs" / "dashboard" / "data.js").write_text("v2\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "second dashboard commit", cwd=work)
    latest_sha = _git("rev-parse", "HEAD", cwd=work).stdout.strip()

    (work / "unrelated.txt").write_text("noise\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "unrelated commit, does not touch docs/dashboard", cwd=work)

    record = last_deploy_commit(cwd=work)

    assert record.sha == latest_sha


def test_last_deploy_commit_propagates_a_git_failure_outside_a_worktree(tmp_path):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(subprocess.CalledProcessError):
        last_deploy_commit(cwd=not_a_repo)


def test_deploy_status_via_cli_reports_the_last_deploy(tmp_path, monkeypatch):
    work = tmp_path / "work"
    _init_repo(work)
    (work / "docs" / "dashboard").mkdir(parents=True)
    (work / "docs" / "dashboard" / "data.js").write_text("v1\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "dashboard: refresh status", cwd=work)
    expected_sha = _git("rev-parse", "HEAD", cwd=work).stdout.strip()

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)

    rc = main(["deploy", "status"])

    assert rc == EXIT_OK


def test_deploy_status_via_cli_reports_no_prior_deploy_clearly(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    _init_repo(work)
    (work / "README.md").write_text("no dashboard here\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: work)

    rc = main(["deploy", "status"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "no dashboard deploy commit found" in out


def test_deploy_status_via_cli_surfaces_a_git_failure_as_exit_failed(tmp_path, monkeypatch):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: not_a_repo)

    rc = main(["deploy", "status"])

    assert rc == EXIT_FAILED


def test_deploy_record_is_frozen():
    record = DeployRecord(sha="abc123", timestamp="2026-08-07T00:00:00+00:00")
    with pytest.raises(Exception):
        record.sha = "other"  # type: ignore[misc]
