"""Story 107.1 (DW-steward-45-1-1): ``pixi run -e pyforge-guild pr-preflight-lanes`` finds every task it runs.

``pr-preflight-lanes`` is the serial reference for every lane a PR gates on (Story 71.1). Pixi 0.81.0 looks each
``depends-on`` entry up by one rule, read here from ``pixi.toml`` the way pixi reads it:

* a bare entry (``"pages-build"``) is looked up in the environment the run was invoked in (``-e pyforge-guild``), not
  in the environment of the task that names it;
* an entry with an ``environment`` is looked up in that environment;
* an environment holds the tasks of its features (``[environments]``), and the default feature's ``[tasks]`` unless it
  sets ``no-default-feature``;
* pixi walks the graph breadth-first and stops at the first entry it cannot find.

At ``2ca62dbca0`` ``pages-check@site`` named a bare ``pages-build``, which pixi looked up in ``pyforge-guild``, where the
``site`` feature's tasks do not exist: ``pixi run --as-is --dry-run -e pyforge-guild pr-preflight-lanes`` exited 1 with
"could not find the task 'pages-build'". The preflight runner was unaffected, because it gives a bare entry its
dependent's environment (``preflight._resolve_dep``).

The rule was measured against pixi 0.81.0 itself on a scratch copy of the tree, at six states (as committed, then each
``site`` task fixed in turn): every time, the first pair this walk cannot find was the task pixi's dry-run named, and
the walk found every pair exactly when pixi exited 0 (the story spec records the run). No test here runs pixi.
"""

from __future__ import annotations

import copy
import tomllib
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from pyforge.steward import preflight

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
PIXI = REPO_ROOT / "pixi.toml"
ROOT = "pr-preflight-lanes"
INVOKING = "pyforge-guild"
SITE = "site"
DEFAULT_FEATURE = "default"  # pixi's name for the manifest's top-level [tasks] / [dependencies]

Missing = tuple[str, str, str]  # (task, environment, the task@environment that names it)


def _pixi() -> dict[str, Any]:
    return tomllib.loads(PIXI.read_text(encoding="utf-8"))


def environment_features(pixi: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Each environment's features, the default feature last unless ``no-default-feature``; pixi always has a
    ``default`` environment, the default feature alone when ``[environments]`` does not declare one."""
    envs: dict[str, tuple[str, ...]] = {}
    for name, spec in (pixi.get("environments") or {}).items():
        if isinstance(spec, list):
            features, with_default = list(spec), True
        else:
            features, with_default = list(spec.get("features", [])), not spec.get("no-default-feature", False)
        envs[name] = (*features, *((DEFAULT_FEATURE,) if with_default else ()))
    envs.setdefault("default", (DEFAULT_FEATURE,))
    return envs


def _feature_tasks(pixi: dict[str, Any], feature: str) -> dict[str, Any]:
    if feature == DEFAULT_FEATURE:
        return pixi.get("tasks") or {}
    return (pixi.get("feature", {}).get(feature) or {}).get("tasks") or {}


def find_task(pixi: dict[str, Any], envs: dict[str, tuple[str, ...]], task: str, env: str) -> dict[str, Any] | None:
    """The task's definition as ``env`` holds it, or ``None`` when no feature of ``env`` declares it."""
    for feature in envs.get(env, ()):
        tasks = _feature_tasks(pixi, feature)
        if task in tasks:
            found = tasks[task]
            return found if isinstance(found, dict) else {"cmd": found}
    return None


def _entries(definition: dict[str, Any]) -> list[str | dict[str, Any]]:
    deps = definition.get("depends-on", [])
    return [deps] if isinstance(deps, (str, dict)) else list(deps)


def walk(pixi: dict[str, Any], root: str, invoking: str) -> tuple[list[Missing], list[tuple[str, str]]]:
    """``pixi run -e <invoking> <root>``'s graph by pixi's rule: every pair it cannot find, breadth-first (the first is
    the one pixi stops at), and every pair with a ``cmd`` it found, in visiting order."""
    envs = environment_features(pixi)
    missing: list[Missing] = []
    found: list[tuple[str, str]] = []
    seen = {(root, invoking)}
    queue: deque[tuple[str, str, str]] = deque([(root, invoking, "the command line")])
    while queue:
        task, env, named_by = queue.popleft()
        definition = find_task(pixi, envs, task, env)
        if definition is None:
            missing.append((task, env, named_by))
            continue
        if "cmd" in definition:
            found.append((task, env))
        for entry in _entries(definition):
            if isinstance(entry, str):
                key = (entry, invoking)
            else:
                key = (str(entry["task"]), str(entry.get("environment", invoking)))
            if key not in seen:
                seen.add(key)
                queue.append((*key, f"{task}@{env}"))
    return missing, found


def _describe(missing: list[Missing]) -> str:
    return "; ".join(f"{task}@{env} (named by {named_by})" for task, env, named_by in missing)


def _bare_site_entries(pixi: dict[str, Any]) -> dict[str, Any]:
    """The tree as it stood at ``2ca62dbca0``: every ``site`` task's ``depends-on`` entry back to a bare name."""
    old = copy.deepcopy(pixi)
    for definition in old["feature"][SITE]["tasks"].values():
        if isinstance(definition, dict) and "depends-on" in definition:
            definition["depends-on"] = [
                entry if isinstance(entry, str) else entry["task"] for entry in _entries(definition)
            ]
    return old


def test_pr_preflight_lanes_finds_every_task_it_runs_from_the_guild() -> None:
    missing, _found = walk(_pixi(), ROOT, INVOKING)
    assert missing == [], (
        f"`pixi run -e {INVOKING} {ROOT}` cannot find: {_describe(missing)}. Pixi looks a bare depends-on entry up in "
        'the environment the run was invoked in; name the dependency\'s own: { task = "...", environment = "..." }'
    )


def test_the_walk_reaches_every_lane_the_preflight_runs() -> None:
    """A blindness guard, and the runner's graph cross-checked against pixi's: the pairs with a ``cmd`` this walk
    finds are the lanes ``list_preflight_lanes`` builds (pixi's own dry-run listed the same 36, in the runner's
    order). The two agree only while no bare entry in the graph sits under a task of another environment."""
    pixi = _pixi()
    _missing, found = walk(pixi, ROOT, INVOKING)
    lanes = [(lane.task, lane.environment) for lane in preflight.list_preflight_lanes(pixi, invoking_env=INVOKING)]
    assert len(found) >= 30
    assert sorted(found) == sorted(lanes)
    assert any(env == SITE for _task, env in found)


def test_on_the_old_site_shape_the_walk_stops_where_pixi_did() -> None:
    """The rule, pinned to what pixi did at ``2ca62dbca0``: ``-e pyforge-guild pr-preflight-lanes`` stopped at
    ``pages-build``; ``-e site pages-check`` and ``-e site docs-site-validate`` exited 0."""
    old = _bare_site_entries(_pixi())
    missing, _found = walk(old, ROOT, INVOKING)
    assert missing[0] == ("pages-build", INVOKING, "pages-check@site")
    assert missing == [
        ("pages-build", INVOKING, "pages-check@site"),
        ("docs-site-validate-links", INVOKING, "docs-site-validate@site"),
        ("docs-site-validate-sidebar", INVOKING, "docs-site-validate@site"),
    ]
    for task in ("pages-check", "docs-site-validate"):
        assert walk(old, task, SITE)[0] == [], task


def test_every_site_task_names_its_environment_on_its_dependencies() -> None:
    """The fix's own shape: each ``[feature.site.tasks.*]`` depends-on entry is ``{ task, environment = "site" }``."""
    bare = [
        f"{name} -> {entry}"
        for name, definition in _pixi()["feature"][SITE]["tasks"].items()
        if isinstance(definition, dict)
        for entry in _entries(definition)
        if not (isinstance(entry, dict) and entry.get("environment") == SITE)
    ]
    assert bare == []


def test_the_walk_reads_every_task_table_pixi_toml_declares() -> None:
    """The walk reads ``[feature.<f>.tasks]`` and the top-level ``[tasks]``. Pixi also has platform tasks
    (``[feature.<f>.target.<platform>.tasks]``) and the older ``depends_on`` key; ``pixi.toml`` uses neither, and if
    it starts to, teach the walk first."""
    pixi = _pixi()
    targets = [
        f"{name}.target.{platform}"
        for name, feature in [(DEFAULT_FEATURE, pixi), *pixi.get("feature", {}).items()]
        for platform, table in (feature.get("target") or {}).items()
        if "tasks" in table
    ]
    assert targets == []
    old_key = [
        name
        for feature in [pixi, *pixi.get("feature", {}).values()]
        for name, definition in (feature.get("tasks") or {}).items()
        if isinstance(definition, dict) and "depends_on" in definition
    ]
    assert old_key == []


# ---- the rule, on fixtures -------------------------------------------------------------------------------------

_FIXTURE = {
    "tasks": {"top": "echo top"},
    "feature": {
        "g": {"tasks": {"root": {"depends-on": [{"task": "x", "environment": "a"}, "y"]}}},
        "fa": {"tasks": {"x": {"cmd": "x", "depends-on": ["y", {"task": "z", "environment": "b"}]}}},
        "fb": {"tasks": {"y": {"cmd": "y"}, "z": {"cmd": "z", "depends-on": ["top"]}}},
    },
    "environments": {
        "g": {"features": ["g"], "no-default-feature": True},
        "a": {"features": ["fa"], "no-default-feature": True},
        "b": ["fb"],
    },
}


def test_a_bare_entry_is_looked_up_in_the_invoking_environment_not_its_dependents() -> None:
    """``x@a`` names a bare ``y``: pixi looks it up in ``g`` (the invoking environment), not in ``a``, so ``y`` is
    missing twice over -- under ``root@g`` first (breadth-first), which is the one reported."""
    missing, found = walk(_FIXTURE, "root", "g")
    assert missing == [("y", "g", "root@g"), ("top", "g", "z@b")]
    assert found == [("x", "a"), ("z", "b")]


def test_an_environment_holds_the_default_feature_unless_it_opts_out() -> None:
    envs = environment_features(_FIXTURE)
    assert envs == {"g": ("g",), "a": ("fa",), "b": ("fb", DEFAULT_FEATURE), "default": (DEFAULT_FEATURE,)}
    assert find_task(_FIXTURE, envs, "top", "b") == {"cmd": "echo top"}
    assert find_task(_FIXTURE, envs, "top", "a") is None
    assert walk(_FIXTURE, "z", "b") == ([], [("z", "b"), ("top", "b")])


@pytest.mark.parametrize(
    ("entry", "expected"),
    [("y", []), ({"task": "y"}, []), ({"task": "y", "environment": "a"}, [("y", "a", "x@b")])],
)
def test_an_entry_without_an_environment_is_a_bare_entry(entry: str | dict[str, str], expected: list[Missing]) -> None:
    pixi = {
        "feature": {"fx": {"tasks": {"x": {"cmd": "x", "depends-on": [entry]}}}, "fy": {"tasks": {"y": {"cmd": "y"}}}},
        "environments": {"b": ["fx", "fy"], "a": ["fx"]},
    }
    assert walk(pixi, "x", "b")[0] == expected
