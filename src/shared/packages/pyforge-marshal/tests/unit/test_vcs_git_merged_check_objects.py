"""Story 87.10: merged-check and merge-tree preview commits must not enter the repo object store."""

from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from pyforge.marshal.adapters import vcs_git as vcs_git_module
from pyforge.marshal.adapters.vcs_git import GitVcs


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


def _count_objects(repo: Path) -> tuple[int, int]:
    """Return (count-loose, count-in-pack) from ``git count-objects -v``."""
    result = _git(repo, "count-objects", "-v")
    loose = 0
    packed = 0
    for line in result.stdout.splitlines():
        if line.startswith("count:"):
            loose = int(line.split(":", 1)[1].strip())
        elif line.startswith("in-pack:"):
            packed = int(line.split(":", 1)[1].strip())
    return loose, packed


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


def _assert_count_objects_unchanged(repo: Path, before: tuple[int, int], fn) -> None:
    fn()
    after = _count_objects(repo)
    assert after == before, f"git count-objects changed: before={before} after={after}"


def test_is_branch_merged_unmerged_branch_does_not_mint_repo_objects(vcs, repo):
    _git(repo, "checkout", "-b", "loop/unmerged")
    (repo / "only-on-branch.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "only-on-branch.txt")
    _git(repo, "commit", "-m", "unmerged work")
    _git(repo, "checkout", "main")

    before = _count_objects(repo)

    def _check() -> None:
        assert vcs.is_branch_merged(repo, "loop/unmerged", into="main") is False

    _assert_count_objects_unchanged(repo, before, _check)


def test_is_branch_merged_squash_equivalent_branch_does_not_mint_repo_objects(vcs, repo):
    _git(repo, "checkout", "-b", "loop/squash")
    (repo / "squash.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "squash.txt")
    _git(repo, "commit", "-m", "squash content")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--squash", "loop/squash")
    _git(repo, "commit", "-m", "Merge loop/squash into main")

    before = _count_objects(repo)

    def _check() -> None:
        assert vcs.is_branch_merged(repo, "loop/squash", into="main") is True

    _assert_count_objects_unchanged(repo, before, _check)


def test_is_branch_merged_ancestor_branch_does_not_mint_repo_objects(vcs, repo):
    _git(repo, "checkout", "-b", "loop/ff")
    (repo / "ff.txt").write_text("ff\n", encoding="utf-8")
    _git(repo, "add", "ff.txt")
    _git(repo, "commit", "-m", "ff content")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "loop/ff")

    before = _count_objects(repo)

    def _check() -> None:
        assert vcs.is_branch_merged(repo, "loop/ff", into="main") is True

    _assert_count_objects_unchanged(repo, before, _check)


def test_add_worktree_for_tree_does_not_mint_repo_objects(vcs, repo, tmp_path):
    _git(repo, "checkout", "-b", "feature/preview")
    (repo / "preview.txt").write_text("preview\n", encoding="utf-8")
    _git(repo, "add", "preview.txt")
    _git(repo, "commit", "-m", "preview feature")
    feature_sha = _git(repo, "rev-parse", "feature/preview").stdout.strip()
    _git(repo, "checkout", "main")

    tree_oid = vcs.merge_tree_write(repo, "main", "feature/preview")
    assert tree_oid is not None
    home = tmp_path / "preview-home"

    before = _count_objects(repo)

    def _check() -> None:
        vcs.add_worktree_for_tree(repo, home, tree_oid, parent=feature_sha)
        assert (home / "preview.txt").read_text(encoding="utf-8") == "preview\n"

    _assert_count_objects_unchanged(repo, before, _check)
    vcs.remove_worktree(repo, home, force=True)


def test_is_branch_merged_fails_when_synthetic_commit_enters_repo_store(vcs, repo, monkeypatch):
    """Mutation guard: writing the virtual commit into the repository store increases loose objects."""
    _git(repo, "checkout", "-b", "loop/mutation")
    (repo / "mutation.txt").write_text("m\n", encoding="utf-8")
    _git(repo, "add", "mutation.txt")
    _git(repo, "commit", "-m", "mutation branch")
    _git(repo, "checkout", "main")

    before = _count_objects(repo)

    @contextmanager
    def _repo_store_commit_tree(_repo_root: Path):
        yield os.environ.copy()

    monkeypatch.setattr(vcs_git_module, "_ephemeral_git_object_env", _repo_store_commit_tree)

    vcs.is_branch_merged(repo, "loop/mutation", into="main")
    after = _count_objects(repo)
    assert after[0] > before[0], "expected loose object count to rise when ephemeral store is bypassed"
