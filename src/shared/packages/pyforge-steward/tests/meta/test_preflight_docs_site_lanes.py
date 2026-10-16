"""Story 105.1: the preflight's docs-site set is exactly the tasks that share the one ``docs-site/`` tree.

``preflight.DOCS_SITE_TASKS`` names the tasks whose lanes hold the docs-site mutex, so no two of them run at once
(``spec-pyforge-steward`` CAP-159: concurrent lanes share no mutable state). This test derives the same set from what
each task does, and fails when the declared set misses a task or names one more:

* **it runs in the tree:** its ``cwd`` is ``docs-site/`` (``npm ci``, ``npm run build``), or it runs npm or astro
  on a ``docs-site/`` path;
* **it needs the tree's install:** its ``depends-on`` closure reaches a task of the first kind;
* **it imports an npm package:** it runs a ``docs-site/`` script whose import closure (relative imports followed)
  names a package, which node reads from ``docs-site/node_modules``;
* **it spawns npm or astro:** it runs a ``docs-site/`` script whose import closure takes ``node:child_process`` and
  names npm, npx, pnpm or astro as a command (``pages.mts`` runs ``spawnSync('npm', ['run', 'build'])``), so the
  task builds in the tree whether or not it depends on the install (Story 105.1's review);
* **it runs herald's suite,** whose built-site tests call ``astro_build`` (``tests/meta/pages_astro.py``) and so run
  ``astro build`` in ``docs-site/``, which rewrites ``docs-site/public/``.

A script that imports only node builtins, spawns nothing and reads only ``docs/`` (the link and sidebar-order
validators) is in none of these, so its lane keeps its concurrency; the test pins that too, from the scripts' own
source. Steward's station-tests job must fire on every file this test reads (Story 98.1's rule): the last test checks
that ``steward_paths`` in ``.github/workflows/pyforge-station-tests.yml`` covers each docs-site file an import closure
visits, which the AST-derived trigger map cannot see.
"""

from __future__ import annotations

import ast
import copy
import fnmatch
import re
import shlex
import tomllib
from pathlib import Path
from typing import Any

import pytest

from pyforge.steward import preflight

REPO_ROOT = Path(__file__).resolve().parents[6]
PIXI = REPO_ROOT / "pixi.toml"
DOCS_SITE = "docs-site"
HERALD_TESTS = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-herald" / "tests"
NPM_TOOLS = frozenset({"npm", "npx", "pnpm", "astro"})
STATION_TESTS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pyforge-station-tests.yml"
SCRIPT_SUFFIXES = (".ts", ".mts", ".js", ".mjs", ".cjs")

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"^\s*//.*$", re.MULTILINE)
_SPECIFIERS = (
    re.compile(r"""(?:^|[;\s])(?:import|export)(?!\s+type\s)\s[^'";]*?\sfrom\s*['"]([^'"]+)['"]"""),
    re.compile(r"""(?:^|[;\s])import\s*['"]([^'"]+)['"]"""),
    re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)"""),
    re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""),
)
# npm, npx, pnpm or astro as the first word of a quoted or backticked string -- ``spawnSync('npm', [...])``,
# ``execSync('npm run build')``, ``spawnSync(`npx`, ...)`` -- or astro's own bin path.
_SPAWNED_TOOL = re.compile(r"""['"`](?:npm|npx|pnpm|astro)(?:\s[^'"`]*)?['"`]|astro/bin/astro\.mjs""")


def _pixi() -> dict[str, Any]:
    return tomllib.loads(PIXI.read_text(encoding="utf-8"))


def _tasks(pixi: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every task in every feature, a string task as ``{"cmd": ...}``."""
    tasks: dict[str, dict[str, Any]] = {}
    for feature in pixi.get("feature", {}).values():
        for name, task in (feature.get("tasks") or {}).items():
            tasks[name] = {"cmd": task} if isinstance(task, str) else task
    return tasks


def _cmd(task: dict[str, Any]) -> str:
    cmd = task.get("cmd", "")
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def _tokens(task: dict[str, Any]) -> list[str]:
    try:
        return shlex.split(_cmd(task))
    except ValueError:
        return _cmd(task).split()


def _in_tree(path: str) -> bool:
    return path == DOCS_SITE or path.startswith(f"{DOCS_SITE}/")


def _runs_in_the_tree(task: dict[str, Any]) -> bool:
    cwd = task.get("cwd")
    if isinstance(cwd, str) and _in_tree(cwd.removeprefix("./").rstrip("/")):
        return True
    tokens = _tokens(task)
    return bool(NPM_TOOLS.intersection(tokens)) and any(_in_tree(token) for token in tokens)


def _dep_names(task: dict[str, Any]) -> list[str]:
    return [dep if isinstance(dep, str) else dep["task"] for dep in task.get("depends-on", [])]


def _closure(name: str, tasks: dict[str, dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    stack = list(_dep_names(tasks[name]))
    while stack:
        dep = stack.pop()
        if dep in seen or dep not in tasks:
            continue
        seen.add(dep)
        stack.extend(_dep_names(tasks[dep]))
    return seen


def _resolve(importer: Path, specifier: str) -> Path:
    base = (importer.parent / specifier).resolve()
    for candidate in (base, *(base.with_name(base.name + s) for s in SCRIPT_SUFFIXES)):
        if candidate.is_file():
            return candidate
    raise AssertionError(f"{importer.relative_to(REPO_ROOT)} imports {specifier!r}, which resolves to no file")


def _specifiers(path: Path) -> list[str]:
    source = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", path.read_text(encoding="utf-8")))
    return [match for pattern in _SPECIFIERS for match in pattern.findall(source)]


def _script_closure(script: Path) -> tuple[set[Path], set[str]]:
    """The files the script reaches through relative imports (itself included), and every non-relative specifier they
    name (``node:fs``, ``yaml``)."""
    named: set[str] = set()
    seen: set[Path] = set()
    stack = [script.resolve()]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        if path.suffix not in SCRIPT_SUFFIXES:
            continue  # JSON and other data a script imports: no further imports
        for specifier in _specifiers(path):
            if specifier.startswith("."):
                stack.append(_resolve(path, specifier))
            else:
                named.add(specifier)
    return seen, named


def import_closure(script: Path) -> set[str]:
    """Every non-relative specifier the script and the files it imports relatively name (``node:fs``, ``yaml``)."""
    return _script_closure(script)[1]


def closure_files(script: Path) -> set[Path]:
    """The script and every file it reaches through relative imports."""
    return _script_closure(script)[0]


def spawns_tool(script: Path) -> bool:
    """True when the script's import closure takes ``node:child_process`` and names npm, npx, pnpm or astro as a
    command: it builds or installs in the tree from inside node."""
    files, named = _script_closure(script)
    if "node:child_process" not in named:
        return False
    return any(_SPAWNED_TOOL.search(_BLOCK_COMMENT.sub("", f.read_text(encoding="utf-8"))) for f in files)


def _packages(specifiers: set[str]) -> set[str]:
    """The specifiers node resolves from ``node_modules``: neither a builtin (``node:``) nor an absolute path."""
    return {s for s in specifiers if not s.startswith(("node:", "/"))}


def _docs_site_scripts(task: dict[str, Any]) -> list[Path]:
    tokens = _tokens(task)
    if not tokens or tokens[0] != "node":
        return []
    return [REPO_ROOT / t for t in tokens[1:] if _in_tree(t) and t.endswith(SCRIPT_SUFFIXES)]


def _runs_herald_suite(task: dict[str, Any]) -> bool:
    env = task.get("env") or {}
    stations = str(env.get("COVERAGE_GATES_STATIONS", "")).replace(",", " ").split()
    cmd = _cmd(task)
    return "pyforge-herald/tests" in cmd or "--station herald" in cmd or "herald" in stations


def _herald_tests_build_astro() -> list[str]:
    """Herald test modules that call ``astro_build``: the reason its suite is a docs-site lane."""
    callers = []
    for path in sorted(HERALD_TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            func = node.func if isinstance(node, ast.Call) else None
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name == "astro_build":
                callers.append(path.relative_to(REPO_ROOT).as_posix())
                break
    return callers


def derive(pixi: dict[str, Any] | None = None) -> dict[str, set[str]]:
    """The docs-site tasks of ``pixi.toml`` (or of ``pixi``), by the rule that puts each in the set."""
    every = _tasks(_pixi() if pixi is None else pixi)
    tasks = {name: task for name, task in every.items() if "cmd" in task}
    in_tree = {name for name, task in tasks.items() if _runs_in_the_tree(task)}
    needs_install = {name for name in tasks if _closure(name, every) & in_tree}
    imports_package = {
        name
        for name, task in tasks.items()
        if any(_packages(import_closure(script)) for script in _docs_site_scripts(task))
    }
    spawns = {name for name, task in tasks.items() if any(spawns_tool(s) for s in _docs_site_scripts(task))}
    herald = (
        {name for name, task in tasks.items() if _runs_herald_suite(task)} if _herald_tests_build_astro() else set()
    )
    return {
        "in_tree": in_tree,
        "needs_install": needs_install,
        "imports_package": imports_package,
        "spawns_tool": spawns,
        "herald": herald,
    }


def test_the_declared_set_is_exactly_the_derived_set() -> None:
    rules = derive()
    derived = set().union(*rules.values())
    missing = sorted(derived - preflight.DOCS_SITE_TASKS)
    extra = sorted(preflight.DOCS_SITE_TASKS - derived)
    assert not missing, f"docs-site tasks missing from preflight.DOCS_SITE_TASKS: {missing} ({rules})"
    assert not extra, f"preflight.DOCS_SITE_TASKS names tasks no rule derives: {extra} ({rules})"


def test_each_rule_sees_the_tasks_it_exists_for() -> None:
    """A blindness guard: each rule finds at least the tasks it was written for on 2026-10-15."""
    rules = derive()
    assert {"docs-site-install", "docs-site-build"} <= rules["in_tree"]
    assert "docs-site-validate-sidebar" in rules["needs_install"]
    # Either rule may carry the Pages lanes: the install dependency, or the build pages.mts spawns (re-review nit).
    assert {"pages-build", "pages-check"} <= rules["needs_install"] | rules["spawns_tool"]
    assert "docs-site-validate-sidebar" in rules["imports_package"]
    assert {"pages-build", "pages-check"} <= rules["spawns_tool"]
    assert {"pyforge-herald-test", "pyforge-herald-coverage-gate"} <= rules["herald"]


def test_a_build_through_a_docs_site_script_is_seen_without_its_install_dependency() -> None:
    """Story 105.1's review: pages-build matches the spawn rule on its own, so dropping its install dependency keeps it
    (and pages-check) in the derived set, and a new task that runs pages.mts with no depends-on is caught."""
    planted = copy.deepcopy(_pixi())
    site = planted["feature"]["site"]["tasks"]
    site["pages-build"].pop("depends-on", None)
    site["pages-preview"] = "node docs-site/scripts/pages.mts build"
    rules = derive(planted)
    derived = set().union(*rules.values())
    assert "pages-build" in rules["spawns_tool"]
    assert "pages-build" not in rules["needs_install"]
    assert {"pages-build", "pages-check", "pages-preview"} <= derived
    assert derived - preflight.DOCS_SITE_TASKS == {"pages-preview"}  # the equality test above would fail on it


@pytest.mark.parametrize(
    ("source", "spawns"),
    [
        ("import { spawnSync } from 'node:child_process';\nspawnSync('npm', ['run', 'build']);\n", True),
        ("import { execSync } from 'node:child_process';\nexecSync('npm run build', { cwd: 'docs-site' });\n", True),
        ("import { spawnSync } from 'node:child_process';\nspawnSync(`npm`, ['run', 'build']);\n", True),
        ('import cp from "node:child_process";\ncp.execFileSync("astro", ["build"]);\n', True),
        (
            "import { spawnSync } from 'node:child_process';\nspawnSync('node', ['docs-site/node_modules/astro/bin/astro.mjs']);\n",
            True,
        ),
        ("import { spawnSync } from 'node:child_process';\nspawnSync('git', ['status']);\n", False),
        (
            "import { spawnSync } from 'node:child_process';\n// npm run build happens elsewhere\nspawnSync('git', ['log']);\n",
            False,
        ),
        ("import fs from 'node:fs';\nconst tool = 'npm';\nfs.writeFileSync('x', tool);\n", False),
    ],
    ids=[
        "spawnSync-argv",
        "execSync-string",
        "backtick",
        "execFileSync",
        "astro-bin",
        "git",
        "npm-in-comment",
        "no-child-process",
    ],
)
def test_the_spawn_rule_reads_every_form_a_node_script_runs_a_tool_in(
    tmp_path: Path, source: str, spawns: bool
) -> None:
    """Re-review nit: the tool may be an argv's first entry or the first word of a command string, quoted or
    backticked; a script that imports child_process for something else, or only names npm, does not match."""
    script = tmp_path / "script.mts"
    script.write_text(source, encoding="utf-8")
    assert spawns_tool(script) is spawns


def test_the_import_scan_reads_nav_checks_yaml_import() -> None:
    """The scan is not vacuous: nav-check.mts imports the yaml package (from docs-site/node_modules)."""
    assert "yaml" in _packages(import_closure(REPO_ROOT / DOCS_SITE / "scripts" / "nav-check.mts"))


def test_herald_s_tests_build_astro_in_docs_site() -> None:
    """The herald rule's reason holds: a herald test calls astro_build, and astro_build runs in docs-site/."""
    assert _herald_tests_build_astro()
    helper = (HERALD_TESTS / "meta" / "pages_astro.py").read_text(encoding="utf-8")
    assert 'DOCS_SITE = REPO_ROOT / "docs-site"' in helper
    assert "cwd=DOCS_SITE" in helper


def test_the_two_validators_import_only_node_builtins_and_stay_concurrent() -> None:
    """The link and sidebar-order validators read docs/ with node builtins: no npm package, no install dependency, so
    their lanes are outside the set and run beside the docs-site lanes."""
    tasks = _tasks(_pixi())
    for name in ("docs-site-validate-links", "docs-site-validate-sidebar-order"):
        task = tasks[name]
        scripts = _docs_site_scripts(task)
        assert scripts, name
        for script in scripts:
            specifiers = import_closure(script)
            assert specifiers, (name, script)
            assert all(s.startswith("node:") for s in specifiers), (name, sorted(specifiers))
            assert not spawns_tool(script), (name, script)
        assert not _closure(name, tasks), name
        assert name not in preflight.DOCS_SITE_TASKS


def test_the_real_lane_list_holds_more_than_one_docs_site_lane() -> None:
    """The mutex bites on the shipped lane list: pr-preflight-lanes has several lanes in the set."""
    lanes = preflight.list_preflight_lanes(_pixi(), invoking_env="pyforge-guild")
    in_set = {lane.task for lane in lanes if lane.task in preflight.DOCS_SITE_TASKS}
    assert {
        "docs-site-install",
        "pages-build",
        "pages-check",
        "docs-site-validate-sidebar",
        "pyforge-herald-test",
        "pyforge-herald-coverage-gate",
    } <= in_set
    keys = preflight.lane_mutex_keys(lanes, {})
    assert {lane.task for lane in lanes if preflight.DOCS_SITE_MUTEX_KEY in keys[(lane.task, lane.environment)]} == (
        in_set
    )


def _steward_paths() -> list[str]:
    """``steward_paths`` from the station-tests workflow's ``changes`` step: git pathspecs, quotes stripped."""
    lines = STATION_TESTS_WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "steward_paths=(")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == ")")
    return [line.strip().strip("'\"") for line in lines[start + 1 : end] if line.strip()]


def _covered(path: str, pathspecs: list[str]) -> bool:
    """git's default pathspec match: a leading-directory or exact path, or a glob whose ``*`` crosses ``/``."""
    for spec in pathspecs:
        if any(ch in spec for ch in "*?["):
            if fnmatch.fnmatchcase(path, spec):
                return True
        elif path == spec or path.startswith(f"{spec.rstrip('/')}/"):
            return True
    return False


def test_steward_s_job_fires_on_every_docs_site_file_this_test_reads() -> None:
    """Story 98.1's rule for what this test reads through import resolution: every file an import closure of a
    docs-site task's script visits, and herald's Astro helper, is on steward_paths."""
    pathspecs = _steward_paths()
    assert "src/shared/packages/pyforge-steward" in pathspecs  # the parser read the right array
    read: set[str] = {(HERALD_TESTS / "meta" / "pages_astro.py").relative_to(REPO_ROOT).as_posix()}
    for task in _tasks(_pixi()).values():
        for script in _docs_site_scripts(task):
            read |= {f.relative_to(REPO_ROOT).as_posix() for f in closure_files(script)}
    assert any(path.startswith("docs-site/src/lib/") for path in read)  # a blindness guard: imports were followed
    missing = sorted(path for path in read if not _covered(path, pathspecs))
    assert not missing, f"steward's station-tests job does not fire on files this test reads: {missing}"
