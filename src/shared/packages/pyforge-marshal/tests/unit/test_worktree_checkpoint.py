"""Story 34.2: worktree auto-checkpoint unit tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core.worktree_checkpoint import (
    auto_checkpoint_message,
    commit_worktree_checkpoint,
    is_auto_checkpoint_subject,
    should_checkpoint_on_idle,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


def test_auto_checkpoint_message_format() -> None:
    assert auto_checkpoint_message("34.2") == "wip: 34.2 (auto-checkpoint)"
    assert is_auto_checkpoint_subject(auto_checkpoint_message("34.2"))


def test_should_checkpoint_on_idle_requires_dirty_worktree() -> None:
    assert not should_checkpoint_on_idle(
        idle_elapsed_s=120.0,
        threshold_s=60.0,
        has_uncommitted_changes=False,
    )
    assert should_checkpoint_on_idle(
        idle_elapsed_s=120.0,
        threshold_s=60.0,
        has_uncommitted_changes=True,
    )


def test_should_checkpoint_on_idle_waits_for_threshold() -> None:
    assert not should_checkpoint_on_idle(
        idle_elapsed_s=30.0,
        threshold_s=60.0,
        has_uncommitted_changes=True,
    )


def test_commit_worktree_checkpoint_no_op_on_clean_worktree(vcs: GitVcs, repo: Path) -> None:
    result = commit_worktree_checkpoint(
        vcs,
        repo_root=repo,
        worktree=repo,
        story_key="34.2",
    )
    assert result.committed is False
    assert result.skipped_reason == "clean worktree"


def test_commit_worktree_checkpoint_commits_dirty_worktree(vcs: GitVcs, repo: Path) -> None:
    (repo / "wip.txt").write_text("progress\n", encoding="utf-8")
    result = commit_worktree_checkpoint(
        vcs,
        repo_root=repo,
        worktree=repo,
        story_key="34.2",
    )
    assert result.committed is True
    assert result.head_sha
    assert vcs.has_uncommitted_changes(repo) is False
    subjects = vcs.commit_subjects(repo, "HEAD")
    assert subjects[0] == auto_checkpoint_message("34.2")


def test_crash_after_checkpoint_leaves_progress_in_a_commit_not_worktree(
    vcs: GitVcs, repo: Path, tmp_path: Path
) -> None:
    """Simulate mid-session crash: checkpoint first, then force-remove worktree."""
    worktree = tmp_path / "dispatch-home"
    _git(repo, "worktree", "add", "-b", "dispatch/story-34-2", str(worktree), "main")
    target = worktree / "src" / "feature.py"
    target.parent.mkdir(parents=True)
    target.write_text("real progress\n", encoding="utf-8")

    result = commit_worktree_checkpoint(
        vcs,
        repo_root=repo,
        worktree=worktree,
        story_key="34.2",
    )
    assert result.committed is True
    saved_sha = result.head_sha
    assert vcs.has_uncommitted_changes(worktree) is False

    _git(repo, "worktree", "remove", "--force", str(worktree))

    subjects = _git(repo, "log", "-1", "--format=%s", saved_sha).stdout.strip()
    assert subjects == auto_checkpoint_message("34.2")
    show = _git(repo, "show", f"{saved_sha}:src/feature.py").stdout
    assert "real progress" in show
