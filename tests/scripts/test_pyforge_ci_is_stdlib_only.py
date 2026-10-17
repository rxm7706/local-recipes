"""``pyforge-ci`` is stdlib-only, and stays so (steward Story 103.3, spec-pyforge-steward CAP-5).

The definition is the comment above ``pyforge-ci = …`` in ``pixi.toml``'s ``[environments]``. This file pins it
three ways:

1. in ``pyforge-ci`` itself, none of the runtime libraries the definition names can be imported (skipped in any
   other environment);
2. from ``pixi.toml``: ``spec-kit`` is in its own feature, not in ``python``; ``pyforge-ci`` does not compose it;
   every other environment that composes ``python`` does; and the ``pyforge-ci`` feature declares exactly its seven
   build, test and upload tools;
3. every ``tests/scripts`` file that guards a library with a module-level ``pytest.importorskip`` (and so skips in
   ``pyforge-ci``) is named by a library task that runs it where the library is declared, and every file those
   tasks name exists. Without this, a guarded file would skip silently forever.

Stdlib + pytest only: this file runs in ``pyforge-ci`` (``pyforge-doctor-scripts-test``).
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_TESTS = REPO_ROOT / "tests" / "scripts"

ENV = "pyforge-ci"
SPEC_KIT_FEATURE = "spec-kit"

#: The import names the definition says no one can import in ``pyforge-ci``: the libraries ``pyforge-doctor``'s
#: run-dependencies, or a ``tests/scripts`` guard, name.
RUNTIME_LIBRARIES = ("yaml", "jsonschema", "ruamel", "mcp", "pydantic", "httpx", "openfeature")

#: What ``[feature.pyforge-ci.dependencies]`` declares: the build, test and upload tools the env exists for.
PYFORGE_CI_TOOLS = frozenset(
    {
        "hatchling",
        "python-build",
        "pytest",
        "pytest-xdist",
        "twine",
        "pixi-build-python",
        "pixi-build-rattler-build",
    }
)

#: The tasks that run guarded ``tests/scripts`` files where their libraries are declared.
LIBRARY_TASKS = ("scripts-lib-test", "pyforge-doctor-aggregate-scripts-test", "docs-gen-test", "docs-map-render-test")

_TEST_FILE = re.compile(r"tests/scripts/(test_[A-Za-z0-9_]+\.py)")


def _manifest() -> dict[str, Any]:
    return tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))


def _features_of(spec: Any) -> list[str]:
    """An ``[environments]`` value's feature list: a bare list, or a table's ``features``."""
    return list(spec if isinstance(spec, list) else spec.get("features", []))


# ---------------------------------------------------------------------------
# 1. Nothing the definition names is importable in pyforge-ci
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("PIXI_ENVIRONMENT_NAME") != ENV, reason="asserts what pyforge-ci can import; run there"
)
def test_no_runtime_library_is_importable_in_pyforge_ci() -> None:
    importable = [name for name in RUNTIME_LIBRARIES if importlib.util.find_spec(name) is not None]
    assert importable == [], f"importable in {ENV}, which is stdlib-only: {importable}"


# ---------------------------------------------------------------------------
# 2. The composition
# ---------------------------------------------------------------------------


def composition_problems(manifest: dict[str, Any]) -> list[str]:
    """One problem per way ``pixi.toml``'s composition breaks the definition."""
    problems: list[str] = []
    features = manifest.get("feature", {})
    if SPEC_KIT_FEATURE in features.get("python", {}).get("dependencies", {}):
        problems.append(
            "[feature.python.dependencies] declares spec-kit; it belongs in [feature.spec-kit.dependencies]"
        )
    if SPEC_KIT_FEATURE not in features.get(SPEC_KIT_FEATURE, {}).get("dependencies", {}):
        problems.append("[feature.spec-kit.dependencies] does not declare spec-kit")
    environments = manifest.get("environments", {})
    if SPEC_KIT_FEATURE in _features_of(environments.get(ENV, [])):
        problems.append(f"{ENV} composes the {SPEC_KIT_FEATURE} feature")
    for name, spec in environments.items():
        composed = _features_of(spec)
        if name != ENV and "python" in composed and SPEC_KIT_FEATURE not in composed:
            problems.append(f"{name} composes python but not {SPEC_KIT_FEATURE}")
    declared = set(features.get(ENV, {}).get("dependencies", {}))
    if declared != PYFORGE_CI_TOOLS:
        extra, missing = sorted(declared - PYFORGE_CI_TOOLS), sorted(PYFORGE_CI_TOOLS - declared)
        problems.append(f"[feature.{ENV}.dependencies] declares extra {extra}, misses {missing}")
    return problems


def test_the_composition_keeps_pyforge_ci_stdlib_only() -> None:
    assert composition_problems(_manifest()) == []


def test_spec_kit_back_in_the_python_feature_is_named() -> None:
    manifest = _manifest()
    manifest["feature"]["python"]["dependencies"]["spec-kit"] = ">=1.2.0"
    assert any("[feature.python.dependencies] declares spec-kit" in p for p in composition_problems(manifest))


def test_pyforge_ci_composing_spec_kit_is_named() -> None:
    manifest = _manifest()
    manifest["environments"][ENV]["features"].append(SPEC_KIT_FEATURE)
    assert f"{ENV} composes the {SPEC_KIT_FEATURE} feature" in composition_problems(manifest)


def test_an_environment_composing_python_without_spec_kit_is_named() -> None:
    manifest = _manifest()
    manifest["environments"]["build"] = [f for f in manifest["environments"]["build"] if f != SPEC_KIT_FEATURE]
    assert f"build composes python but not {SPEC_KIT_FEATURE}" in composition_problems(manifest)


def test_a_library_declared_in_the_pyforge_ci_feature_is_named() -> None:
    manifest = _manifest()
    manifest["feature"][ENV]["dependencies"]["ruamel.yaml"] = ">=0.19.1"
    assert any("declares extra ['ruamel.yaml']" in p for p in composition_problems(manifest))


# ---------------------------------------------------------------------------
# 3. Every guarded tests/scripts file runs in a library task
# ---------------------------------------------------------------------------


def _is_importorskip(node: ast.AST) -> str | None:
    """The module a ``pytest.importorskip("<module>")`` call names, else None."""
    if not isinstance(node, ast.Call) or not node.args:
        return None
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "importorskip"):
        return None
    if not (isinstance(func.value, ast.Name) and func.value.id == "pytest"):
        return None
    first = node.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def module_level_library_guards(source: str) -> list[str]:
    """The non-stdlib, non-``pyforge`` modules a file guards with a top-level ``pytest.importorskip``."""
    guarded: list[str] = []
    for stmt in ast.parse(source).body:
        value = stmt.value if isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign)) else None
        module = _is_importorskip(value) if value is not None else None
        if module is None:
            continue
        top = module.split(".")[0]
        if top not in sys.stdlib_module_names and top != "pyforge":
            guarded.append(module)
    return guarded


def library_task_cmds(manifest: dict[str, Any]) -> dict[str, str]:
    """Each library task's ``cmd``."""
    cmds: dict[str, str] = {}
    for feature in manifest.get("feature", {}).values():
        for task, body in feature.get("tasks", {}).items():
            if task in LIBRARY_TASKS:
                cmds[task] = body if isinstance(body, str) else body.get("cmd", "")
    return cmds


def library_task_files(manifest: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, set[str]]:
    """Each library task's ``tests/scripts`` file names, read from its ``cmd`` and from any pytest argument file
    (``@path``) the ``cmd`` names. A missing argument file names no files; ``library_split_problems`` reports it."""
    named: dict[str, set[str]] = {}
    for task, cmd in library_task_cmds(manifest).items():
        files = set(_TEST_FILE.findall(cmd))
        for token in cmd.split():
            args_file = root / token[1:] if token.startswith("@") else None
            if args_file is not None and args_file.is_file():
                files |= set(_TEST_FILE.findall(args_file.read_text(encoding="utf-8")))
        named[task] = files
    return named


def library_split_problems(
    manifest: dict[str, Any], sources: dict[str, str], present: set[str], root: Path = REPO_ROOT
) -> list[str]:
    """One problem per guarded file no library task runs, per missing task or argument file, and per named file that
    is gone."""
    named = library_task_files(manifest, root)
    problems = [f"library task {task} is not declared in pixi.toml" for task in LIBRARY_TASKS if task not in named]
    for task, cmd in sorted(library_task_cmds(manifest).items()):
        problems.extend(
            f"{task} reads the argument file {token[1:]}, which does not exist"
            for token in cmd.split()
            if token.startswith("@") and not (root / token[1:]).is_file()
        )
    covered = set().union(*named.values()) if named else set()
    for name in sorted(sources):
        guards = module_level_library_guards(sources[name])
        if guards and name not in covered:
            problems.append(
                f"tests/scripts/{name} guards {guards} at module level, so it skips in {ENV}, but no library task "
                f"({', '.join(LIBRARY_TASKS)}) runs it -- add it to scripts-lib-test"
            )
    for task, files in sorted(named.items()):
        problems.extend(f"{task} names tests/scripts/{f}, which does not exist" for f in sorted(files - present))
    return problems


def _live_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(SCRIPTS_TESTS.glob("test_*.py"))}


def test_every_guarded_file_runs_in_a_library_task() -> None:
    sources = _live_sources()
    assert library_split_problems(_manifest(), sources, set(sources)) == []


def test_the_live_tree_has_guarded_files_to_check() -> None:
    """The check above is not vacuous: it sees the guarded files, and they are the ones the tasks run."""
    sources = _live_sources()
    guarded = {name for name, text in sources.items() if module_level_library_guards(text)}
    assert "test_deck_facts.py" in guarded
    assert "test_apply_verification_verdicts.py" in guarded
    # test_detectors_doctor_sources.py guards inside a helper, not at module level: its stdlib tests run in pyforge-ci.
    assert "test_detectors_doctor_sources.py" not in guarded
    assert "test_pyforge_ci_is_stdlib_only.py" not in guarded


def test_a_guarded_file_no_task_runs_is_named() -> None:
    sources = _live_sources()
    sources["test_new_yaml_thing.py"] = 'import pytest\n\npytest.importorskip("yaml")\n'
    problems = library_split_problems(_manifest(), sources, set(sources))
    assert len(problems) == 1
    assert problems[0].startswith("tests/scripts/test_new_yaml_thing.py guards ['yaml']")


def test_a_guard_inside_a_function_or_on_a_stdlib_or_pyforge_module_is_not_a_library_guard() -> None:
    source = (
        "import pytest\n"
        'pytest.importorskip("tomllib")\n'
        'pytest.importorskip("pyforge.doctor.sources.chain")\n'
        "def helper():\n"
        '    return pytest.importorskip("yaml")\n'
    )
    assert module_level_library_guards(source) == []
    assert module_level_library_guards('import pytest\nyaml = pytest.importorskip("yaml")\n') == ["yaml"]


def detectors_run_by_a_library_task(found: list[dict[str, Any]]) -> list[str]:
    """``scripts/detectors.py`` maps a detector to the first task whose ``cmd`` contains its file name, and
    ``test_flag_gate_check.py`` contains ``flag_gate_check.py``; so a library task that listed its files inline in
    ``cmd`` would become those detectors' task. One problem per detector the registry maps to a library task."""
    return [
        f"{row['path']} maps to library task {row['task']}; list that task's files in an argument file (`@path`)"
        for row in found
        if row.get("task") in LIBRARY_TASKS
    ]


def _detectors_module():
    scripts = str(REPO_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import detectors  # noqa: PLC0415  (scripts/ has no __init__.py)

    return detectors


def test_no_detector_maps_to_a_library_task() -> None:
    found, _gaps = _detectors_module().discover()
    assert detectors_run_by_a_library_task(found) == []


def test_a_library_task_listing_a_detectors_test_inline_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    detectors = _detectors_module()
    tasks = dict(detectors._pixi_tasks())
    inline = {"scripts-lib-test": "python -m pytest tests/scripts/test_flag_gate_check.py -q"}
    monkeypatch.setattr(detectors, "_pixi_tasks", lambda: {**inline, **tasks, **inline})
    found, _gaps = detectors.discover()
    assert detectors_run_by_a_library_task(found) == [
        "scripts/flag_gate_check.py maps to library task scripts-lib-test; list that task's files in an argument "
        "file (`@path`)"
    ]


def test_a_missing_argument_file_is_named(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["feature"]["guild-tasks"]["tasks"]["scripts-lib-test"]["cmd"] = "python -m pytest @gone.txt -q"
    sources = _live_sources()
    problems = library_split_problems(manifest, sources, set(sources), root=tmp_path)
    assert "scripts-lib-test reads the argument file gone.txt, which does not exist" in problems


def test_a_named_file_that_is_gone_is_named() -> None:
    manifest = copy.deepcopy(_manifest())
    sources = _live_sources()
    present = set(sources) - {"test_deck_facts.py"}
    sources.pop("test_deck_facts.py")
    problems = library_split_problems(manifest, sources, present)
    assert problems == ["scripts-lib-test names tests/scripts/test_deck_facts.py, which does not exist"]
