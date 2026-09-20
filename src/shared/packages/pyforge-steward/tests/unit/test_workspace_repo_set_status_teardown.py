"""Story 13.4 — set-level status + safe teardown (dirty refusal, merged-only)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.workspace import (
    WorkspaceError,
    clean_repo_set,
    load_bookkeeping,
    open_repo_set_members,
    start_repo_set,
    status_repo_set,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _make_repo(tmp_path: Path, name: str) -> Path:
    origin = tmp_path / f"{name}.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)

    work = tmp_path / name
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    scripts = work / "scripts"
    scripts.mkdir()
    (scripts / "bmad-loop-worktree").write_text("#!/usr/bin/env true\n", encoding="utf-8")
    (work / "README.md").write_text(f"{name}\n", encoding="utf-8")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    _git("remote", "set-url", "origin", str(origin), cwd=work)
    _git("fetch", "origin", cwd=work)
    return work


def _write_repo_sets(
    path: Path,
    *,
    primary: Path,
    secondary: Path,
) -> None:
    document = {
        "projects": {
            "fleet-feature": {
                "repos": {
                    "primary": {"path": str(primary)},
                    "secondary": {"path": str(secondary)},
                }
            }
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


@pytest.fixture
def two_repos(tmp_path: Path) -> tuple[Path, Path]:
    return _make_repo(tmp_path, "local-recipes"), _make_repo(tmp_path, "tracker")


@pytest.fixture
def open_set(two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    primary, secondary = two_repos
    config = primary / ".steward" / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary)
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)
    start_repo_set("fleet-feature", from_ref="origin/main")
    return primary, secondary, config


def test_status_repo_set_reports_dirty_and_unpushed_across_members(
    open_set: tuple[Path, Path, Path],
) -> None:
    primary, secondary, _config = open_set
    members = open_repo_set_members("fleet-feature")
    assert len(members) == 2
    by_name = {m.name: m for m in members}

    # Dirty primary.
    Path(by_name["primary"].record.path, "dirty.txt").write_text("x\n", encoding="utf-8")
    # Unpushed secondary (ahead of origin/main).
    _git(
        "commit",
        "--allow-empty",
        "-m",
        "ahead",
        cwd=Path(by_name["secondary"].record.path),
    )

    rows = status_repo_set("fleet-feature")
    assert {r.member for r in rows} == {"primary", "secondary"}
    primary_row = next(r for r in rows if r.member == "primary")
    secondary_row = next(r for r in rows if r.member == "secondary")
    assert primary_row.status.dirty is True
    assert secondary_row.status.dirty is False
    assert secondary_row.status.ahead == 1


def test_clean_repo_set_refuses_dirty_and_names_member(
    open_set: tuple[Path, Path, Path],
) -> None:
    _primary, _secondary, _config = open_set
    members = open_repo_set_members("fleet-feature")
    dirty_member = next(m for m in members if m.name == "secondary")
    Path(dirty_member.record.path, "dirt.txt").write_text("nope\n", encoding="utf-8")

    with pytest.raises(WorkspaceError, match=r"dirty member\(s\): secondary"):
        clean_repo_set("fleet-feature", merged_only=True)

    # Nothing archived — both members still open.
    assert len(open_repo_set_members("fleet-feature")) == 2
    assert Path(dirty_member.record.path).is_dir()


def test_clean_repo_set_merged_only_archives_per_member(
    open_set: tuple[Path, Path, Path],
) -> None:
    primary, secondary, _config = open_set
    members = {m.name: m for m in open_repo_set_members("fleet-feature")}

    # Merge only primary's feature branch into origin/main.
    branch = members["primary"].record.branch
    _git("checkout", "main", cwd=primary)
    _git("merge", "--ff-only", branch, cwd=primary)
    _git("push", "origin", "main", cwd=primary)

    # Advance secondary so it stays unmerged.
    _git(
        "commit",
        "--allow-empty",
        "-m",
        "unmerged",
        cwd=Path(members["secondary"].record.path),
    )

    result = clean_repo_set("fleet-feature", merged_only=True)

    assert len(result["archived"]) == 1
    assert result["archived"][0]["member"] == "primary"
    archive = Path(result["archived"][0]["archive"])
    assert archive.is_file()
    assert archive.name.endswith(".tar.gz")

    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["member"] == "secondary"
    assert result["skipped"][0]["reason"] == "not-merged"
    assert Path(members["secondary"].record.path).is_dir()
    assert not Path(members["primary"].record.path).exists()
    assert load_bookkeeping(primary / ".steward" / "workspaces.yaml") == ()
    assert len(load_bookkeeping(secondary / ".steward" / "workspaces.yaml")) == 1
    # Partial teardown must keep the coordinated workspace file while a member
    # remains open (only unlink when the set is fully closed).
    ws_file = primary / ".steward" / "workspaces" / "f-fleet-feature.code-workspace"
    assert ws_file.is_file()


def test_clean_repo_set_refuses_unassessable_member(
    open_set: tuple[Path, Path, Path],
) -> None:
    """Missing worktree path → status.error → clean must refuse, not archive."""
    members = {m.name: m for m in open_repo_set_members("fleet-feature")}
    gone = Path(members["secondary"].record.path)
    # Remove the worktree directory but leave bookkeeping so status is unassessable.
    import shutil

    shutil.rmtree(gone)
    assert not gone.exists()

    with pytest.raises(WorkspaceError, match=r"cannot assess member ['\"]secondary['\"]"):
        clean_repo_set("fleet-feature", merged_only=False, confirm=lambda _slug: True)

    # Owned primary must still be open — no partial archive on assess failure.
    still = open_repo_set_members("fleet-feature")
    assert {m.name for m in still} == {"primary", "secondary"}
    assert Path(members["primary"].record.path).is_dir()


def test_clean_repo_set_archives_not_deletes_when_clean(
    open_set: tuple[Path, Path, Path],
) -> None:
    primary, secondary, _config = open_set
    members = {m.name: m for m in open_repo_set_members("fleet-feature")}
    marker = Path(members["primary"].record.path) / "keep-me.txt"
    marker.write_text("recover\n", encoding="utf-8")
    # Staging the marker makes the tree dirty — commit it so clean may proceed.
    _git("add", "keep-me.txt", cwd=Path(members["primary"].record.path))
    _git("commit", "-m", "marker", cwd=Path(members["primary"].record.path))

    result = clean_repo_set(
        "fleet-feature",
        merged_only=False,
        confirm=lambda slug: True,
    )

    assert len(result["archived"]) == 2
    import tarfile

    primary_archive = Path(next(r["archive"] for r in result["archived"] if r["member"] == "primary"))
    with tarfile.open(primary_archive, "r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("keep-me.txt") for n in names)
    assert open_repo_set_members("fleet-feature") == ()
    ws = primary / ".steward" / "workspaces" / "f-fleet-feature.code-workspace"
    assert not ws.exists()
    assert load_bookkeeping(secondary / ".steward" / "workspaces.yaml") == ()


def test_own_worktrees_only_set_wide_hides_foreign_loop_homes(
    open_set: tuple[Path, Path, Path],
) -> None:
    primary, secondary, _config = open_set
    # Plant Marshal-style foreign worktrees in both members.
    for repo in (primary, secondary):
        foreign = repo.parent / f"{repo.name}-loop-home"
        _git(
            "worktree",
            "add",
            str(foreign),
            "-b",
            f"loop/{repo.name}",
            "origin/main",
            cwd=repo,
        )

    rows = status_repo_set("fleet-feature")
    text = json.dumps([r.to_dict() for r in rows])
    assert "loop/" not in text
    assert "loop-home" not in text
    assert {r.member for r in rows} == {"primary", "secondary"}

    # Merge both so --merged-only would archive owned set members only.
    for item in open_repo_set_members("fleet-feature"):
        _git("checkout", "main", cwd=item.root)
        _git("merge", "--ff-only", item.record.branch, cwd=item.root)
        _git("push", "origin", "main", cwd=item.root)

    result = clean_repo_set("fleet-feature", merged_only=True)
    assert len(result["archived"]) == 2
    for repo in (primary, secondary):
        foreign = repo.parent / f"{repo.name}-loop-home"
        assert foreign.is_dir(), "foreign loop-home must remain"
        listed = _git("worktree", "list", "--porcelain", cwd=repo).stdout
        assert str(foreign.resolve()) in listed


def test_cli_status_and_clean_repo_set(
    open_set: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    primary, _secondary, config = open_set
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)

    rc = main(["workspace", "status", "fleet-feature", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 2
    assert {row["member"] for row in payload} == {"primary", "secondary"}

    # Dirty one member → clean must refuse and name it.
    members = open_repo_set_members("fleet-feature")
    Path(members[0].record.path, "x.txt").write_text("dirt\n", encoding="utf-8")
    dirty_name = members[0].name

    rc = main(["workspace", "clean", "fleet-feature", "--merged-only", "--json"])
    assert rc == EXIT_FAILED
    captured = capsys.readouterr()
    err = json.loads(captured.err or captured.out)
    assert "dirty member" in err["error"]
    assert dirty_name in err["error"]
