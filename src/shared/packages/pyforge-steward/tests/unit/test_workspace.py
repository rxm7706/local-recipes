"""Story 13.1–13.2 — `steward workspace start|ls|status|clean` + own-worktrees-only HARD."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import pyforge.steward.workspace as ws_module
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.workspace import (
    WorkspaceError,
    WorkspaceRecord,
    clean_workspaces,
    format_ls,
    format_status,
    list_workspaces,
    load_bookkeeping,
    save_bookkeeping,
    scratch_path_for,
    start_workspace,
    status_workspaces,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


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
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
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
    start_workspace("owned", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")

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
    start_workspace("owned", root=repo, bookkeeping=bookkeeping, path=owned, from_ref="origin/main")

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
    start_workspace("unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
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
    start_workspace("to-archive", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
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


def test_clean_archive_leaves_out_reinstallable_envs_but_keeps_pixi_config(repo: Path, tmp_path: Path):
    """Story 68.1 (CAP-155): `.pixi/envs` and `.pixi/solve-group-envs` are
    rebuilt from the lock on demand (~13 GB after a preflight) -- never
    archived; the rest of `.pixi/` (the tracked `config.toml`) still is."""
    import tarfile

    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "with-envs"
    start_workspace("with-envs", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "marker.txt").write_text("keep-me\n", encoding="utf-8")
    (dest / ".pixi" / "envs" / "default" / "bin").mkdir(parents=True)
    (dest / ".pixi" / "envs" / "default" / "bin" / "python").write_text("env\n", encoding="utf-8")
    (dest / ".pixi" / "solve-group-envs" / "g").mkdir(parents=True)
    (dest / ".pixi" / "solve-group-envs" / "g" / "lib").write_text("env\n", encoding="utf-8")
    (dest / ".pixi" / "config.toml").write_text("[pypi-config]\n", encoding="utf-8")
    (dest / ".pixi" / "envs-notes.txt").write_text("not an env dir\n", encoding="utf-8")
    (dest / ".pixi" / "bld" / "pyforge-core" / "work").mkdir(parents=True)
    (dest / ".pixi" / "bld" / "pyforge-core" / "work" / "wheel.whl").write_text("build cache\n", encoding="utf-8")

    result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)

    archive = Path(result["archived"][0]["archive"])
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "with-envs/marker.txt" in names
    assert "with-envs/.pixi/config.toml" in names
    assert "with-envs/.pixi/envs-notes.txt" in names
    assert not [n for n in names if "/.pixi/envs" in n and not n.endswith("envs-notes.txt")]
    assert not [n for n in names if "/.pixi/solve-group-envs" in n]
    assert not [n for n in names if "/.pixi/bld" in n]
    assert not dest.exists()


def test_a_failed_archive_leaves_no_partial_file_and_keeps_the_record(repo: Path, tmp_path: Path):
    """Story 68.1 review 1 (M2): an unreadable file makes the tar fail; the half-written
    archive is removed (a kept record is retried every sweep, so leaving it leaked one per
    sweep), the worktree stays, and the record stays in bookkeeping with its error."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "unreadable"
    start_workspace("unreadable", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    secret = dest / "root-owned.bin"
    secret.write_text("x\n", encoding="utf-8")
    secret.chmod(0)
    try:
        if secret.stat().st_mode & 0o444 or os.access(secret, os.R_OK):
            pytest.skip("running with privileges that ignore file modes")
        result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)
    finally:
        secret.chmod(0o644)

    assert result["archived"] == []
    assert result["skipped"][0]["reason"].startswith("error: could not archive")
    assert list(archive_dir.glob("*.tar.gz")) == []
    assert dest.is_dir()
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["unreadable"]


def test_an_interrupt_mid_tar_leaves_no_partial_archive(repo: Path, tmp_path: Path, monkeypatch):
    """Story 68.1 review 2 (L-E): whatever stops the tar -- a Ctrl-C included -- the
    half-written archive is removed; the interrupt still propagates and the record stays."""
    import tarfile

    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    start_workspace("a", root=repo, bookkeeping=bookkeeping, path=tmp_path / "a", from_ref="origin/main")
    (tmp_path / "a" / "unlanded.txt").write_text("work\n", encoding="utf-8")  # so it tars (Story 69.1)

    def _interrupt(self, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(tarfile.TarFile, "add", _interrupt)
    with pytest.raises(KeyboardInterrupt):
        clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)

    assert list(archive_dir.glob("*.tar.gz")) == []
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["a"]


def test_an_interrupt_mid_sweep_never_drops_the_record_in_flight(repo: Path, tmp_path: Path):
    """Story 68.1 review 1 (M1): not only WorkspaceError -- a Ctrl-C at the confirm prompt
    must not lose the popped record from bookkeeping."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    start_workspace("a", root=repo, bookkeeping=bookkeeping, path=tmp_path / "a", from_ref="origin/main")
    start_workspace("b", root=repo, bookkeeping=bookkeeping, path=tmp_path / "b", from_ref="origin/main")

    def _interrupt(slug: str) -> bool:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        clean_workspaces(
            merged_only=False, root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive", confirm=_interrupt
        )

    assert sorted(r.slug for r in load_bookkeeping(bookkeeping)) == ["a", "b"]


def test_clean_via_cli_exits_failed_when_a_record_errored(repo: Path, tmp_path: Path, monkeypatch, capsys):
    """Story 68.1 review 1 (L3): the sweep finishes past an undecidable record, but the
    run still reports failure."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    save_bookkeeping(
        bookkeeping,
        (
            WorkspaceRecord(
                "stale", str(tmp_path / "gone"), "deleted-branch", "origin/deleted", "2026-09-16T13:01:19+00:00"
            ),
        ),
    )
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
    monkeypatch.setattr("pyforge.steward.workspace.default_archive_dir", lambda: tmp_path / "archive")

    rc = main(["workspace", "clean", "--merged-only", "--json"])

    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)  # a failed duty's summary goes to stderr
    assert payload["skipped"][0]["reason"].startswith("error: ")


def test_fleet_clean_reports_and_keeps_a_record_whose_branch_is_gone(repo: Path, tmp_path: Path):
    """Story 68.1 (CAP-155): a record the sweep cannot decide no longer stops
    it -- the live 2026-09-27 case raised on `git merge-base --is-ancestor` for
    a deleted branch -- and is kept in bookkeeping, not dropped by the save."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    stale = WorkspaceRecord(
        slug="stale",
        path=str(tmp_path / "stale-gone"),
        branch="branch-that-was-deleted",
        source="origin/source-that-was-deleted",
        created_at="2026-09-16T13:01:19+00:00",
    )
    save_bookkeeping(bookkeeping, (stale,))
    merged = tmp_path / "merged"
    start_workspace("merged", root=repo, bookkeeping=bookkeeping, path=merged, from_ref="origin/main")

    result = clean_workspaces(merged_only=True, root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)

    assert [row["slug"] for row in result["archived"]] == ["merged"]
    assert [row["slug"] for row in result["skipped"]] == ["stale"]
    assert result["skipped"][0]["reason"].startswith("error: git merge-base --is-ancestor branch-that-was-deleted")
    assert [r.slug for r in load_bookkeeping(bookkeeping)] == ["stale"]
    assert not merged.exists()


def test_clean_json_via_cli(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "cli-clean"
    start_workspace("cli-clean", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "cli-clean", cwd=repo)
    _git("push", "origin", "main", cwd=repo)

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
    monkeypatch.setattr("pyforge.steward.workspace.default_archive_dir", lambda: archive_dir)

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
        start_workspace("dup", root=repo, bookkeeping=bookkeeping, path=tmp_path / "dup-2")


def test_ls_json_via_cli_empty(repo: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)

    rc = main(["workspace", "ls", "--json"])

    assert rc == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []


def test_clean_declined_confirm_skips_and_keeps_path(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "declined"
    start_workspace("declined", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")

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
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
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
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
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
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
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
    start_workspace("reuse", root=repo, bookkeeping=bookkeeping, path=dest1, from_ref="origin/main")

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
    record = start_workspace("reuse", root=repo, bookkeeping=bookkeeping, path=dest2, from_ref="origin/main")
    assert record.slug == "reuse"
    assert dest2.is_dir()


# --- Story 13.2 / CAP-3: status ---


def test_status_reports_clean_ahead_behind_merged(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "status-a"
    start_workspace("status-a", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")

    # Fresh equal tip: clean, ahead=0, behind=0, merged into source.
    fresh = status_workspaces(root=repo, bookkeeping=bookkeeping)
    assert len(fresh) == 1
    assert fresh[0].slug == "status-a"
    assert fresh[0].dirty is False
    assert fresh[0].ahead == 0
    assert fresh[0].behind == 0
    assert fresh[0].merged is True

    # Dirty + ahead.
    (dest / "dirty.txt").write_text("x\n", encoding="utf-8")
    _git("add", "dirty.txt", cwd=dest)
    _git("commit", "-m", "ahead commit", cwd=dest)
    (dest / "untracked.txt").write_text("y\n", encoding="utf-8")

    after = status_workspaces("status-a", root=repo, bookkeeping=bookkeeping)
    assert len(after) == 1
    assert after[0].dirty is True
    assert after[0].ahead == 1
    assert after[0].behind == 0
    assert after[0].merged is False

    # Behind: advance origin/main without merging status-a.
    _git("checkout", "main", cwd=repo)
    _git("commit", "--allow-empty", "-m", "main moves", cwd=repo)
    _git("push", "origin", "main", cwd=repo)

    behind = status_workspaces("status-a", root=repo, bookkeeping=bookkeeping)[0]
    assert behind.ahead == 1
    assert behind.behind == 1
    assert behind.merged is False


def test_status_foreign_loop_home_invisible(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    owned = tmp_path / "owned-status"
    start_workspace(
        "owned-status",
        root=repo,
        bookkeeping=bookkeeping,
        path=owned,
        from_ref="origin/main",
    )

    foreign = tmp_path / "loop-homes" / "pyforge-marshal"
    foreign.parent.mkdir(parents=True)
    _git(
        "worktree",
        "add",
        str(foreign),
        "-b",
        "loop/pyforge-marshal",
        "origin/main",
        cwd=repo,
    )

    statuses = status_workspaces(root=repo, bookkeeping=bookkeeping)
    payload = json.loads(format_status(statuses, as_json=True))
    assert [s["slug"] for s in payload] == ["owned-status"]
    assert "loop/pyforge-marshal" not in json.dumps(payload)
    assert str(foreign) not in json.dumps(payload)
    assert foreign.is_dir()


def test_status_unknown_slug_errors(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "known"
    start_workspace("known", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    with pytest.raises(WorkspaceError, match="not in bookkeeping"):
        status_workspaces("missing", root=repo, bookkeeping=bookkeeping)


def test_status_json_via_cli(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "cli-status"
    start_workspace("cli-status", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)

    rc = main(["workspace", "status", "cli-status", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["slug"] == "cli-status"
    assert payload[0]["dirty"] is False
    assert payload[0]["ahead"] == 0
    assert payload[0]["behind"] == 0
    assert payload[0]["merged"] is True
    assert "path" in payload[0]


def test_status_cli_all_and_human(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "human-status"
    start_workspace(
        "human-status",
        root=repo,
        bookkeeping=bookkeeping,
        path=dest,
        from_ref="origin/main",
    )

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)

    rc = main(["workspace", "status"])
    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "human-status" in out
    assert "clean" in out
    assert "ahead=0" in out
    assert "merged" in out


def test_status_missing_path_per_row_error_keeps_siblings(repo: Path, tmp_path: Path, monkeypatch, capsys):
    """Missing bookkeeping path → per-row error; other rows still reported; duty ok."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    good = tmp_path / "status-good"
    start_workspace(
        "status-good",
        root=repo,
        bookkeeping=bookkeeping,
        path=good,
        from_ref="origin/main",
    )
    # Inject a stale bookkeeping row whose path was deleted (never discovered via git).
    gone = tmp_path / "status-gone"
    existing = load_bookkeeping(bookkeeping)
    save_bookkeeping(
        bookkeeping,
        existing
        + (
            WorkspaceRecord(
                slug="status-gone",
                path=str(gone),
                branch="status-gone",
                source="origin/main",
                created_at="2026-08-23T00:00:00+00:00",
            ),
        ),
    )
    assert not gone.exists()

    statuses = status_workspaces(root=repo, bookkeeping=bookkeeping)
    assert len(statuses) == 2
    by_slug = {s.slug: s for s in statuses}
    assert by_slug["status-good"].error is None
    assert by_slug["status-good"].dirty is False
    assert by_slug["status-gone"].error is not None
    assert "missing" in by_slug["status-gone"].error.lower()
    assert by_slug["status-gone"].dirty is None
    assert by_slug["status-gone"].ahead is None
    assert by_slug["status-gone"].behind is None
    assert by_slug["status-gone"].merged is None

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
    rc = main(["workspace", "status", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert {row["slug"] for row in payload} == {"status-good", "status-gone"}
    gone_row = next(r for r in payload if r["slug"] == "status-gone")
    assert "error" in gone_row
    assert gone_row["dirty"] is None
    assert gone_row["ahead"] is None
    assert gone_row["behind"] is None
    assert gone_row["merged"] is None
    good_row = next(r for r in payload if r["slug"] == "status-good")
    assert "error" not in good_row

    rc = main(["workspace", "status"])
    assert rc == EXIT_OK
    human = capsys.readouterr().out
    assert "status-gone\terror\t" in human
    assert "status-good" in human
    assert "clean" in human


def test_status_unknown_slug_via_cli_exits_failed(repo: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)

    rc = main(["workspace", "status", "no-such-slug", "--json"])

    assert rc == EXIT_FAILED
    err = json.loads(capsys.readouterr().err)
    assert "not in bookkeeping" in err["error"]


# --- Story 69.1 (CAP-157): a worktree already on its source keeps a note, not a tarball ---


def _clean_one(repo: Path, tmp_path: Path, slug: str, *, source: str = "origin/main") -> Path:
    """Clean the single workspace `slug` (confirmed) and return what it left in the archive dir."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    cleaned = clean_workspaces(
        slug=slug, root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive", confirm=lambda s: True
    )
    assert [row["slug"] for row in cleaned["archived"]] == [slug], cleaned
    return Path(cleaned["archived"][0]["archive"])


def test_a_clean_worktree_on_its_source_leaves_a_note_naming_what_it_did_not_keep(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "landed"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    exclude = Path(_git("rev-parse", "--git-common-dir", cwd=repo).stdout.strip())
    exclude = (exclude if exclude.is_absolute() else repo / exclude) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("*.local\n", encoding="utf-8")
    (wt / "dev-secret.local").write_text("token\n", encoding="utf-8")  # ignored: not unlanded work
    head = _git("rev-parse", "HEAD", cwd=wt).stdout.strip()

    left = _clean_one(repo, tmp_path, "landed")

    assert left.name.endswith(".landed.txt")
    assert list((tmp_path / "archive").glob("*.tar.gz")) == []
    note = left.read_text(encoding="utf-8")
    assert f"HEAD: {head}" in note and "on source: origin/main at " in note
    assert "dev-secret.local" in note  # a dropped local file is named, never silently gone
    assert not wt.exists()


def test_a_worktree_with_an_unlanded_commit_still_archives(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "ahead"
    start_workspace("ahead", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "not on main", cwd=wt)

    assert _clean_one(repo, tmp_path, "ahead").name.endswith(".tar.gz")


def test_a_worktree_with_an_uncommitted_edit_still_archives(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "dirty"
    start_workspace("dirty", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "README.md").write_text("edited, not committed\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "dirty").name.endswith(".tar.gz")


def test_a_worktree_whose_source_git_cannot_resolve_still_archives(repo: Path, tmp_path: Path):
    """A proof git cannot give is no proof: the worktree archives, it is never dropped."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "unproven"
    start_workspace("unproven", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    records = [
        r if r.slug != "unproven" else WorkspaceRecord(r.slug, r.path, r.branch, "origin/gone", r.created_at)
        for r in load_bookkeeping(bookkeeping)
    ]
    save_bookkeeping(bookkeeping, tuple(records))

    assert _clean_one(repo, tmp_path, "unproven").name.endswith(".tar.gz")


def test_a_worktree_with_an_untracked_file_still_archives(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    wt = tmp_path / "untracked"
    start_workspace("untracked", root=repo, bookkeeping=bookkeeping, path=wt, from_ref="origin/main")
    (wt / "notes.md").write_text("never committed\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "untracked").name.endswith(".tar.gz")


# --- Story 69.1 review 1: every way `status` alone could certify unlanded work as landed ---


def _exclude(repo: Path, pattern: str) -> None:
    common = Path(_git("rev-parse", "--git-common-dir", cwd=repo).stdout.strip())
    exclude = (common if common.is_absolute() else repo / common) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write(pattern + "\n")


def _started(repo: Path, tmp_path: Path, slug: str) -> Path:
    wt = tmp_path / slug
    start_workspace(slug, root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=wt, from_ref="origin/main")
    return wt


def test_an_untracked_file_archives_even_when_config_hides_untracked_files(repo: Path, tmp_path: Path):
    _git("config", "status.showUntrackedFiles", "no", cwd=repo)
    wt = _started(repo, tmp_path, "hidden-untracked")
    (wt / "precious.txt").write_text("work\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "hidden-untracked").name.endswith(".tar.gz")


def test_a_skip_worktree_edit_archives(repo: Path, tmp_path: Path):
    wt = _started(repo, tmp_path, "skip-worktree")
    _git("update-index", "--skip-worktree", "README.md", cwd=wt)
    (wt / "README.md").write_text("local override\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "skip-worktree").name.endswith(".tar.gz")


def test_an_assume_unchanged_edit_archives(repo: Path, tmp_path: Path):
    wt = _started(repo, tmp_path, "assume-unchanged")
    _git("update-index", "--assume-unchanged", "README.md", cwd=wt)
    (wt / "README.md").write_text("local override\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "assume-unchanged").name.endswith(".tar.gz")


def test_a_detached_head_on_main_does_not_prove_the_branch_and_the_branch_is_kept(repo: Path, tmp_path: Path):
    """Cleanup deletes the recorded branch, not HEAD: a branch commit behind a detached HEAD on
    `origin/main` is unlanded -- it archives, and the unmerged branch survives cleanup."""
    wt = _started(repo, tmp_path, "detached")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "on the branch only", cwd=wt)
    branch_tip = _git("rev-parse", "HEAD", cwd=wt).stdout.strip()
    _git("checkout", "-q", "--detach", "origin/main", cwd=wt)

    assert _clean_one(repo, tmp_path, "detached").name.endswith(".tar.gz")
    assert _git("rev-parse", "refs/heads/detached", cwd=repo).stdout.strip() == branch_tip


def test_a_local_ref_shadowing_the_source_does_not_hide_an_unlanded_commit(repo: Path, tmp_path: Path):
    """Story 69.1 read a shadowed source as no proof at all; since Story 70.1 (CAP-158) the proof reads
    `refs/remotes/origin/main` itself, so the shadow at the unlanded tip is simply not consulted -- the
    unlanded commit still archives and the branch is kept (a landed worktree past a shadow now leaves a
    note: test_workspace_full_refs.py)."""
    wt = _started(repo, tmp_path, "shadowed")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "unlanded", cwd=wt)
    _git("branch", "origin/main", "HEAD", cwd=wt)  # a LOCAL branch named like the source

    assert _clean_one(repo, tmp_path, "shadowed").name.endswith(".tar.gz")
    assert _git("rev-parse", "--verify", "refs/heads/shadowed", cwd=repo).returncode == 0


def test_ignored_tier3_work_that_is_not_a_backlink_archives(repo: Path, tmp_path: Path):
    _exclude(repo, "_bmad-output/projects/*/implementation-artifacts")
    wt = _started(repo, tmp_path, "tier3")
    drafts = wt / "_bmad-output" / "projects" / "demo" / "implementation-artifacts"
    drafts.mkdir(parents=True)
    (drafts / "spec-1-1-draft.md").write_text("a story draft nowhere else\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "tier3").name.endswith(".tar.gz")


def test_a_backlinked_tier3_symlink_does_not_block_the_note(repo: Path, tmp_path: Path):
    """As in this repo, `_bmad-output/` holds tracked planning artifacts, so git names the
    ignored backlink symlink itself (an all-ignored `_bmad-output/` collapses to the directory,
    which conservatively tars)."""
    _exclude(repo, "_bmad-output/projects/*/implementation-artifacts")
    tracked = repo / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "epics.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("# epics\n", encoding="utf-8")
    _git("add", "_bmad-output", cwd=repo)
    _git("commit", "-m", "tracked planning artifact", cwd=repo)
    _git("push", "-q", "origin", "main", cwd=repo)
    wt = _started(repo, tmp_path, "backlinked")
    shared = tmp_path / "primary-tier3"
    shared.mkdir()
    link = wt / "_bmad-output" / "projects" / "demo" / "implementation-artifacts"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(shared, target_is_directory=True)

    assert _clean_one(repo, tmp_path, "backlinked").name.endswith(".landed.txt")


def test_a_failed_ignored_listing_archives_instead_of_writing_an_empty_note(repo: Path, tmp_path: Path, monkeypatch):
    wt = _started(repo, tmp_path, "listing-fails")
    real = ws_module._git_bytes

    def _fail_ignored(*args, cwd):
        if "--ignored" in args:
            return subprocess.CompletedProcess(args, 128, stdout=b"", stderr=b"fatal: simulated")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(ws_module, "_git_bytes", _fail_ignored)
    assert _clean_one(repo, tmp_path, "listing-fails").name.endswith(".tar.gz")
    assert not wt.exists()


def test_the_note_lists_at_most_200_ignored_paths_and_counts_the_rest(repo: Path, tmp_path: Path):
    _exclude(repo, "*.cache")
    wt = _started(repo, tmp_path, "many-ignored")
    for n in range(250):
        (wt / f"f{n:03d}.cache").write_text("x\n", encoding="utf-8")

    note = _clean_one(repo, tmp_path, "many-ignored").read_text(encoding="utf-8")
    assert "git-ignored paths not kept (250):" in note
    assert "  ... and 50 more" in note


# --- Story 69.1 review 2 ---


def test_a_non_utf8_ignored_name_neither_crashes_the_sweep_nor_goes_unnamed(repo: Path, tmp_path: Path):
    """It crashed the whole sweep with a UnicodeDecodeError (CAP-155: one bad record never stops it)."""
    import os

    _exclude(repo, "*.local")
    wt = _started(repo, tmp_path, "latin1")
    (wt / os.fsdecode(b"caf\xe9.local")).write_text("x\n", encoding="utf-8")

    note = _clean_one(repo, tmp_path, "latin1").read_text(encoding="utf-8")
    assert "caf\\xe9.local" in note


def test_a_shadowing_ref_hides_no_unlanded_commit_even_with_ambiguity_warnings_off(repo: Path, tmp_path: Path):
    """As above with `core.warnAmbiguousRefs=false` (Story 69.1 review 2): no warning is read either way,
    because the proof names the full ref (Story 70.1)."""
    _git("config", "core.warnAmbiguousRefs", "false", cwd=repo)
    wt = _started(repo, tmp_path, "quiet-shadow")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "unlanded", cwd=wt)
    _git("branch", "origin/main", "HEAD", cwd=wt)

    assert _clean_one(repo, tmp_path, "quiet-shadow").name.endswith(".tar.gz")
    assert _git("rev-parse", "--verify", "refs/heads/quiet-shadow", cwd=repo).returncode == 0


def test_quoted_tier3_paths_still_force_a_tarball(repo: Path, tmp_path: Path):
    _exclude(repo, "_bmad-output/projects/*/implementation-artifacts")
    wt = _started(repo, tmp_path, "quoted")
    drafts = wt / "_bmad-output" / "projects" / 'we"ird' / "implementation-artifacts"
    drafts.mkdir(parents=True)
    (drafts / "story.md").write_text("a draft\n", encoding="utf-8")

    assert _clean_one(repo, tmp_path, "quoted").name.endswith(".tar.gz")


def test_an_unmerged_branch_is_kept_and_the_clean_output_says_so(repo: Path, tmp_path: Path):
    wt = _started(repo, tmp_path, "unmerged")
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "not on main", cwd=wt)
    tip = _git("rev-parse", "HEAD", cwd=wt).stdout.strip()
    cleaned = clean_workspaces(
        slug="unmerged",
        root=repo,
        bookkeeping=repo / ".steward" / "workspaces.yaml",
        archive_dir=tmp_path / "archive",
        confirm=lambda s: True,
    )

    assert cleaned["archived"][0]["branch_kept"] == "unmerged"
    assert _git("rev-parse", "refs/heads/unmerged", cwd=repo).stdout.strip() == tip
    assert "(branch unmerged kept: not on its source)" in ws_module.format_clean(cleaned, as_json=False)


def test_a_merged_branch_is_still_deleted(repo: Path, tmp_path: Path):
    _started(repo, tmp_path, "merged-away")
    left = _clean_one(repo, tmp_path, "merged-away")

    assert left.name.endswith(".landed.txt")
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "refs/heads/merged-away"], cwd=repo, capture_output=True
    )
    assert probe.returncode != 0


def test_the_skip_journal_is_copied_into_the_note(repo: Path, tmp_path: Path):
    _exclude(repo, ".steward/")
    wt = _started(repo, tmp_path, "journaled")
    (wt / ".steward").mkdir()
    (wt / ".steward" / "preflight-skips.log").write_text(
        "2026-09-27T12:00:00Z\trefs/heads/journaled\tabc1234567\tpreflight ran green\n", encoding="utf-8"
    )

    note = _clean_one(repo, tmp_path, "journaled").read_text(encoding="utf-8")
    assert "pre-push skip journal (.steward/preflight-skips.log), copied (1 line(s)):" in note
    assert "refs/heads/journaled\tabc1234567\tpreflight ran green" in note


def test_a_gitlink_is_no_proof(repo: Path, tmp_path: Path):
    _git("update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},sub", cwd=repo)
    _git("commit", "-m", "a submodule gitlink", cwd=repo)
    _git("push", "-q", "origin", "main", cwd=repo)
    _started(repo, tmp_path, "with-gitlink")

    assert _clean_one(repo, tmp_path, "with-gitlink").name.endswith(".tar.gz")


def test_a_per_worktree_ref_is_no_proof(repo: Path, tmp_path: Path):
    wt = _started(repo, tmp_path, "worktree-ref")
    _git("update-ref", "refs/worktree/keep", "HEAD", cwd=wt)

    assert _clean_one(repo, tmp_path, "worktree-ref").name.endswith(".tar.gz")
