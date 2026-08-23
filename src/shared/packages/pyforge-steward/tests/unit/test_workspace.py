"""Story 13.1 — `steward workspace start|ls|clean` + own-worktrees-only HARD."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.workspace import (
    WorkspaceError,
    clean_workspaces,
    format_ls,
    list_workspaces,
    load_bookkeeping,
    scratch_path_for,
    start_workspace,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _make_repo(tmp_path: Path) -> Path:
    """Bare origin + work checkout on main, with scripts/bmad-loop-worktree marker."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)

    work = tmp_path / "local-recipes"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    scripts = work / "scripts"
    scripts.mkdir()
    (scripts / "bmad-loop-worktree").write_text("#!/usr/bin/env true\n", encoding="utf-8")
    (work / "README.md").write_text("scratch\n", encoding="utf-8")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path)


def test_start_creates_worktree_records_and_prints_path(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "scratch-a"

    record = start_workspace(
        "feat-a",
        from_ref="origin/main",
        root=repo,
        bookkeeping=bookkeeping,
        path=dest,
    )

    assert dest.is_dir()
    assert (dest / "README.md").is_file()
    assert record.path == str(dest.resolve())
    assert record.branch == "feat-a"
    assert record.source == "origin/main"
    loaded = load_bookkeeping(bookkeeping)
    assert len(loaded) == 1
    assert loaded[0].slug == "feat-a"


def test_start_json_via_cli(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "cli-start"

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )
    monkeypatch.setattr(
        "pyforge.steward.workspace.scratch_path_for",
        lambda slug, root=None: dest,
    )

    rc = main(["workspace", "start", "cli-slug", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == "cli-slug"
    assert payload["path"] == str(dest.resolve())
    assert payload["branch"] == "cli-slug"
    assert dest.is_dir()


def test_ls_is_cheap_bookkeeping_only(repo: Path, tmp_path: Path, monkeypatch):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "owned"
    start_workspace(
        "owned", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main"
    )

    # Plant a foreign Marshal-style loop-home worktree — must stay invisible.
    foreign = tmp_path / "loop-homes" / "pyforge-marshal"
    foreign.parent.mkdir(parents=True)
    _git("worktree", "add", str(foreign), "-b", "loop/pyforge-marshal", "origin/main", cwd=repo)

    calls: list[tuple[str, ...]] = []
    real_run = subprocess.run

    def spy_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
            calls.append(tuple(cmd))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy_run)

    records = list_workspaces(bookkeeping=bookkeeping)
    text = format_ls(records, as_json=True)
    payload = json.loads(text)

    assert [r["slug"] for r in payload] == ["owned"]
    assert "loop/pyforge-marshal" not in text
    assert str(foreign) not in text
    # CAP-2: ls must not spawn any git subprocess (bookkeeping only).
    assert calls == []


def test_foreign_loop_home_invisible_to_ls_and_clean(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    owned = tmp_path / "owned-wt"
    start_workspace(
        "owned", root=repo, bookkeeping=bookkeeping, path=owned, from_ref="origin/main"
    )

    foreign = tmp_path / "loop-homes" / "pyforge-marshal"
    foreign.parent.mkdir(parents=True)
    _git("worktree", "add", str(foreign), "-b", "loop/pyforge-marshal", "origin/main", cwd=repo)

    ls_payload = json.loads(format_ls(list_workspaces(bookkeeping=bookkeeping), as_json=True))
    assert [r["slug"] for r in ls_payload] == ["owned"]

    # Merge owned into origin/main so --merged-only archives it.
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "owned", cwd=repo)
    _git("push", "origin", "main", cwd=repo)

    result = clean_workspaces(
        merged_only=True,
        root=repo,
        bookkeeping=bookkeeping,
        archive_dir=archive_dir,
    )

    assert len(result["archived"]) == 1
    assert result["archived"][0]["slug"] == "owned"
    assert not owned.exists()
    assert foreign.is_dir(), "foreign Marshal loop-home must be untouched"
    assert load_bookkeeping(bookkeeping) == ()
    # Foreign still registered with git.
    listed = _git("worktree", "list", "--porcelain", cwd=repo).stdout
    assert str(foreign.resolve()) in listed


def test_clean_merged_only_leaves_unmerged(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "unmerged"
    start_workspace(
        "unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main"
    )
    # Advance the branch so it is ahead of origin/main (not merged).
    _git("commit", "--allow-empty", "-m", "ahead", cwd=dest)

    result = clean_workspaces(
        merged_only=True,
        root=repo,
        bookkeeping=bookkeeping,
        archive_dir=archive_dir,
    )

    assert result["archived"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "not-merged"
    assert dest.is_dir()
    assert len(load_bookkeeping(bookkeeping)) == 1


def test_clean_archives_not_deletes(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "to-archive"
    start_workspace(
        "to-archive", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main"
    )
    (dest / "marker.txt").write_text("keep-me\n", encoding="utf-8")

    result = clean_workspaces(
        merged_only=False,
        root=repo,
        bookkeeping=bookkeeping,
        archive_dir=archive_dir,
        confirm=lambda slug: True,
    )

    assert len(result["archived"]) == 1
    archive = Path(result["archived"][0]["archive"])
    assert archive.is_file()
    assert archive.suffixes[-2:] == [".tar", ".gz"] or archive.name.endswith(".tar.gz")
    assert not dest.exists()
    # Recoverable content.
    import tarfile

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("marker.txt") for n in names)


def test_clean_json_via_cli(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "cli-clean"
    start_workspace(
        "cli-clean", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main"
    )
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "cli-clean", cwd=repo)
    _git("push", "origin", "main", cwd=repo)

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_archive_dir", lambda: archive_dir
    )

    rc = main(["workspace", "clean", "--merged-only", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["archived"]) == 1
    assert payload["archived"][0]["slug"] == "cli-clean"


def test_scratch_path_convention(repo: Path):
    path = scratch_path_for("steward/13-1", root=repo)
    assert path == repo.parent / f"{repo.name}-wt-steward-13-1"


def test_duplicate_start_refuses(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "dup"
    start_workspace("dup", root=repo, bookkeeping=bookkeeping, path=dest)
    with pytest.raises(WorkspaceError, match="already recorded"):
        start_workspace(
            "dup", root=repo, bookkeeping=bookkeeping, path=tmp_path / "dup-2"
        )


def test_ls_json_via_cli_empty(repo: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )

    rc = main(["workspace", "ls", "--json"])

    assert rc == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []

def test_clean_declined_confirm_skips_and_keeps_path(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "declined"
    start_workspace(
        "declined", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main"
    )

    result = clean_workspaces(
        merged_only=False,
        root=repo,
        bookkeeping=bookkeeping,
        archive_dir=archive_dir,
        confirm=lambda slug: False,
    )

    assert result["archived"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "declined"
    assert dest.is_dir()
    assert len(load_bookkeeping(bookkeeping)) == 1


def test_start_cli_from_ref_json(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "from-other"
    # Create origin/other for --from
    _git("branch", "other", cwd=repo)
    _git("push", "origin", "other", cwd=repo)

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )
    monkeypatch.setattr(
        "pyforge.steward.workspace.scratch_path_for",
        lambda slug, root=None: dest,
    )

    rc = main(["workspace", "start", "from-other", "--from", "origin/other", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "origin/other"
    assert payload["slug"] == "from-other"
    assert dest.is_dir()


def test_duplicate_start_via_cli_exits_failed(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "cli-dup"
    start_workspace("cli-dup", root=repo, bookkeeping=bookkeeping, path=dest)

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )
    monkeypatch.setattr(
        "pyforge.steward.workspace.scratch_path_for",
        lambda slug, root=None: tmp_path / "cli-dup-2",
    )

    rc = main(["workspace", "start", "cli-dup", "--json"])

    assert rc == EXIT_FAILED
    captured = capsys.readouterr()
    err = captured.out + captured.err
    assert "already recorded" in err


def test_start_cli_non_json_prints_exactly_path(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "plain-path"

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping
    )
    monkeypatch.setattr(
        "pyforge.steward.workspace.scratch_path_for",
        lambda slug, root=None: dest,
    )

    rc = main(["workspace", "start", "plain-path"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert out == str(dest.resolve()) + "\n"


def test_start_after_clean_reuses_slug(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest1 = tmp_path / "reuse-1"
    dest2 = tmp_path / "reuse-2"
    start_workspace(
        "reuse", root=repo, bookkeeping=bookkeeping, path=dest1, from_ref="origin/main"
    )

    result = clean_workspaces(
        merged_only=False,
        root=repo,
        bookkeeping=bookkeeping,
        archive_dir=archive_dir,
        confirm=lambda slug: True,
    )
    assert len(result["archived"]) == 1
    assert load_bookkeeping(bookkeeping) == ()

    # Same slug must succeed again — branch was deleted during archive.
    record = start_workspace(
        "reuse", root=repo, bookkeeping=bookkeeping, path=dest2, from_ref="origin/main"
    )
    assert record.slug == "reuse"
    assert dest2.is_dir()
