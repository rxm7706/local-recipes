"""Story 27.5: pr-preflight runs pages-check only when docsite-check.yml paths change."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[6]
_STEWARD_SRC = _REPO_ROOT / "src/shared/packages/pyforge-steward/src"
if str(_STEWARD_SRC) not in sys.path:
    sys.path.insert(0, str(_STEWARD_SRC))

from pyforge.steward import preflight, preflight_ci  # noqa: E402

INVOKING_ENV = "pyforge-guild"
_STEWARD_PLACEHOLDER = "src/shared/packages/pyforge-steward/placeholder.txt"


def _repo_root() -> Path:
    if (_REPO_ROOT / "pixi.toml").is_file():
        return _REPO_ROOT
    raise AssertionError("could not locate repo root")


def _git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for leaked in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(leaked, None)
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _write(repo: Path, relative: str, text: str = "x\n") -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(tmp_path: Path, branch_files: dict[str, str]) -> Path:
    root = _repo_root()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    shutil.copytree(root / ".github" / "workflows", repo / ".github" / "workflows")
    shutil.copy(root / "pixi.toml", repo / "pixi.toml")
    _write(repo, _STEWARD_PLACEHOLDER)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    for relative, text in branch_files.items():
        _write(repo, relative, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "branch", "--allow-empty")
    return repo


def _select(repo: Path) -> preflight_ci.Selection:
    pixi = tomllib.loads((repo / "pixi.toml").read_text(encoding="utf-8"))
    lanes = preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV)
    return preflight_ci.select_lanes(repo, lanes, pixi)


def _selected_tasks(selection: preflight_ci.Selection) -> set[str]:
    return {v.task for v in selection.verdicts if v.selected}


def test_pr_preflight_carries_pages_check_not_site_check() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    preflight_lanes = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]
    legs = preflight_lanes["depends-on"]
    pages_legs = [leg for leg in legs if isinstance(leg, dict) and leg.get("task") == "pages-check"]
    site_legs = [leg for leg in legs if isinstance(leg, dict) and leg.get("task") == "site-check"]
    assert pages_legs == [{"task": "pages-check", "environment": "site"}]
    assert site_legs == []


def test_pages_check_lane_bound_to_docsite_check_workflow() -> None:
    root = _repo_root()
    workflow = yaml.safe_load((root / ".github/workflows/docsite-check.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["check"]["steps"]
    run_lines = [s["run"] for s in steps if isinstance(s, dict) and "run" in s]
    assert any("pages-check" in line for line in run_lines)
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    lanes = preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV)
    pages_lane = next(lane for lane in lanes if lane.task == "pages-check")
    assert any(preflight_ci._step_matches(pages_lane, line, pixi) for line in run_lines)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/shared/packages/pyforge-marshal/src/x.py", False),
        ("docs/how-to/x.md", True),
    ],
)
def test_docsite_check_paths_under_github_glob_semantics(path: str, expected: bool) -> None:
    root = _repo_root()
    workflow = yaml.safe_load((root / ".github/workflows/docsite-check.yml").read_text(encoding="utf-8"))
    patterns = workflow[True]["pull_request"]["paths"]
    assert preflight_ci.filter_matches(patterns, path) is expected


def test_marshal_only_diff_leaves_pages_check_unselected(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"src/shared/packages/pyforge-marshal/src/x.py": "x = 1\n"})
    selection = _select(repo)
    assert "pages-check" not in _selected_tasks(selection)
    skipped = {v.task: v for v in selection.verdicts if not v.selected}
    assert skipped["pages-check"].workflow == "docsite-check.yml"


def test_docs_how_to_diff_selects_pages_check(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"docs/how-to/x.md": "# how-to\n"})
    selection = _select(repo)
    assert "pages-check" in _selected_tasks(selection)
    assert "site-check" not in _selected_tasks(selection)
