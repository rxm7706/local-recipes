"""Meta test -- the testing kit's own suite stays wired into CI (Story 19.5,
spec-pyforge-testing-charter CAP-3).

Before Story 19.5 no workflow ran ``pyforge-testing-kit-test``: the kit was only
a shared-surface trigger for the station jobs and ``core-test``, and the local
``pyforge-station-tests`` aggregate skipped it. ``test_flags.py`` went red unseen
when steward Story 76.2 gave the platform flag tree flagd ``metadata``. This test
pins the wiring the way pyforge-core's ``test_conformance_lane_wired.py`` pins
``core-test``, on raw text: the job, its gate, the paths that fire it, and the
local leg. Each detector is proven non-vacuous against a mutated copy of the
real input.

Story 118.1 (spec-pyforge-testing-charter:CAP-7 and the CAP-3 lane clause) gave
the suite two halves: the modules marked ``live_tree`` read the repository
outside the kit, the rest is the package half, which runs with no host package
on the path. This test accepts two wirings and reds one that drops a half:
today's one ``testing-kit-test`` job running ``pyforge-testing-kit-test``, or
the split steward:S-124.1 and steward:S-124.2 land -- ``testing-kit-test``
running a package-half task and ``testing-kit-live-test`` running
``pyforge-testing-kit-live-test``, with ``pyforge-testing-kit-test`` kept as the
``depends-on`` aggregate of both halves, so it stays the whole suite. Which half
a task runs is read from its ``-m`` marker expression. The
``test_detector_fires_when_a_half_is_dropped_*`` tests prove it on a split copy
of today's input. This module reads ``pixi.toml`` and the workflow, so it is
itself ``live_tree``.
"""

from __future__ import annotations

import copy
import re
import shlex
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

# tests/meta -> tests -> pyforge-testing-kit -> packages -> shared -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
PIXI_TOML = _REPO_ROOT / "pixi.toml"

JOB = "testing-kit-test"
TASK = "pyforge-testing-kit-test"
ENV = "pyforge-testing-kit"
GATE = "needs.changes.outputs.testing_kit"
RUN = f"pixi run --frozen -e {ENV} {TASK}"
TESTS = "src/shared/packages/pyforge-testing-kit/tests"
# Story 118.1: the split wiring (steward:S-124.1 / S-124.2) adds a live-tree job and task beside the package half.
LIVE_JOB = "testing-kit-live-test"
LIVE_TASK = "pyforge-testing-kit-live-test"
LIVE_RUN = f"pixi run --frozen -e {ENV} {LIVE_TASK}"
# The live-tree job may be gated on the kit's output or on a `testing_kit_live` output of its own.
LIVE_GATES = (GATE, f"{GATE}_live")
PACKAGE_HALF = "package"
LIVE_HALF = "live-tree"
BOTH_HALVES = frozenset({PACKAGE_HALF, LIVE_HALF})
# Every input that can change the suite's verdict: the shared surface (pixi.toml, pixi.lock,
# this workflow), the kit, pyforge-core and django-pyforge (both on the whole-suite task's
# PYTHONPATH), and the platform flag tree (test_flag_fixture_matches_the_platform_tree.py).
INPUTS = (
    "pixi.toml",
    "pixi.lock",
    ".github/workflows/pyforge-station-tests.yml",
    "src/shared/packages/pyforge-testing-kit/**",
    "src/shared/packages/pyforge-core/**",
    "src/shared/packages/django-pyforge/**",
    "src/platform/config/flags.json",
)
# The two inputs outside the shared surface that flip the kit's gate on their own.
EXTRA_GATE_PATHS = ("src/shared/packages/django-pyforge", "src/platform/config/flags.json")

_HEADER = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]*$", re.MULTILINE)
_PATH_ENTRY = re.compile(r"^\s+-\s+'([^']+)'\s*$", re.MULTILINE)
_RUN_LINE = re.compile(r"^\s+-\s+run:\s*(.+?)\s*$", re.MULTILINE)
_OUTPUT = re.compile(r"^\s+testing_kit:\s*\$\{\{\s*steps\.filter\.outputs\.testing_kit\s*\}\}\s*$", re.MULTILINE)
_SEED = re.compile(r'^\s*TESTING_KIT_CHANGED="\$SHARED_CHANGED"\s*$', re.MULTILINE)
_ECHO = re.compile(r'^\s*echo "testing_kit=\$TESTING_KIT_CHANGED" >> "\$GITHUB_OUTPUT"\s*$', re.MULTILINE)
_SET = re.compile(r"^\s*TESTING_KIT_CHANGED=true\s*$", re.MULTILINE)
_NEEDS = re.compile(r"^\s+needs:\s*(.+?)\s*$", re.MULTILINE)
_ENUMERATED = re.compile(r"tests/(?:meta|unit|integration|conformance)\b")
_KIT_RUN = re.compile(rf"^pixi run --frozen -e {re.escape(ENV)} ([\w-]+)$")


def _blocks(text: str) -> dict[str, str]:
    heads = list(_HEADER.finditer(text))
    return {
        m.group(1): text[m.end() : heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        for i, m in enumerate(heads)
    }


def _jobs(text: str) -> dict[str, str]:
    return _blocks(text[text.index("\njobs:\n") :])


def _trigger_paths(text: str, event: str) -> set[str]:
    on = text[text.index("\non:\n") : text.index("\njobs:\n")]
    return set(_PATH_ENTRY.findall(_blocks(on).get(event, "")))


def _is_gated(block: str, gates: tuple[str, ...]) -> bool:
    # The gate may sit inside a larger expression: steward Story 99.2 wraps every job's
    # `if:` in its CI pause switches (`vars.PAUSE_*`) and a workflow_dispatch override.
    return any(re.search(rf"^\s+if:.*\b{re.escape(gate)} == 'true'", block, re.MULTILINE) for gate in gates)


# --- which half of the suite a pixi task runs ---------------------------------


def _kit_tasks(pixi_data: dict) -> dict:
    return pixi_data["feature"][ENV]["tasks"]


def _marker_expression(cmd: str) -> str | None:
    """The ``-m`` expression of the pytest command in ``cmd`` (None when it selects no marker)."""
    tokens = shlex.split(cmd)
    for i, token in enumerate(tokens):
        if token == "-m" and i + 1 < len(tokens):
            return tokens[i + 1]
        if token.startswith("-m") and len(token) > 2 and not token.startswith("--"):
            return token[2:]
    return None


def task_halves(pixi_data: dict, name: str, _seen: frozenset[str] = frozenset()) -> frozenset[str]:
    """The halves of the kit's suite the kit-env task ``name`` runs: its own ``cmd`` read by its ``-m``
    expression (none, or one that does not name ``live_tree``, is the whole suite), plus every task it
    ``depends-on`` in the kit's environment."""
    task = _kit_tasks(pixi_data).get(name)
    if task is None or name in _seen:
        return frozenset()
    cmd, deps = (task, []) if isinstance(task, str) else (task.get("cmd", ""), task.get("depends-on", []))
    halves: set[str] = set()
    for segment in re.split(r"&&|;", cmd):
        if "pytest" not in segment or TESTS not in shlex.split(segment):
            continue
        expression = _marker_expression(segment) or ""
        if "live_tree" not in expression:
            halves |= BOTH_HALVES
        elif re.search(r"\bnot\s+live_tree\b", expression):
            halves.add(PACKAGE_HALF)
        else:
            halves.add(LIVE_HALF)
    for dep in deps:
        dep_name = dep if isinstance(dep, str) else dep.get("task", "")
        if isinstance(dep, dict) and dep.get("environment", ENV) != ENV:
            continue
        halves |= task_halves(pixi_data, dep_name, _seen | {name})
    return frozenset(halves)


def _kit_runs(block: str) -> list[str]:
    """The kit-env pixi tasks a job's run steps invoke."""
    return [m.group(1) for r in _RUN_LINE.findall(block) if (m := _KIT_RUN.match(r)) is not None]


# --- the detectors (pure: text in, problems out) -----------------------------


def job_problems(workflow_text: str) -> list[str]:
    """The kit's job (and, split, its live-tree job) exists, needs ``changes``, is gated on
    ``testing_kit`` and runs one pixi task; neither is a gate on another job."""
    jobs = _jobs(workflow_text)
    block = jobs.get(JOB)
    if block is None:
        return [f"no `{JOB}` job under jobs:"]
    split = LIVE_JOB in jobs
    wired = ((JOB, (GATE,)), (LIVE_JOB, LIVE_GATES)) if split else ((JOB, (GATE,)),)
    problems: list[str] = []
    for name, gates in wired:
        block = jobs[name]
        if not re.search(r"^\s+needs:\s*changes\s*$", block, re.MULTILINE):
            problems.append(f"`{name}` does not need `changes`")
        if not _is_gated(block, gates):
            problems.append(f"`{name}` is not gated on `{'` or `'.join(gates)}`")
        runs = _RUN_LINE.findall(block)
        if not split and RUN not in runs:
            problems.append(f"`{JOB}` does not run exactly `{RUN}`")
        if name == LIVE_JOB and LIVE_RUN not in runs:
            problems.append(f"`{LIVE_JOB}` does not run exactly `{LIVE_RUN}`")
        if split and name == JOB and len(_kit_runs(block)) != 1:
            problems.append(f"`{JOB}` does not run exactly one `pixi run --frozen -e {ENV} <task>`")
        if any("pytest" in r or _ENUMERATED.search(r) for r in runs):
            problems.append(f"`{name}` invokes pytest or a tests/ sub-path directly instead of the pixi task")
        needed = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
        for other_name, other in jobs.items():
            if other_name != name and any(needed.search(n) for n in _NEEDS.findall(other)):
                problems.append(f"`{other_name}` needs `{name}` -- it is a peer of the other jobs, not a gate on them")
    return problems


def halves_problems(workflow_text: str, pixi_data: dict) -> list[str]:
    """CI runs both halves of the suite: one job running the whole suite, or a package-half job and a
    live-tree job (Story 118.1)."""
    jobs = _jobs(workflow_text)
    ran: dict[str, frozenset[str]] = {}
    for name in (JOB, LIVE_JOB):
        if name in jobs:
            ran[name] = frozenset(half for task in _kit_runs(jobs[name]) for half in task_halves(pixi_data, task))
    if not ran:
        return []
    covered = frozenset(half for halves in ran.values() for half in halves)
    names = "`, `".join(ran)
    problems = [
        f"no job runs the {half} half of the kit's suite (the kit's jobs: `{names}`)"
        for half in sorted(BOTH_HALVES - covered)
    ]
    if LIVE_JOB in ran and LIVE_HALF not in ran[LIVE_JOB]:
        problems.append(f"`{LIVE_JOB}` does not run the {LIVE_HALF} half")
    return problems


def gate_problems(workflow_text: str) -> list[str]:
    """``changes`` seeds the gate from the shared surface, flips it on the extra inputs, and emits it."""
    block = _jobs(workflow_text).get("changes", "")
    problems: list[str] = []
    if _OUTPUT.search(block) is None:
        problems.append("`changes` does not declare a `testing_kit` output from steps.filter.outputs.testing_kit")
    seed, echo = _SEED.search(block), _ECHO.search(block)
    if seed is None:
        problems.append('`TESTING_KIT_CHANGED="$SHARED_CHANGED"` seed missing -- a shared-surface change must fire it')
    if echo is None:
        problems.append('`echo "testing_kit=$TESTING_KIT_CHANGED" >> "$GITHUB_OUTPUT"` missing')
    if seed is not None and echo is not None:
        between = block[seed.end() : echo.start()]
        for path in EXTRA_GATE_PATHS:
            if path not in between:
                problems.append(f"`{path}` does not flip TESTING_KIT_CHANGED")
        if _SET.search(between) is None:
            problems.append("nothing between the seed and the echo sets `TESTING_KIT_CHANGED=true`")
    return problems


def trigger_problems(workflow_text: str) -> list[str]:
    """Every input the suite reads fires the workflow, on pull requests and on pushes to main."""
    problems: list[str] = []
    for event in ("pull_request", "push"):
        paths = _trigger_paths(workflow_text, event)
        problems.extend(f"`{p}` is not an on.{event}.paths trigger" for p in INPUTS if p not in paths)
    return problems


def leg_problems(pixi_data: dict) -> list[str]:
    """The local twin runs the kit's task, and the task is the whole suite: one command over the whole
    tests tree, or the aggregate of a package-half task and a live-tree task."""
    problems: list[str] = []
    legs = pixi_data["feature"]["guild-tasks"]["tasks"]["pyforge-station-tests"].get("depends-on", [])
    if {"task": TASK, "environment": ENV} not in legs:
        problems.append(f"pyforge-station-tests has no {{task = {TASK!r}, environment = {ENV!r}}} leg")
    task = _kit_tasks(pixi_data).get(TASK, {})
    cmd = task if isinstance(task, str) else task.get("cmd", "")
    if cmd and TESTS not in cmd.split():
        problems.append(f"`{TASK}` cmd {cmd!r} does not target the whole tests/ tree")
    for half in sorted(BOTH_HALVES - task_halves(pixi_data, TASK)):
        problems.append(f"`{TASK}` does not run the {half} half -- it must stay the whole suite")
    return problems


# --- the real input ----------------------------------------------------------


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _pixi_data() -> dict:
    return tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))


def test_the_job_is_wired() -> None:
    assert job_problems(_workflow_text()) == []


def test_the_changes_job_computes_the_gate() -> None:
    assert gate_problems(_workflow_text()) == []


def test_every_input_fires_the_workflow() -> None:
    assert trigger_problems(_workflow_text()) == []


def test_the_local_twin_runs_the_kit() -> None:
    assert leg_problems(_pixi_data()) == []


def test_ci_runs_both_halves_of_the_suite() -> None:
    assert halves_problems(_workflow_text(), _pixi_data()) == []


# --- mutation: each detector fires on a broken copy --------------------------


def _without(text: str, needle: str) -> str:
    assert needle in text, f"mutation premise: {needle!r} present in the real input"
    return text.replace(needle, "", 1)


def test_detector_fires_when_the_job_is_deleted() -> None:
    text = _workflow_text()
    block = _jobs(text)[JOB]
    mutated = _without(text, f"\n  {JOB}:{block}")
    assert job_problems(mutated) == [f"no `{JOB}` job under jobs:"]


def test_detector_fires_when_the_job_runs_pytest_directly() -> None:
    mutated = _workflow_text().replace(
        f"      - run: {RUN}\n", "      - run: pytest src/shared/packages/pyforge-testing-kit/tests\n"
    )
    assert job_problems(mutated) == [
        f"`{JOB}` does not run exactly `{RUN}`",
        f"`{JOB}` invokes pytest or a tests/ sub-path directly instead of the pixi task",
    ]


def test_detector_fires_when_the_gate_output_is_dropped() -> None:
    mutated = _without(_workflow_text(), '          echo "testing_kit=$TESTING_KIT_CHANGED" >> "$GITHUB_OUTPUT"\n')
    assert gate_problems(mutated) == ['`echo "testing_kit=$TESTING_KIT_CHANGED" >> "$GITHUB_OUTPUT"` missing']


def test_detector_fires_when_the_flag_tree_no_longer_flips_the_gate() -> None:
    mutated = _without(_workflow_text(), "              src/platform/config/flags.json 2>/dev/null; then\n")
    assert "`src/platform/config/flags.json` does not flip TESTING_KIT_CHANGED" in gate_problems(mutated)


def test_detector_fires_when_a_trigger_is_dropped() -> None:
    mutated = _workflow_text().replace("      - 'src/shared/packages/django-pyforge/**'\n", "")
    assert trigger_problems(mutated) == [
        "`src/shared/packages/django-pyforge/**` is not an on.pull_request.paths trigger",
        "`src/shared/packages/django-pyforge/**` is not an on.push.paths trigger",
    ]


def test_detector_fires_when_the_local_leg_is_removed() -> None:
    data = _pixi_data()
    legs = data["feature"]["guild-tasks"]["tasks"]["pyforge-station-tests"]["depends-on"]
    legs.remove({"task": TASK, "environment": ENV})
    assert leg_problems(data) == [f"pyforge-station-tests has no {{task = {TASK!r}, environment = {ENV!r}}} leg"]


def test_detector_fires_when_the_gate_is_neutered() -> None:
    mutated = _workflow_text().replace(
        "            TESTING_KIT_CHANGED=true\n", "            TESTING_KIT_CHANGED=false\n"
    )
    assert gate_problems(mutated) == ["nothing between the seed and the echo sets `TESTING_KIT_CHANGED=true`"]


def test_detector_fires_when_the_if_line_changes() -> None:
    text = _workflow_text()
    assert text.count(f"{GATE} == 'true'") == 1, "mutation premise: one job gates on the kit"
    mutated = text.replace(f"{GATE} == 'true'", "needs.changes.outputs.core == 'true'")
    assert job_problems(mutated) == [f"`{JOB}` is not gated on `{GATE}`"]


def test_detector_fires_on_an_extra_pytest_step() -> None:
    mutated = _workflow_text().replace(
        f"      - run: {RUN}\n",
        f"      - run: {RUN}\n      - run: pytest src/shared/packages/pyforge-testing-kit/tests\n",
    )
    assert job_problems(mutated) == [f"`{JOB}` invokes pytest or a tests/ sub-path directly instead of the pixi task"]


def test_detector_fires_when_another_job_needs_the_kit_job() -> None:
    text = _workflow_text()
    start = text.index("  atlas-test:\n")
    needs = text.index("    needs: changes\n", start)
    mutated = text[:needs] + "    needs: [changes, testing-kit-test]\n" + text[needs + len("    needs: changes\n") :]
    assert mutated != text, "mutation premise: atlas-test needs only changes"
    assert job_problems(mutated) == [
        f"`atlas-test` needs `{JOB}` -- it is a peer of the other jobs, not a gate on them"
    ]


def test_detector_fires_when_a_shared_surface_trigger_is_dropped() -> None:
    mutated = _workflow_text().replace("      - 'pixi.toml'\n", "")
    assert trigger_problems(mutated) == [
        "`pixi.toml` is not an on.pull_request.paths trigger",
        "`pixi.toml` is not an on.push.paths trigger",
    ]


# --- Story 118.1: the split wiring passes, and a dropped half reds ----------------

_PACKAGE_TASK = "pyforge-testing-kit-package-test"  # the split copy's package-half task (any name the job runs)


def _split_workflow(text: str | None = None) -> str:
    """Today's workflow split the way steward:S-124.2 lands it: the kit job runs the package half and a
    live-tree job, a copy of it, runs the live half."""
    text = _workflow_text() if text is None else text
    block = _jobs(text)[JOB]
    assert f"      - run: {RUN}\n" in block, "mutation premise: the kit job runs the whole-suite task"
    package = block.replace(f"      - run: {RUN}\n", f"      - run: pixi run --frozen -e {ENV} {_PACKAGE_TASK}\n")
    live = block.replace(f"      - run: {RUN}\n", f"      - run: {LIVE_RUN}\n")
    return text.replace(f"\n  {JOB}:{block}", f"\n  {JOB}:{package}\n  {LIVE_JOB}:{live}", 1)


def _split_pixi(data: dict | None = None) -> dict:
    """Today's pixi data split the way steward:S-124.1 lands it: two half tasks, and the kit's task
    kept as their ``depends-on`` aggregate."""
    data = copy.deepcopy(_pixi_data() if data is None else data)
    tasks = _kit_tasks(data)
    whole = tasks[TASK]
    assert TESTS in whole["cmd"].split(), "mutation premise: the kit's task runs the whole tests tree"
    tasks[_PACKAGE_TASK] = {"cmd": f'pytest {TESTS} -q -m "not live_tree"'}
    tasks[LIVE_TASK] = {"cmd": f"pytest {TESTS} -q -m live_tree", "env": whole.get("env", {})}
    tasks[TASK] = {"depends-on": [_PACKAGE_TASK, {"task": LIVE_TASK, "environment": ENV}]}
    return data


def test_the_split_wiring_passes_every_detector() -> None:
    workflow, data = _split_workflow(), _split_pixi()
    assert task_halves(data, _PACKAGE_TASK) == {PACKAGE_HALF}
    assert task_halves(data, LIVE_TASK) == {LIVE_HALF}
    assert task_halves(data, TASK) == BOTH_HALVES
    assert job_problems(workflow) == []
    assert halves_problems(workflow, data) == []
    assert leg_problems(data) == []
    assert gate_problems(workflow) == []
    assert trigger_problems(workflow) == []


def test_detector_fires_when_a_half_is_dropped_from_ci() -> None:
    workflow = _split_workflow()
    live = _jobs(workflow)[LIVE_JOB]
    mutated = _without(workflow, f"\n  {LIVE_JOB}:{live}")
    assert halves_problems(mutated, _split_pixi()) == [
        f"no job runs the {LIVE_HALF} half of the kit's suite (the kit's jobs: `{JOB}`)"
    ]


def test_detector_fires_when_a_half_is_dropped_from_the_live_job() -> None:
    mutated = _split_workflow().replace(
        f"      - run: {LIVE_RUN}\n", f"      - run: pixi run --frozen -e {ENV} {_PACKAGE_TASK}\n"
    )
    assert halves_problems(mutated, _split_pixi()) == [
        f"no job runs the {LIVE_HALF} half of the kit's suite (the kit's jobs: `{JOB}`, `{LIVE_JOB}`)",
        f"`{LIVE_JOB}` does not run the {LIVE_HALF} half",
    ]
    assert f"`{LIVE_JOB}` does not run exactly `{LIVE_RUN}`" in job_problems(mutated)


def test_detector_fires_when_a_half_is_dropped_from_the_aggregate() -> None:
    data = _split_pixi()
    _kit_tasks(data)[TASK]["depends-on"] = [_PACKAGE_TASK]
    assert leg_problems(data) == [f"`{TASK}` does not run the {LIVE_HALF} half -- it must stay the whole suite"]


def test_detector_fires_when_a_half_is_dropped_from_the_whole_suite_task() -> None:
    data = copy.deepcopy(_pixi_data())
    whole = _kit_tasks(data)[TASK]
    whole["cmd"] = f'{whole["cmd"]} -m "not live_tree"'
    assert leg_problems(data) == [f"`{TASK}` does not run the {LIVE_HALF} half -- it must stay the whole suite"]
    assert halves_problems(_workflow_text(), data) == [
        f"no job runs the {LIVE_HALF} half of the kit's suite (the kit's jobs: `{JOB}`)"
    ]
