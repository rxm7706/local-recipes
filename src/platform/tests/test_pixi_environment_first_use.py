"""Steward Story 117.23: a pixi environment a test runs is installed once, locked.

The first ``pixi run -e <env>`` of a checkout builds the environment's path
packages and reinstalls them. Two such runs at once let one process uninstall a
package while the other runs it. Platform CI's test shard 2 on PR #2409 failed
that way: two xdist workers started ``pixi run -e pyforge-warden`` in the same
millisecond. ``conftest.py``'s ``pyforge_warden_env`` fixture installs the
environment once, under a file lock, and every module that runs it must use the
fixture.
"""

from __future__ import annotations

import re
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_RUNS_ENV = re.compile(r'"pixi",\s*"run",\s*"-e",\s*"([\w-]+)"')
_USES_FIXTURE = 'pytestmark = pytest.mark.usefixtures("pyforge_warden_env")'
#: The environments a fixture installs once, by name.
_FIXTURES = {"pyforge-warden": _USES_FIXTURE}


def environments_run(text: str) -> set[str]:
    """The pixi environments a module's source runs with ``pixi run -e``."""
    return set(_RUNS_ENV.findall(text))


def _modules_running_an_environment() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in sorted(_TESTS.rglob("*.py")):
        if path == Path(__file__).resolve():
            continue
        envs = environments_run(path.read_text(encoding="utf-8"))
        if envs:
            found[str(path.relative_to(_TESTS))] = envs
    return found


def test_the_scan_finds_the_modules_that_run_the_warden_environment() -> None:
    found = _modules_running_an_environment()
    assert {
        "test_deploy_gates_on_promotion_verdict.py",
        "test_golden_path_promotion_closure.py",
        "test_golden_path_promotion_verdict.py",
    } <= set(found)


def test_every_module_that_runs_an_environment_uses_its_install_fixture() -> None:
    missing = []
    for module, envs in _modules_running_an_environment().items():
        text = (_TESTS / module).read_text(encoding="utf-8")
        for env in sorted(envs):
            mark = _FIXTURES.get(env)
            if mark is None:
                missing.append(
                    f"{module}: runs {env}, which no install fixture covers; "
                    "add one to conftest.py"
                )
            elif mark not in text:
                missing.append(f"{module}: runs {env} without {mark}")
    assert not missing, "\n".join(missing)


def test_the_scan_reads_an_argv_split_over_lines() -> None:
    text = '[\n    "pixi",\n    "run",\n    "-e",\n    "pyforge-warden",\n]'
    assert environments_run(text) == {"pyforge-warden"}
    assert environments_run('["pixi", "install", "-e", "pyforge-warden"]') == set()
