"""Meta test -- the conformance suite's CI wiring stays wired (Story 52.2,
SPEC-pyforge-core CAP-8).

Story 52.2 made this package's whole ``tests/`` tree a PR gate: a
``core-test`` job in ``.github/workflows/pyforge-station-tests.yml`` gated on
a ``core`` filter output (shared surface OR any station changed), and a
``pyforge-core-test`` leg at the head of the local ``pyforge-station-tests``
aggregate in ``pixi.toml``. Before that job existed, the four
``tests/meta/*_sole_ownership.py`` guards had never run on a PR and six
violations accumulated unseen (cleared by Story 52.1). Nothing else in the
repo pins that wiring: deleting the job, dropping the in-loop
``CORE_CHANGED=true`` (so a station-only diff no longer fires the job), or
removing the pixi leg would each go unnoticed -- the gate would silently
stop being a gate, exactly the failure that motivated it. This test pins
each of those, structurally.

Same shape as ``pyforge-steward``'s ``test_workflow_path_filters_match.py``
(a workflow-structure meta test), but on RAW TEXT with regexes rather than
``yaml.safe_load``: PyYAML is not a dependency of the ``pyforge-core`` pixi
environment (``[feature.pyforge-core.dependencies]`` is pytest + build
backends only), and this package's stdlib-only leaf constraint
(``test_leaf_constraint.py``) is a value worth keeping in its tests too.
``pixi.toml`` is parsed for real with stdlib ``tomllib``.

The station roster is derived from the filesystem (``sibling_station_dirs``,
``tests/meta/conftest.py``), never hardcoded, so a ninth ``pyforge-*``
station cannot appear un-gated: every ``pyforge-*`` package directory must
be a ``pull_request`` path trigger, and every one that is not part of the
shared-surface list must be in the ``changes`` job's station loop. Each
detector is proven non-vacuous against a mutated copy of the real input.

Story 117.1 (spec-pyforge-core:CAP-14 and the CAP-8 amendment) gave the suite
two halves: the modules marked ``live_tree`` read the repository outside the
package, the rest is the package half a second root runs from the package
alone. This test accepts two wirings and reds one that drops a half: today's
one ``core-test`` job running ``pyforge-core-test``, or the split
steward:S-124.1 and steward:S-124.2 land -- a package-half job and a
``core-live-test`` job, the job carrying the live-tree half gated on the
``core`` output seeded from ``CORE_CHANGED``, and ``pyforge-core-test`` kept
as the ``depends-on`` aggregate of both halves, so it stays the whole suite.
Which half a task runs is read from its ``-m`` marker expression. The
``test_detector_fires_when_a_half_is_dropped_*`` tests prove it on the
split: the real one since steward:S-124.2 landed it (``core-test`` runs
``pyforge-core-package-test`` on ``core_package``, the shared surface;
``core-live-test`` runs ``pyforge-core-live-test`` on ``core``), a mutated
copy of a single wiring before. This module reads ``pixi.toml`` and the
workflow, so it is itself ``live_tree``.
"""

from __future__ import annotations

import ast
import re
import shlex
import tomllib

import pytest
from conftest import PACKAGES_ROOT, sibling_station_dirs

pytestmark = pytest.mark.live_tree

# src/shared/packages -> src/shared -> src -> repo root
REPO_ROOT = PACKAGES_ROOT.parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
PIXI_TOML = REPO_ROOT / "pixi.toml"

CORE_JOB = "core-test"
CORE_TASK = "pyforge-core-test"
CORE_ENV = "pyforge-core"
CORE_GATE = "needs.changes.outputs.core"
CORE_RUN = f"pixi run --frozen -e {CORE_ENV} {CORE_TASK}"
CORE_TESTS = "src/shared/packages/pyforge-core/tests"
# Story 117.1: the split wiring (steward:S-124.1 / S-124.2) adds a live-tree job and task beside the package half.
CORE_LIVE_JOB = "core-live-test"
CORE_LIVE_TASK = "pyforge-core-live-test"
PACKAGE_HALF = "package"
LIVE_HALF = "live-tree"
BOTH_HALVES = frozenset({PACKAGE_HALF, LIVE_HALF})

_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*$", re.MULTILINE)
_JOB_HEADER = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]*$", re.MULTILINE)
_TRIGGER_HEADER = re.compile(r"^  ([A-Za-z_]+):[ \t]*$", re.MULTILINE)
_PATH_ENTRY = re.compile(r"^\s+-\s+'([^']+)'\s*$", re.MULTILINE)
_IF_LINE = re.compile(r"^\s+if:\s*(.+?)\s*$", re.MULTILINE)
_NEEDS_LINE = re.compile(r"^\s+needs:\s*(.+?)\s*$", re.MULTILINE)
_RUN_LINE = re.compile(r"^\s+-\s+run:\s*(.+?)\s*$", re.MULTILINE)
_META_FILE = re.compile(r"tests/(?:meta|unit)\b")
_SHARED_DIFF = re.compile(r'git diff --quiet "\$BASE"\.\.\.HEAD -- \\\n(.*?)2>/dev/null; then', re.DOTALL)
_STATION_LOOP = re.compile(r"^\s*for s in ([^;\n]+); do\n(.*?)^\s*done\s*$", re.MULTILINE | re.DOTALL)
_CORE_SEED = re.compile(r'^\s*CORE_CHANGED="\$SHARED_CHANGED"\s*$', re.MULTILINE)
_CORE_SET = re.compile(r"^\s*CORE_CHANGED=true\s*$", re.MULTILINE)
_CORE_OUT = re.compile(r'^\s*echo "core=\$CORE_CHANGED" >> "\$GITHUB_OUTPUT"\s*$', re.MULTILINE)
_CORE_TASK_RUN = re.compile(rf"pixi run --frozen -e {CORE_ENV} ([\w-]+)")
_CORE_GATE_EXACT = re.compile(re.escape(CORE_GATE) + r"\b")


# --- raw-text structure helpers ---------------------------------------------


def _top_level_blocks(text: str) -> dict[str, str]:
    heads = list(_TOP_LEVEL_KEY.finditer(text))
    return {
        m.group(1): text[m.end() : heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        for i, m in enumerate(heads)
    }


def _two_space_blocks(block: str, header: re.Pattern[str]) -> dict[str, str]:
    heads = list(header.finditer(block))
    return {
        m.group(1): block[m.end() : heads[i + 1].start() if i + 1 < len(heads) else len(block)]
        for i, m in enumerate(heads)
    }


def _jobs(text: str) -> dict[str, str]:
    return _two_space_blocks(_top_level_blocks(text)["jobs"], _JOB_HEADER)


def _pull_request_paths(text: str) -> list[str]:
    triggers = _two_space_blocks(_top_level_blocks(text)["on"], _TRIGGER_HEADER)
    return _PATH_ENTRY.findall(triggers.get("pull_request", ""))


def _shared_surface_packages(changes_block: str) -> list[str]:
    """The ``pyforge-*`` package names in the ``changes`` job's
    ``SHARED_CHANGED`` git-diff path list -- the workflow's own declaration of
    which ``src/shared/packages/`` members are NOT stations."""
    m = _SHARED_DIFF.search(changes_block)
    if m is None:
        return []
    return [token.split("/")[-1] for token in m.group(1).split() if token.startswith("src/shared/packages/")]


def _station_loop(changes_block: str) -> tuple[list[str], str] | None:
    m = _STATION_LOOP.search(changes_block)
    return None if m is None else (m.group(1).split(), m.group(2))


# --- which half of the suite a pixi task runs (Story 117.1) -------------------


def _selects(expr: str, *, live: bool) -> bool:
    """Does the ``-m`` expression select a test marked ``live_tree`` (``live``)
    or an unmarked one? Every other marker reads as absent."""

    def ev(node: ast.expr) -> bool:
        if isinstance(node, ast.BoolOp):
            values = [ev(v) for v in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.Name):
            return live if node.id == "live_tree" else False
        raise ValueError(f"unsupported -m expression {expr!r}")

    return ev(ast.parse(expr, mode="eval").body)


def _cmd_halves(cmd: str) -> frozenset[str]:
    """The halves a task command runs: each ``pytest`` over the whole core
    ``tests/`` tree adds the halves its last ``-m`` selects (both with none);
    a run of an enumerated sub-path adds nothing."""
    halves: set[str] = set()
    for part in cmd.split("&&"):
        if CORE_TESTS not in part or _META_FILE.search(part):
            continue
        argv = shlex.split(part)
        start = next((i for i, arg in enumerate(argv) if arg == "pytest" or arg.endswith("/pytest")), None)
        if start is None:
            continue
        args = argv[start + 1 :]
        exprs = [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "-m"]
        if not exprs:
            halves |= BOTH_HALVES
            continue
        halves |= {half for half, live in ((PACKAGE_HALF, False), (LIVE_HALF, True)) if _selects(exprs[-1], live=live)}
    return frozenset(halves)


def _core_tasks(pixi_data: dict) -> dict:
    return pixi_data["feature"]["pyforge-core"]["tasks"]


def _leg_name(leg: str | dict) -> str:
    return leg if isinstance(leg, str) else leg.get("task", "")


def _task_halves(core_tasks: dict, name: str, seen: frozenset[str] = frozenset()) -> frozenset[str]:
    """The halves a ``pyforge-core`` task runs: its own command's, plus every
    ``depends-on`` leg's (an aggregate is the union of its legs)."""
    task = core_tasks.get(name)
    if task is None or name in seen:
        return frozenset()
    if isinstance(task, str):
        task = {"cmd": task}
    halves = set(_cmd_halves(task.get("cmd", "")))
    for leg in task.get("depends-on", []):
        halves |= _task_halves(core_tasks, _leg_name(leg), seen | {name})
    return frozenset(halves)


def _dropped(halves: frozenset[str]) -> str:
    """The halves missing from ``halves``, worded for a problem line ('' when none)."""
    return " and ".join(half for half in (PACKAGE_HALF, LIVE_HALF) if half not in halves)


def _core_run(block: str) -> str | None:
    """The job's ``pixi run --frozen -e pyforge-core <task>`` run step, if any."""
    return next((run for run in _RUN_LINE.findall(block) if _CORE_TASK_RUN.fullmatch(run)), None)


# --- the detectors (pure: text in, problems out) -----------------------------


def core_job_problems(workflow_text: str) -> list[str]:
    """(a) a ``core-test`` job gated on the ``core`` output, running the pixi
    task and never an enumerated file list; a peer, not a gate on others.
    Once the suite is split (a ``core-live-test`` job beside it, Story 117.1),
    each of the two jobs is gated on a ``changes`` output and runs one
    ``pyforge-core`` pixi task; which half each runs, and the live half's
    gate, are ``lane_halves_problems``'s to judge."""
    problems: list[str] = []
    jobs = _jobs(workflow_text)
    block = jobs.get(CORE_JOB)
    if block is None:
        return [f"no `{CORE_JOB}` job under jobs:"]
    if CORE_LIVE_JOB not in jobs:
        if_line = _IF_LINE.search(block)
        if if_line is None or CORE_GATE not in if_line.group(1):
            problems.append(f"`{CORE_JOB}` is not gated on `{CORE_GATE}`")
        runs = _RUN_LINE.findall(block)
        if not any(CORE_TASK in r for r in runs):
            problems.append(f"`{CORE_JOB}` has no run step invoking `{CORE_TASK}`")
        if CORE_RUN not in runs:
            problems.append(f"`{CORE_JOB}` does not run exactly `{CORE_RUN}`")
    else:
        for name in (CORE_JOB, CORE_LIVE_JOB):
            if_line = _IF_LINE.search(jobs[name])
            if if_line is None or "needs.changes.outputs." not in if_line.group(1):
                problems.append(f"`{name}` is not gated on a `changes` output")
            if _core_run(jobs[name]) is None:
                problems.append(f"`{name}` has no run step invoking a `{CORE_ENV}` pixi task")
    for job in (CORE_JOB, CORE_LIVE_JOB):
        if job not in jobs:
            continue
        runs = _RUN_LINE.findall(jobs[job])
        if _META_FILE.search(jobs[job]):
            problems.append(f"`{job}` enumerates a tests/ sub-path -- the gate runs the pixi task, never a file list")
        if any("pytest" in r for r in runs):
            problems.append(f"`{job}` invokes pytest directly instead of the pixi task")
        for name, other in jobs.items():
            if name != job and any(job in n for n in _NEEDS_LINE.findall(other)):
                problems.append(f"`{name}` needs `{job}` -- it is a peer of the station jobs, not a gate on them")
    return problems


def lane_halves_problems(workflow_text: str, pixi_data: dict) -> list[str]:
    """(e) Story 117.1: the core jobs run both halves of the suite between
    them -- one job running the whole suite, or a package-half job and a
    live-tree job -- and every job that runs the live-tree half is gated on
    the ``core`` output, which the station loop flips on any station's change."""
    problems: list[str] = []
    jobs = _jobs(workflow_text)
    tasks = _core_tasks(pixi_data)
    carried: set[str] = set()
    for name in (CORE_JOB, CORE_LIVE_JOB):
        block = jobs.get(name)
        run = None if block is None else _core_run(block)
        if block is None or run is None:
            continue
        match = _CORE_TASK_RUN.fullmatch(run)
        assert match is not None
        halves = _task_halves(tasks, match.group(1))
        carried |= halves
        if_line = _IF_LINE.search(block)
        if LIVE_HALF in halves and (if_line is None or _CORE_GATE_EXACT.search(if_line.group(1)) is None):
            problems.append(
                f"`{name}` runs the {LIVE_HALF} half but is not gated on `{CORE_GATE}` -- "
                "a station-only diff would not fire it"
            )
    dropped = _dropped(frozenset(carried))
    if dropped:
        problems.append(f"the core jobs drop the {dropped} half of the suite -- CI runs it nowhere")
    return problems


def changes_wiring_problems(workflow_text: str) -> list[str]:
    """(b) the ``changes`` job seeds ``CORE_CHANGED`` from the shared surface,
    flips it inside the station loop, and emits it as the ``core`` output."""
    problems: list[str] = []
    block = _jobs(workflow_text).get("changes")
    if block is None:
        return ["no `changes` job under jobs:"]
    if not re.search(r"^\s+core:\s*\$\{\{\s*steps\.filter\.outputs\.core\s*\}\}\s*$", block, re.MULTILINE):
        problems.append("`changes` does not declare a `core` output from steps.filter.outputs.core")
    if _CORE_SEED.search(block) is None:
        problems.append('`CORE_CHANGED="$SHARED_CHANGED"` seed missing -- a shared-surface change must fire core-test')
    loop = _station_loop(block)
    if loop is None:
        problems.append("no `for s in ...; do ... done` station loop in the changes shell")
    elif _CORE_SET.search(loop[1]) is None:
        problems.append(
            "the station loop does not assign `CORE_CHANGED=true` -- a station-only diff would not fire core-test"
        )
    if _CORE_OUT.search(block) is None:
        problems.append('`echo "core=$CORE_CHANGED" >> "$GITHUB_OUTPUT"` missing')
    return problems


def pixi_leg_problems(pixi_data: dict) -> list[str]:
    """(c) the local twin: ``pyforge-core-test`` in env ``pyforge-core`` is the
    FIRST ``pyforge-station-tests`` leg; the task runs the whole tests tree --
    one command, or (Story 117.1) a ``depends-on`` aggregate of the package
    half and the live-tree half, never one half alone; ``pr-preflight``
    inherits it."""
    problems: list[str] = []
    tasks = pixi_data["feature"]["guild-tasks"]["tasks"]
    legs = tasks["pyforge-station-tests"].get("depends-on", [])
    if not legs or legs[0] != {"task": CORE_TASK, "environment": CORE_ENV}:
        problems.append(
            f"pyforge-station-tests' first depends-on leg is {legs[:1]!r}, "
            f"not {{task = {CORE_TASK!r}, environment = {CORE_ENV!r}}}"
        )
    preflight = [d if isinstance(d, str) else d["task"] for d in tasks["pr-preflight-lanes"].get("depends-on", [])]
    if "pyforge-station-tests" not in preflight:
        problems.append(
            "pr-preflight no longer depends on pyforge-station-tests, so it no longer inherits the core leg"
        )
    task = _core_tasks(pixi_data).get(CORE_TASK, {})
    cmd = task.get("cmd", "")
    if not task.get("depends-on") and (CORE_TESTS not in cmd or _META_FILE.search(cmd)):
        problems.append(f"`{CORE_TASK}` cmd {cmd!r} does not target the whole tests/ tree")
    else:
        dropped = _dropped(_task_halves(_core_tasks(pixi_data), CORE_TASK))
        if dropped:
            problems.append(f"`{CORE_TASK}` is not the whole suite -- it drops the {dropped} half")
    return problems


def roster_problems(workflow_text: str, package_names: list[str]) -> list[str]:
    """(d) every ``pyforge-*`` package dir is a pull_request path trigger, and
    every one outside the shared-surface list is in the station loop -- so a
    ninth station cannot appear un-gated."""
    problems: list[str] = []
    pr_paths = _pull_request_paths(workflow_text)
    for pkg in package_names:
        if f"src/shared/packages/{pkg}/**" not in pr_paths:
            problems.append(f"`src/shared/packages/{pkg}/**` is not an on.pull_request.paths trigger")
    changes = _jobs(workflow_text).get("changes", "")
    shared = _shared_surface_packages(changes)
    if CORE_ENV not in shared:
        problems.append("`src/shared/packages/pyforge-core` is not in the SHARED_CHANGED diff list")
    loop = _station_loop(changes)
    roster = loop[0] if loop else []
    stations = [pkg.removeprefix("pyforge-") for pkg in package_names if pkg not in shared]
    for s in stations:
        if s not in roster:
            problems.append(f"station `pyforge-{s}` is missing from the changes loop roster {roster}")
    for s in roster:
        if f"pyforge-{s}" not in package_names:
            problems.append(f"loop roster names `{s}` but src/shared/packages/pyforge-{s} does not exist")
    return problems


# --- fixtures ----------------------------------------------------------------


def _workflow_text() -> str:
    assert WORKFLOW.is_file(), f"expected {WORKFLOW} to exist"
    return WORKFLOW.read_text(encoding="utf-8")


def _pixi_data() -> dict:
    assert PIXI_TOML.is_file(), f"expected {PIXI_TOML} to exist"
    return tomllib.loads(PIXI_TOML.read_text(encoding="utf-8"))


def _all_pyforge_packages() -> list[str]:
    """Filesystem-derived: ``sibling_station_dirs`` (every pyforge-* but core,
    testing-kit included) plus pyforge-core itself."""
    names = sorted({p.name for p in sibling_station_dirs()} | {CORE_ENV})
    assert (PACKAGES_ROOT / "pyforge-testing-kit").is_dir(), "roster premise: pyforge-testing-kit exists"
    assert "pyforge-testing-kit" in names
    return names


# The split wiring (Story 117.1): the real one since steward:S-124.1 / S-124.2 landed it, else a mutated copy of
# a single task and job. The copy names its package-half task; the real split names its own.
_COPY_PACKAGE_TASK = "pyforge-core-package-test"


def _split_pixi_data() -> dict:
    data = _pixi_data()
    tasks = _core_tasks(data)
    if tasks[CORE_TASK].get("depends-on"):
        return data
    whole = tasks[CORE_TASK]["cmd"]
    tasks[_COPY_PACKAGE_TASK] = {"cmd": f'{whole} -m "not live_tree"'}
    tasks[CORE_LIVE_TASK] = {"cmd": f"{whole} -m live_tree"}
    tasks[CORE_TASK] = {
        "depends-on": [
            {"task": _COPY_PACKAGE_TASK, "environment": CORE_ENV},
            {"task": CORE_LIVE_TASK, "environment": CORE_ENV},
        ]
    }
    return data


def _split_halves(data: dict) -> tuple[str, str]:
    """``(package-half task, live-tree task)``: the two legs of the split aggregate."""
    tasks = _core_tasks(data)
    legs = [_leg_name(leg) for leg in tasks[CORE_TASK]["depends-on"]]
    package = next(leg for leg in legs if _task_halves(tasks, leg) == {PACKAGE_HALF})
    live = next(leg for leg in legs if _task_halves(tasks, leg) == {LIVE_HALF})
    return package, live


def _split_workflow_text() -> str:
    text = _workflow_text()
    jobs = _jobs(text)
    if CORE_LIVE_JOB in jobs:
        return text
    package, live = _split_halves(_split_pixi_data())
    header = f"  {CORE_JOB}:"
    block = jobs[CORE_JOB]
    start = text.index(f"\n{header}\n") + 1
    end = start + len(header) + len(block)
    assert text[start + len(header) : end] == block, "mutation premise: the core-test block is contiguous"
    package_job = header + block.replace(CORE_RUN, f"pixi run --frozen -e {CORE_ENV} {package}")
    live_job = f"  {CORE_LIVE_JOB}:" + block.replace(CORE_RUN, f"pixi run --frozen -e {CORE_ENV} {live}")
    return text[:start] + package_job + live_job + text[end:]


# --- the guards --------------------------------------------------------------


def test_core_test_job_is_wired():
    assert core_job_problems(_workflow_text()) == []


def test_changes_job_computes_the_core_output():
    assert changes_wiring_problems(_workflow_text()) == []


def test_pixi_aggregate_runs_the_core_leg_first():
    assert pixi_leg_problems(_pixi_data()) == []


def test_every_pyforge_package_is_gated():
    assert roster_problems(_workflow_text(), _all_pyforge_packages()) == []


def test_the_core_jobs_run_the_whole_suite():
    assert lane_halves_problems(_workflow_text(), _pixi_data()) == []


def test_the_split_wiring_is_accepted():
    text, data = _split_workflow_text(), _split_pixi_data()
    assert CORE_LIVE_JOB in _jobs(text)
    assert core_job_problems(text) == []
    assert changes_wiring_problems(text) == []
    assert pixi_leg_problems(data) == []
    assert lane_halves_problems(text, data) == []


# --- non-vacuous proof: each detector fires on the mutation it exists for ----


def _without_line(text: str, pattern: re.Pattern[str]) -> str:
    m = pattern.search(text)
    assert m is not None, f"mutation premise: {pattern.pattern!r} present in the real input"
    return text[: m.start()] + text[m.end() :]


def test_detector_fires_when_the_core_job_is_deleted():
    text = _workflow_text()
    jobs = _jobs(text)
    start = text.index(f"\n  {CORE_JOB}:\n")
    end = start + 1 + len(f"  {CORE_JOB}:\n") + len(jobs[CORE_JOB])
    mutated = text[:start] + text[end:]
    assert CORE_JOB not in _jobs(mutated)
    assert core_job_problems(mutated) == [f"no `{CORE_JOB}` job under jobs:"]


def test_detector_fires_when_the_core_job_enumerates_files():
    text = _workflow_text().replace(
        f"- run: {_core_run(_jobs(_workflow_text())[CORE_JOB])}",
        "- run: pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py",
    )
    problems = core_job_problems(text)
    assert any("enumerates" in p for p in problems), problems
    assert any("invokes pytest directly" in p for p in problems), problems


def test_detector_fires_when_the_loop_no_longer_flips_core():
    mutated = _without_line(_workflow_text(), _CORE_SET)
    assert changes_wiring_problems(mutated) == [
        "the station loop does not assign `CORE_CHANGED=true` -- a station-only diff would not fire core-test"
    ]


def test_detector_fires_when_the_core_output_is_dropped():
    mutated = _without_line(_workflow_text(), _CORE_OUT)
    assert changes_wiring_problems(mutated) == ['`echo "core=$CORE_CHANGED" >> "$GITHUB_OUTPUT"` missing']


def test_detector_fires_when_the_pixi_leg_is_removed():
    data = _pixi_data()
    legs = data["feature"]["guild-tasks"]["tasks"]["pyforge-station-tests"]["depends-on"]
    data["feature"]["guild-tasks"]["tasks"]["pyforge-station-tests"]["depends-on"] = legs[1:]
    problems = pixi_leg_problems(data)
    assert len(problems) == 1 and "first depends-on leg" in problems[0], problems


def test_detector_fires_on_an_ungated_ninth_station():
    problems = roster_problems(_workflow_text(), [*_all_pyforge_packages(), "pyforge-ninth"])
    assert problems == [
        "`src/shared/packages/pyforge-ninth/**` is not an on.pull_request.paths trigger",
        "station `pyforge-ninth` is missing from the changes loop roster "
        f"{_station_loop(_jobs(_workflow_text())['changes'])[0]}",
    ]


def test_detector_fires_when_a_half_is_dropped_from_the_workflow():
    text = _split_workflow_text()
    header = f"  {CORE_LIVE_JOB}:"
    start = text.index(f"\n{header}\n") + 1
    mutated = text[:start] + text[start + len(header) + len(_jobs(text)[CORE_LIVE_JOB]) :]
    assert CORE_LIVE_JOB not in _jobs(mutated)
    assert lane_halves_problems(mutated, _split_pixi_data()) == [
        f"the core jobs drop the {LIVE_HALF} half of the suite -- CI runs it nowhere"
    ]


def test_detector_fires_when_a_half_is_dropped_from_the_aggregate():
    data = _split_pixi_data()
    _package, live = _split_halves(data)
    task = _core_tasks(data)[CORE_TASK]
    task["depends-on"] = [leg for leg in task["depends-on"] if _leg_name(leg) != live]
    assert pixi_leg_problems(data) == [f"`{CORE_TASK}` is not the whole suite -- it drops the {LIVE_HALF} half"]


def test_detector_fires_when_a_half_is_dropped_by_the_package_job():
    text = _split_workflow_text()
    package, live = _split_halves(_split_pixi_data())
    mutated = text.replace(
        f"- run: pixi run --frozen -e {CORE_ENV} {package}\n", f"- run: pixi run --frozen -e {CORE_ENV} {live}\n"
    )
    assert mutated != text, "mutation premise: a job runs the package half"
    problems = lane_halves_problems(mutated, _split_pixi_data())
    assert f"the core jobs drop the {PACKAGE_HALF} half of the suite -- CI runs it nowhere" in problems, problems


def test_detector_fires_when_the_live_half_is_not_gated_on_core():
    text = _split_workflow_text()
    block = _jobs(text)[CORE_LIVE_JOB]
    if_line = _IF_LINE.search(block)
    assert if_line is not None and _CORE_GATE_EXACT.search(if_line.group(1)), "mutation premise: gated on core"
    assert text.count(block) == 1
    mutated = text.replace(block, block.replace(CORE_GATE, f"{CORE_GATE}_package"))
    assert lane_halves_problems(mutated, _split_pixi_data()) == [
        f"`{CORE_LIVE_JOB}` runs the {LIVE_HALF} half but is not gated on `{CORE_GATE}` -- "
        "a station-only diff would not fire it"
    ]
