"""Story 13.3 — multi-repo repo-set ``workspace start`` + missing-member naming."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.workspace import (
    RepoSetStartResult,
    WorkspaceError,
    load_bookkeeping,
    load_repo_sets,
    start_repo_set,
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
    secondary: Path | None,
    missing_name: str | None = None,
) -> None:
    repos: dict[str, dict[str, str]] = {
        "primary": {"path": str(primary)},
    }
    if secondary is not None:
        repos["secondary"] = {"path": str(secondary)}
    if missing_name is not None:
        repos[missing_name] = {"path": str(primary.parent / "absent-repo")}
    document = {"projects": {"fleet-feature": {"repos": repos}}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


@pytest.fixture
def two_repos(tmp_path: Path) -> tuple[Path, Path]:
    primary = _make_repo(tmp_path, "local-recipes")
    secondary = _make_repo(tmp_path, "tracker")
    return primary, secondary


def test_load_repo_sets_parses_projects(two_repos: tuple[Path, Path], tmp_path: Path) -> None:
    primary, secondary = two_repos
    config = tmp_path / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary)
    sets = load_repo_sets(config)
    assert "fleet-feature" in sets
    assert len(sets["fleet-feature"].members) == 2
    names = {m.name for m in sets["fleet-feature"].members}
    assert names == {"primary", "secondary"}


def test_start_repo_set_creates_worktrees_and_code_workspace(
    two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    primary, secondary = two_repos
    config = primary / ".steward" / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary)
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)

    result = start_repo_set("fleet-feature", from_ref="origin/main")

    assert isinstance(result, RepoSetStartResult)
    assert result.branch == "f-fleet-feature"
    assert len(result.members) == 2
    ws_path = Path(result.workspace_file)
    assert ws_path.is_file()
    payload = json.loads(ws_path.read_text(encoding="utf-8"))
    assert len(payload["folders"]) == 2

    for repo in (primary, secondary):
        records = load_bookkeeping(repo / ".steward" / "workspaces.yaml")
        assert len(records) == 1
        assert records[0].branch == "f-fleet-feature"


def test_start_repo_set_names_missing_members(two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    primary, secondary = two_repos
    config = primary / ".steward" / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary, missing_name="ghost")
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)

    with pytest.raises(WorkspaceError, match="missing local repos.*ghost"):
        start_repo_set("fleet-feature")

    assert not load_bookkeeping(primary / ".steward" / "workspaces.yaml")
    assert not load_bookkeeping(secondary / ".steward" / "workspaces.yaml")


def test_cli_repo_set_start_json(two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    primary, secondary = two_repos
    config = primary / ".steward" / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary)
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)

    rc = main(["workspace", "start", "fleet-feature", "--json"])
    assert rc == EXIT_OK


def test_cli_repo_set_missing_member_fails(two_repos: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    primary, secondary = two_repos
    config = primary / ".steward" / "repo-sets.yaml"
    _write_repo_sets(config, primary=primary, secondary=secondary, missing_name="ghost")
    monkeypatch.setattr("pyforge.steward.workspace.repo_root", lambda: primary)
    monkeypatch.setattr("pyforge.steward.workspace.default_repo_sets_path", lambda: config)

    rc = main(["workspace", "start", "fleet-feature", "--json"])
    assert rc == EXIT_FAILED
