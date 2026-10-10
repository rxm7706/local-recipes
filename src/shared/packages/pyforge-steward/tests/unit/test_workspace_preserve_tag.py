"""Story 85.5 — ``workspace clean`` parks unlanded commits as preserve tags."""

from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pyforge.core.preserve_refs import parse_preserve_ref

from pyforge.steward.workspace import (
    WORKSPACE_PRESERVE_TAG_FLAG,
    clean_workspaces,
    start_workspace,
    workspace_preserve_tag_enabled,
)

_FLAG = "pyforge.steward.workspace_preserve_tag"

_FLAG_METADATA = {
    "owner": "steward",
    "story": "85-5-workspace-clean-parks-unlanded-commits-as-a-preserve-tag-before-removing-the-worktree",
    "created": "2026-10-04",
    "on_everywhere": "",
    "cleanup_by": "",
}


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
    purge_dir = work / "docs" / "governance"
    purge_dir.mkdir(parents=True)
    (purge_dir / "preserve-purge-list.json").write_text(
        json.dumps({"schema_version": 1, "commit_shas": [], "paths": []}),
        encoding="utf-8",
    )
    return work


def _write_flagd_tree(tmp_path: Path, variant: str) -> Path:
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps(
            {
                "flags": {
                    _FLAG: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                        "metadata": _FLAG_METADATA,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path)


def _clean(
    repo: Path,
    tmp_path: Path,
    slug: str,
    *,
    preserve_tag_enabled: bool | None = None,
    flags_path: Path | None = None,
) -> dict:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    kwargs: dict = {
        "slug": slug,
        "root": repo,
        "bookkeeping": bookkeeping,
        "archive_dir": tmp_path / "archive",
        "confirm": lambda _s: True,
    }
    if preserve_tag_enabled is not None:
        with patch(
            "pyforge.steward.workspace.workspace_preserve_tag_enabled",
            return_value=preserve_tag_enabled,
        ):
            return clean_workspaces(**kwargs)
    if flags_path is not None:
        monkey = pytest.MonkeyPatch()
        monkey.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
        try:
            return clean_workspaces(**kwargs)
        finally:
            monkey.undo()
    return clean_workspaces(**kwargs)


def test_flag_off_keeps_legacy_tarball_for_unlanded_commit(repo: Path, tmp_path: Path) -> None:
    flags = _write_flagd_tree(tmp_path, "off")
    wt = tmp_path / "ahead"
    start_workspace(
        "ahead",
        root=repo,
        bookkeeping=repo / ".steward" / "workspaces.yaml",
        path=wt,
        from_ref="origin/main",
    )
    (wt / "work.txt").write_text("work\n", encoding="utf-8")
    _git("add", "work.txt", cwd=wt)
    _git("commit", "-m", "not on main", cwd=wt)

    result = _clean(repo, tmp_path, "ahead", flags_path=flags)

    row = result["archived"][0]
    assert row["archive"].endswith(".tar.gz")
    assert "preserve_tag" not in row
    assert not wt.exists()


def test_flag_on_writes_preserve_tag_and_removes_worktree(repo: Path, tmp_path: Path) -> None:
    wt = tmp_path / "story-wt"
    slug = "dispatch-pyforge-steward-85-5"
    branch = "dispatch/pyforge-steward/85-5"
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _git("worktree", "add", "-b", branch, str(wt), "origin/main", cwd=repo)
    from pyforge.steward.workspace import WorkspaceRecord, load_bookkeeping, save_bookkeeping

    save_bookkeeping(
        bookkeeping,
        load_bookkeeping(bookkeeping)
        + (
            WorkspaceRecord(
                slug=slug,
                path=str(wt.resolve()),
                branch=branch,
                source="origin/main",
                created_at="2026-10-10T00:00:00+00:00",
            ),
        ),
    )
    (wt / "tracked-edit.txt").write_text("edit\n", encoding="utf-8")
    _git("add", "tracked-edit.txt", cwd=wt)
    _git("commit", "-m", "unlanded", cwd=wt)
    (wt / "untracked.txt").write_text("never added\n", encoding="utf-8")

    result = _clean(repo, tmp_path, slug, preserve_tag_enabled=True)

    row = result["archived"][0]
    assert row.get("preserve_tag", "").startswith("preserve/")
    assert "workspace-" in row["preserve_tag"]
    assert not wt.exists()
    parsed = parse_preserve_ref(f"refs/tags/{row['preserve_tag']}")
    assert parsed.project_slug == "pyforge-steward"
    assert parsed.story_key == "85.5"
    assert parsed.producer == "workspace"
    tree = _git("rev-parse", f"{row['preserve_tag']}^{{tree}}", cwd=repo).stdout.strip()
    paths = _git("ls-tree", "-r", "--name-only", tree, cwd=repo).stdout
    assert "tracked-edit.txt" in paths
    assert "untracked.txt" in paths


def test_flag_on_push_debt_still_removes_worktree(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wt = tmp_path / "ahead"
    start_workspace(
        "ahead", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=wt, from_ref="origin/main"
    )
    _git("commit", "--allow-empty", "-m", "ahead", cwd=wt)

    def _push_fail(*_a, **_k):
        from pyforge.core.preserve_refs import PushPreserveResult

        return PushPreserveResult("refs/tags/preserve/unbound/workspace-deadbeef", False, ())

    monkeypatch.setattr("pyforge.steward.workspace.push_preserve_ref", _push_fail)

    result = _clean(repo, tmp_path, "ahead", preserve_tag_enabled=True)

    row = result["archived"][0]
    assert row.get("preserve_debt")
    assert not wt.exists()


def test_flag_on_tag_failure_keeps_worktree(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wt = tmp_path / "blocked"
    start_workspace(
        "blocked", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=wt, from_ref="origin/main"
    )
    _git("commit", "--allow-empty", "-m", "ahead", cwd=wt)

    from pyforge.core.preserve_refs import PreserveGitError

    def _tag_boom(*_a, **_k):
        raise PreserveGitError("read-only object store")

    monkeypatch.setattr("pyforge.steward.workspace.tag_preserve", _tag_boom)

    result = _clean(repo, tmp_path, "blocked", preserve_tag_enabled=True)

    assert result["archived"] == []
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["branch_kept"] == "blocked"
    assert wt.is_dir()


def test_flag_on_landed_worktree_keeps_note_not_tag(repo: Path, tmp_path: Path) -> None:
    wt = tmp_path / "landed"
    start_workspace(
        "landed", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=wt, from_ref="origin/main"
    )

    result = _clean(repo, tmp_path, "landed", preserve_tag_enabled=True)

    row = result["archived"][0]
    assert row["archive"].endswith(".landed.txt")
    assert "preserve_tag" not in row


def test_flag_on_host_local_tarball_holds_only_ignored(repo: Path, tmp_path: Path) -> None:
    wt = tmp_path / "ignored-only"
    start_workspace(
        "ignored-only",
        root=repo,
        bookkeeping=repo / ".steward" / "workspaces.yaml",
        path=wt,
        from_ref="origin/main",
    )
    _git("commit", "--allow-empty", "-m", "ahead", cwd=wt)
    common = Path(_git("rev-parse", "--git-common-dir", cwd=repo).stdout.strip())
    exclude = (common if common.is_absolute() else repo / common) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("*.local\n", encoding="utf-8")
    (wt / "secret.local").write_text("ignored bytes\n", encoding="utf-8")

    result = _clean(repo, tmp_path, "ignored-only", preserve_tag_enabled=True)

    row = result["archived"][0]
    assert row.get("host_local") == "true"
    archive = Path(row["archive"])
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("secret.local") for n in names)
    assert not any(n.endswith("README.md") for n in names)


def test_station_source_has_no_marshal_import() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "pyforge" / "steward"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "pyforge.marshal" not in text, path.name


def test_mutation_removing_park_call_must_fail(repo: Path, tmp_path: Path) -> None:
    """Guard: ``clean`` must call ``_park_unlanded_preserve`` before removing an unlanded tree."""
    import pyforge.steward.workspace as ws

    wt = tmp_path / "mut"
    start_workspace(
        "mut", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=wt, from_ref="origin/main"
    )
    _git("commit", "--allow-empty", "-m", "ahead", cwd=wt)

    real = ws._park_unlanded_preserve

    def _noop_park(*_a, **_k):
        raise AssertionError("_park_unlanded_preserve must run when preserve tag is on and branch is unlanded")

    ws._park_unlanded_preserve = _noop_park
    try:
        with pytest.raises(AssertionError):
            _clean(repo, tmp_path, "mut", preserve_tag_enabled=True)
    finally:
        ws._park_unlanded_preserve = real


def test_read_boolean_flag_fixture(tmp_path: Path) -> None:
    from pyforge.core.flags import read_boolean

    on_path = _write_flagd_tree(tmp_path, "on")
    assert read_boolean(_FLAG, default=False, flags_path=on_path) is True
    off_dir = tmp_path / "offdir"
    off_dir.mkdir()
    off_path = _write_flagd_tree(off_dir, "off")
    assert read_boolean(_FLAG, default=False, flags_path=off_path) is False
    assert workspace_preserve_tag_enabled(flags_path=off_path) is False


def test_flag_key_is_the_module_constant() -> None:
    assert _FLAG == WORKSPACE_PRESERVE_TAG_FLAG
