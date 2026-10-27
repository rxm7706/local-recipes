"""Story 45.1 (a fix under spec-pyforge-herald CAP-61): herald's built-site tests install docs-site first.

The built-site tests (``pages_astro.needs_astro``: ``test_one_generator.py``, ``test_agent_surface_and_changes.py``,
``test_docs_site_nav.py``) build Astro from ``docs-site/node_modules``. Until this story nothing that ran herald's suite
installed it, so on a fresh worktree and on every CI runner the 25 tests skipped and said nothing (steward Story
105.1's residual risk). These tests pin the fix where it can regress:

* ``pyforge-herald-test`` stays npm-free, and so do ``pyforge-station-tests`` and the SBOM laptop gate, which run it
  from the SBOM alone (fnd:CAP-13; the operator's ruling on the independent review);
* ``pyforge-herald-test-built`` runs ``docs-site-install`` in the ``site`` environment and then that suite;
  ``pyforge-herald-test-coverage`` installs first too, and sets ``HERALD_DOCS_SITE_REQUIRED``;
* the coverage-gate task takes no install dependency (CI's coverage leg runs its driver, not the task, so the
  preflight's reader can select the gate's lane without the install's, and that lane would never start);
* CI's herald job runs ``pyforge-herald-test-built`` with ``HERALD_DOCS_SITE_REQUIRED=1`` and the ``site`` environment
  set up;
* ``needs_astro`` fails, never skips, when the install is required and missing, and pytest reports that as a failure;
  a build helper a module fixture calls fails first, naming the install rather than node's stack.

The preflight half (a herald-only diff runs the install, then herald's lane) is ``test_preflight_pages_lane.py``'s.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pages_astro
import pytest
import yaml
from pages_astro import DOCS_SITE_REQUIRED_ENV, NOT_INSTALLED, requires_astro

REPO_ROOT = Path(__file__).resolve().parents[6]
META = Path(__file__).resolve().parent
INSTALL = {"task": "docs-site-install", "environment": "site"}
SUITE = {"task": "pyforge-herald-test", "environment": "pyforge-herald"}
STATION_TESTS = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"


def _pixi() -> dict[str, Any]:
    return tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))


def _herald_tasks() -> dict[str, dict]:
    return _pixi()["feature"]["pyforge-herald"]["tasks"]


def _closure_touches_site(pixi: dict[str, Any], root: str) -> list[str]:
    """Every task in ``root``'s ``depends-on`` closure that runs in the ``site`` environment or is a ``site`` task."""
    features = {name: feature for name, feature in pixi["feature"].items() if isinstance(feature.get("tasks"), dict)}
    site_tasks = set(pixi["feature"]["site"]["tasks"])
    found: list[str] = []
    seen: set[str] = set()
    stack = [root]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        task = next((f["tasks"][name] for f in features.values() if name in f["tasks"]), None)
        for dep in (task or {}).get("depends-on", []) if isinstance(task, dict) else []:
            dep_name = dep if isinstance(dep, str) else dep["task"]
            if dep_name in site_tasks or (isinstance(dep, dict) and dep.get("environment") == "site"):
                found.append(f"{name} -> {dep_name}")
            stack.append(dep_name)
    return found


def test_the_plain_suite_task_stays_npm_free() -> None:
    task = _herald_tasks()["pyforge-herald-test"]
    assert "depends-on" not in task
    assert DOCS_SITE_REQUIRED_ENV not in task.get("env", {})


@pytest.mark.parametrize("aggregate", ["pyforge-station-tests", "sbom-laptop-gate"])
def test_the_station_suites_and_the_laptop_gate_never_reach_the_site_environment(aggregate: str) -> None:
    """fnd:CAP-13: the laptop gate runs the station suites from the SBOM alone, and ``feature:site`` is won't-do in
    ``docs/foundry/sbom-gaps.md``, so neither aggregate's closure may run a task in ``site`` (npm ci)."""
    assert _closure_touches_site(_pixi(), aggregate) == []


def test_the_closure_check_sees_the_site_environment() -> None:
    """A blindness guard: the same walk finds the install under the built task and the Pages check."""
    assert _closure_touches_site(_pixi(), "pyforge-herald-test-built") == [
        "pyforge-herald-test-built -> docs-site-install"
    ]
    assert _closure_touches_site(_pixi(), "pr-preflight-lanes")


def test_the_built_task_installs_then_runs_the_suite() -> None:
    """Cmd-less, so pixi runs its two dependencies in the order they are declared: the install, then the suite."""
    task = _herald_tasks()["pyforge-herald-test-built"]
    assert "cmd" not in task
    assert task["depends-on"] == [INSTALL, SUITE]


def test_the_coverage_report_installs_first_and_requires_the_install() -> None:
    task = _herald_tasks()["pyforge-herald-test-coverage"]
    assert task["depends-on"] == [INSTALL]
    assert task["env"][DOCS_SITE_REQUIRED_ENV] == "1"


def test_the_install_is_npm_ci_in_docs_site() -> None:
    """What the dependency runs: the one install every docs-site task uses (``cwd`` docs-site, ``npm ci``)."""
    install = _pixi()["feature"]["site"]["tasks"]["docs-site-install"]
    assert install["cmd"] == "npm ci"
    assert install["cwd"] == "docs-site"
    # Ready when a preflight run starts: with a dependency of its own, herald could take the first docs-site turn
    # (45.1 re-review, nit 2) and run before the install.
    assert "depends-on" not in install


def test_the_coverage_gate_takes_no_install_dependency() -> None:
    """CI's coverage step runs ``scripts/coverage_gates_ci.py --report`` by command line inside the herald job, after
    the suite wrote its coverage JSON (steward Story 117.2), so CI never runs the install with the gate. The task
    depends on the plain suite only -- the one that wrote the report, in herald's own environment -- never on
    ``docs-site-install`` or anything in the ``site`` environment: the gate's CI rule is now the herald job's own, so
    the suite is always selected with it and the dependency can no longer strand the lane (steward Story 107.1;
    DW-steward-103-6-1)."""
    pixi = _pixi()
    gate = _herald_tasks()["pyforge-herald-coverage-gate"]
    assert gate.get("depends-on") == [SUITE]
    assert _closure_touches_site(pixi, "pyforge-herald-coverage-gate") == []
    assert DOCS_SITE_REQUIRED_ENV not in gate.get("env", {})


def test_ci_s_herald_job_runs_the_built_task_strictly_with_the_site_environment() -> None:
    job = yaml.safe_load(STATION_TESTS.read_text(encoding="utf-8"))["jobs"]["herald-test"]
    setups = [step for step in job["steps"] if str(step.get("uses", "")).startswith("prefix-dev/setup-pixi@")]
    assert len(setups) == 1
    assert {"pyforge-herald", "site"} <= set(str(setups[0]["with"]["environments"]).split())
    runs = [step for step in job["steps"] if "run" in step and "pyforge-herald-test" in str(step["run"])]
    # By task name, so pixi runs the install first; the variable turns a missing install into failures.
    assert [str(step["run"]).strip() for step in runs] == [
        "pixi run --frozen -e pyforge-herald pyforge-herald-test-built"
    ]
    assert runs[0]["env"][DOCS_SITE_REQUIRED_ENV] == "1"


def _decorated(**state: bool):
    def a_built_site_test(tmp_path: Path) -> None:
        """A stand-in with a fixture argument."""

    return a_built_site_test, requires_astro(**state)(a_built_site_test)


def test_an_installed_tree_runs_the_test_unchanged() -> None:
    original, decorated = _decorated(ready=True, required=True)
    assert decorated is original


def test_a_missing_install_skips_naming_the_command_when_not_required() -> None:
    _, decorated = _decorated(ready=False, required=False)
    (mark,) = decorated.pytestmark
    assert mark.name == "skip"
    assert NOT_INSTALLED in mark.kwargs["reason"]


def test_a_missing_install_fails_when_required() -> None:
    _, decorated = _decorated(ready=False, required=True)
    assert list(inspect.signature(decorated).parameters) == ["tmp_path"]  # pytest still injects the fixtures
    with pytest.raises(pytest.fail.Exception) as failed:
        decorated(tmp_path=Path("."))
    assert DOCS_SITE_REQUIRED_ENV in str(failed.value)
    assert NOT_INSTALLED in str(failed.value)


def test_a_build_helper_fails_naming_the_install_when_astro_cannot_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """A module fixture builds before its tests run, so under a required install its failure is the first one seen:
    ``astro_build`` checks first and names the install (``test_agent_surface_and_changes.py``'s builder does too)."""
    monkeypatch.setattr(pages_astro, "RENDER_READY", False)
    with pytest.raises(pytest.fail.Exception) as failed:
        pages_astro.astro_build(Path("never-built"))
    assert NOT_INSTALLED in str(failed.value)
    assert "docs-site/node_modules/astro/bin/astro.mjs" in str(failed.value)


def test_pytest_reports_a_required_missing_install_as_a_failure(tmp_path: Path) -> None:
    """End to end, in a child pytest: the required case is a red test and the optional case a skip, so a lost
    dependency can never pass as a skip."""
    module = tmp_path / "test_probe.py"
    module.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(META)!r})\n"
        "from pages_astro import requires_astro\n\n\n"
        "@requires_astro(ready=False, required=True)\n"
        "def test_required(tmp_path):\n    pass\n\n\n"
        "@requires_astro(ready=False, required=False)\n"
        "def test_optional(tmp_path):\n    pass\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k not in ("PYTEST_ADDOPTS", DOCS_SITE_REQUIRED_ENV)}
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rfs", "-p", "no:cacheprovider", str(module)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "1 failed, 1 skipped" in done.stdout, done.stdout
    assert f"FAILED test_probe.py::test_required - Failed: {DOCS_SITE_REQUIRED_ENV}=1" in done.stdout, done.stdout
