"""``pyforge-ci`` is stdlib-only, and stays so (steward Story 103.3, spec-pyforge-steward CAP-5).

The definition is the comment above ``pyforge-ci = …`` in ``pixi.toml``'s ``[environments]``. This file pins it
three ways:

1. in ``pyforge-ci`` itself, none of the runtime libraries the definition names can be imported (skipped in any
   other environment);
2. from ``pixi.toml``: ``spec-kit`` is in its own feature, not in ``python``; ``pyforge-ci`` does not compose it;
   every other environment that composes ``python`` does; and the ``pyforge-ci`` feature declares exactly its seven
   build, test and upload tools;
3. every ``tests/scripts`` file that skips in ``pyforge-ci`` for want of a library is named by a library task that
   CI runs (``LIBRARY_TASKS``, each a Detectors ``scripts-suite`` step), and every file those tasks name exists.
   "Skips for want of a library" is a module-level guard on any library (``pytest.importorskip`` at import time, in
   any of its spellings, or a ``pytestmark`` ``skipif``), or a guard inside a test on one of the definition's runtime
   libraries (``importorskip``, ``skipif``, or the ``flag_provider`` / ``flag_states`` openfeature hooks). Without
   this, a guarded file would skip silently forever. Its mirror: where each library task runs, every library its
   files guard imports, so the step cannot pass by skipping.

Stdlib + pytest only: this file runs in ``pyforge-ci`` (``pyforge-doctor-scripts-test``) and, for the mirror, in
``pyforge-guild`` (``scripts-lib-test``).
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

#: The tasks CI runs guarded ``tests/scripts`` files in, each with the environment its Detectors ``scripts-suite``
#: step runs it in. ``docs-gen-test`` and ``docs-map-render-test`` are pr-preflight legs only, so they do not count.
LIBRARY_TASKS = {"scripts-lib-test": "pyforge-guild", "pyforge-doctor-aggregate-scripts-test": "pyforge-doctor"}

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
# 3. Every guarded tests/scripts file runs in a library task, and its libraries import there
# ---------------------------------------------------------------------------

_PYTEST_HOOKS_NEEDING_OPENFEATURE = frozenset({"flag_provider", "flag_states"})
"""``tests/scripts/conftest.py``'s ``flag_provider`` fixture skips its test without ``openfeature``, and
``pyforge.testing_kit.flags.flag_states`` runs a test through that fixture: a file that uses either guards
``openfeature`` inside its tests."""

_SKIP_EXCEPTIONS = frozenset({"ImportError", "ModuleNotFoundError", "Exception", "BaseException"})


def _const_str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


#: The in-repo sources ``tests/scripts/conftest.py`` puts on ``sys.path``, which the definition allows beside the
#: standard library. Every other ``pyforge.*`` package (doctor, scribe, warden, ...) is a library like any other.
_IN_REPO_SOURCES = (("pyforge", "core"), ("pyforge", "testing_kit"))

#: The guards no library task's environment can satisfy, each pinned to its owner's deferred-work row:
#: ``file -> (module, owning project, DW id)``. The definition in ``pixi.toml`` names each one. A guard on any other
#: library, in a file no library task runs, reds this file, and so does a pin that no longer matches a guard.
PINNED_EXCEPTIONS: dict[str, tuple[str, str, str]] = {
    "test_scribe_install_nightly_trigger.py": ("apscheduler", "pyforge-scribe", "DW-scribe-103-3-1"),
    "test_exit_code_domains_are_declared.py": ("pyforge.warden", "pyforge-warden", "DW-warden-103-3-1"),
}


def _library(module: str) -> bool:
    parts = module.split(".")
    if parts[0] in sys.stdlib_module_names or parts == ["pyforge"]:
        return False
    return tuple(parts[:2]) not in _IN_REPO_SOURCES


def _pinned(name: str, module: str) -> bool:
    pin = PINNED_EXCEPTIONS.get(name)
    return pin is not None and (module == pin[0] or module.startswith(pin[0] + "."))


def _without_defs(node: ast.AST, *, into_functions: bool) -> list[ast.AST]:
    """Every node under ``node``. With ``into_functions`` false, a function or lambda body is not entered, so what
    remains is what runs when the module is imported (class bodies and if/try/with/for blocks included)."""
    out: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        out.append(child)
        if not into_functions and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        stack.extend(ast.iter_child_nodes(child))
    return out


class _Guards:
    """How one ``tests/scripts`` file guards its libraries, read from its AST."""

    def __init__(self, source: str) -> None:
        self.tree = ast.parse(source)
        self.pytest_names = {"pytest"}
        self.importorskip_names: set[str] = set()
        self.skip_names: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                self.pytest_names |= {a.asname for a in node.names if a.name == "pytest" and a.asname}
            elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
                self.importorskip_names |= {a.asname or a.name for a in node.names if a.name == "importorskip"}
                self.skip_names |= {a.asname or a.name for a in node.names if a.name == "skip"}
        self.flag_modules = self._try_import_flags()

    @staticmethod
    def _catches_import_error(node: ast.Try) -> bool:
        caught = {
            (h.type.id if isinstance(h.type, ast.Name) else getattr(h.type, "attr", ""))
            for h in node.handlers
            if h.type is not None
        } | ({"BaseException"} if any(h.type is None for h in node.handlers) else set())
        return bool(caught & _SKIP_EXCEPTIONS)

    @staticmethod
    def _try_imports(node: ast.Try) -> tuple[set[str], set[str]]:
        """The library modules a ``try`` body imports, and the names its imports bind."""
        modules: set[str] = set()
        bound: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    modules.add(alias.name)
                    bound.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(stmt, ast.ImportFrom) and stmt.module and stmt.level == 0:
                modules.add(stmt.module)
                bound |= {a.asname or a.name for a in stmt.names}
        return {m for m in modules if _library(m)}, bound

    def _try_import_flags(self) -> dict[str, set[str]]:
        """``try: import x`` blocks that catch the ImportError: each name the block binds (the import itself, or a
        ``_HAS_X = True``-style flag in the body or handler) mapped to the library modules it imports."""
        flags: dict[str, set[str]] = {}
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Try) or not self._catches_import_error(node):
                continue
            modules, bound = self._try_imports(node)
            for stmt in [*node.body, *(s for h in node.handlers for s in h.body)]:
                if isinstance(stmt, ast.Assign):
                    bound |= {t.id for t in stmt.targets if isinstance(t, ast.Name)}
            for name in bound if modules else ():
                flags.setdefault(name, set()).update(modules)
        return flags

    def _is_skip(self, node: ast.AST, *, module_level: bool) -> bool:
        """A ``pytest.skip(...)`` call (or a bare ``skip`` imported from pytest); with ``module_level``, only one that
        passes ``allow_module_level=True``, the form that skips a whole file at import."""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        named = (
            isinstance(func, ast.Attribute)
            and func.attr == "skip"
            and isinstance(func.value, ast.Name)
            and func.value.id in self.pytest_names
        ) or (isinstance(func, ast.Name) and func.id in self.skip_names)
        if not named or not module_level:
            return named
        return any(
            k.arg == "allow_module_level" and isinstance(k.value, ast.Constant) and bool(k.value.value)
            for k in node.keywords
        )

    def _skips_on_import_failure(self, nodes: list[ast.AST], *, module_level: bool) -> set[str]:
        """The library modules whose absence reaches a skip: a ``try: import x`` whose ImportError handler calls
        ``pytest.skip``, or an ``if`` whose condition tests a library (``find_spec`` / ``import_module`` of a string,
        or a ``try: import`` flag) and whose body calls ``pytest.skip``."""
        found: set[str] = set()
        for node in nodes:
            if isinstance(node, ast.Try) and self._catches_import_error(node):
                handlers = [n for h in node.handlers for n in _without_defs(h, into_functions=not module_level)]
                if any(self._is_skip(n, module_level=module_level) for n in handlers):
                    found |= self._try_imports(node)[0]
            elif isinstance(node, ast.If):
                body = [n for s in node.body for n in [s, *_without_defs(s, into_functions=not module_level)]]
                if any(self._is_skip(n, module_level=module_level) for n in body):
                    found |= self._condition_modules(node.test)
        return found

    def _importorskip(self, node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call) or not node.args:
            return None
        func = node.func
        named = (
            isinstance(func, ast.Attribute)
            and func.attr == "importorskip"
            and isinstance(func.value, ast.Name)
            and func.value.id in self.pytest_names
        ) or (isinstance(func, ast.Name) and func.id in self.importorskip_names)
        return _const_str(node.args[0]) if named else None

    def _condition_modules(self, condition: ast.AST) -> set[str]:
        """The library modules a condition tests: a ``find_spec`` / ``import_module`` of a string, or a name a
        ``try: import`` block binds."""
        found: set[str] = set()
        for sub in ast.walk(condition):
            if isinstance(sub, ast.Call) and sub.args:
                callee = sub.func.attr if isinstance(sub.func, ast.Attribute) else getattr(sub.func, "id", "")
                if callee in ("find_spec", "import_module") and (module := _const_str(sub.args[0])):
                    found.add(module)
            elif isinstance(sub, ast.Name):
                found |= self.flag_modules.get(sub.id, set())
        return {m for m in found if _library(m)}

    def _skipif_modules(self, node: ast.AST) -> set[str]:
        """The library modules a ``pytest.mark.skipif(<condition>, ...)`` call's condition tests."""
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "skipif"):
            return set()
        return self._condition_modules(node.args[0]) if node.args else set()

    def module_level(self) -> list[str]:
        """The library modules whose absence skips the whole file: an ``importorskip`` that runs at import (at the
        top level, or inside a module-level ``if`` / ``try`` / ``with`` block or class body; a bare ``importorskip``
        imported from pytest counts), a module-level ``pytestmark`` ``skipif``, and a ``pytest.skip(...,
        allow_module_level=True)`` reached when a library is missing (an ImportError handler, or an ``if`` on a
        ``find_spec``)."""
        at_import = _without_defs(self.tree, into_functions=False)
        guarded: list[str] = sorted(self._skips_on_import_failure(at_import, module_level=True))
        for node in at_import:
            module = self._importorskip(node)
            if module is not None and _library(module):
                guarded.append(module)
        for stmt in self.tree.body:
            targets = (
                stmt.targets
                if isinstance(stmt, ast.Assign)
                else [stmt.target]
                if isinstance(stmt, ast.AnnAssign)
                else []
            )
            if any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets) and stmt.value is not None:
                for node in ast.walk(stmt.value):
                    guarded.extend(sorted(self._skipif_modules(node)))
        return sorted(set(guarded))

    def anywhere(self) -> list[str]:
        """Every library module any guard in the file names, inside a test or not: ``importorskip`` calls, ``skipif``
        marks, a ``pytest.skip`` reached when a library is missing (an ImportError handler, or an ``if`` on a
        ``find_spec``), and ``openfeature`` for a file that uses ``flag_provider`` or ``flag_states``."""
        everything = _without_defs(self.tree, into_functions=True)
        guarded: set[str] = set(self.module_level()) | self._skips_on_import_failure(everything, module_level=False)
        for node in everything:
            module = self._importorskip(node)
            if module is not None and _library(module):
                guarded.add(module)
            guarded |= self._skipif_modules(node)
            name = node.id if isinstance(node, ast.Name) else node.arg if isinstance(node, ast.arg) else None
            if name in _PYTEST_HOOKS_NEEDING_OPENFEATURE:
                guarded.add("openfeature")
        return sorted(guarded)


def module_level_library_guards(source: str) -> list[str]:
    """The library modules (not the standard library, not the in-repo core / testing-kit sources) whose absence skips
    the whole file."""
    return _Guards(source).module_level()


def library_guards_in_tests(source: str) -> list[str]:
    """The library modules the file guards only inside its tests (a module-level guard is not repeated here)."""
    guards = _Guards(source)
    return sorted(set(guards.anywhere()) - set(guards.module_level()))


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
    """One problem per guarded file no library task runs (a guard on any library, at module level or inside a test,
    that ``PINNED_EXCEPTIONS`` does not pin), per missing task or argument file, and per named file that is gone."""
    named = library_task_files(manifest, root)
    problems = [f"library task {task} is not declared in pixi.toml" for task in LIBRARY_TASKS if task not in named]
    for task, cmd in sorted(library_task_cmds(manifest).items()):
        problems.extend(
            f"{task} reads the argument file {token[1:]}, which does not exist"
            for token in cmd.split()
            if token.startswith("@") and not (root / token[1:]).is_file()
        )
    covered = set().union(*named.values()) if named else set()
    tasks = ", ".join(sorted(LIBRARY_TASKS))
    for name in sorted(sources):
        if name in covered:
            continue
        guards = [m for m in module_level_library_guards(sources[name]) if not _pinned(name, m)]
        if guards:
            problems.append(
                f"tests/scripts/{name} guards {guards} at module level, so it skips in {ENV}, but no library task "
                f"({tasks}) runs it -- add it to tests/scripts/scripts-lib-test.txt"
            )
        elif in_tests := [m for m in library_guards_in_tests(sources[name]) if not _pinned(name, m)]:
            problems.append(
                f"tests/scripts/{name} guards {in_tests} inside its tests, so they skip in {ENV}, but no library task "
                f"({tasks}) runs it -- add it to tests/scripts/scripts-lib-test.txt"
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
    assert library_guards_in_tests(sources["test_detectors_doctor_sources.py"]) == [
        "jsonschema",
        "pyforge.doctor.sources.__main__",
        "yaml",
    ]
    assert library_guards_in_tests(sources["test_worktree_sweep.py"]) == ["openfeature"]
    assert library_guards_in_tests(sources["test_bmad_estate_check.py"]) == ["pyforge.scribe"]
    assert "test_pyforge_ci_is_stdlib_only.py" not in guarded


def test_a_guarded_file_no_task_runs_is_named() -> None:
    sources = _live_sources()
    sources["test_new_yaml_thing.py"] = 'import pytest\n\npytest.importorskip("yaml")\n'
    problems = library_split_problems(_manifest(), sources, set(sources))
    assert len(problems) == 1
    assert problems[0].startswith("tests/scripts/test_new_yaml_thing.py guards ['yaml'] at module level")


@pytest.mark.parametrize(
    "source",
    [
        'import pytest\n\ndef test_x():\n    pytest.importorskip("openfeature")\n',
        "def test_x(flag_provider):\n    assert flag_provider\n",
        'import pytest\n\n@pytest.mark.skipif(__import__("importlib").util.find_spec("yaml") is None, reason="x")\n'
        "def test_x():\n    pass\n",
        "import importlib.util\nimport pytest\n\ndef test_x():\n"
        '    if importlib.util.find_spec("yaml") is None:\n        pytest.skip("no yaml")\n',
        "import pytest\n\ndef test_x():\n    try:\n        import jsonschema\n    except ImportError:\n"
        '        pytest.skip("no jsonschema")\n',
        'import pytest\n\ndef test_x():\n    pytest.importorskip("boto3")\n',
        'import pytest\n\ndef test_x():\n    pytest.importorskip("pyforge.warden.verdict")\n',
    ],
    ids=[
        "importorskip-in-a-test",
        "flag-provider-fixture",
        "skipif-on-find-spec",
        "find-spec-then-skip",
        "import-error-then-skip",
        "a-non-runtime-library",
        "a-pyforge-station-package",
    ],
)
def test_a_library_guarded_inside_a_test_no_task_runs_is_named(source: str) -> None:
    sources = _live_sources()
    sources["test_new_in_test_guard.py"] = source
    problems = library_split_problems(_manifest(), sources, set(sources))
    assert len(problems) == 1
    assert problems[0].startswith("tests/scripts/test_new_in_test_guard.py guards [")
    assert "inside its tests" in problems[0]


def test_a_file_named_only_by_a_preflight_only_task_is_not_covered() -> None:
    """``docs-gen-test`` and ``docs-map-render-test`` are pr-preflight legs, not scripts-suite steps: a guarded file
    that only they name would skip in every CI step."""
    manifest = _manifest()
    sources = _live_sources()
    sources["test_docs_new_thing.py"] = 'import pytest\n\npytest.importorskip("yaml")\n'
    docs_gen = manifest["feature"]["guild-tasks"]["tasks"]["docs-gen-test"]
    docs_gen["cmd"] = docs_gen["cmd"].replace(" -q", " tests/scripts/test_docs_new_thing.py -q")
    problems = library_split_problems(manifest, sources, set(sources))
    assert any(p.startswith("tests/scripts/test_docs_new_thing.py guards ['yaml'] at module level") for p in problems)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('import pytest\nif True:\n    pytest.importorskip("yaml")\n', ["yaml"]),
        ('import pytest\ntry:\n    pytest.importorskip("jsonschema")\nfinally:\n    pass\n', ["jsonschema"]),
        ('from pytest import importorskip\nimportorskip("ruamel.yaml")\n', ["ruamel.yaml"]),
        ('import pytest as pt\nyaml = pt.importorskip("yaml")\n', ["yaml"]),
        (
            "import pytest\ntry:\n    import yaml\n    HAVE = True\nexcept ImportError:\n    HAVE = False\n"
            'pytestmark = pytest.mark.skipif(not HAVE, reason="no yaml")\n',
            ["yaml"],
        ),
        (
            "import importlib.util\nimport pytest\n"
            'pytestmark = [pytest.mark.skipif(importlib.util.find_spec("httpx") is None, reason="x")]\n',
            ["httpx"],
        ),
        (
            "import pytest\ntry:\n    import yaml\nexcept ImportError:\n"
            '    pytest.skip("no yaml", allow_module_level=True)\n',
            ["yaml"],
        ),
        (
            "import importlib.util\nfrom pytest import skip\n"
            'if importlib.util.find_spec("ruamel.yaml") is None:\n    skip("x", allow_module_level=True)\n',
            ["ruamel.yaml"],
        ),
    ],
    ids=[
        "in-an-if",
        "in-a-try",
        "from-pytest-import",
        "pytest-alias",
        "pytestmark-try-flag",
        "pytestmark-find-spec",
        "import-error-skip-module",
        "find-spec-skip-module",
    ],
)
def test_module_level_guards_in_every_form_are_seen(source: str, expected: list[str]) -> None:
    assert module_level_library_guards(source) == expected


def test_a_guard_inside_a_function_or_on_a_stdlib_or_in_repo_core_module_is_not_a_module_level_guard() -> None:
    source = (
        "import pytest\n"
        'pytest.importorskip("tomllib")\n'
        'pytest.importorskip("pyforge.core.roster")\n'
        'pytest.importorskip("pyforge.testing_kit.flags")\n'
        "def helper():\n"
        '    return pytest.importorskip("yaml")\n'
    )
    assert module_level_library_guards(source) == []
    assert library_guards_in_tests(source) == ["yaml"]
    # Every other pyforge package is a library: the definition allows only the in-repo core and testing kit.
    assert module_level_library_guards('import pytest\npytest.importorskip("pyforge.doctor.sources.chain")\n') == [
        "pyforge.doctor.sources.chain"
    ]
    assert module_level_library_guards('import pytest\nyaml = pytest.importorskip("yaml")\n') == ["yaml"]


_RUN_STEP = re.compile(r"^[ \t]+(?:-[ \t]+)?run:[ \t]*pixi run --frozen -e (?P<env>\S+) (?P<task>\S+)[ \t]*$", re.M)


def _scripts_suite_steps(text: str) -> set[tuple[str, str]]:
    """``(task, environment)`` for each ``run: pixi run --frozen -e <env> <task>`` step of the Detectors
    ``scripts-suite`` job, read as text (this file stays stdlib-only, so no YAML parser). Only a ``run:`` line counts,
    so a commented-out step reads as absent."""
    job = re.search(r"^  scripts-suite:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n)", text, re.M | re.S)
    body = job.group(1) if job else ""
    return {(m["task"], m["env"]) for m in _RUN_STEP.finditer(body)}


def _detectors_workflow() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "detectors.yml").read_text(encoding="utf-8")


def test_every_library_task_is_a_scripts_suite_step_in_its_environment() -> None:
    steps = _scripts_suite_steps(_detectors_workflow())
    assert {(task, env) for task, env in LIBRARY_TASKS.items()} <= steps, steps


def test_a_commented_out_step_reads_as_absent() -> None:
    text = _detectors_workflow()
    live = "        run: pixi run --frozen -e pyforge-guild scripts-lib-test\n"
    assert live in text
    assert ("scripts-lib-test", "pyforge-guild") not in _scripts_suite_steps(
        text.replace(live, "        # " + live.lstrip())
    )


def test_every_pinned_exception_still_guards_its_library_and_has_its_row() -> None:
    """A pin is honest: its file exists and still guards the pinned library, its owner's ledger carries the row, and
    the definition in ``pixi.toml`` names the row."""
    sources = _live_sources()
    definition = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    problems = []
    for name, (module, project, row) in sorted(PINNED_EXCEPTIONS.items()):
        if name not in sources or not any(_pinned(name, m) for m in _Guards(sources[name]).anywhere()):
            problems.append(f"{name} no longer guards {module}: drop its pin")
        ledger = REPO_ROOT / "_bmad-output" / "projects" / project / "planning-artifacts" / "deferred-work-ledger.md"
        if f"### {row}:" not in (ledger.read_text(encoding="utf-8") if ledger.is_file() else ""):
            problems.append(f"{row} is not a row in {ledger.relative_to(REPO_ROOT)}")
        if row not in definition:
            problems.append(f"the pyforge-ci definition in pixi.toml does not name {row}")
    assert problems == []


def test_an_unpinned_guard_in_a_pinned_file_is_still_named() -> None:
    """A pin covers its one library: another library guarded in the same file still needs a library task."""
    sources = _live_sources()
    sources["test_scribe_install_nightly_trigger.py"] += '\n\ndef test_more():\n    pytest.importorskip("boto3")\n'
    problems = library_split_problems(_manifest(), sources, set(sources))
    assert problems == [
        "tests/scripts/test_scribe_install_nightly_trigger.py guards ['boto3'] inside its tests, so they skip in "
        f"{ENV}, but no library task ({', '.join(sorted(LIBRARY_TASKS))}) runs it -- add it to "
        "tests/scripts/scripts-lib-test.txt"
    ]


@pytest.mark.parametrize("task", sorted(LIBRARY_TASKS))
def test_every_module_a_library_task_file_guards_imports_where_the_task_runs(task: str) -> None:
    """The mirror of test 1: in the environment a library task runs in, every library its files guard imports, so the
    step cannot pass by skipping. scripts-lib-test runs this file in pyforge-guild; the aggregate's half asserts only
    when this file is run in pyforge-doctor (the aggregate task's command is Doctor's and lists its two files)."""
    env = LIBRARY_TASKS[task]
    if os.environ.get("PIXI_ENVIRONMENT_NAME") != env:
        pytest.skip(f"asserts what {env} can import; run there")
    sources = _live_sources()
    missing = []
    for name in sorted(library_task_files(_manifest())[task]):
        for module in _Guards(sources[name]).anywhere():
            if _pinned(name, module):
                continue
            try:
                found = importlib.util.find_spec(module) is not None
            except ModuleNotFoundError:
                found = False
            if not found:
                missing.append(f"{name}: {module}")
    assert missing == [], f"{task} would skip these in {env}: {missing}"


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
