"""``scripts/cfe_rebuild_guard_check.py::retro_commits_since`` never counts a merge.

A merge commit restates the churn of the commits it merged in, so counting it
made the newest "retro" an unauthored SHA: `main` went red after every CFE retro
merge (a post-merge re-point ritual, PR #1009 -> 9ec3606b79) and a PR carrying a
retro could never match on the `pull_request` event, where GitHub checks out a
synthetic ``refs/pull/N/merge`` commit (Detectors run 33912193119, 2026-09-04).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[6]
_GUARD = _REPO_ROOT / "scripts" / "cfe_rebuild_guard_check.py"
_SURFACE = ".claude/skills/conda-forge-expert"


def _load_guard():
    spec = importlib.util.spec_from_file_location("_cfe_rebuild_guard_under_test", _GUARD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _commit_all(cwd: Path, subject: str) -> str:
    _git(cwd, "add", "-A")
    _git(cwd, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", subject)
    return _git(cwd, "rev-parse", "HEAD")


def test_a_merge_that_carries_a_retro_is_not_itself_a_retro(tmp_path: Path) -> None:
    guard = _load_guard()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README").write_text("base\n", encoding="utf-8")
    base = _commit_all(repo, "base")

    _git(repo, "checkout", "-q", "-b", "retro")
    (repo / _SURFACE / "scripts").mkdir(parents=True)
    (repo / _SURFACE / "scripts" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (repo / _SURFACE / "CHANGELOG.md").write_text("v1\n", encoding="utf-8")
    retro = _commit_all(repo, "retro: x")

    _git(repo, "checkout", "-q", "main")
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge retro into main",
        "retro",
    )
    merge = _git(repo, "rev-parse", "HEAD")
    assert merge != retro

    retros = guard.retro_commits_since(repo, base)
    assert retros == [retro], (
        f"the authored retro must be the newest qualifying retro; the merge that carried it must not appear: {retros}"
    )
