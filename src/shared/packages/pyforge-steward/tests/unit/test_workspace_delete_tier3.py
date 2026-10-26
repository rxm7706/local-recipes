"""Story 13.7 -- a landed workspace that holds Tier-3 files deletes, and keeps the files.

``clean --delete`` asks CAP-157's proof, which refuses a real git-ignored path under ``_bmad-output/``. A steward
workspace has no ``implementation-artifacts`` backlink, so the run journal ``dispatch_land_finalize`` writes there
after the merge made every hand-landed workspace undeletable, and ``--delete`` called it ``not-merged`` while
``status`` read it merged. Now the files move to the main checkout's Tier-3 store first, never over a file there,
and every refusal names its own cause.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from pyforge.steward.workspace import (
    clean_workspaces,
    format_clean,
    load_bookkeeping,
    start_workspace,
    status_workspaces,
)

_JOURNAL = Path("_bmad-output/projects/demo/implementation-artifacts/runs/r1/journal.jsonl")


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _branch_exists(repo: Path, branch: str) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=repo, capture_output=True
        ).returncode
        == 0
    )


def _make_repo(tmp_path: Path, *, separate_git_dir: bool = False) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    work = tmp_path / "local-recipes"
    work.mkdir()
    if separate_git_dir:
        _git("init", "-b", "main", f"--separate-git-dir={tmp_path / 'repo.git'}", cwd=work)
    else:
        _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    (work / "scripts").mkdir()
    (work / "scripts" / "bmad-loop-worktree").write_text("#!/usr/bin/env true\n", encoding="utf-8")
    # As in this repo: Tier-3 is git-ignored and planning artifacts beside it are tracked.
    (work / ".gitignore").write_text("_bmad-output/projects/*/implementation-artifacts\n", encoding="utf-8")
    planning = work / "_bmad-output" / "projects" / "demo" / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text("# epics\n", encoding="utf-8")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path)


def _landed(repo: Path, tmp_path: Path, bookkeeping: Path, slug: str = "landed") -> Path:
    """A workspace off ``origin/main`` with one commit, merged into ``main`` and pushed, as a PR merge would."""
    wt = tmp_path / f"{slug}-wt"
    start_workspace(slug, root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "work", cwd=wt)
    _git("merge", "--no-ff", "-m", f"Merge {slug}", slug, cwd=repo)
    _git("push", "origin", "main", cwd=repo)
    return wt


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_landed_workspace_with_a_run_journal_deletes_and_the_journal_moves_to_the_main_checkout(
    repo: Path, tmp_path: Path
):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, '{"kind": "dispatch-land-finalize-resync"}\n')

    [status] = status_workspaces(root=repo, bookkeeping=bookkeeping)
    assert (status.dirty, status.merged) == (False, True)

    result = clean_workspaces(delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)

    assert result["skipped"] == []
    [row] = result["deleted"]
    assert row["slug"] == "landed"
    assert (row["tier3_moved_to"], row["tier3_moved"]) == (str(repo), "1")
    assert (repo / _JOURNAL).read_text(encoding="utf-8") == '{"kind": "dispatch-land-finalize-resync"}\n'
    assert not wt.exists()
    assert not _branch_exists(repo, "landed")
    assert load_bookkeeping(bookkeeping) == ()
    assert not archive_dir.exists() or list(archive_dir.iterdir()) == []
    assert _git("tag", "--list", cwd=repo).stdout == ""


def test_every_file_under_a_tier3_directory_moves_and_a_symlink_stays_a_symlink(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    tier3 = wt / "_bmad-output" / "projects" / "demo" / "implementation-artifacts"
    _write(tier3 / "sprint-status.yaml", "development_status: {}\n")
    _write(tier3 / "runs" / "r1" / "journal.jsonl", "{}\n")
    _write(tier3 / "runs" / "r2" / "deep" / "notes.md", "notes\n")
    (tier3 / "latest").symlink_to("runs/r2")
    # The main checkout already holds other runs; its directory is merged into, never replaced.
    _write(
        repo / "_bmad-output" / "projects" / "demo" / "implementation-artifacts" / "runs" / "r0" / "journal.jsonl",
        "r0\n",
    )

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["deleted"][0]["tier3_moved"] == "4"
    main = repo / "_bmad-output" / "projects" / "demo" / "implementation-artifacts"
    assert (main / "sprint-status.yaml").read_text(encoding="utf-8") == "development_status: {}\n"
    assert (main / "runs" / "r1" / "journal.jsonl").read_text(encoding="utf-8") == "{}\n"
    assert (main / "runs" / "r2" / "deep" / "notes.md").read_text(encoding="utf-8") == "notes\n"
    assert (main / "runs" / "r0" / "journal.jsonl").read_text(encoding="utf-8") == "r0\n"
    assert (main / "latest").is_symlink() and os.readlink(main / "latest") == "runs/r2"
    assert not wt.exists()


def test_a_file_already_in_the_main_checkout_is_never_overwritten(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "workspace copy\n")
    _write(wt / _JOURNAL.parent / "other.jsonl", "other\n")
    _write(repo / _JOURNAL, "main copy\n")

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["deleted"] == []
    [skipped] = result["skipped"]
    assert skipped["reason"] == f"Tier-3 work: {_JOURNAL} already in {repo}"
    assert (repo / _JOURNAL).read_text(encoding="utf-8") == "main copy\n"
    assert (wt / _JOURNAL).read_text(encoding="utf-8") == "workspace copy\n"
    assert not (repo / _JOURNAL.parent / "other.jsonl").exists()  # nothing moves when one file cannot
    assert _branch_exists(repo, "landed")
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["landed"]


def test_no_main_checkout_means_nothing_moves(tmp_path: Path):
    repo = _make_repo(tmp_path, separate_git_dir=True)  # the common git directory is not a .git directory
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "{}\n")
    tier3_dir = _JOURNAL.parents[2]  # git names the ignored implementation-artifacts directory

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["deleted"] == []
    assert result["skipped"][0]["reason"] == f"Tier-3 work: {tier3_dir} (no main checkout to move it to)"
    assert (wt / _JOURNAL).read_text(encoding="utf-8") == "{}\n"
    assert not (repo / _JOURNAL).exists()
    assert _branch_exists(repo, "landed")


def test_a_per_worktree_ref_is_refused_by_name_not_as_not_merged(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _git("update-ref", "refs/worktree/keep", "HEAD", cwd=wt)

    [status] = status_workspaces(root=repo, bookkeeping=bookkeeping)
    assert status.merged is True

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["skipped"][0]["reason"] == "holds per-worktree refs"
    assert wt.is_dir()
    assert _branch_exists(repo, "landed")


def test_an_unlanded_workspace_with_tier3_files_is_still_not_merged_and_moves_nothing(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "open-wt"
    start_workspace("open", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "work", cwd=wt)
    _write(wt / _JOURNAL, "{}\n")

    result = clean_workspaces(
        delete=True, slug="open", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["skipped"][0]["reason"] == "not-merged"
    assert (wt / _JOURNAL).is_file()
    assert not (repo / _JOURNAL).exists()


def test_format_clean_names_where_the_tier3_files_went():
    text = format_clean(
        {
            "deleted": [
                {"slug": "a", "tier3_moved_to": "/repo", "tier3_moved": "2"},
                {"slug": "b"},
            ]
        },
        as_json=False,
    )
    assert text.splitlines() == ["deleted a (2 Tier-3 file(s) moved to /repo)", "deleted b"]
