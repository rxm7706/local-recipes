"""Unit tests for pyforge.steward.preflight_ci (Story 71.2, spec-pyforge-steward CAP-159).

Every repository here is a real git repository carrying a copy of the REAL
``.github/workflows/`` files and ``pixi.toml``, with one commit on
``refs/remotes/origin/main`` and a branch commit on top. The selection is read from those
workflow files at run time; the expected sets below name lanes (that is the test's oracle)
but steward holds no such table.

The Story 71.2 spec's literal lane lists were minted against an older lane graph. Two lanes
joined the graph since and have no entry in them, and both have to run wherever CI's own rule
says they do:

* ``pyforge-doctor-aggregate-scripts-test`` -- ``detectors.yml``'s ``scripts-suite`` job runs it
  on every pull request, so it belongs with the always-on lanes;
* ``pages-check`` -- herald Story 27.5 replaced ``pr-preflight``'s always-on ``site-check`` leg with
  ``pages-check``, selected when ``pages.yml``'s ``pull_request`` ``paths`` fire (Story 102.2).
  ``site-check`` stays a pixi task only; no pull_request workflow runs it.

Likewise ``docs/how-to/**`` is one of ``pages.yml``'s trigger paths, so a ``docs/how-to/``
diff also fires the three ``docs-site-validate-*`` lanes. The tests assert the spec's lanes
exactly and these additions explicitly.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
import yaml

from pyforge.steward import preflight, preflight_ci

REPO_ROOT = Path(__file__).resolve().parents[6]
INVOKING_ENV = "pyforge-guild"

_NOOP_INSTALL = lambda _env: 0  # noqa: E731
_SERIAL = {"jobs": 1, "install_environment": _NOOP_INSTALL}


def _run_journal_record(repo: Path) -> dict:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return next(record for record in reversed(records) if "lanes" in record)


STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
LINT = {"ruff", "ruff-format", "mypy", "target-version-check", "precommit-config-check"}
SPEC_ALWAYS_ON = {"detectors-ci", "pyforge-doctor-scripts-test", "docs-map-render-test", "docs-gen-test"}
ALWAYS_ON_SINCE_SPEC = {"pyforge-doctor-aggregate-scripts-test"}
DOCS_SITE_VALIDATE = {"docs-site-validate-links", "docs-site-validate-sidebar-order", "docs-site-validate-sidebar"}
PAGES_CHECK_LEAVES = {"pages-check", "pages-build", "docs-site-install", "docs-site-sidebar"}
GATES = {f"pyforge-{s}-coverage-gate" for s in STATIONS}
NO_CI_COUNTERPART = {"docs-map-render-test", "docs-gen-test"}
ALWAYS_ON = SPEC_ALWAYS_ON | ALWAYS_ON_SINCE_SPEC

STEWARD_PLACEHOLDER = "src/shared/packages/pyforge-steward/placeholder.txt"


# ---------------------------------------------------------------------------
# Fixture repositories
# ---------------------------------------------------------------------------


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


WorkflowEdit = tuple[str, str, str]  # (workflow file, old text, new text)


def make_repo(
    tmp_path: Path,
    branch_files: Mapping[str, str],
    *,
    with_base: bool = True,
    edits: Sequence[WorkflowEdit] = (),
) -> Path:
    """Real workflows + pixi.toml, a base commit (``refs/remotes/origin/main``), a branch commit.

    ``edits`` rewrite the FIXTURE's copy of a workflow (never the real file) before the base
    commit, so the diff under test stays the branch's own."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    shutil.copytree(REPO_ROOT / ".github" / "workflows", repo / ".github" / "workflows")
    for name, old, new in edits:
        path = repo / ".github" / "workflows" / name
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not in {name}"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
    shutil.copy(REPO_ROOT / "pixi.toml", repo / "pixi.toml")
    _write(repo, STEWARD_PLACEHOLDER)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    if with_base:
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    for relative, text in branch_files.items():
        _write(repo, relative, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "branch", "--allow-empty")
    return repo


def lanes_and_pixi(repo: Path) -> tuple[list[preflight.Lane], dict]:
    pixi = tomllib.loads((repo / "pixi.toml").read_text(encoding="utf-8"))
    return preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV), pixi


def select(repo: Path) -> preflight_ci.Selection:
    lanes, pixi = lanes_and_pixi(repo)
    return preflight_ci.select_lanes(repo, lanes, pixi)


def selected_tasks(selection: preflight_ci.Selection) -> set[str]:
    return {v.task for v in selection.verdicts if v.selected}


def selected_lanes(selection: preflight_ci.Selection) -> list[preflight.LaneKey]:
    """The selected lanes, each its ``(task, environment)``: one task may run in two environments
    (atlas Story 31.1's second ``mypy``), so a count of lanes never collapses to task names (Story 103.5)."""
    return [(v.task, v.environment) for v in selection.verdicts if v.selected]


def verdict(selection: preflight_ci.Selection, task: str) -> preflight_ci.LaneVerdict:
    return next(v for v in selection.verdicts if v.task == task)


def suite(station: str) -> str:
    return f"pyforge-{station}-test"


def gate(station: str) -> str:
    return f"pyforge-{station}-coverage-gate"


@pytest.fixture(scope="module")
def all_tasks() -> set[str]:
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    return {lane.task for lane in preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV)}


# ---------------------------------------------------------------------------
# GitHub's filter-pattern rules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("patterns", "path", "expected"),
    [
        (["src/*.py"], "src/a.py", True),
        (["src/*.py"], "src/pkg/a.py", False),  # `*` stops at `/` (fnmatch would match)
        (["src/**"], "src/pkg/deep/a.py", True),  # `**` crosses it
        (["src/**"], "other/a.py", False),
        (["**/*.md"], "docs/dreams/a.md", True),
        (["**.md"], "a/b.md", True),
        (["src/shared/packages/pyforge-*/**"], "src/shared/packages/pyforge-marshal/x/y.py", True),
        (["src/shared/packages/pyforge-*/**"], "src/shared/packages/django-pyforge/x.py", False),
        (
            ["scripts/conda-forge-packaging-inventory-operations_*.py"],
            "scripts/conda-forge-packaging-inventory-operations_a.py",
            True,
        ),
        (["scripts/*"], "scripts/container-gates/x", False),
        (["pixi.toml"], "pixi.toml", True),
        (["pixi.toml"], "sub/pixi.toml", False),
        (["docs/**", "!docs/dreams/**"], "docs/dreams/a.md", False),  # a later `!` excludes
        (["docs/**", "!docs/dreams/**"], "docs/how-to/a.md", True),
        (["a?c"], "ac", True),  # `?` is zero or one of the preceding character
        (["a?c"], "abc", False),
        (["ab+c"], "abbbc", True),
        (["file[0-9].txt"], "file7.txt", True),
        (["file[!0-9].txt"], "file7.txt", False),
    ],
)
def test_filter_matches_follows_github_rules(patterns: list[str], path: str, expected: bool) -> None:
    assert preflight_ci.filter_matches(patterns, path) is expected


# ---------------------------------------------------------------------------
# Reading a lane's CI counterpart out of a run: text
# ---------------------------------------------------------------------------


class _L:
    def __init__(self, task: str, environment: str = INVOKING_ENV) -> None:
        self.task, self.environment = task, environment


PIXI_FIXTURE = tomllib.loads(
    """
[feature.guild-tasks.tasks.parent]
depends-on = ["child"]

[feature.guild-tasks.tasks.child]
cmd = "python scripts/tool.py --scope repo"

[feature.guild-tasks.tasks.gate]
cmd = "python scripts/gate.py --base origin/main --suites unit"

[feature.guild-tasks.tasks.two-step]
cmd = "pytest a/tests -q && pytest b/tests -q"
"""
)


@pytest.mark.parametrize(
    ("task", "lane_env", "text", "expected"),
    [
        ("child", INVOKING_ENV, "pixi run --frozen -e pyforge-guild parent", True),  # depends-on closure
        ("child", INVOKING_ENV, "pixi run --frozen -e pyforge-guild child", True),  # its own task
        ("parent", INVOKING_ENV, "pixi run --frozen -e pyforge-guild child", False),  # not the other direction
        ("child", INVOKING_ENV, "# pixi run parent\necho hi", False),  # a comment is not a step
        ("child", INVOKING_ENV, "${{ steps.py.outputs.cmd }} scripts/tool.py --scope repo 2>&1 | tee out", True),
        ("child", INVOKING_ENV, "python scripts/tool.py --list", False),  # same script, other flags
        ("child", INVOKING_ENV, "python scripts/tool.py --scope other", False),  # same flag, other value
        ("gate", "s", 'pixi run -e s python scripts/gate.py \\\n --base "$BASE" --suites unit', True),  # dynamic value
        (
            "gate",
            "s",
            "pixi run -e other python scripts/gate.py --base x --suites unit",
            False,
        ),  # env must equal the lane's
        ("two-step", INVOKING_ENV, "pytest a/tests -q", False),  # every `&&` segment must be there
        ("two-step", INVOKING_ENV, "pytest a/tests -q\npytest b/tests -q", True),
    ],
)
def test_step_matches_task_closure_or_own_command_line(task: str, lane_env: str, text: str, expected: bool) -> None:
    assert preflight_ci._step_matches(_L(task, lane_env), text, PIXI_FIXTURE) is expected


# ---------------------------------------------------------------------------
# I/O matrix: one station, shared surface, CFE only, Dream only, docsite
# ---------------------------------------------------------------------------


def test_marshal_only_branch_selects_marshal_core_and_always_on_lanes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"src/shared/packages/pyforge-marshal/src/x.py": "x = 1\n"})
    selection = select(repo)
    chosen = selected_tasks(selection)
    assert chosen >= LINT | SPEC_ALWAYS_ON | ALWAYS_ON_SINCE_SPEC | {
        "pyforge-core-test",
        suite("marshal"),
        gate("marshal"),
        suite("atlas"),
        suite("doctor"),
        suite("scribe"),
    }
    assert selection.all_reason is None


def test_marshal_selection_journals_the_workflow_and_rule_that_skipped_each_lane(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"src/shared/packages/pyforge-marshal/src/x.py": "x = 1\n"})
    journal = select(repo).to_journal()
    skipped = {entry["lane"]: entry for entry in journal["skipped"]}
    # Count lanes, each its (task, environment), never task names (Story 103.5).
    journaled = [(e["lane"], e["environment"]) for e in [*journal["selected"], *journal["skipped"]]]
    assert len(set(journaled)) == len(journaled) == len(lanes_and_pixi(repo)[0])
    assert all(entry["workflow"] and entry["rule"] for entry in skipped.values())
    assert skipped[suite("warden")]["workflow"] == "pyforge-station-tests.yml"
    assert "needs.changes.outputs.warden" in skipped[suite("warden")]["rule"]
    assert skipped[gate("warden")]["workflow"] == "coverage-gates.yml"
    assert skipped["test-ci"]["workflow"] == "cfe-regression-net.yml"
    assert "on.pull_request.paths" in skipped["test-ci"]["rule"]
    assert skipped["pyforge-testing-kit-test"]["workflow"] == "pyforge-station-tests.yml"
    assert {e["lane"] for e in journal["selected"]} >= {"docs-map-render-test", "docs-gen-test"}
    assert "no CI counterpart" in next(e for e in journal["selected"] if e["lane"] == "docs-gen-test")["reason"]


def test_pixi_toml_triggers_lint_and_station_lanes_not_pages(tmp_path: Path) -> None:
    """``pixi.toml`` is not a ``pages.yml`` path (Story 102.2); it no longer selects pages-check."""
    repo = make_repo(tmp_path, {"pixi.toml": (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8") + "\n# touched\n"})
    chosen = selected_tasks(select(repo))
    assert ALWAYS_ON <= chosen
    assert LINT <= chosen
    assert not (chosen & PAGES_CHECK_LEAVES)
    assert not (chosen & DOCS_SITE_VALIDATE)
    assert not (chosen & GATES)


def test_cfe_only_branch_selects_the_lanes_station_tests_reads(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {".claude/skills/conda-forge-expert/scripts/x.py": "x = 1\n"})
    chosen = selected_tasks(select(repo))
    assert ALWAYS_ON <= chosen
    assert not chosen & GATES
    assert {
        suite("atlas"),
        suite("doctor"),
        suite("herald"),
        suite("marshal"),
        suite("mason"),
        suite("steward"),
        suite("warden"),
    } <= chosen


def test_dream_only_branch_selects_the_always_on_lanes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"docs/dreams/a-dream.md": "# dream\n"})
    chosen = selected_tasks(select(repo))
    assert SPEC_ALWAYS_ON <= chosen
    # ``docs/dreams/**`` is outside ``pages.yml``'s twelve published-input paths (Story 102.2).
    assert chosen == (
        ALWAYS_ON
        | {suite("doctor"), suite("herald"), suite("marshal"), suite("steward")}
        | _spurious_lint_tasks_from_station_tests_changes(repo)
    )
    assert not (chosen & LINT - _spurious_lint_tasks_from_station_tests_changes(repo))
    assert "test-ci" not in chosen and not chosen & GATES


def test_pages_check_leaves_carry_dependency_edges_from_pixi() -> None:
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    by_task = {lane.task: lane for lane in preflight.list_preflight_lanes(pixi, invoking_env=INVOKING_ENV)}
    for name in PAGES_CHECK_LEAVES:
        assert name in by_task
    assert by_task["pages-check"].depends_on == (("pages-build", "site"),)
    assert set(by_task["pages-build"].depends_on) == {
        ("docs-site-install", "site"),
        ("docs-site-sidebar", "site"),
    }


def test_docsite_branch_selects_the_docsite_validators_and_the_always_on_lanes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"docsite/page.html": "<p>x</p>\n"})
    assert selected_tasks(select(repo)) == (
        ALWAYS_ON
        | DOCS_SITE_VALIDATE
        | PAGES_CHECK_LEAVES
        | {suite("herald")}
        | _spurious_lint_tasks_from_station_tests_changes(repo)
    )


def test_django_pyforge_branch_selects_kit_steward_doctor_marshal_and_core(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"src/shared/packages/django-pyforge/src/x.py": "x = 1\n"})
    selection = select(repo)
    chosen = selected_tasks(selection)
    assert {
        "pyforge-testing-kit-test",
        "pyforge-steward-test",
        "pyforge-doctor-test",
        "pyforge-marshal-test",
        "pyforge-core-test",
    } <= chosen
    assert chosen - NO_CI_COUNTERPART == oracle_selection(repo, tmp_path)


def test_django_herald_branch_selects_steward_and_herald(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"src/shared/packages/django-herald/src/x.py": "x = 1\n"})
    chosen = selected_tasks(select(repo))
    assert {suite("steward"), suite("herald")} <= chosen


def test_lint_types_only_branch_selects_steward(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"scripts/lint_types.py": "# touched\n"})
    chosen = selected_tasks(select(repo))
    assert suite("steward") in chosen


# ---------------------------------------------------------------------------
# Parity oracle: the workflows' own rules, evaluated independently of preflight_ci
# ---------------------------------------------------------------------------


def _oracle_segment(segment: str) -> re.Pattern[str]:
    return re.compile("".join("[^/]*" if char == "*" else re.escape(char) for char in segment))


def _oracle_match(pattern: list[str], segments: list[str]) -> bool:
    if not pattern:
        return not segments
    if pattern[0] == "**":
        if len(pattern) == 1:
            return bool(segments)
        return any(_oracle_match(pattern[1:], segments[i:]) for i in range(len(segments) + 1))
    return (
        bool(segments)
        and bool(_oracle_segment(pattern[0]).fullmatch(segments[0]))
        and _oracle_match(pattern[1:], segments[1:])
    )


def _oracle_fires(repo: Path, workflow: str, changed: list[str]) -> bool:
    data = yaml.safe_load((repo / ".github" / "workflows" / workflow).read_text(encoding="utf-8"))
    paths = data[True]["pull_request"]
    if not paths or "paths" not in paths:
        return True
    return any(_oracle_match(p.split("/"), c.split("/")) for p in paths["paths"] for c in changed)


def _oracle_push_fires(repo: Path, workflow: str, changed: list[str]) -> bool:
    data = yaml.safe_load((repo / ".github" / "workflows" / workflow).read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))
    if not isinstance(triggers, dict):
        return False
    push = triggers.get("push")
    if not isinstance(push, dict) or "paths" not in push:
        return False
    return any(preflight_ci.filter_matches(push["paths"], path) for path in changed)


# Story 98.1: the station-tests `changes` step's shell lists script paths (e.g.
# `scripts/target_version_check.py`) that also appear in lint-types pixi task
# commands. preflight_ci treats that filter script as a lane host, so those
# lint subtasks run whenever station-tests fires even though lint-types.yml does
# not. The oracle below mirrors that seam so parity tests stay honest.
_LINT_TASK_SCRIPT_PATHS: dict[str, str] = {
    "target-version-check": "scripts/target_version_check.py",
    "precommit-config-check": "scripts/precommit_config_check.py",
}


def _station_tests_changes_script(repo: Path) -> str:
    data = yaml.safe_load((repo / ".github" / "workflows" / "pyforge-station-tests.yml").read_text(encoding="utf-8"))
    step = next(s for s in data["jobs"]["changes"]["steps"] if "run" in s)
    return step["run"]


def _spurious_lint_tasks_from_station_tests_changes(repo: Path) -> set[str]:
    script = _station_tests_changes_script(repo)
    return {task for task, path in _LINT_TASK_SCRIPT_PATHS.items() if path in script}


def _oracle_outputs(repo: Path, workflow: str, tmp_path: Path) -> dict[str, str]:
    """Run the workflow's own `changes` shell against the fixture repository."""
    data = yaml.safe_load((repo / ".github" / "workflows" / workflow).read_text(encoding="utf-8"))
    step = next(s for s in data["jobs"]["changes"]["steps"] if "run" in s)
    output = tmp_path / f"oracle-{workflow}.out"
    output.write_text("", encoding="utf-8")
    script = step["run"].replace("${{ github.event_name }}", "pull_request")
    subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=repo,
        env={**os.environ, "GITHUB_BASE_REF": "main", "GITHUB_OUTPUT": str(output)},
        check=True,
        capture_output=True,
    )
    return dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if "=" in line)


def oracle_selection(repo: Path, tmp_path: Path) -> set[str]:
    """The lanes the workflows' own rules run for the committed diff. The job -> lane pairs
    below are the TEST's reading of the workflows; steward holds none of them."""
    changed = [p for p in _git(repo, "diff", "--name-only", "refs/remotes/origin/main...HEAD").splitlines() if p]
    chosen: set[str] = set()
    if _oracle_fires(repo, "lint-types.yml", changed):
        chosen |= LINT
    chosen |= {
        "detectors-ci",
        "pyforge-doctor-scripts-test",
        "pyforge-doctor-aggregate-scripts-test",
    }  # no paths filter
    if _oracle_fires(repo, "cfe-regression-net.yml", changed):
        chosen.add("test-ci")
    if _oracle_fires(repo, "pages.yml", changed):
        chosen |= DOCS_SITE_VALIDATE | PAGES_CHECK_LEAVES
    if _oracle_fires(repo, "pyforge-station-tests.yml", changed):
        out = _oracle_outputs(repo, "pyforge-station-tests.yml", tmp_path)
        for key, lane in [("core", "pyforge-core-test"), ("testing_kit", "pyforge-testing-kit-test")] + [
            (s, suite(s)) for s in STATIONS
        ]:
            if out.get(key) == "true":
                chosen.add(lane)
    if _oracle_fires(repo, "coverage-gates.yml", changed):
        out = _oracle_outputs(repo, "coverage-gates.yml", tmp_path)
        chosen |= {gate(s) for s in json.loads(out["stations"])}
    if _oracle_fires(repo, "pyforge-station-tests.yml", changed):
        chosen |= _spurious_lint_tasks_from_station_tests_changes(repo)
    return chosen


@pytest.mark.parametrize(
    "files",
    [
        {"src/shared/packages/pyforge-marshal/src/x.py": "x\n"},
        {"pixi.toml": (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8") + "\n# touched\n"},
        {".claude/skills/conda-forge-expert/scripts/x.py": "x\n"},
        {"docs/dreams/a-dream.md": "# dream\n"},
        {"docsite/page.html": "<p>x</p>\n"},
        {"src/shared/packages/pyforge-core/src/x.py": "x\n", "src/shared/packages/pyforge-herald/src/y.py": "y\n"},
        {"presentations/deck/a.md": "x\n"},
        {"scripts/tests/test_x.py": "x\n"},
        {"README.md": "x\n"},
        {"src/shared/packages/django-pyforge/src/x.py": "x\n"},
        {"src/shared/packages/django-herald/src/x.py": "x\n"},
        {"scripts/lint_types.py": "# touched\n"},
    ],
    ids=[
        "marshal",
        "pixi",
        "cfe",
        "dream",
        "docsite",
        "core+herald",
        "presentations",
        "atlas-extra",
        "readme-only",
        "django-pyforge",
        "django-herald",
        "lint-types",
    ],
)
def test_selection_equals_the_lanes_the_workflows_own_rules_select(tmp_path: Path, files: dict[str, str]) -> None:
    repo = make_repo(tmp_path, files)
    selection = select(repo)
    assert selection.all_reason is None
    assert selected_tasks(selection) - NO_CI_COUNTERPART == oracle_selection(repo, tmp_path)
    assert NO_CI_COUNTERPART <= selected_tasks(selection)


# ---------------------------------------------------------------------------
# Anything the reader cannot evaluate runs the lane, and the journal says why
# ---------------------------------------------------------------------------


def test_no_base_ref_selects_every_lane_and_journals_why(tmp_path: Path, all_tasks: set[str]) -> None:
    repo = make_repo(tmp_path, {"docs/dreams/a-dream.md": "# dream\n"}, with_base=False)
    selection = select(repo)
    assert selected_tasks(selection) == all_tasks
    journal = selection.to_journal()
    assert journal["mode"] == "all"
    assert "refs/remotes/origin/main" in journal["all_reason"]
    assert journal["skipped"] == []


def test_a_short_origin_main_is_not_the_base(tmp_path: Path, all_tasks: set[str]) -> None:
    """Only the full ref counts: a local branch named `origin/main` must not stand in for it."""
    repo = make_repo(tmp_path, {"docs/dreams/a-dream.md": "# dream\n"}, with_base=False)
    _git(repo, "branch", "origin/main", "main")
    assert selected_tasks(select(repo)) == all_tasks


def test_unrecognised_paths_ignore_runs_that_workflows_lane_and_names_the_rule(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"docs/dreams/a-dream.md": "# dream\n"},
        edits=[("cfe-regression-net.yml", "  pull_request:\n    paths:\n", "  pull_request:\n    paths-ignore:\n")],
    )
    selection = select(repo)
    assert "test-ci" in selected_tasks(selection)
    assert "paths-ignore" in verdict(selection, "test-ci").reason
    assert "cfe-regression-net.yml" in verdict(selection, "test-ci").reason


def test_unrecognised_job_if_runs_that_job_s_lane_and_names_the_rule(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"src/shared/packages/pyforge-marshal/src/x.py": "x\n"},
        edits=[
            (
                "pyforge-station-tests.yml",
                "&& (needs.changes.outputs.marshal == 'true')) }}",
                "&& (needs.changes.outputs.marshal == 'true' && github.actor != 'nobody')) }}",
            )
        ],
    )
    selection = select(repo)
    chosen = selected_tasks(selection)
    assert suite("marshal") in chosen
    assert suite("warden") not in chosen  # warden did not change; its own `if:` is still read
    assert "github.actor" in verdict(selection, suite("marshal")).reason


def test_unexpandable_matrix_selects_every_gate_and_names_the_rule(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"src/shared/packages/pyforge-warden/src/x.py": "x\n"},
        edits=[
            (
                "coverage-gates.yml",
                "${{ fromJSON(needs.changes.outputs.stations) }}",
                "${{ fromJSON(github.event.inputs.stations) }}",
            )
        ],
    )
    selection = select(repo)
    assert GATES <= selected_tasks(selection)
    assert "strategy.matrix.station" in verdict(selection, gate("marshal")).reason


def test_a_failing_changes_step_runs_its_workflow_s_lanes(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"src/shared/packages/pyforge-warden/src/x.py": "x\n"},
        edits=[("pyforge-station-tests.yml", "set -euo pipefail", "exit 3")],
    )
    selection = select(repo)
    station_lanes = {"pyforge-core-test", "pyforge-testing-kit-test"} | {suite(s) for s in STATIONS}
    assert station_lanes <= selected_tasks(selection)
    assert "exited 3" in verdict(selection, suite("atlas")).reason
    # Another workflow's lanes are still decided by their own rules.
    assert "test-ci" not in selected_tasks(selection)
    assert gate("marshal") not in selected_tasks(selection) and gate("warden") in selected_tasks(selection)


def test_unreadable_changes_output_runs_its_workflow_s_lanes(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"src/shared/packages/pyforge-warden/src/x.py": "x\n"},
        edits=[
            (
                "pyforge-station-tests.yml",
                'echo "core=$CORE_CHANGED" >> "$GITHUB_OUTPUT"',
                'echo "not an output line" >> "$GITHUB_OUTPUT"',
            )
        ],
    )
    selection = select(repo)
    assert suite("atlas") in selected_tasks(selection)
    assert "unreadable GITHUB_OUTPUT" in verdict(selection, suite("atlas")).reason


def test_a_job_output_that_is_not_a_run_step_output_is_unevaluable(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path,
        {"src/shared/packages/pyforge-warden/src/x.py": "x\n"},
        edits=[
            (
                "coverage-gates.yml",
                "stations: ${{ steps.filter.outputs.stations }}",
                "stations: ${{ steps.nope.outputs.stations }}",
            )
        ],
    )
    selection = select(repo)
    assert GATES <= selected_tasks(selection)
    assert "not a run step's output" in verdict(selection, gate("atlas")).reason


# ---------------------------------------------------------------------------
# A dirty tree can only add lanes
# ---------------------------------------------------------------------------

MARSHAL_ONLY = {"src/shared/packages/pyforge-marshal/src/x.py": "x = 1\n"}
STEWARD_LANES = {suite("steward"), gate("steward")}


def _dirty_untracked(repo: Path) -> None:
    _write(repo, "src/shared/packages/pyforge-steward/src/new.py")


def _dirty_staged(repo: Path) -> None:
    _write(repo, "src/shared/packages/pyforge-steward/src/new.py")
    _git(repo, "add", "src/shared/packages/pyforge-steward/src/new.py")


def _dirty_unstaged(repo: Path) -> None:
    _write(repo, STEWARD_PLACEHOLDER, "changed\n")


@pytest.mark.parametrize(
    "dirty", [_dirty_untracked, _dirty_staged, _dirty_unstaged], ids=["untracked", "staged", "unstaged"]
)
def test_dirty_steward_file_adds_the_steward_lanes(tmp_path: Path, dirty: Callable[[Path], None]) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY)
    clean = selected_tasks(select(repo))
    assert not clean & STEWARD_LANES
    dirty(repo)
    selection = select(repo)
    chosen = selected_tasks(selection)
    assert clean <= chosen
    assert STEWARD_LANES <= chosen
    if dirty is not _dirty_unstaged:
        assert suite("herald") in chosen
    assert selection.dirty_paths and "src/shared/packages/pyforge-steward" in selection.dirty_paths[0]


def test_dirty_tree_leaves_the_real_repository_untouched(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY)
    _dirty_untracked(repo)
    before = (_git(repo, "status", "--porcelain"), _git(repo, "rev-parse", "HEAD"), _git(repo, "for-each-ref"))
    select(repo)
    after = (_git(repo, "status", "--porcelain"), _git(repo, "rev-parse", "HEAD"), _git(repo, "for-each-ref"))
    assert before == after


def test_a_dirty_revert_never_removes_a_committed_lane(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY)
    committed = selected_tasks(select(repo))
    (repo / "src/shared/packages/pyforge-marshal/src/x.py").unlink()  # the working tree undoes the branch's change
    assert committed <= selected_tasks(select(repo))


def test_gitignored_files_do_not_count_as_dirty(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY)
    _write(repo, ".gitignore", ".steward/\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "ignore")
    clean = selected_tasks(select(repo))
    _write(repo, ".steward/preflight-runs.jsonl", "{}\n")
    assert selected_tasks(select(repo)) == clean


# ---------------------------------------------------------------------------
# run_preflight runs only the selected lanes and journals the selection
# ---------------------------------------------------------------------------


def test_run_preflight_runs_selected_lanes_in_order_and_journals_the_selection(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY)
    lanes, _ = lanes_and_pixi(repo)
    ran: list[preflight.LaneKey] = []

    def fake_run(lane: preflight.Lane) -> int:
        ran.append((lane.task, lane.environment))
        return 0

    code = preflight.run_preflight(repo, invoking_env=INVOKING_ENV, run_lane=fake_run, **_SERIAL)
    assert code == preflight.EXIT_OK
    expected = selected_lanes(select(repo))
    assert len(set(expected)) == len(expected)  # each lane once, a task in two environments twice
    assert set(ran) == set(expected)
    # declaration order kept
    assert ran == [(lane.task, lane.environment) for lane in lanes if (lane.task, lane.environment) in expected]

    record = _run_journal_record(repo)
    assert [(entry["task"], entry["environment"]) for entry in record["lanes"]] == ran
    selection = record["selection"]
    assert selection["mode"] == "diff"
    assert [(e["lane"], e["environment"]) for e in selection["selected"]] == expected
    assert len(selection["skipped"]) == len(lanes) - len(expected)
    assert all(e["workflow"] and e["rule"] for e in selection["skipped"])


def test_run_preflight_with_no_base_ref_runs_every_lane(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, MARSHAL_ONLY, with_base=False)
    lanes, _ = lanes_and_pixi(repo)
    ran: list[str] = []
    code = preflight.run_preflight(
        repo, invoking_env=INVOKING_ENV, run_lane=lambda lane: ran.append(lane.task) or 0, **_SERIAL
    )
    assert code == preflight.EXIT_OK
    assert ran == [lane.task for lane in lanes]
    record = _run_journal_record(repo)
    assert record["selection"]["mode"] == "all"
    assert "refs/remotes/origin/main" in record["selection"]["all_reason"]


def test_static_service_mutex_keys_reads_workflow_services(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(
        repo,
        ".github/workflows/w.yml",
        "on:\n  pull_request:\n    paths: ['**']\n"
        "jobs:\n  j:\n    services:\n      postgres:\n        image: pgvector/pgvector:pg17\n"
        "    steps:\n      - run: pixi run --frozen -e pyforge-guild lane-a\n",
    )
    _write(
        repo,
        "pixi.toml",
        '[feature.guild-tasks.tasks.lane-a]\ncmd = "true"\n',
    )
    lane = preflight.Lane(task="lane-a", environment="pyforge-guild")
    pixi = tomllib.loads((repo / "pixi.toml").read_text(encoding="utf-8"))
    keys = preflight_ci.static_service_mutex_keys(repo, [lane], pixi)
    assert keys[("lane-a", "pyforge-guild")] == "services:postgres"


def test_service_mutex_keys_follows_ci_firing_site(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(
        repo,
        ".github/workflows/w.yml",
        "on:\n  pull_request:\n    paths: ['**']\n"
        "jobs:\n  j:\n    services:\n      redis:\n        image: redis:7\n"
        "    steps:\n      - run: pixi run --frozen -e pyforge-guild lane-b\n",
    )
    _write(
        repo,
        "pixi.toml",
        '[feature.guild-tasks.tasks.lane-b]\ncmd = "true"\n',
    )
    _write(repo, "touch.txt", "x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, "touch.txt", "y\n")
    _git(repo, "add", "touch.txt")
    _git(repo, "commit", "-q", "-m", "branch")

    lane = preflight.Lane(task="lane-b", environment="pyforge-guild")
    pixi = tomllib.loads((repo / "pixi.toml").read_text(encoding="utf-8"))
    assert preflight_ci.lane_service_mutex_key(repo, lane, pixi) == "services:redis"
    keys = preflight_ci.service_mutex_keys(repo, [lane], pixi)
    assert keys[("lane-b", "pyforge-guild")] == "services:redis"


def test_pages_yml_push_fires_pages_check_for_tutorials(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"docs/tutorials/a.md": "# a\n"})
    lanes, pixi = lanes_and_pixi(repo)
    lane = next(item for item in lanes if item.task == "pages-check")
    assert "pages-check" in selected_tasks(select(repo))
    assert "pages.yml" in preflight_ci.firing_workflows_for_lane(repo, lane, pixi)


def test_pages_yml_push_does_not_fire_for_dream_only(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {"docs/dreams/a-dream.md": "# dream\n"})
    lanes, pixi = lanes_and_pixi(repo)
    lane = next(item for item in lanes if item.task == "pages-check")
    assert "pages.yml" not in preflight_ci.firing_workflows_for_lane(repo, lane, pixi)


def test_a_repository_without_workflows_still_selects_every_lane(tmp_path: Path) -> None:
    """Not a git repository at all: nothing can be read, so nothing is skipped."""
    pixi_path = tmp_path / "pixi.toml"
    pixi_path.write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = ['a', 'b']\n"
        "[feature.guild-tasks.tasks.a]\ncmd = 'true'\n[feature.guild-tasks.tasks.b]\ncmd = 'true'\n",
        encoding="utf-8",
    )
    ran: list[str] = []
    assert (
        preflight.run_preflight(
            tmp_path, pixi_path=pixi_path, run_lane=lambda lane: ran.append(lane.task) or 0, **_SERIAL
        )
        == 0
    )
    assert ran == ["a", "b"]


# --- the pause-only gate shape (steward 102.3's re-review) ----------------------------------------


class _GateState:
    """The two readers ``_eval_ci_if_expression`` reaches: the CI variables and a ``needs`` output."""

    def __init__(self, ci_vars: Mapping[str, str], outputs: Mapping[str, str]) -> None:
        self._vars = ci_vars
        self._outputs = outputs

    def ci_var_lookup(self, name: str) -> str:
        return self._vars.get(name, "")

    def _needs_output(self, workflow, job, dep: str, name: str) -> str:
        return self._outputs[f"{dep}.{name}"]


def _pages_deploy_if() -> str:
    """The live ``pages.deploy`` gate, as the renderer writes it (``dispatch: pause-only``)."""
    workflow = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
    return preflight_ci._normalize_condition(workflow["jobs"]["deploy"]["if"])


def _gate(text: str, *, event: str = "pull_request", ci_vars: Mapping[str, str] | None = None, changed: str = "true"):
    return preflight_ci._eval_ci_if_expression(
        text,
        registry={},
        context={"github.event_name": event},
        state=_GateState(ci_vars or {}, {"build.changed": changed}),
        workflow=preflight_ci.Workflow(file="pages.yml", data={}),
        job_id="deploy",
        job={"needs": "build"},
    )


def test_the_pause_only_gate_is_read_not_unevaluable() -> None:
    """The lane evaluator reads ``(dispatch || (pauses)) && (inner)``: a ``||`` nested under ``&&``
    recurses and ``github.ref`` is an atom. A pull request is never on ``refs/heads/main``, so the
    deploy gate is false under the simulated event, paused or not."""
    text = _pages_deploy_if()
    assert "github.ref == 'refs/heads/main'" in text and text.startswith("(github.event_name == 'workflow_dispatch'")
    assert _gate(text) is False
    assert _gate(text, ci_vars={"PAUSE_PAGES": "true"}) is False


@pytest.mark.parametrize(
    ("text", "ci_vars", "expected"),
    [
        ("(github.event_name == 'pull_request' || (vars.P != 'true')) && (github.ref != 'refs/heads/main')", {}, True),
        ("(github.event_name == 'push' || (vars.P != 'true')) && (needs.build.outputs.changed == 'true')", {}, True),
        (
            "(github.event_name == 'push' || (vars.P != 'true')) && (needs.build.outputs.changed == 'true')",
            {"P": "true"},
            False,
        ),
        (
            "github.event_name == 'push' || (vars.P != 'true' && (github.ref == 'refs/heads/main' || vars.Q == 'x'))",
            {"Q": "x"},
            True,
        ),
        (
            "github.event_name == 'push' || (vars.P != 'true' && (github.ref == 'refs/heads/main' || vars.Q == 'x'))",
            {},
            False,
        ),
    ],
    ids=["ref-ne", "needs-under-or-group", "paused", "deeper-nesting-true", "deeper-nesting-false"],
)
def test_nested_groups_evaluate_as_github_does(text: str, ci_vars: dict, expected: bool) -> None:
    assert _gate(text, ci_vars=ci_vars) is expected


@pytest.mark.parametrize(
    ("text", "event"),
    [
        ("github.ref == 'refs/pull/12/merge'", "pull_request"),  # a pull request's ref carries its number
        ("vars.P != 'true' && github.ref == 'refs/heads/main'", "push"),  # only the simulated event is known
        ("vars.P != 'true' && github.ref_name == 'main'", "pull_request"),  # outside the grammar still says so
    ],
    ids=["pr-ref-literal", "not-a-pull-request", "unknown-atom"],
)
def test_a_ref_the_simulation_cannot_know_stays_unevaluable(text: str, event: str) -> None:
    with pytest.raises(preflight_ci._Unevaluable):
        _gate(text, event=event)


def test_a_ref_atom_on_a_push_only_site_is_unevaluable() -> None:
    """102.3's lane-B re-review: a push-only workflow is judged through ``on.push``, where the ref after the
    merge is the branch's own, so ``github.ref == 'refs/heads/main'`` must not read False there (its lane
    would never be selected): it is unevaluable, and the lane runs and says why."""
    text = "vars.P != 'true' && github.ref == 'refs/heads/main'"
    with pytest.raises(preflight_ci._Unevaluable, match="needs the run's own ref"):
        preflight_ci._eval_ci_if_expression(
            text,
            registry={},
            context={"github.event_name": "pull_request", preflight_ci._TRIGGER_KEY: "push"},
            state=_GateState({}, {}),
            workflow=preflight_ci.Workflow(file="push-only.yml", data={}),
            job_id="publish",
            job={},
        )

    class _Holder:
        ci_registry: dict = {}

        def _context(self) -> dict[str, str]:
            return {"github.event_name": "pull_request"}

        def ci_var_lookup(self, name: str) -> str:
            return ""

    job = {"if": "${{ " + text + " }}", "steps": [{"run": "true"}]}
    push_only = preflight_ci.Workflow(
        file="push-only.yml", data={"on": {"push": {"branches": ["main"]}}, "jobs": {"publish": job}}
    )
    with pytest.raises(preflight_ci._Unevaluable):
        preflight_ci._State._job_holds(_Holder(), push_only, "publish", job)  # type: ignore[arg-type]
    pull_request = preflight_ci.Workflow(file="pr.yml", data={"on": {"pull_request": {}}, "jobs": {"publish": job}})
    holds, _ = preflight_ci._State._job_holds(_Holder(), pull_request, "publish", job)  # type: ignore[arg-type]
    assert holds is False  # a pull request's ref is never refs/heads/main
