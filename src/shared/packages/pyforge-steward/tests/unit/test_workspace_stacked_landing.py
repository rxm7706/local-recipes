"""Story 13.6 -- a workspace started ``--from`` another branch is landed once its branch is on ``origin/main``.

``start --from <branch>`` records that branch as the source. Once the work lands on main the local source branch
never moves again, so judging only against it left a landed workspace ``unmerged`` in ``status``, skipped as
``not-merged`` by ``clean --delete`` and ``--merged-only``, and archived as a tarball instead of a note.
"""

from __future__ import annotations

import json
import shutil
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


@pytest.mark.parametrize("shadow", ["refs/heads/refs/remotes/origin/base", "refs/heads/origin/base"])
def test_a_local_ref_named_like_an_origin_source_never_lands_it(repo: Path, tmp_path: Path, shadow: str) -> None:
    """Reviews 2 and 3: the non-trunk half of "by commit, never by name" -- a pruned ``origin/base`` and a local ref
    named like it (by full or short name) at the unlanded tip."""
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
    _git("update-ref", shadow, tip, cwd=repo)
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


def _landed_origin_main_workspace_with_a_detached_commit(repo: Path, tmp_path: Path, bookkeeping: Path) -> Path:
    """An ``origin/main`` workspace whose branch is on main (it has no commit of its own), detached at one more."""
    wt = tmp_path / "detached-wt"
    start_workspace("detached", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    _git("checkout", "--detach", cwd=wt)
    _commit(wt, "detached.txt")
    return wt


def test_a_broken_git_link_still_names_the_detached_head(repo: Path, tmp_path: Path) -> None:
    """Review 3: with the worktree's ``.git`` link broken, HEAD is read as the repository records it."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed_origin_main_workspace_with_a_detached_commit(repo, tmp_path, bookkeeping)
    (wt / ".git").write_text(f"gitdir: {tmp_path / 'nowhere'}\n", encoding="utf-8")
    result = clean_workspaces(
        merged_only=True, slug="detached", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert result["skipped"][0]["reason"] == "not-merged"
    assert wt.is_dir()


def test_a_detached_head_past_a_landed_branch_whose_source_is_gone_is_kept(repo: Path, tmp_path: Path) -> None:
    """Review 3: HEAD the source cannot place and the trunk does not hold is not landed (mutant mE)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("worktree", "remove", str(tmp_path / "base-wt"), cwd=repo)
    _git("branch", "-D", "base", cwd=repo)
    _detach_with_a_commit(stacked)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert stacked.is_dir()


def test_a_local_full_ref_source_proves_nothing(repo: Path, tmp_path: Path) -> None:
    """Review 3 (mutant mN): only a remote-tracking ref is a landing; ``refs/heads/base`` holding the worktree is not."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    base = tmp_path / "base-wt"
    start_workspace("base", root=repo, bookkeeping=bookkeeping, path=base, from_ref="origin/main")
    _commit(base, "base.txt")
    wt = tmp_path / "on-base-wt"
    start_workspace("on-base", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="refs/heads/base")
    result = clean_workspaces(
        slug="on-base", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a", confirm=lambda _slug: True
    )
    (row,) = result["archived"]
    assert row["archive"].endswith(".tar.gz")


def _add_upstream(repo: Path, tmp_path: Path) -> None:
    upstream = tmp_path / "upstream.git"
    subprocess.run(["git", "init", "--bare", str(upstream)], check=True, capture_output=True)
    _git("remote", "add", "upstream", str(upstream), cwd=repo)
    _git("push", "upstream", "main", cwd=repo)


def test_a_landing_on_another_remote_still_proves_it(repo: Path, tmp_path: Path) -> None:
    """Review 3: ``upstream/main`` proved landings before this story and still does."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _add_upstream(repo, tmp_path)
    wt = tmp_path / "up-wt"
    start_workspace("up", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="upstream/main")
    _commit(wt, "up.txt")
    _git("merge", "--no-ff", "-m", "Merge up", "up", cwd=repo)
    _git("push", "upstream", "main", cwd=repo)
    result = clean_workspaces(delete=True, slug="up", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a")
    assert [r["slug"] for r in result["deleted"]] == ["up"]
    assert not wt.exists()


def test_a_workspace_named_like_its_remote_source_is_never_compared_with_itself(repo: Path, tmp_path: Path) -> None:
    """Review 3 (before this story too): slug and branch ``upstream/main`` started from ``upstream/main``; read by
    name, the source was the branch itself and ``--merged-only`` deleted it with an unlanded commit."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _add_upstream(repo, tmp_path)
    wt = tmp_path / "self-wt"
    start_workspace("upstream/main", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="upstream/main")
    _commit(wt, "self.txt")
    (row,) = status_workspaces("upstream/main", root=repo, bookkeeping=bookkeeping)
    assert row.merged is False
    result = clean_workspaces(
        merged_only=True, slug="upstream/main", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert _branch_exists(repo, "upstream/main")


def test_a_revision_source_is_read_as_recorded(repo: Path, tmp_path: Path) -> None:
    """Review 3: ``origin/main~0`` is no refname, so it is read through ``_source_ref`` as at the baseline: no error
    row."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "rev-wt"
    start_workspace("rev", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main~0")
    _commit(wt, "rev.txt")
    (row,) = status_workspaces("rev", root=repo, bookkeeping=bookkeeping)
    assert row.error is None
    assert row.merged is False


def test_without_an_origin_remote_a_branch_named_like_the_trunk_proves_nothing(repo: Path, tmp_path: Path) -> None:
    """Review 4 (N1): in an ``upstream``-only repository, the trunk ``origin/main`` is still a remote-tracking name;
    the workspace's own branch ``origin/main`` is never read as it."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _git("remote", "rename", "origin", "upstream", cwd=repo)
    wt = tmp_path / "named-wt"
    start_workspace("origin/main", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="upstream/main")
    _commit(wt, "named.txt")
    (row,) = status_workspaces("origin/main", root=repo, bookkeeping=bookkeeping)
    assert row.merged is False
    result = clean_workspaces(
        merged_only=True, slug="origin/main", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert _branch_exists(repo, "origin/main")


def test_with_the_origin_remote_unconfigured_its_refs_still_decide(repo: Path, tmp_path: Path) -> None:
    """Review 4 (N3): ``remote.origin`` removed from config, its refs kept, and a local ``origin/main`` at the unlanded
    tip: the remote-tracking ref decides."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    _git("config", "--remove-section", "remote.origin", cwd=repo)
    _git("update-ref", "refs/heads/origin/main", "refs/heads/stacked", cwd=repo)
    (row,) = status_workspaces("stacked", root=repo, bookkeeping=bookkeeping)
    assert row.merged is False
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert stacked.is_dir()


def test_a_garbage_head_file_is_not_an_unborn_head(repo: Path, tmp_path: Path) -> None:
    """Review 4: git lists an unreadable HEAD file as forty zeros with no branch line; that is not unborn."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "garbage-wt"
    start_workspace("garbage", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    gitdir = Path(_git("rev-parse", "--absolute-git-dir", cwd=wt).stdout.strip())
    (gitdir / "HEAD").write_text("garbage\n", encoding="utf-8")
    result = clean_workspaces(
        merged_only=True, slug="garbage", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert wt.is_dir()


def test_a_worktree_listing_git_cannot_give_is_not_a_landing(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review 4: when ``worktree list --porcelain -z`` fails, a present worktree's HEAD is not known to be landed.

    (The fallback for a directory git does not list, mutant mR5, is not pinned: archiving it loses nothing.)
    """
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "listing-wt"
    start_workspace("listing", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    real = ws_module._git_bytes  # noqa: SLF001

    def failing_listing(*args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
        if args[:2] == ("worktree", "list"):
            return subprocess.CompletedProcess(["git", *args], 129, b"", b"unknown option: -z")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(ws_module, "_git_bytes", failing_listing)
    result = clean_workspaces(
        merged_only=True, slug="listing", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert wt.is_dir()


def test_a_remote_whose_name_has_a_slash_still_proves_a_landing(repo: Path, tmp_path: Path) -> None:
    """Review 4 (N6b, N6): the longest configured remote that prefixes the source names its remote-tracking ref."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    fork = tmp_path / "fork.git"
    subprocess.run(["git", "init", "--bare", str(fork)], check=True, capture_output=True)
    _git("remote", "add", "team/fork", str(fork), cwd=repo)
    _git("push", "team/fork", "main", cwd=repo)
    landed = tmp_path / "landed-wt"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=landed, from_ref="team/fork/main")
    _commit(landed, "landed.txt")
    _git("merge", "--no-ff", "-m", "Merge landed", "landed", cwd=repo)
    _git("push", "team/fork", "main", cwd=repo)
    selfnamed = tmp_path / "self-wt"
    start_workspace("team/fork/main", root=repo, bookkeeping=bookkeeping, path=selfnamed, from_ref="team/fork/main")
    _commit(selfnamed, "self.txt")
    rows = {row.slug: row for row in status_workspaces(root=repo, bookkeeping=bookkeeping)}
    assert rows["landed"].merged is True
    assert rows["team/fork/main"].merged is False
    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["deleted"]] == ["landed"]


def test_a_remotes_spelling_names_the_remote_tracking_ref(repo: Path, tmp_path: Path) -> None:
    """Review 4: ``remotes/origin/main`` is ``refs/remotes/origin/main``, as git's name lookup reads it."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "remotes-wt"
    start_workspace("spelled", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="remotes/origin/main")
    result = clean_workspaces(
        delete=True, slug="spelled", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert [r["slug"] for r in result["deleted"]] == ["spelled"]


def _deleted_by_hand_with_an_unmerged_branch(repo: Path, tmp_path: Path, bookkeeping: Path) -> Path:
    """An ``origin/main`` workspace with its own commit (HEAD at its branch tip), its directory deleted by hand."""
    wt = tmp_path / "g-wt"
    start_workspace("g", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    _commit(wt, "g.txt")
    shutil.rmtree(wt)
    return wt


def test_delete_names_the_unmerged_branch_of_a_deleted_directory_as_before(repo: Path, tmp_path: Path) -> None:
    """Review 5: a deleted directory whose branch is not landed is refused with Story 13.5's text and exit."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _deleted_by_hand_with_an_unmerged_branch(repo, tmp_path, bookkeeping)
    result = clean_workspaces(delete=True, slug="g", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a")
    assert result["skipped"][0]["reason"] == "branch g not on origin/main"


def test_the_default_clean_drops_a_deleted_directory_whose_head_its_kept_branch_holds(
    repo: Path, tmp_path: Path
) -> None:
    """Review 5: a deleted directory whose HEAD is at its unmerged branch's tip is cleaned as at the baseline
    (``.missing.txt``, the branch kept)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _deleted_by_hand_with_an_unmerged_branch(repo, tmp_path, bookkeeping)
    result = clean_workspaces(
        slug="g", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a", confirm=lambda _slug: True
    )
    (row,) = result["archived"]
    assert row["archive"].endswith(".missing.txt")
    assert row["branch_kept"] == "g"
    assert load_bookkeeping(bookkeeping) == ()


def test_delete_reports_a_source_git_cannot_resolve_as_an_error_as_before(repo: Path, tmp_path: Path) -> None:
    """Review 5: a git failure on a deleted directory's branch stays an error row, so a fleet run exits 1."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _deleted_by_hand_with_an_unmerged_branch(repo, tmp_path, bookkeeping)
    save_bookkeeping(
        bookkeeping,
        tuple(
            WorkspaceRecord(r.slug, r.path, r.branch, "origin/gone", r.created_at)
            for r in load_bookkeeping(bookkeeping)
        ),
    )
    result = clean_workspaces(delete=True, slug="g", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a")
    assert result["skipped"][0]["reason"].startswith("error: git merge-base --is-ancestor g origin/gone failed")


def test_a_workspace_named_like_its_remotes_spelled_source_is_never_compared_with_itself(
    repo: Path, tmp_path: Path
) -> None:
    """Review 5 (mutant mT2): slug and branch ``remotes/origin/main`` started from it; once the remote ref is pruned,
    read by name the source would be the branch itself."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "remotes-self-wt"
    start_workspace("remotes/origin/main", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="remotes/origin/main")
    _commit(wt, "remotes-self.txt")
    _git("update-ref", "-d", "refs/remotes/origin/main", cwd=repo)
    result = clean_workspaces(
        merged_only=True, slug="remotes/origin/main", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert _branch_exists(repo, "remotes/origin/main")


def test_a_local_source_that_merely_starts_like_a_remote_is_local(repo: Path, tmp_path: Path) -> None:
    """Review 5 (mutant mT11): ``originals`` is a local branch, not ``origin`` + ``als``."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _git("branch", "originals", "main", cwd=repo)
    wt = tmp_path / "originals-wt"
    start_workspace("from-originals", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="originals")
    _commit(wt, "o.txt")
    (row,) = status_workspaces("from-originals", root=repo, bookkeeping=bookkeeping)
    assert row.error is None
    assert row.merged is False


def _stacked_landed_then_detached_and_deleted(repo: Path, tmp_path: Path, bookkeeping: Path) -> str:
    """Review 7: ``stacked`` landed on main (not on its local source ``base``), its worktree detached at one more
    commit, then its directory deleted by hand. Returns that commit."""
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    detached = _detach_with_a_commit(stacked)
    shutil.rmtree(stacked)
    return detached


def test_the_trunk_never_lands_a_deleted_stacked_directory_whose_recorded_head_is_past_it(
    repo: Path, tmp_path: Path
) -> None:
    """Review 7 (T1): the baseline kept this record (the branch is not on ``base``); landing it through the trunk
    alone would prune the commit git still records."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    detached = _stacked_landed_then_detached_and_deleted(repo, tmp_path, bookkeeping)
    merged_only = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert merged_only["skipped"][0]["reason"] == "not-merged"
    deleted = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert deleted["skipped"][0]["reason"] == "branch stacked not on base or origin/main"
    assert f"HEAD {detached}" in _git("worktree", "list", "--porcelain", cwd=repo).stdout
    assert _branch_exists(repo, "stacked")


def test_the_trunk_never_turns_a_gone_sources_error_into_a_landing_past_a_recorded_head(
    repo: Path, tmp_path: Path
) -> None:
    """Review 7 (T5): with ``base`` deleted too, ``--delete`` reports the source's error as the baseline did."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _stacked_landed_then_detached_and_deleted(repo, tmp_path, bookkeeping)
    _git("worktree", "remove", str(tmp_path / "base-wt"), cwd=repo)
    _git("branch", "-D", "base", cwd=repo)
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"].startswith("error: git merge-base --is-ancestor stacked base failed")
    assert _branch_exists(repo, "stacked")


def test_a_revision_source_never_reads_a_local_ref_named_like_the_remote(repo: Path, tmp_path: Path) -> None:
    """Review 7 (V1): ``origin/main~0`` is read as ``refs/remotes/origin/main~0``, as at the baseline, so a local
    branch ``origin/main`` at the unlanded tip proves nothing (Story 70.1)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "rev-shadow-wt"
    start_workspace("rev-shadow", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main~0")
    _commit(wt, "rev-shadow.txt")
    _git("update-ref", "refs/heads/origin/main", "refs/heads/rev-shadow", cwd=repo)
    (row,) = status_workspaces("rev-shadow", root=repo, bookkeeping=bookkeeping)
    assert row.merged is False
    result = clean_workspaces(
        merged_only=True, slug="rev-shadow", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["archived"] == []
    assert _branch_exists(repo, "rev-shadow")


@pytest.mark.parametrize("mode", ["merged-only", "delete"])
def test_cleaning_one_workspace_never_unregisters_another_deleted_by_hand(
    repo: Path, tmp_path: Path, mode: str
) -> None:
    """Review 8: a trunk-landed ``stacked`` is cleaned; a sibling deleted by hand keeps its registration (and so the
    commit only its detached HEAD holds), because the clean unregisters its own worktree alone."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    sibling = _landed_origin_main_workspace_with_a_detached_commit(repo, tmp_path, bookkeeping)
    detached = _git("-C", str(sibling), "rev-parse", "HEAD", cwd=repo).stdout.strip()
    shutil.rmtree(sibling)
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("worktree", "remove", str(stacked), cwd=repo)  # gone, as AC (2) and (5) leave it
    if mode == "delete":
        result = clean_workspaces(
            delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
        )
        assert [r["slug"] for r in result["deleted"]] == ["stacked"]
    else:
        result = clean_workspaces(
            merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
        )
        assert [r["slug"] for r in result["archived"]] == ["stacked"]
    assert f"HEAD {detached}" in _git("worktree", "list", "--porcelain", cwd=repo).stdout


def test_a_gone_directorys_per_worktree_ref_keeps_it_from_landing_through_the_trunk(repo: Path, tmp_path: Path) -> None:
    """Review 8: unregistering deletes ``refs/worktree/*``; a commit only such a ref holds keeps the record."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    _git("checkout", "--detach", cwd=stacked)
    _commit(stacked, "kept-by-worktree-ref.txt")
    _git("update-ref", "refs/worktree/keep", "HEAD", cwd=stacked)
    _git("checkout", "stacked", cwd=stacked)
    shutil.rmtree(stacked)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "not-merged"
    assert _branch_exists(repo, "stacked")


def test_a_gone_directory_with_a_failed_listing_is_not_landed_through_the_trunk(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review 8 (mutant mW6)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _stacked_landed_then_detached_and_deleted(repo, tmp_path, bookkeeping)
    real = ws_module._git_bytes  # noqa: SLF001

    def failing_listing(*args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
        if args[:2] == ("worktree", "list"):
            return subprocess.CompletedProcess(["git", *args], 129, b"", b"unknown option: -z")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(ws_module, "_git_bytes", failing_listing)
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "not-merged"
    assert _branch_exists(repo, "stacked")


def test_a_gone_directory_with_a_garbage_head_is_not_landed_through_the_trunk(repo: Path, tmp_path: Path) -> None:
    """Review 8 (mutant mW4): zeros with no branch line in a gone directory's registration are no unborn HEAD."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=True)
    admin = Path(_git("rev-parse", "--absolute-git-dir", cwd=stacked).stdout.strip())
    shutil.rmtree(stacked)
    (admin / "HEAD").write_text("garbage\n", encoding="utf-8")
    result = clean_workspaces(
        merged_only=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "not-merged"


def test_a_gone_unmerged_directory_without_the_trunk_is_refused_not_an_error(repo: Path, tmp_path: Path) -> None:
    """Review 8 (mutant mW7): a trunk git cannot resolve never turns a gone directory's refusal into an error row."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stacked = _stacked(repo, tmp_path, bookkeeping, land=False)
    shutil.rmtree(stacked)
    _git("update-ref", "-d", "refs/remotes/origin/main", cwd=repo)
    result = clean_workspaces(
        delete=True, slug="stacked", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )
    assert result["skipped"][0]["reason"] == "branch stacked not on base or origin/main"
