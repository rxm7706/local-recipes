"""Story 117.30: every task in the preflight's alone-tail set has a tail the preflight can run alone.

``preflight.ALONE_TAIL_TASKS`` names the tasks whose last ``&&`` segment measures its own CPU time, so the preflight
runs that segment with no other lane in flight (``spec-pyforge-steward`` CAP-175, a fix under CAP-159). A declared
task whose command loses its tail would be refused by every run that selects it (exit 2), and a tail that ran under
xdist would load the cores itself; this module reads the repository's ``pixi.toml`` and fails on either before a run
does.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.steward import preflight

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
PIXI = REPO_ROOT / "pixi.toml"
XDIST_FLAGS = ("-n", "--numprocesses", "--dist", "--maxprocesses")


def _pixi() -> dict:
    return tomllib.loads(PIXI.read_text(encoding="utf-8"))


@pytest.mark.parametrize("task", sorted(preflight.ALONE_TAIL_TASKS))
def test_each_declared_task_splits_into_a_head_and_a_serial_pytest_tail(task: str) -> None:
    plan = preflight.alone_tail_plan(_pixi(), task)
    assert plan is not None, f"{task}: its cmd has no '&&' tail the preflight can run as one argv"
    assert plan.tail[0] == "pytest" or plan.tail[:3] == ("python", "-m", "pytest"), plan.tail
    assert not any(token.split("=")[0] in XDIST_FLAGS for token in plan.tail), (
        f"{task}: the tail runs alone so no other process loads the cores; under xdist it would load them itself"
    )


@pytest.mark.parametrize("task", sorted(preflight.ALONE_TAIL_TASKS))
def test_each_declared_task_is_a_preflight_lane(task: str) -> None:
    lanes = preflight.list_preflight_lanes(_pixi(), invoking_env=preflight.DEFAULT_INVOKING_ENV)
    assert task in {lane.task for lane in lanes}


def test_doctor_s_tail_is_the_five_second_budget_test_and_its_head_skips_it() -> None:
    plan = preflight.alone_tail_plan(_pixi(), "pyforge-doctor-live-test")
    assert plan is not None
    budget = "src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py"
    assert budget in plan.tail
    assert len(plan.head) == 1
    assert f"--ignore={budget}" in plan.head[0]
