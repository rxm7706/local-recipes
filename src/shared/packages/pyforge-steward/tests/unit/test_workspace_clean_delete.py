"""Story 13.5 — ``steward workspace clean --delete`` (no prompt, no archive)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from pyforge.steward.workspace import (
    WorkspaceRecord,
    clean_workspaces,
    load_bookkeeping,
    save_bookkeeping,
    start_workspace,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _make_repo(tmp_path: Path) -> Path:
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


def _kwargs(repo: Path, tmp_path: Path, bookkeeping: Path) -> dict:
    return {
        "root": repo,
        "bookkeeping": bookkeeping,
        "archive_dir": tmp_path / "archive",
    }


def test_delete_drops_record_when_worktree_and_branch_gone(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    stale = WorkspaceRecord(
        slug="stale",
        path=str(tmp_path / "missing-wt"),
        branch="missing-branch",
        source="origin/main",
        created_at="2026-10-07T00:00:00+00:00",
    )
    save_bookkeeping(bookkeeping, (stale,))

    result = clean_workspaces(delete=True, slug="stale", **_kwargs(repo, tmp_path, bookkeeping))

    assert result["deleted"] == [stale.to_dict()]
    assert result["skipped"] == []
    assert load_bookkeeping(bookkeeping) == ()
    assert not (tmp_path / "archive").exists() or list((tmp_path / "archive").iterdir()) == []


def test_delete_landed_worktree_without_archive(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    archive_dir = tmp_path / "archive"
    dest = tmp_path / "landed"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "landed", cwd=repo)
    _git("push", "origin", "main", cwd=repo)

    result = clean_workspaces(delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=archive_dir)

    assert [row["slug"] for row in result["deleted"]] == ["landed"]
    assert not dest.exists()
    assert (
        subprocess.run(
            ["git", "rev-parse", "--verify", "landed"],
            cwd=repo,
            capture_output=True,
        ).returncode
        != 0
    )
    assert load_bookkeeping(bookkeeping) == ()
    assert not list(archive_dir.iterdir()) if archive_dir.is_dir() else True


def test_delete_refuses_not_merged(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "unmerged"
    start_workspace("unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "only-here.txt").write_text("x\n", encoding="utf-8")
    _git("add", "only-here.txt", cwd=dest)
    _git("commit", "-m", "ahead", cwd=dest)

    result = clean_workspaces(delete=True, slug="unmerged", **_kwargs(repo, tmp_path, bookkeeping))

    assert result["deleted"] == []
    assert result["skipped"][0]["reason"] == "not-merged"
    assert dest.is_dir()
    assert len(load_bookkeeping(bookkeeping)) == 1


def test_delete_refuses_skip_worktree(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "skip-wt"
    start_workspace("skip-wt", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("update-index", "--skip-worktree", "README.md", cwd=dest)
    (dest / "README.md").write_text("local override\n", encoding="utf-8")

    result = clean_workspaces(delete=True, slug="skip-wt", **_kwargs(repo, tmp_path, bookkeeping))

    assert result["skipped"][0]["reason"] == "dirty"
    assert dest.is_dir()


def test_delete_refuses_dirty(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "dirty"
    start_workspace("dirty", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "edit.txt").write_text("dirty\n", encoding="utf-8")

    result = clean_workspaces(delete=True, slug="dirty", **_kwargs(repo, tmp_path, bookkeeping))

    assert result["skipped"][0]["reason"] == "dirty"
    assert dest.is_dir()


def test_delete_gone_worktree_branch_off_source_keeps_branch(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "off-source"
    start_workspace("off-source", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "c.txt").write_text("c\n", encoding="utf-8")
    _git("add", "c.txt", cwd=dest)
    _git("commit", "-m", "ahead", cwd=dest)
    _git("worktree", "remove", "--force", str(dest), cwd=repo)

    result = clean_workspaces(delete=True, slug="off-source", **_kwargs(repo, tmp_path, bookkeeping))

    assert "not on" in result["skipped"][0]["reason"]
    assert _git("rev-parse", "--verify", "off-source", cwd=repo).returncode == 0
    assert len(load_bookkeeping(bookkeeping)) == 1


def test_delete_gone_worktree_branch_on_source_drops_branch(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "merged-gone"
    start_workspace("merged-gone", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "merged-gone", cwd=repo)
    _git("worktree", "remove", "--force", str(dest), cwd=repo)

    result = clean_workspaces(delete=True, slug="merged-gone", **_kwargs(repo, tmp_path, bookkeeping))

    assert result["deleted"][0]["slug"] == "merged-gone"
    assert (
        subprocess.run(
            ["git", "rev-parse", "--verify", "merged-gone"],
            cwd=repo,
            capture_output=True,
        ).returncode
        != 0
    )
    assert load_bookkeeping(bookkeeping) == ()


def test_fleet_delete_reports_deleted_and_skipped(repo: Path, tmp_path: Path):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    kw = _kwargs(repo, tmp_path, bookkeeping)

    gone = WorkspaceRecord(
        slug="gone-both",
        path=str(tmp_path / "nope"),
        branch="nope-branch",
        source="origin/main",
        created_at="2026-10-07T00:00:00+00:00",
    )
    save_bookkeeping(bookkeeping, (gone,))

    landed_path = tmp_path / "fleet-landed"
    start_workspace("fleet-landed", root=repo, bookkeeping=bookkeeping, path=landed_path, from_ref="origin/main")
    _git("checkout", "main", cwd=repo)
    _git("merge", "--ff-only", "fleet-landed", cwd=repo)

    dirty_path = tmp_path / "fleet-dirty"
    start_workspace("fleet-dirty", root=repo, bookkeeping=bookkeeping, path=dirty_path, from_ref="origin/main")
    (dirty_path / "x.txt").write_text("x", encoding="utf-8")

    unmerged_path = tmp_path / "fleet-unmerged"
    start_workspace("fleet-unmerged", root=repo, bookkeeping=bookkeeping, path=unmerged_path, from_ref="origin/main")
    (unmerged_path / "y.txt").write_text("y\n", encoding="utf-8")
    _git("add", "y.txt", cwd=unmerged_path)
    _git("commit", "-m", "y", cwd=unmerged_path)

    result = clean_workspaces(delete=True, **kw)

    deleted_slugs = {row["slug"] for row in result["deleted"]}
    skipped = {row["slug"]: row["reason"] for row in result["skipped"]}
    assert deleted_slugs == {"gone-both", "fleet-landed"}
    assert skipped["fleet-dirty"] == "dirty"
    assert skipped["fleet-unmerged"] == "not-merged"


def test_cli_slug_delete_refusal_exits_one(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "cli-refuse"
    start_workspace("cli-refuse", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "z.txt").write_text("z", encoding="utf-8")

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
    monkeypatch.setattr("pyforge.steward.workspace.default_archive_dir", lambda: tmp_path / "archive")

    rc = main(["workspace", "clean", "cli-refuse", "--delete"])

    assert rc == EXIT_FAILED
    assert "dirty" in capsys.readouterr().err


def test_cli_delete_usage_errors(repo: Path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr(
        "pyforge.steward.workspace.default_bookkeeping_path", lambda: repo / ".steward" / "workspaces.yaml"
    )
    monkeypatch.setattr("pyforge.steward.workspace.load_repo_sets", lambda: {"fleet-feature": object()})

    rc = main(["workspace", "clean", "--delete", "--merged-only"])
    assert rc == EXIT_USAGE

    rc = main(["workspace", "clean", "fleet-feature", "--delete"])
    assert rc == EXIT_USAGE


def test_cli_fleet_delete_json(repo: Path, tmp_path: Path, monkeypatch, capsys):
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    gone = WorkspaceRecord(
        slug="json-gone",
        path=str(tmp_path / "json-missing"),
        branch="json-missing-b",
        source="origin/main",
        created_at="2026-10-07T00:00:00+00:00",
    )
    save_bookkeeping(bookkeeping, (gone,))

    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: repo)
    monkeypatch.setattr("pyforge.steward.workspace.default_bookkeeping_path", lambda: bookkeeping)
    monkeypatch.setattr("pyforge.steward.workspace.default_archive_dir", lambda: tmp_path / "archive")

    rc = main(["workspace", "clean", "--delete", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert "deleted" in payload
    assert payload["deleted"][0]["slug"] == "json-gone"


def test_delete_mutation_guard_unmerged_must_not_be_removed(repo: Path, tmp_path: Path):
    """If ``--delete`` ever removed an unmerged worktree, this test would pass wrongly."""
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    dest = tmp_path / "mut-unmerged"
    start_workspace("mut-unmerged", root=repo, bookkeeping=bookkeeping, path=dest, from_ref="origin/main")
    (dest / "u.txt").write_text("u\n", encoding="utf-8")
    _git("add", "u.txt", cwd=dest)
    _git("commit", "-m", "u", cwd=dest)

    clean_workspaces(delete=True, slug="mut-unmerged", **_kwargs(repo, tmp_path, bookkeeping))

    assert dest.is_dir(), "unmerged worktree must be kept — delete implementation regressed"
