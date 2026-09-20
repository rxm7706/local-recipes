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
"""

from __future__ import annotations

import re
import tomllib

from conftest import PACKAGES_ROOT, sibling_station_dirs

# src/shared/packages -> src/shared -> src -> repo root
REPO_ROOT = PACKAGES_ROOT.parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
PIXI_TOML = REPO_ROOT / "pixi.toml"

CORE_JOB = "core-test"
CORE_TASK = "pyforge-core-test"
CORE_ENV = "pyforge-core"
CORE_GATE = "needs.changes.outputs.core"
CORE_RUN = f"pixi run --frozen -e {CORE_ENV} {CORE_TASK}"

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


# --- the detectors (pure: text in, problems out) -----------------------------


def core_job_problems(workflow_text: str) -> list[str]:
    """(a) a ``core-test`` job gated on the ``core`` output, running the pixi
    task and never an enumerated file list; a peer, not a gate on others."""
    problems: list[str] = []
    jobs = _jobs(workflow_text)
    block = jobs.get(CORE_JOB)
    if block is None:
        return [f"no `{CORE_JOB}` job under jobs:"]
    if_line = _IF_LINE.search(block)
    if if_line is None or CORE_GATE not in if_line.group(1):
        problems.append(f"`{CORE_JOB}` is not gated on `{CORE_GATE}`")
    runs = _RUN_LINE.findall(block)
    if not any(CORE_TASK in r for r in runs):
        problems.append(f"`{CORE_JOB}` has no run step invoking `{CORE_TASK}`")
    if CORE_RUN not in runs:
        problems.append(f"`{CORE_JOB}` does not run exactly `{CORE_RUN}`")
    if _META_FILE.search(block):
        problems.append(f"`{CORE_JOB}` enumerates a tests/ sub-path -- the gate runs the pixi task, never a file list")
    if any("pytest" in r for r in runs):
        problems.append(f"`{CORE_JOB}` invokes pytest directly instead of the pixi task")
    for name, other in jobs.items():
        if name != CORE_JOB and any(CORE_JOB in n for n in _NEEDS_LINE.findall(other)):
            problems.append(f"`{name}` needs `{CORE_JOB}` -- it is a peer of the station jobs, not a gate on them")
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
    FIRST ``pyforge-station-tests`` leg; the task runs the whole tests tree;
    ``pr-preflight`` inherits it."""
    problems: list[str] = []
    tasks = pixi_data["feature"]["guild-tasks"]["tasks"]
    legs = tasks["pyforge-station-tests"].get("depends-on", [])
    if not legs or legs[0] != {"task": CORE_TASK, "environment": CORE_ENV}:
        problems.append(
            f"pyforge-station-tests' first depends-on leg is {legs[:1]!r}, "
            f"not {{task = {CORE_TASK!r}, environment = {CORE_ENV!r}}}"
        )
    preflight = [d if isinstance(d, str) else d["task"] for d in tasks["pr-preflight"].get("depends-on", [])]
    if "pyforge-station-tests" not in preflight:
        problems.append(
            "pr-preflight no longer depends on pyforge-station-tests, so it no longer inherits the core leg"
        )
    cmd = pixi_data["feature"]["pyforge-core"]["tasks"].get(CORE_TASK, {}).get("cmd", "")
    if "src/shared/packages/pyforge-core/tests" not in cmd or _META_FILE.search(cmd):
        problems.append(f"`{CORE_TASK}` cmd {cmd!r} does not target the whole tests/ tree")
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


# --- the guards --------------------------------------------------------------


def test_core_test_job_is_wired():
    assert core_job_problems(_workflow_text()) == []


def test_changes_job_computes_the_core_output():
    assert changes_wiring_problems(_workflow_text()) == []


def test_pixi_aggregate_runs_the_core_leg_first():
    assert pixi_leg_problems(_pixi_data()) == []


def test_every_pyforge_package_is_gated():
    assert roster_problems(_workflow_text(), _all_pyforge_packages()) == []


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
        f"- run: {CORE_RUN}",
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
