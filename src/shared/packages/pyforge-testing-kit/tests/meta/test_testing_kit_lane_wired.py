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
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

# tests/meta -> tests -> pyforge-testing-kit -> packages -> shared -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
PIXI_TOML = _REPO_ROOT / "pixi.toml"

JOB = "testing-kit-test"
TASK = "pyforge-testing-kit-test"
ENV = "pyforge-testing-kit"
GATE = "needs.changes.outputs.testing_kit"
RUN = f"pixi run --frozen -e {ENV} {TASK}"
# Every input the suite reads: the kit, pyforge-core and django-pyforge (both on its
# PYTHONPATH), and the platform flag tree (test_flags.py's shape check).
INPUTS = (
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


# --- the detectors (pure: text in, problems out) -----------------------------


def job_problems(workflow_text: str) -> list[str]:
    """The job exists, needs ``changes``, is gated on ``testing_kit`` and runs the pixi task."""
    block = _jobs(workflow_text).get(JOB)
    if block is None:
        return [f"no `{JOB}` job under jobs:"]
    problems: list[str] = []
    if not re.search(r"^\s+needs:\s*changes\s*$", block, re.MULTILINE):
        problems.append(f"`{JOB}` does not need `changes`")
    if not re.search(rf"^\s+if:\s*{re.escape(GATE)} == 'true'\s*$", block, re.MULTILINE):
        problems.append(f"`{JOB}` is not gated on `{GATE}`")
    if RUN not in _RUN_LINE.findall(block):
        problems.append(f"`{JOB}` does not run exactly `{RUN}`")
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
    return problems


def trigger_problems(workflow_text: str) -> list[str]:
    """Every input the suite reads fires the workflow, on pull requests and on pushes to main."""
    problems: list[str] = []
    for event in ("pull_request", "push"):
        paths = _trigger_paths(workflow_text, event)
        problems.extend(f"`{p}` is not an on.{event}.paths trigger" for p in INPUTS if p not in paths)
    return problems


def leg_problems(pixi_data: dict) -> list[str]:
    """The local twin runs the kit's task, and the task runs the whole tests tree."""
    problems: list[str] = []
    legs = pixi_data["feature"]["guild-tasks"]["tasks"]["pyforge-station-tests"].get("depends-on", [])
    if {"task": TASK, "environment": ENV} not in legs:
        problems.append(f"pyforge-station-tests has no {{task = {TASK!r}, environment = {ENV!r}}} leg")
    cmd = pixi_data["feature"][ENV]["tasks"].get(TASK, {}).get("cmd", "")
    if "src/shared/packages/pyforge-testing-kit/tests" not in cmd.split():
        problems.append(f"`{TASK}` cmd {cmd!r} does not target the whole tests/ tree")
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
    assert job_problems(mutated) == [f"`{JOB}` does not run exactly `{RUN}`"]


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
    assert len(leg_problems(data)) == 1
