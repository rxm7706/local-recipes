"""Story 117.24 — a new workspace starts with the mypy caches of the last one.

``scripts/lint_types.py`` keeps one mypy cache per package per pixi environment, at
``src/shared/packages/<package>/.mypy_cache/<environment>/``. ``workspace clean`` copies a worktree's caches into the
checkout it runs from before it removes the worktree, and ``workspace start`` copies the checkout's caches into the
new worktree, so the new worktree's first mypy lane runs warm.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import pyforge.steward.workspace as ws_module
from pyforge.steward.workspace import (
    clean_workspaces,
    copy_mypy_caches,
    mypy_cache_dirs,
    start_workspace,
)

PACKAGE = Path("src/shared/packages/pyforge-demo")


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _cache(tree: Path, environment: str, text: str, *, package: Path = PACKAGE) -> Path:
    """One cached module of ``environment``'s mypy cache under ``tree``; returns the cache's root."""
    root = tree / package / ".mypy_cache" / environment
    meta = root / "3.14" / "pyforge" / "demo.meta.json"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(text, encoding="utf-8")
    return root


def _read(tree: Path, environment: str, *, package: Path = PACKAGE) -> str:
    meta = tree / package / ".mypy_cache" / environment / "3.14" / "pyforge" / "demo.meta.json"
    return meta.read_text(encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout with one package and a ``.gitignore`` that ignores mypy's caches, as the real one does."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    work = tmp_path / "local-recipes"
    work.mkdir()
    _git("init", "-b", "main", cwd=work)
    _git("config", "user.email", "test@example.com", cwd=work)
    _git("config", "user.name", "Test", cwd=work)
    (work / "scripts").mkdir()
    (work / "scripts" / "bmad-loop-worktree").write_text("#!/usr/bin/env true\n", encoding="utf-8")
    (work / ".gitignore").write_text(".mypy_cache/\n", encoding="utf-8")
    (work / PACKAGE).mkdir(parents=True)
    (work / PACKAGE / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work


def test_the_caches_are_the_per_environment_directories_only(tmp_path: Path) -> None:
    _cache(tmp_path, "pyforge-guild", "{}")
    _cache(tmp_path, "pyforge-foundry-full", "{}")
    # mypy's default layout: a version directory straight under .mypy_cache/, not a cache lint_types.py writes.
    (tmp_path / PACKAGE / ".mypy_cache" / "3.14" / "pyforge").mkdir(parents=True)
    # a directory with no version directory inside is no mypy cache either
    (tmp_path / PACKAGE / ".mypy_cache" / "notes").mkdir()

    assert mypy_cache_dirs(tmp_path) == [
        PACKAGE / ".mypy_cache" / "pyforge-foundry-full",
        PACKAGE / ".mypy_cache" / "pyforge-guild",
    ]


def test_a_copy_replaces_the_target_and_skips_a_package_the_target_lacks(tmp_path: Path) -> None:
    source, dest = tmp_path / "source", tmp_path / "dest"
    _cache(source, "pyforge-guild", "new")
    _cache(source, "pyforge-guild", "{}", package=Path("src/shared/packages/pyforge-gone"))
    _cache(dest, "pyforge-guild", "old")
    stale = dest / PACKAGE / ".mypy_cache" / "pyforge-guild" / "3.14" / "pyforge" / "stale.meta.json"
    stale.write_text("{}", encoding="utf-8")

    copied, failures = copy_mypy_caches(source, dest)

    assert (copied, failures) == (1, [])
    assert _read(dest, "pyforge-guild") == "new"
    assert not stale.exists(), "the target is replaced, not merged into"
    assert not (dest / "src/shared/packages/pyforge-gone").exists()
    assert sorted(p.name for p in (dest / PACKAGE / ".mypy_cache").iterdir()) == ["pyforge-guild"]


def test_a_copy_is_never_a_link(tmp_path: Path) -> None:
    source, dest = tmp_path / "source", tmp_path / "dest"
    _cache(source, "pyforge-guild", "mine")
    (dest / PACKAGE).mkdir(parents=True)

    copy_mypy_caches(source, dest)
    (dest / PACKAGE / ".mypy_cache" / "pyforge-guild" / "3.14" / "pyforge" / "demo.meta.json").write_text(
        "theirs", encoding="utf-8"
    )

    assert _read(source, "pyforge-guild") == "mine"


def test_a_failed_copy_is_reported_and_leaves_no_half_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, dest = tmp_path / "source", tmp_path / "dest"
    _cache(source, "pyforge-guild", "new")
    _cache(dest, "pyforge-guild", "old")

    def refuse(src: Path, dst: Path, **_kwargs: object) -> None:
        Path(dst).mkdir(parents=True)
        (Path(dst) / "half").write_text("x", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(ws_module.shutil, "copytree", refuse)

    copied, failures = copy_mypy_caches(source, dest)

    assert copied == 0
    assert len(failures) == 1 and "pyforge-guild" in failures[0] and "disk full" in failures[0]
    assert _read(dest, "pyforge-guild") == "old"
    assert sorted(p.name for p in (dest / PACKAGE / ".mypy_cache").iterdir()) == ["pyforge-guild"]


def test_start_copies_the_checkout_s_caches_into_the_new_worktree(repo: Path, tmp_path: Path) -> None:
    _cache(repo, "pyforge-guild", "warm")
    dest = tmp_path / "next"

    start_workspace("next", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=dest)

    assert _read(dest, "pyforge-guild") == "warm"
    assert _git("status", "--porcelain", cwd=dest).stdout == "", "the copied caches are ignored, as in the real tree"


def test_start_goes_on_when_the_copy_fails(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _cache(repo, "pyforge-guild", "warm")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("no space left")

    monkeypatch.setattr(ws_module.shutil, "copytree", refuse)
    dest = tmp_path / "next"

    record = start_workspace("next", root=repo, bookkeeping=repo / ".steward" / "workspaces.yaml", path=dest)

    assert Path(record.path).is_dir()
    assert "workspace start: mypy cache not copied" in capsys.readouterr().err


def test_clean_keeps_the_worktree_s_caches_for_the_next_start(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    _cache(repo, "pyforge-guild", "older")
    done = tmp_path / "done"
    start_workspace("done", root=repo, bookkeeping=bookkeeping, path=done)
    _cache(done, "pyforge-guild", "newer")
    _cache(done, "pyforge-foundry-full", "newer")

    result = clean_workspaces(
        root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "archive", confirm=lambda _: True
    )

    assert [row["slug"] for row in result["archived"]] == ["done"]
    assert not done.exists()
    assert _read(repo, "pyforge-guild") == "newer"
    assert _read(repo, "pyforge-foundry-full") == "newer"

    following = tmp_path / "following"
    start_workspace("following", root=repo, bookkeeping=bookkeeping, path=following)
    assert _read(following, "pyforge-foundry-full") == "newer"


def test_clean_delete_keeps_the_worktree_s_caches(repo: Path, tmp_path: Path) -> None:
    bookkeeping = repo / ".steward" / "workspaces.yaml"
    landed = tmp_path / "landed"
    start_workspace("landed", root=repo, bookkeeping=bookkeeping, path=landed)
    _cache(landed, "pyforge-guild", "from-landed")

    result = clean_workspaces(
        delete=True, slug="landed", root=repo, bookkeeping=bookkeeping, archive_dir=tmp_path / "a"
    )

    assert [row["slug"] for row in result["deleted"]] == ["landed"]
    assert not landed.exists()
    assert _read(repo, "pyforge-guild") == "from-landed"
