"""Story 83.19: dispatch never commits the CFE surface outside a sanctioned retro."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.testing_kit.cfe_surface import CFE_CHANGELOG_PATH

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core.dispatch_cfe_commit import (
    CFE_COMMIT_GATE_CODE,
    RETRO_CFE_COMMIT_SUBJECT,
    commit_pending_cfe_retro,
    findings_for_unsanctioned_cfe_commits,
    paths_excluding_cfe,
)
from pyforge.marshal.core.worktree_checkpoint import auto_checkpoint_message, commit_worktree_checkpoint

_CFE_TEST = ".claude/skills/conda-forge-expert/tests/meta/test_example.py"


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
    cfe_dir = repo / ".claude" / "skills" / "conda-forge-expert" / "tests" / "meta"
    cfe_dir.mkdir(parents=True)
    (cfe_dir / "test_example.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / ".claude" / "skills" / "conda-forge-expert" / "CHANGELOG.md").write_text(
        "# Changelog\n", encoding="utf-8"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "branch", "story")
    _git(repo, "checkout", "story")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


def test_paths_excluding_cfe_partitions() -> None:
    non_cfe = paths_excluding_cfe(("src/a.py", _CFE_TEST))
    assert len(non_cfe) == 1
    assert non_cfe[0].as_posix() == "src/a.py"


def test_auto_checkpoint_leaves_cfe_uncommitted(vcs: GitVcs, repo: Path) -> None:
    (repo / "wip.txt").write_text("x\n", encoding="utf-8")
    cfe_file = repo / _CFE_TEST
    cfe_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")

    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")
    assert result.committed is True
    assert vcs.has_uncommitted_changes(repo) is True
    show = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout
    assert _CFE_TEST not in show
    assert "wip.txt" in show


def test_commit_pending_cfe_retro_refuses_without_changelog(vcs: GitVcs, repo: Path) -> None:
    cfe_file = repo / _CFE_TEST
    cfe_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")
    dirty = vcs.changed_files(repo, repo, base="HEAD")
    outcome = commit_pending_cfe_retro(vcs, worktree=repo, changed_paths=dirty)
    assert outcome.committed is False
    assert outcome.finding is not None
    assert outcome.finding.code == CFE_COMMIT_GATE_CODE
    assert "Rule 2" in outcome.finding.message


def test_commit_pending_cfe_retro_commits_with_changelog(vcs: GitVcs, repo: Path) -> None:
    cfe_file = repo / _CFE_TEST
    cfe_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")
    changelog = repo / CFE_CHANGELOG_PATH
    changelog.write_text("# Changelog\n\n## 8.99.0\n", encoding="utf-8")
    dirty = vcs.changed_files(repo, repo, base="HEAD")
    outcome = commit_pending_cfe_retro(vcs, worktree=repo, changed_paths=dirty)
    assert outcome.committed is True
    assert outcome.finding is None
    subject = _git(repo, "log", "-1", "--format=%s").stdout.strip()
    assert subject == RETRO_CFE_COMMIT_SUBJECT
    show = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout
    assert CFE_CHANGELOG_PATH in show
    assert _CFE_TEST in show


def test_unsanctioned_commits_finding_for_wip_checkpoint(vcs: GitVcs, repo: Path) -> None:
    cfe_file = repo / _CFE_TEST
    cfe_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")
    vcs.commit_paths(
        repo,
        (cfe_file,),
        __import__("pyforge.marshal.core.egress", fromlist=["to_redacted_text"]).to_redacted_text(
            auto_checkpoint_message("83.19")
        ),
    )
    findings = findings_for_unsanctioned_cfe_commits(repo, base="main")
    assert len(findings) == 1
    assert findings[0].code == CFE_COMMIT_GATE_CODE


def test_mutation_checkpoint_without_cfe_filter_commits_cfe(vcs: GitVcs, repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Removing the CFE filter must put CFE paths in a wip: commit (mutation guard)."""
    import pyforge.marshal.core.worktree_checkpoint as wc

    monkeypatch.setattr(wc, "paths_excluding_cfe", lambda paths: tuple(Path(p) for p in paths))
    cfe_file = repo / _CFE_TEST
    cfe_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")
    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")
    assert result.committed is True
    show = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout
    assert _CFE_TEST in show
