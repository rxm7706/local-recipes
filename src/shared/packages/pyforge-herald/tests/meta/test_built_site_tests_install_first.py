"""Story 45.1 (a fix under spec-pyforge-herald CAP-61): herald's built-site tests install docs-site first.

The built-site tests (``pages_astro.needs_astro``: ``test_one_generator.py``, ``test_agent_surface_and_changes.py``,
``test_docs_site_nav.py``) build Astro from ``docs-site/node_modules``. Until this story nothing that ran herald's suite
installed it, so on a fresh worktree and on every CI runner the 25 tests skipped and said nothing (steward Story
105.1's residual risk). These tests pin the fix where it can regress:

* herald's suite tasks depend on ``docs-site-install`` in the ``site`` environment, so ``pixi run`` installs first,
  and they set ``HERALD_DOCS_SITE_REQUIRED``, under which a missing install fails a built-site test;
* the coverage-gate task takes no such dependency (CI's coverage leg runs its driver, not the task, so the preflight's
  reader can select the gate's lane without the install's, and that lane would never start);
* CI's herald job runs the task by name with the ``site`` environment set up;
* ``needs_astro`` fails, never skips, when the install is required and missing, and pytest reports that as a failure;
  a build helper a module fixture calls fails first, naming the install rather than node's stack.

The preflight half (a herald-only diff selects the install beside herald's lane) is ``test_preflight_pages_lane.py``'s.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pages_astro
import pytest
import yaml
from pages_astro import DOCS_SITE_REQUIRED_ENV, NOT_INSTALLED, requires_astro

REPO_ROOT = Path(__file__).resolve().parents[6]
META = Path(__file__).resolve().parent
INSTALL = {"task": "docs-site-install", "environment": "site"}
SUITE_TASKS = ("pyforge-herald-test", "pyforge-herald-test-coverage")
STATION_TESTS = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"


def _herald_tasks() -> dict[str, dict]:
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    return pixi["feature"]["pyforge-herald"]["tasks"]


@pytest.mark.parametrize("name", SUITE_TASKS)
def test_each_suite_task_installs_docs_site_first_and_requires_the_install(name: str) -> None:
    task = _herald_tasks()[name]
    assert task["depends-on"] == [INSTALL], name
    assert task["env"][DOCS_SITE_REQUIRED_ENV] == "1", name


def test_the_install_is_npm_ci_in_docs_site() -> None:
    """What the dependency runs: the one install every docs-site task uses (``cwd`` docs-site, ``npm ci``)."""
    pixi = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    install = pixi["feature"]["site"]["tasks"]["docs-site-install"]
    assert install["cmd"] == "npm ci"
    assert install["cwd"] == "docs-site"


def test_the_coverage_gate_takes_no_install_dependency() -> None:
    """CI's coverage leg runs ``scripts/coverage_gates_ci.py``, not this task, so pr-preflight selects the gate's lane on
    a diff that selects nothing else of herald's (``scripts/coverage_gate.py`` alone fires every station's gate). A lane
    whose dependency lane is not in the run never starts, and the run never ends; the suite task carries the install."""
    gate = _herald_tasks()["pyforge-herald-coverage-gate"]
    assert "depends-on" not in gate
    assert DOCS_SITE_REQUIRED_ENV not in gate.get("env", {})


def test_ci_s_herald_job_runs_the_task_with_the_site_environment() -> None:
    job = yaml.safe_load(STATION_TESTS.read_text(encoding="utf-8"))["jobs"]["herald-test"]
    setups = [step for step in job["steps"] if str(step.get("uses", "")).startswith("prefix-dev/setup-pixi@")]
    assert len(setups) == 1
    assert {"pyforge-herald", "site"} <= set(str(setups[0]["with"]["environments"]).split())
    runs = [str(step.get("run", "")).strip() for step in job["steps"]]
    # By task name, so pixi runs the dependency; a bare pytest would skip it.
    assert "pixi run --frozen -e pyforge-herald pyforge-herald-test" in runs


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
