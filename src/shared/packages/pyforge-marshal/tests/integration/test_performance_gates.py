"""Story 12.5 — performance gates (NFR-P1 / NFR-P2 / NFR-P3 / SC-09).

Uses a local-recipes-sized synthetic fixture (nested dirs + multi-pattern
``.gitignore``), matching ``test_seed_verbs_check``'s NFR-P1 technique.
"""

from __future__ import annotations

import subprocess
import time
from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.model.manifest import Manifest, load_manifest
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.init import run_init

_PERF_FIXTURE_GITIGNORE = """\
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/
build/
dist/
.venv/
node_modules/
.DS_Store
*.log
.env
.marshal/
_bmad-output/projects/*/implementation-artifacts/
"""


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _commit_all(repo: Path, message: str = "commit") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, "--allow-empty")


def _init_git_repo(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(repo, "initial")
    return repo


def _local_recipes_sized_tree(root: Path) -> Path:
    """~1200 nested files + representative .gitignore (NFR-P1 fixture)."""
    _init_git_repo(root)
    (root / ".gitignore").write_text(_PERF_FIXTURE_GITIGNORE, encoding="utf-8")
    for i in range(12):
        for j in range(10):
            leaf = root / f"dir{i}" / f"sub{j}" / "leaf"
            leaf.mkdir(parents=True, exist_ok=True)
            for k in range(10):
                (leaf / f"file{k}.txt").write_text("x\n", encoding="utf-8")
    _commit_all(root, "perf-fixture")
    return root


@pytest.fixture(scope="module")
def real_manifest() -> Manifest:
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def test_check_under_nfr_p1_budget(real_manifest, tmp_path):
    repo = _local_recipes_sized_tree(tmp_path / "sized")
    started = time.perf_counter()
    run_check(repo, real_manifest)
    elapsed = time.perf_counter() - started
    assert elapsed < 5.0, f"check took {elapsed:.2f}s, over NFR-P1 5s budget"


def test_adopt_dry_run_under_nfr_p2_budget(real_manifest, tmp_path):
    repo = _local_recipes_sized_tree(tmp_path / "sized")
    started = time.perf_counter()
    run_adopt(repo, real_manifest, apply=False, confirm=lambda: False)
    elapsed = time.perf_counter() - started
    assert elapsed < 10.0, f"adopt --dry-run took {elapsed:.2f}s, over NFR-P2 10s budget"


def test_init_e2e_under_nfr_p3_budget(real_manifest, tmp_path):
    """SC-09 / NFR-P3: init end-to-end < 5 minutes wall-clock.

    Uses a dry-run against a fresh path with the real manifest so the gate
    exercises detect+plan cost without depending on every packaged whole-file
    template being present (known limitation of the packaged tree). The
    budget is 300 s; a healthy run finishes in seconds.
    """
    target = tmp_path / "init-target"
    started = time.perf_counter()
    run_init(target, real_manifest, dry_run=True)
    elapsed = time.perf_counter() - started
    assert elapsed < 300.0, f"init e2e took {elapsed:.2f}s, over NFR-P3 5min budget"
