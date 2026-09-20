"""Unit tests for `branch_diff_guard` (retro-pyforge-steward-2026-09-04.md
action item 11) against a throwaway git repo, not this checkout."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.testing_kit import (
    changed_paths_since,
    commit_files,
    commit_subject,
    commits_since,
    diff_text_since,
    existed_at_ref,
    pyforge_import_offenders,
    unsanctioned_commits,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "base.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "branch", "main")
    _git(root, "branch", "origin_main_ref")
    return root


def _make_origin_main(root: Path) -> None:
    # Simulate a remote-tracking `origin/main` ref without a real remote.
    (root / ".git" / "refs" / "remotes" / "origin").mkdir(parents=True, exist_ok=True)
    sha = _git(root, "rev-parse", "HEAD").strip()
    (root / ".git" / "refs" / "remotes" / "origin" / "main").write_text(sha + "\n")


def test_changed_paths_since_skips_loudly_without_base_ref(repo: Path):
    with pytest.raises(pytest.skip.Exception):
        changed_paths_since(repo, base="origin/main", pathspec="src")


def test_changed_paths_since_reports_changed_files(repo: Path):
    _make_origin_main(repo)
    (repo / "src").mkdir()
    (repo / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add src/new.py")
    changed = changed_paths_since(repo, base="origin/main", pathspec="src")
    assert changed == ["src/new.py"]


def test_changed_paths_since_includes_untracked_when_asked(repo: Path):
    _make_origin_main(repo)
    (repo / "src").mkdir()
    (repo / "src" / "untracked.py").write_text("z = 3\n", encoding="utf-8")
    changed = changed_paths_since(repo, base="origin/main", pathspec="src", include_untracked=True)
    assert changed == ["src/untracked.py"]
    assert changed_paths_since(repo, base="origin/main", pathspec="src") == []


def test_changed_paths_since_always_include(repo: Path):
    _make_origin_main(repo)
    changed = changed_paths_since(repo, base="origin/main", always_include=("self.py",))
    assert changed == ["self.py"]


def test_diff_text_since_skips_loudly_without_base_ref(repo: Path):
    with pytest.raises(pytest.skip.Exception):
        diff_text_since(repo, base="origin/main")


def test_diff_text_since_returns_patch(repo: Path):
    _make_origin_main(repo)
    (repo / "base.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "change base")
    text = diff_text_since(repo, base="origin/main", pathspec="base.py")
    assert "-x = 1" in text
    assert "+x = 2" in text


def test_existed_at_ref(repo: Path):
    _make_origin_main(repo)
    assert existed_at_ref(repo, "base.py", ref="origin/main") is True
    assert existed_at_ref(repo, "does-not-exist.py", ref="origin/main") is False


def test_pyforge_import_offenders_finds_top_level_imports(repo: Path):
    (repo / "clean.py").write_text("import os\n", encoding="utf-8")
    (repo / "dirty_import.py").write_text("import pyforge.core\n", encoding="utf-8")
    (repo / "dirty_from.py").write_text("from pyforge.core import x\n", encoding="utf-8")
    offenders = pyforge_import_offenders(["clean.py", "dirty_import.py", "dirty_from.py", "missing.py"], repo)
    assert offenders == ["dirty_import.py:1", "dirty_from.py:1"]


def test_commits_since_and_commit_metadata(repo: Path):
    _make_origin_main(repo)
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add a.py")
    shas = commits_since(repo, base="origin/main")
    assert len(shas) == 1
    assert commit_subject(repo, shas[0]) == "add a.py"
    assert commit_files(repo, shas[0]) == ["a.py"]


def test_unsanctioned_commits_accepts_a_sanctioned_retro(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    changelog = "surface/CHANGELOG.md"
    (repo / surface).mkdir()
    (repo / changelog).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retro: bump surface")
    assert unsanctioned_commits(repo, pathspec=surface, changelog_path=changelog) == []


def test_unsanctioned_commits_flags_an_unsanctioned_edit(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    (repo / surface).mkdir()
    (repo / surface / "file.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "story: touch surface")
    bad = unsanctioned_commits(repo, pathspec=surface, changelog_path=f"{surface}/CHANGELOG.md")
    assert len(bad) == 1
    assert "story: touch surface" in bad[0]


def test_unsanctioned_commits_flags_uncommitted_dirt(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    changelog = f"{surface}/CHANGELOG.md"
    (repo / surface).mkdir()
    (repo / changelog).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retro: seed surface")
    (repo / changelog).write_text("v2\n", encoding="utf-8")  # uncommitted edit, not staged
    bad = unsanctioned_commits(repo, pathspec=surface, changelog_path=changelog)
    assert any(entry.startswith("uncommitted:") for entry in bad)
