"""Story 70.1 (spec-pyforge-steward CAP-158): a local branch or tag named like the workspace's source
(``origin/main``) or its branch never stands in for them in ``workspace start``, ``status`` or ``clean``.

Git resolves a short name to ``refs/tags/<n>`` and ``refs/heads/<n>`` before ``refs/remotes/<n>``, so every
git read of a recorded source ``origin/<b>`` names ``refs/remotes/origin/<b>``, and every read of the
workspace's branch names ``refs/heads/<branch>``. Recorded sources stay as written."""

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


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Bare origin + work checkout on main, with the scripts/bmad-loop-worktree marker."""
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


def _shadow(kind: str, name: str, at: str, *, cwd: Path) -> None:
    _git(kind, name, at, cwd=cwd)


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_start_branches_from_the_remote_past_a_shadow(repo: Path, tmp_path: Path, kind: str) -> None:
    _git("commit", "--allow-empty", "-m", "local only", cwd=repo)
    _shadow(kind, "origin/main", "HEAD", cwd=repo)
    bookkeeping = repo / ".steward" / "workspaces.yaml"

    record = start_workspace("fresh", root=repo, bookkeeping=bookkeeping, path=tmp_path / "fresh")

    assert _git("rev-parse", "HEAD", cwd=tmp_path / "fresh") == _git("rev-parse", "refs/remotes/origin/main", cwd=repo)
    assert record.source == "origin/main"  # recorded as written


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_clean_merged_only_keeps_an_unmerged_branch_past_a_source_shadow(repo: Path, tmp_path: Path, kind: str) -> None:
    """The trap: a shadow at the unmerged tip read the branch as merged, so ``clean --merged-only`` removed the
    worktree and deleted the branch -- its commits left reachable only through the stray ref."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "unmerged"
    start_workspace("unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)
    _shadow(kind, "origin/main", _git("rev-parse", "HEAD", cwd=dest), cwd=repo)

    result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive")

    assert result["archived"] == []
    assert [row["reason"] for row in result["skipped"]] == ["not-merged"]
    assert dest.is_dir()
    assert _git("rev-parse", "--verify", "refs/heads/unmerged", cwd=repo)
    assert len(load_bookkeeping(bookkeeping)) == 1


def test_clean_merged_only_keeps_an_unmerged_branch_past_a_branch_name_tag(repo: Path, tmp_path: Path) -> None:
    """A tag named like the workspace's branch, on the source, stood in for the branch in the merged check."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "unmerged"
    start_workspace("unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)
    _shadow("tag", "unmerged", "refs/remotes/origin/main", cwd=repo)

    result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive")

    assert [row["reason"] for row in result["skipped"]] == ["not-merged"]
    assert dest.is_dir()


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_status_reads_the_remote_past_a_shadow(repo: Path, tmp_path: Path, kind: str) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "ahead"
    start_workspace("ahead", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)
    _shadow(kind, "origin/main", _git("rev-parse", "HEAD", cwd=dest), cwd=repo)

    (row,) = status_workspaces(root=repo, bookkeeping=bookkeeping)

    assert row.error is None
    assert (row.ahead, row.behind, row.merged) == (1, 0, False)


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_a_confirmed_clean_keeps_an_unmerged_branch_past_a_shadow(repo: Path, tmp_path: Path, kind: str) -> None:
    """The branch-drop proof read the source short: a confirmed (not ``--merged-only``) clean past a shadow at the
    unmerged tip archived the files and then deleted the branch, whose history a tarball does not hold."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "unmerged"
    start_workspace("unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)
    tip = _git("rev-parse", "HEAD", cwd=dest)
    _shadow(kind, "origin/main", tip, cwd=repo)

    result = clean_workspaces(
        slug="unmerged", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive", confirm=lambda s: True
    )

    (row,) = result["archived"]
    assert row["archive"].endswith(".tar.gz")
    assert _git("rev-parse", "--verify", "refs/heads/unmerged", cwd=repo) == tip


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_a_landed_worktree_past_a_shadow_leaves_a_note(repo: Path, tmp_path: Path, kind: str) -> None:
    """The landed proof asked git for the short source and refused whatever was not under ``refs/remotes/``, so a
    shadow turned a provable landing into a tarball; it now asks for the remote-tracking ref itself."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "landed"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "local only", cwd=repo)
    _shadow(kind, "origin/main", "HEAD", cwd=repo)

    result = clean_workspaces(
        slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive", confirm=lambda s: True
    )

    (row,) = result["archived"]
    assert row["archive"].endswith(".landed.txt")
    assert not dest.exists()


def test_a_slug_that_begins_refs_is_read_as_its_own_branch(repo: Path, tmp_path: Path) -> None:
    """``start`` creates ``refs/heads/<slug>`` whatever the slug; a slug beginning ``refs/`` must not be read as a
    different, full ref -- ``refs/heads/main`` read as the real ``main`` made an unmerged workspace look merged."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "refs-slug"
    start_workspace("refs/heads/main", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)

    (row,) = status_workspaces(root=repo, bookkeeping=bookkeeping)

    assert (row.ahead, row.merged) == (1, False)


def test_a_merged_workspace_still_cleans_with_no_shadow(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "landed"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")

    result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive")

    assert [row["slug"] for row in result["archived"]] == ["landed"]
    assert not dest.exists()
