"""Story 106.1 — every environment that runs the ``mypy`` task gets its own cache (live tree, AC5).

Reads the environments from where they are declared: ``pr-preflight-lanes`` in ``pixi.toml``
(a bare ``lint-types`` or ``mypy`` entry runs in the environment ``pr-preflight`` is invoked
from, ``pyforge-guild``; a table entry names its own) and the ``pixi run -e <env>`` steps of
``.github/workflows/lint-types.yml``. For each real ``pyforge-*`` package, the real
``scripts/lint_types.py`` must give every one of those environments a different cache
directory under ``<package>/.mypy_cache/``, a path the root ``.gitignore`` already ignores.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

ROOT = Path(__file__).resolve().parents[6]
SCRIPTS = ROOT / "scripts"
WORKFLOW = ROOT / ".github" / "workflows" / "lint-types.yml"
INVOKING_ENVIRONMENT = "pyforge-guild"  # the pre-push hook runs `pixi run --frozen -e pyforge-guild pr-preflight`
MYPY_TASKS = frozenset({"mypy", "lint-types"})  # `lint-types` depends on `mypy`
_WORKFLOW_STEP = re.compile(r"pixi run (?:--frozen )?-e (?P<env>[a-z0-9-]+) (?P<task>[a-z0-9-]+)\s*$", re.MULTILINE)


def _load_lint_types():
    name = "_lint_types_mypy_cache_meta"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "lint_types.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _preflight_mypy_environments() -> set[str]:
    pixi = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    depends_on = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]["depends-on"]
    envs: set[str] = set()
    for entry in depends_on:
        if isinstance(entry, str) and entry in MYPY_TASKS:
            envs.add(INVOKING_ENVIRONMENT)
        elif isinstance(entry, dict) and entry.get("task") in MYPY_TASKS:
            envs.add(entry.get("environment", INVOKING_ENVIRONMENT))
    return envs


def _workflow_mypy_environments() -> set[str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    return {m["env"] for m in _WORKFLOW_STEP.finditer(text) if m["task"] in MYPY_TASKS}


def test_the_preflight_and_ci_run_mypy_in_at_least_two_environments() -> None:
    """Blindness guard: the readers find both mypy lanes, so the next test is not vacuous."""
    assert {"pyforge-guild", "pyforge-foundry-full"} <= _preflight_mypy_environments()
    assert {"pyforge-guild", "pyforge-foundry-full"} <= _workflow_mypy_environments()


def test_every_mypy_environment_gets_its_own_cache_in_every_package() -> None:
    """Mutation: key ``mypy_cache_dir`` on a constant, or drop the environment — this test fails."""
    mod = _load_lint_types()
    environments = sorted(_preflight_mypy_environments() | _workflow_mypy_environments())
    packages = mod.pyforge_packages()
    assert len(packages) >= 10
    for pkg in packages:
        dirs = [mod.mypy_cache_dir(pkg, {"PIXI_ENVIRONMENT_NAME": env}) for env in environments]
        assert len(set(dirs)) == len(environments), f"{pkg.name}: {dirs}"
        for cache in dirs:
            assert cache.parent == pkg / ".mypy_cache", cache


def test_the_root_gitignore_ignores_mypy_cache_at_any_depth() -> None:
    """The per-environment directories sit under ``.mypy_cache/``, ignored by an unanchored rule."""
    rules = [line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]
    assert ".mypy_cache/" in rules
