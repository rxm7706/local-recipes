"""Story 13.6 -- a workspace started ``--from`` another branch is landed once its branch is on ``origin/main``.

``start --from <branch>`` records that branch as the source. Once the work lands on main the local source branch
never moves again, so judging only against it left a landed workspace ``unmerged`` in ``status``, skipped as
``not-merged`` by ``clean --delete`` and ``--merged-only``, and archived as a tarball instead of a note.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.steward.workspace import (
    clean_workspaces,
    load_bookkeeping,
    start_workspace,
    status_workspaces,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _branch_exists(repo: Path, branch: str) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=repo, capture_output=True
        ).returncode
        == 0
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    work = tmp_path / "local-recipes"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    (work / "scripts").mkdir()
    (work / "scripts" / "bmad-loop-worktree").write_text("#!/usr/bin/env true\n", encoding="utf-8")
    (work / "README.md").write_text("scratch\n", encoding="utf-8")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


def _commit(wt: Path, name: str) -> None:
    (wt / name).write_text(f"{name}\n", encoding="utf-8")
    _git("add", name, cwd=wt)
    _git("commit", "-m", name, cwd=wt)


def _stacked(repo: Path, tmp_path: Path, bookkeeping: Path, *, land: bool) -> Path:
    """A ``base`` workspace off ``origin/main`` with one commit, and a ``stacked`` one ``--from base`` with another.

    With ``land``, ``stacked`` merges into ``main`` and is pushed, as a PR merge would; the local ``base`` branch, the
    stacked workspace's recorded source, stays where it was.
    """
    base = tmp_path / "base-wt"
    start_workspace("base", root=repo, bookkeeping=bookkeeping, path=base, from_ref="origin/main")
    _commit(base, "base.txt")
    stacked = tmp_path / "stacked-wt"
    start_workspace("stacked", root=repo, bookkeeping=bookkeeping, path=stacked, from_ref="base")
    _commit(stacked, "stacked.txt")
    if land:
        _git("merge", "--no-ff", "-m", "Merge stacked", "stacked", cwd=repo)
        _git("push", "origin", "main", cwd=repo)
    return stacked


def test_status_reads_a_landed_stacked_workspace_merged(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _stacked(repo, tmp_path, bookkeeping, land=True)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.source == "base"
    assert row.merged is True


def test_delete_removes_a_landed_stacked_workspace(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    result = clean_workspaces(delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)
    assert [row["slug"] for row in result["deleted"]] == ["stacked"]
    assert result["skipped"] == []
    assert not stacked.exists()
    assert not _branch_exists(repo, "stacked")
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["base"]
    assert not archive_dir.exists() or not list(archive_dir.iterdir())


def test_merged_only_leaves_a_note_for_a_landed_stacked_workspace(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir
    )
    (row,) = result["archived"]
    assert row["archive"].endswith(".landed.txt")
    assert "branch_kept" not in row
    note = Path(row["archive"]).read_text(encoding="utf-8")
    assert "on source: origin/main at " in note
    assert not stacked.exists()
    assert not _branch_exists(repo, "stacked")


def test_an_unlanded_stacked_workspace_is_still_refused(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.merged is False
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["deleted"] == []
    assert result["skipped"][0]["reason"] == "not-merged"
    assert stacked.is_dir()
    assert _branch_exists(repo, "stacked")


def test_a_landed_stacked_workspace_whose_source_branch_is_gone_is_deleted(repo: Path, tmp_path: Path) -> None:
    """The base branch is often deleted once it lands; the trunk still proves the stacked branch landed.

    ``status`` still reports the row unreachable, as before: its ahead/behind count needs the recorded source.
    """
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("worktree", "remove", str(tmp_path / "base-wt"), cwd=repo)
    _git("branch", "-D", "base", cwd=repo)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.merged is None and row.error is not None
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["deleted"]] == ["stacked"]
    assert not stacked.exists()
    assert not _branch_exists(repo, "stacked")


def test_a_repository_without_the_trunk_keeps_the_source_verdict(repo: Path, tmp_path: Path) -> None:
    """A repo-set member may have no ``origin/main``: the trunk then answers "not landed there", never an error."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    _git("update-ref", "-d", "refs/remotes/origin/main", cwd=repo)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.error is None
    assert row.merged is False
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "not-merged"
    assert stacked.is_dir()
