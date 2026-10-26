"""Story 13.7 -- a landed workspace that holds Tier-3 files deletes, and keeps the files.

``clean --delete`` asks CAP-157's proof, which refuses a real git-ignored path under ``_bmad-output/``. A steward
workspace has no ``implementation-artifacts`` backlink, so the run journal ``dispatch_land_finalize`` writes there
after the merge made every hand-landed workspace undeletable, and ``--delete`` called it ``not-merged`` while
``status`` read it merged. Now the files move to the main checkout's Tier-3 store first, never over a file there,
and every refusal names its own cause.
"""

from __future__ import annotations

import errno
import os
import subprocess
from pathlib import Path

import pytest

from pyforge.steward import workspace as ws_module
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


def _make_repo(tmp_path: Path, *, separate_git_dir: str | None = None) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    work = tmp_path / "local-recipes"
    work.mkdir()
    if separate_git_dir:
        (tmp_path / separate_git_dir).parent.mkdir(parents=True, exist_ok=True)
        _git("init", "-b", "main", f"--separate-git-dir={tmp_path / separate_git_dir}", cwd=work)
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


@pytest.mark.parametrize("git_dir", ["repo.git", "elsewhere/.git"])
def test_a_separate_git_dir_has_no_main_checkout_so_nothing_moves(tmp_path: Path, git_dir: str):
    """git lists the git directory, or the parent of one named ``.git``, as the main worktree; neither is the
    checkout, so the files must not land there (review 1)."""
    repo = _make_repo(tmp_path, separate_git_dir=git_dir)
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
    assert list(tmp_path.rglob("journal.jsonl")) == [wt / _JOURNAL]  # nowhere beside the git directory
    assert _branch_exists(repo, "landed")


def test_a_bare_repository_has_no_main_checkout_so_nothing_moves(tmp_path: Path):
    _make_repo(tmp_path)
    bare = tmp_path / "proj.git"
    _git("clone", "--bare", str(tmp_path / "origin.git"), str(bare), cwd=tmp_path)
    _git("config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*", cwd=bare)
    _git("config", "user.email", "test@example.com", cwd=bare)
    _git("config", "user.name", "Test", cwd=bare)
    _git("fetch", "origin", cwd=bare)
    bookkeeping = tmp_path / "bookkeeping" / "workspaces.yaml"
    wt = tmp_path / "bare-wt"
    start_workspace("landed", root=bare, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "work", cwd=wt)
    _git("push", "origin", "HEAD:main", cwd=wt)
    _git("fetch", "origin", cwd=bare)
    _write(wt / _JOURNAL, "{}\n")
    tier3_dir = _JOURNAL.parents[2]  # git names the ignored implementation-artifacts directory

    result = clean_workspaces(
        delete=True, slug="landed", root=bare, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["deleted"] == []
    assert result["skipped"][0]["reason"] == f"Tier-3 work: {tier3_dir} (no main checkout to move it to)"
    assert (wt / _JOURNAL).read_text(encoding="utf-8") == "{}\n"
    assert not (tmp_path / "_bmad-output").exists()
    assert _branch_exists(bare, "landed")


def test_a_locked_worktree_moves_nothing(repo: Path, tmp_path: Path):
    """Its removal would fail after the move, splitting the journal between the worktree and main (review 2)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "{}\n")
    _git("worktree", "lock", str(wt), cwd=repo)
    tier3_dir = _JOURNAL.parents[2]

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["skipped"][0]["reason"] == f"Tier-3 work: {tier3_dir} (the worktree is locked)"
    assert (wt / _JOURNAL).is_file()
    assert not (repo / _JOURNAL).exists()
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["landed"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any directory")
def test_a_tier3_directory_git_cannot_open_is_no_proof_and_nothing_is_removed(repo: Path, tmp_path: Path):
    """git leaves a directory it cannot open out of the ignored listing, with a warning and exit 0 (review 1)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "{}\n")
    sibling = wt / _JOURNAL.parents[1] / "r0" / "journal.jsonl"
    _write(sibling, "r0\n")
    unreadable = (wt / _JOURNAL).parent
    unreadable.chmod(0)
    try:
        result = clean_workspaces(
            delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
        )
    finally:
        unreadable.chmod(0o755)

    reason = result["skipped"][0]["reason"]
    assert reason.startswith("git-ignored listing failed: ") and str(_JOURNAL.parent) in reason  # git's warning
    assert (wt / _JOURNAL).is_file() and sibling.is_file()
    assert not (repo / _JOURNAL.parents[1]).exists()
    assert _branch_exists(repo, "landed")


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any directory")
def test_an_unreadable_directory_outside_bmad_output_deletes_as_before(repo: Path, tmp_path: Path):
    """Ignored content elsewhere goes with the worktree, as at fd06415e4d; only a warning under ``_bmad-output/``
    is no proof (review 2)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _git("config", "core.excludesFile", str(tmp_path / "excludes"), cwd=repo)
    (tmp_path / "excludes").write_text(".pixi/envs\n", encoding="utf-8")
    secret = wt / ".pixi" / "envs" / "e" / "secret"
    secret.mkdir(parents=True)
    secret.chmod(0)
    try:
        result = clean_workspaces(
            delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
        )
    finally:
        if secret.exists():
            secret.chmod(0o755)

    assert [row["slug"] for row in result["deleted"]] == ["landed"], result["skipped"]
    assert not wt.exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes any directory")
def test_a_tier3_directory_that_cannot_be_written_moves_nothing(repo: Path, tmp_path: Path):
    """The file could be linked into main but not removed here, and would be in both places (review 2)."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "{}\n")
    (wt / _JOURNAL).parent.chmod(0o500)
    try:
        result = clean_workspaces(
            delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
        )
    finally:
        (wt / _JOURNAL).parent.chmod(0o755)

    assert result["skipped"][0]["reason"] == f"Tier-3 work: {_JOURNAL} cannot move: its directory is not writable"
    assert (wt / _JOURNAL).is_file()
    assert not (repo / _JOURNAL).exists()


def test_a_source_that_cannot_be_removed_is_never_left_in_both_places(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    src_dir, main = tmp_path / "wt", tmp_path / "main"
    _write(src_dir / "a.jsonl", "a\n")
    real_unlink = os.unlink

    def _refuse_source(path, *args, **kwargs):
        if Path(path) == src_dir / "a.jsonl":
            raise PermissionError(errno.EACCES, "Permission denied")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(ws_module.os, "unlink", _refuse_source)

    with pytest.raises(ws_module.WorkspaceError, match="could not be removed"):
        ws_module._move_no_clobber(src_dir / "a.jsonl", main / "a.jsonl")

    assert (src_dir / "a.jsonl").read_text(encoding="utf-8") == "a\n"
    assert not (main / "a.jsonl").exists()


def test_a_fifo_holds_no_data_and_goes_with_the_worktree(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    _write(wt / _JOURNAL, "{}\n")
    os.mkfifo(wt / _JOURNAL.parent / "pipe")

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    assert result["deleted"][0]["tier3_moved"] == "1"
    assert (repo / _JOURNAL).is_file()
    assert not os.path.lexists(repo / _JOURNAL.parent / "pipe")
    assert not wt.exists()


def test_a_non_utf8_name_is_shown_escaped_and_the_report_prints(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = _landed(repo, tmp_path, bookkeeping)
    name = os.fsdecode(b"run-\xff.jsonl")
    _write(wt / _JOURNAL.parent / name, "workspace\n")
    _write(repo / _JOURNAL.parent / name, "main\n")

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive"
    )

    reason = result["skipped"][0]["reason"]
    assert reason == f"Tier-3 work: {_JOURNAL.parent}/run-\\xff.jsonl already in {repo}"
    format_clean(result, as_json=False).encode("utf-8")  # review 4: a surrogate here raised on print
    assert (repo / _JOURNAL.parent / name).read_text(encoding="utf-8") == "main\n"


def test_a_symlink_never_replaces_a_file_written_after_the_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Every existence check says "absent", as when the file appears between the check and the move (review 1).
    monkeypatch.setattr(ws_module.os.path, "lexists", lambda path: False)
    src_dir, main = tmp_path / "wt", tmp_path / "main"
    src_dir.mkdir()
    main.mkdir()
    (src_dir / "latest").symlink_to("runs/r2")
    (main / "latest").write_text("written meanwhile\n", encoding="utf-8")

    with pytest.raises(ws_module.WorkspaceError, match="appeared before the move"):
        ws_module._move_no_clobber(src_dir / "latest", main / "latest")

    assert (main / "latest").read_text(encoding="utf-8") == "written meanwhile\n"
    assert (src_dir / "latest").is_symlink()


def test_across_filesystems_a_copy_never_replaces_a_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def _no_hard_link(src, dst, *args, **kwargs):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(ws_module.os, "link", _no_hard_link)
    src_dir, main = tmp_path / "wt", tmp_path / "main"
    _write(src_dir / "a.jsonl", "a\n")
    _write(src_dir / "b.jsonl", "b\n")
    _write(main / "b.jsonl", "written meanwhile\n")
    monkeypatch.setattr(ws_module.os.path, "lexists", lambda path: False)

    ws_module._move_no_clobber(src_dir / "a.jsonl", main / "a.jsonl")
    with pytest.raises(ws_module.WorkspaceError, match="appeared before the move"):
        ws_module._move_no_clobber(src_dir / "b.jsonl", main / "b.jsonl")

    assert (main / "a.jsonl").read_text(encoding="utf-8") == "a\n" and not (src_dir / "a.jsonl").exists()
    assert (main / "b.jsonl").read_text(encoding="utf-8") == "written meanwhile\n"
    assert (src_dir / "b.jsonl").read_text(encoding="utf-8") == "b\n"


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
