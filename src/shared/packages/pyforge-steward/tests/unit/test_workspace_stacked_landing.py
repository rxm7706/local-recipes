"""Story 13.6 -- a workspace started ``--from`` another branch is landed once its branch is on ``origin/main``.

``start --from <branch>`` records that branch as the source. Once the work lands on main the local source branch
never moves again, so judging only against it left a landed workspace ``unmerged`` in ``status``, skipped as
``not-merged`` by ``clean --delete`` and ``--merged-only``, and archived as a tarball instead of a note.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.steward import workspace as ws_module
from pyforge.steward.workspace import (
    WorkspaceRecord,
    clean_workspaces,
    load_bookkeeping,
    save_bookkeeping,
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
    purge_dir = work / "docs" / "governance"
    purge_dir.mkdir(parents=True)
    (purge_dir / "preserve-purge-list.json").write_text(
        json.dumps({"schema_version": 1, "commit_shas": [], "paths": []}), encoding="utf-8"
    )
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
    assert "recorded source: base\n" in note
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


#: Local refs git's name lookup reads for the trunk when ``refs/remotes/origin/main`` is missing: by its full name
#: (``refs/heads/refs/remotes/origin/main``, Story 13.6 review 1) and by its short name (``refs/heads/origin/main``).
TRUNK_SHADOWS = ("refs/heads/refs/remotes/origin/main", "refs/heads/origin/main")


def _shadow_the_trunk(repo: Path, sha: str, shadow: str = TRUNK_SHADOWS[0]) -> None:
    """No remote-tracking ``origin/main``, and a local ref named like it at ``sha``."""
    _git("update-ref", "-d", "refs/remotes/origin/main", cwd=repo)
    _git("update-ref", shadow, sha, cwd=repo)


@pytest.mark.parametrize("shadow", TRUNK_SHADOWS)
def test_a_local_ref_named_like_the_trunk_never_lands_a_stacked_workspace(
    repo: Path, tmp_path: Path, shadow: str
) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    _shadow_the_trunk(repo, _git("rev-parse", "refs/heads/stacked", cwd=repo).stdout.strip(), shadow)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.error is None
    assert row.merged is False
    merged_only = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert merged_only["skipped"][0]["reason"] == "not-merged"
    deleted = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert deleted["skipped"][0]["reason"] == "not-merged"
    assert stacked.is_dir()
    assert _branch_exists(repo, "stacked")
    # The landed proof must not read the shadow either: the default clean archives a tarball and keeps the branch.
    archived = clean_workspaces(
        slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a", confirm=lambda _slug: True
    )
    (row,) = archived["archived"]
    assert row["archive"].endswith(".tar.gz")
    assert row["branch_kept"] == "stacked"


def test_a_local_ref_named_like_origin_main_never_lands_an_origin_main_workspace(repo: Path, tmp_path: Path) -> None:
    """The same shadow for a workspace started from ``origin/main``: the source cannot be read, so it is an error."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "plain-wt"
    start_workspace("plain", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    _commit(wt, "plain.txt")
    _shadow_the_trunk(repo, _git("rev-parse", "refs/heads/plain", cwd=repo).stdout.strip())
    result = clean_workspaces(
        merged_only=True, slug="plain", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert result["skipped"][0]["reason"].startswith("error: git merge-base --is-ancestor plain origin/main failed")
    assert wt.is_dir()
    assert _branch_exists(repo, "plain")


def _detach_with_a_commit(stacked: Path) -> str:
    _git("checkout", "--detach", cwd=stacked)
    _commit(stacked, "detached.txt")
    return _git("rev-parse", "HEAD", cwd=stacked).stdout.strip()


def test_merged_only_keeps_a_landed_stacked_workspace_whose_detached_head_is_not_landed(
    repo: Path, tmp_path: Path
) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _detach_with_a_commit(stacked)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "not-merged"
    assert stacked.is_dir()
    assert _branch_exists(repo, "stacked")


def test_clean_parks_a_detached_head_past_a_landed_branch_as_a_preserve_tag(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ws_module, "workspace_preserve_tag_enabled", lambda **_kwargs: True)
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    detached = _detach_with_a_commit(stacked)
    result = clean_workspaces(
        slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a", confirm=lambda _slug: True
    )
    (row,) = result["archived"]
    tag = row["preserve_tag"]
    assert _git("rev-parse", f"{tag}^{{commit}}", cwd=repo).stdout.strip() == detached
    assert not stacked.exists()


def test_delete_drops_a_landed_stacked_branch_whose_worktree_is_gone(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("worktree", "remove", str(stacked), cwd=repo)
    assert _branch_exists(repo, "stacked")
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["deleted"]] == ["stacked"]
    assert not _branch_exists(repo, "stacked")


def test_a_gone_worktree_whose_branch_is_on_neither_ref_names_both(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    _git("worktree", "remove", str(stacked), cwd=repo)
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "branch stacked not on base or origin/main"
    assert _branch_exists(repo, "stacked")


def test_the_proof_takes_the_landing_ref_that_holds_the_worktree_not_the_first_that_resolves(
    repo: Path, tmp_path: Path
) -> None:
    """A remote source that resolves but does not hold the worktree gives way to the trunk."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    base = tmp_path / "base-wt"
    start_workspace("base", root=repo, bookkeeping=bookkeeping, path=base, from_ref="origin/main")
    _commit(base, "base.txt")
    _git("push", "origin", "base", cwd=repo)
    stacked = tmp_path / "stacked-wt"
    start_workspace("stacked", root=repo, bookkeeping=bookkeeping, path=stacked, from_ref="origin/base")
    _commit(stacked, "stacked.txt")
    _git("merge", "--no-ff", "-m", "Merge stacked", "stacked", cwd=repo)
    _git("push", "origin", "main", cwd=repo)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    (row,) = result["archived"]
    note = Path(row["archive"]).read_text(encoding="utf-8")
    assert "on source: origin/main at " in note
    assert "recorded source: origin/base\n" in note
    assert not _branch_exists(repo, "stacked")


def test_an_unresolvable_source_with_an_unlanded_commit_still_archives(repo: Path, tmp_path: Path) -> None:
    """The trunk is present but does not hold the worktree: no proof, so a tarball, and the branch is kept."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "unproven-wt"
    start_workspace("unproven", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    _commit(wt, "unlanded.txt")
    records = tuple(
        r if r.slug != "unproven" else WorkspaceRecord(r.slug, r.path, r.branch, "origin/gone", r.created_at)
        for r in load_bookkeeping(bookkeeping)
    )
    save_bookkeeping(bookkeeping, records)
    result = clean_workspaces(
        slug="unproven", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a", confirm=lambda _slug: True
    )
    (row,) = result["archived"]
    assert row["archive"].endswith(".tar.gz")
    assert row["branch_kept"] == "unproven"


def test_a_local_ref_named_like_an_origin_source_never_lands_it(repo: Path, tmp_path: Path) -> None:
    """Review 2: the non-trunk half of "by commit, never by name" -- a pruned ``origin/base`` and a local
    ``refs/heads/refs/remotes/origin/base`` at the unlanded tip."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    base = tmp_path / "base-wt"
    start_workspace("base", root=repo, bookkeeping=bookkeeping, path=base, from_ref="origin/main")
    _commit(base, "base.txt")
    _git("push", "origin", "base", cwd=repo)
    stacked = tmp_path / "stacked-wt"
    start_workspace("stacked", root=repo, bookkeeping=bookkeeping, path=stacked, from_ref="origin/base")
    _commit(stacked, "stacked.txt")
    tip = _git("rev-parse", "refs/heads/stacked", cwd=repo).stdout.strip()
    _git("update-ref", "-d", "refs/remotes/origin/base", cwd=repo)
    _git("update-ref", "refs/heads/refs/remotes/origin/base", tip, cwd=repo)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.merged is not True
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert stacked.is_dir()
    assert _branch_exists(repo, "stacked")


def test_a_full_ref_source_is_read_by_commit_too(repo: Path, tmp_path: Path) -> None:
    """Review 2: a source recorded as ``refs/remotes/origin/main``, whose remote-tracking ref is gone, with a local
    branch of that full name at the unlanded tip, is never a landing."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "full-wt"
    start_workspace("full", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="refs/remotes/origin/main")
    _commit(wt, "full.txt")
    _shadow_the_trunk(repo, _git("rev-parse", "refs/heads/full", cwd=repo).stdout.strip())
    (row,) = status_workspaces("full", root=repo, bookkeeping=bookkeeping)
    assert row.merged is not True
    result = clean_workspaces(
        merged_only=True, slug="full", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert wt.is_dir()
    assert _branch_exists(repo, "full")


def test_a_trunk_shadowed_while_present_still_proves_a_landing(repo: Path, tmp_path: Path) -> None:
    """Review 2: with both ``refs/remotes/origin/main`` and ``refs/heads/refs/remotes/origin/main``, git's name
    lookup only reports ambiguity; the exact lookup still reads the remote-tracking ref."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    plain = tmp_path / "plain-wt"
    start_workspace("plain", root=repo, bookkeeping=bookkeeping, path=plain, from_ref="origin/main")
    _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("update-ref", "refs/heads/refs/remotes/origin/main", "refs/heads/stacked", cwd=repo)
    rows = {row.slug: row for row in status_workspaces(root=repo, bookkeeping=bookkeeping)}
    assert rows["plain"].error is None and rows["plain"].merged is True
    assert rows["stacked"].error is None and rows["stacked"].merged is True
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["deleted"]] == ["stacked"]


def test_merged_only_cleans_a_landed_stacked_branch_whose_worktree_is_gone(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("worktree", "remove", str(stacked), cwd=repo)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["archived"]] == ["stacked"]
    assert not _branch_exists(repo, "stacked")


def test_an_unborn_head_leaves_the_branch_verdict_as_before(repo: Path, tmp_path: Path) -> None:
    """Review 2: a HEAD git cannot read names no commit to lose; ``--merged-only`` cleans a landed workspace as before."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "unborn-wt"
    start_workspace("unborn", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    _git("checkout", "--orphan", "never-committed", cwd=wt)
    result = clean_workspaces(
        merged_only=True, slug="unborn", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["archived"]] == ["unborn"]
    assert not wt.exists()
