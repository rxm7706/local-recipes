"""Story 27.5 / 102.2: pr-preflight runs pages-check when pages.yml pull_request paths change."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
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


def test_pages_check_lane_bound_to_pages_workflow() -> None:
    root = _repo_root()
    workflow = yaml.safe_load((root / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["build"]["steps"]
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
def test_pages_paths_under_github_glob_semantics(path: str, expected: bool) -> None:
    root = _repo_root()
    workflow = yaml.safe_load((root / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
    patterns = workflow[True]["pull_request"]["paths"]
    assert preflight_ci.filter_matches(patterns, path) is expected


def test_marshal_only_diff_leaves_pages_check_unselected(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"src/shared/packages/pyforge-marshal/src/x.py": "x = 1\n"})
    selection = _select(repo)
    assert "pages-check" not in _selected_tasks(selection)
    skipped = {v.task: v for v in selection.verdicts if not v.selected}
    assert skipped["pages-check"].workflow == "pages.yml"


def test_docs_how_to_diff_selects_pages_check(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"docs/how-to/x.md": "# how-to\n"})
    selection = _select(repo)
    assert "pages-check" in _selected_tasks(selection)
    assert "site-check" not in _selected_tasks(selection)


def test_a_herald_only_diff_runs_the_install_before_herald_s_suite(tmp_path: Path) -> None:
    """Story 45.1: a diff touching only herald's tests fires herald's job and not pages.yml, and the preflight still
    runs docs-site-install before herald's suite. The job's step runs pyforge-herald-test-built (the install, then the
    suite), so the reader selects both lanes; pyforge-herald-test itself has no edge to the install (it stays npm-free
    for the SBOM laptop gate), so pr-preflight-lanes declares the install before the station suites, where it takes the
    docs-site lanes' first turn, and a touched run keeps it beside herald's lane."""
    repo = _make_repo(tmp_path, {"src/shared/packages/pyforge-herald/tests/unit/probe.py": "# probe\n"})
    pixi = tomllib.loads((repo / "pixi.toml").read_text(encoding="utf-8"))
    lanes = preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV)
    selection = preflight_ci.select_lanes(repo, lanes, pixi)
    chosen = [lane for lane in lanes if selection.is_selected(lane)]
    keys = [(lane.task, lane.environment) for lane in chosen]
    assert {("pyforge-herald-test", "pyforge-herald"), ("docs-site-install", "site")} <= set(keys)
    assert ("pages-check", "site") not in keys  # the Pages workflow did not fire: the install comes from herald's job
    herald = next(lane for lane in lanes if lane.task == "pyforge-herald-test")
    assert herald.depends_on == ()
    assert keys.index(("docs-site-install", "site")) < keys.index(("pyforge-herald-test", "pyforge-herald"))
    docs_lanes = [lane.task for lane in lanes if lane.task in preflight.DOCS_SITE_TASKS]
    assert docs_lanes[0] == "docs-site-install"  # the first docs-site turn (steward Story 105.1's _next_lane)
    cut = preflight.touched_cut(repo, chosen, pixi, selection)
    assert dict(cut.reasons)[("docs-site-install", "site")] == "pyforge-herald-test@pyforge-herald reads its install"


def test_the_install_runs_before_herald_s_suite_in_one_slot_and_many(tmp_path: Path) -> None:
    """Story 45.1, end to end through ``run_preflight`` with an injected runner: on the shipped lane list, a herald-only
    selection runs docs-site-install to its end before herald's suite starts, at ``--jobs 1`` and ``--jobs 8``, in the
    full and the touched scope."""
    repo = _make_repo(tmp_path, {"src/shared/packages/pyforge-herald/tests/unit/probe.py": "# probe\n"})
    for scope in (preflight.SCOPE_FULL, preflight.SCOPE_TOUCHED):
        for jobs in (1, 8):
            rows: dict[str, tuple[float, float]] = {}
            lock = threading.Lock()

            def run_ctx(ctx: preflight.LaneRunContext, rows=rows, lock=lock) -> int:
                start = time.monotonic()
                time.sleep(0.05 if ctx.lane.task in preflight.DOCS_SITE_TASKS else 0.0)
                with lock:
                    rows[ctx.lane.task] = (start, time.monotonic())
                return 0

            code = preflight.run_preflight(
                repo,
                invoking_env=INVOKING_ENV,
                jobs=jobs,
                install_environment=lambda _env: 0,
                run_lane_ctx=run_ctx,
                scope=scope,
                scratch_parent=tmp_path,
            )
            assert code == preflight.EXIT_OK, (scope, jobs)
            assert rows["docs-site-install"][1] <= rows["pyforge-herald-test"][0], (scope, jobs, rows)
