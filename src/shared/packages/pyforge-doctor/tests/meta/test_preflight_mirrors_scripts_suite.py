"""Every step of the Detectors ``scripts-suite`` job is a ``pr-preflight`` leg (Story 39.1).

``pr-preflight`` promises that a green local run means a green CI run. Doctor Story 38.5
added a second ``scripts-suite`` step (``tests/scripts/test_detectors_doctor_sources.py``
under ``-e pyforge-doctor``) and no ``pr-preflight`` leg ran it, so the three tests it
exists for only ever skipped locally. This test reds the next such step: each ``run:`` in
the job must be ``pixi run --frozen -e <env> <task>``, and ``(task, env)`` must be one of
``pr-preflight``'s ``depends-on`` legs.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

# tests/meta/test_x.py -> parents[3] is src/shared/packages/ (same arithmetic as the sibling
# test_flag_gate_stays_outside_every_station.py).
PACKAGES_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PACKAGES_ROOT.parents[2]

_PIXI_RUN = re.compile(r"pixi run --frozen -e (?P<env>\S+) (?P<task>\S+)")

#: The environment ``pr-preflight`` runs in (``pixi run -e pyforge-guild pr-preflight``), so the one a
#: bare-string leg, which pins no environment, runs in.
_PREFLIGHT_ENV = "pyforge-guild"


def _preflight_legs(pixi: dict[str, Any]) -> set[tuple[str, str]]:
    """``pr-preflight``'s legs as ``(task, environment)``; a bare string leg runs in ``_PREFLIGHT_ENV``."""
    legs: set[tuple[str, str]] = set()
    for dep in pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]["depends-on"]:
        if isinstance(dep, str):
            legs.add((dep, _PREFLIGHT_ENV))
        else:
            legs.add((dep["task"], dep.get("environment", _PREFLIGHT_ENV)))
    return legs


def unmirrored_steps(workflow: dict[str, Any], pixi: dict[str, Any]) -> list[str]:
    """One problem per ``scripts-suite`` step that ``pr-preflight`` does not run."""
    legs = _preflight_legs(pixi)
    problems: list[str] = []
    for step in workflow["jobs"]["scripts-suite"]["steps"]:
        run = step.get("run")
        if run is None:
            continue
        name = step.get("name", run)
        match = _PIXI_RUN.fullmatch(run.strip())
        if match is None:
            problems.append(
                f"scripts-suite step {name!r} runs {run.strip()!r}: call a named task "
                "(`pixi run --frozen -e <env> <task>`) so pr-preflight can run the same one"
            )
        elif (match["task"], match["env"]) not in legs:
            problems.append(
                f"scripts-suite step {name!r} runs task {match['task']!r} in {match['env']!r}, "
                "which is not a pr-preflight depends-on leg"
            )
    return problems


def _live() -> tuple[dict[str, Any], dict[str, Any]]:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/detectors.yml").read_text(encoding="utf-8"))
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    return workflow, pixi


def test_every_scripts_suite_step_is_a_pr_preflight_leg() -> None:
    workflow, pixi = _live()
    assert unmirrored_steps(workflow, pixi) == []


def test_the_doctor_env_step_is_the_leg_story_39_1_added() -> None:
    """The step 38.5 added runs as a named task in ``pyforge-doctor``, and pr-preflight runs it."""
    workflow, pixi = _live()
    runs = [step["run"].strip() for step in workflow["jobs"]["scripts-suite"]["steps"] if "run" in step]
    assert "pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test" in runs
    assert ("pyforge-doctor-aggregate-scripts-test", "pyforge-doctor") in _preflight_legs(pixi)


def test_a_step_with_no_leg_is_named() -> None:
    """Mutation: drop the leg and the step is reported, by task and environment."""
    workflow, pixi = _live()
    deps = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]["depends-on"]
    pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]["depends-on"] = [
        dep for dep in deps if not (isinstance(dep, dict) and dep["task"] == "pyforge-doctor-aggregate-scripts-test")
    ]
    problems = unmirrored_steps(workflow, pixi)
    assert len(problems) == 1
    assert "'pyforge-doctor-aggregate-scripts-test' in 'pyforge-doctor'" in problems[0]


def test_a_step_mirroring_a_bare_string_leg_is_not_reported() -> None:
    """Review 1: a bare-string leg (``docs-map-render-test``) runs in ``pyforge-guild``, so a step running it there
    is mirrored, not a false positive."""
    workflow, pixi = _live()
    workflow["jobs"]["scripts-suite"]["steps"].append(
        {"name": "bare", "run": "pixi run --frozen -e pyforge-guild docs-map-render-test"}
    )
    assert unmirrored_steps(workflow, pixi) == []


def test_a_step_that_is_not_a_named_task_is_named() -> None:
    """A raw command (the shape 38.5 shipped) cannot be mirrored, so it is reported."""
    workflow, pixi = _live()
    workflow["jobs"]["scripts-suite"]["steps"].append(
        {"name": "raw", "run": "pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/x.py -q"}
    )
    problems = unmirrored_steps(workflow, pixi)
    assert len(problems) == 1
    assert problems[0].startswith("scripts-suite step 'raw'")
