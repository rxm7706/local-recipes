"""Story 58.1 (spec-pyforge-steward:CAP-175): herald's suite runs under pytest-xdist, and no two Astro builds overlap.

Every Astro build runs with ``docs-site/`` as its working directory and rewrites ``docs-site/public`` from scratch, so
the modules that build must share one xdist worker. ``tests/conftest.py`` puts a module in that group when it names the
build helper ``pages_astro``. This module holds the two halves of that rule: nothing starts Astro without the helper,
and the conftest marks exactly the modules that name it.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parents[1]
BUILD_HELPER = TESTS / "meta" / "pages_astro.py"

#: A build started outside the helper: the Astro binary or a node package runner, as an argument a process is given.
_BUILD_COMMANDS = ("astro", "npm", "n" + "px", "pnpm")
_STARTS_A_BUILD = re.compile(r"node_modules/\.bin/astro")


def _conftest():
    spec = importlib.util.spec_from_file_location("herald_tests_conftest_under_test", TESTS / "conftest.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _test_modules() -> list[Path]:
    return sorted(TESTS.rglob("test_*.py"))


def _argv_strings(path: Path) -> list[str]:
    """The string constants a module hands to ``subprocess`` calls as a literal argument list."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        owner = func.value.id if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else ""
        if owner != "subprocess":
            continue
        for arg in node.args[:1]:
            if isinstance(arg, ast.List | ast.Tuple):
                found.extend(e.value for e in arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str))
    return found


def test_the_build_helper_is_the_module_that_runs_astro() -> None:
    source = BUILD_HELPER.read_text(encoding="utf-8")
    assert "def astro_build(" in source and "cwd=DOCS_SITE" in source


def test_no_test_module_starts_a_build_without_the_helper() -> None:
    """A module that ran Astro or a node package runner itself would build outside the group, beside another build."""
    conftest = _conftest()
    offenders = []
    for path in _test_modules():
        if conftest.module_builds_the_site(str(path)):
            continue
        argv = _argv_strings(path)
        if any(a in _BUILD_COMMANDS or _STARTS_A_BUILD.search(a) for a in argv):
            offenders.append(str(path.relative_to(TESTS)))
    assert not offenders, f"these modules start a build without tests/meta/pages_astro.py: {offenders}"


def test_the_conftest_groups_the_modules_that_name_the_helper() -> None:
    conftest = _conftest()
    names = {p.name for p in _test_modules() if conftest.module_builds_the_site(str(p))}
    assert {"test_one_generator.py", "test_site_shell.py", "test_pages_artifact.py", "test_docs_site_nav.py"} <= names
    # A module that only names the docs-site pixi tasks builds nothing and must stay out of the one worker.
    assert "test_preflight_pages_lane.py" not in names
    assert conftest.DOCS_SITE_XDIST_GROUP


def test_every_test_of_a_builder_carries_the_group(request: pytest.FixtureRequest) -> None:
    """The hook ran on this session's own collection: each collected item of a builder module carries the mark, and
    no other herald item does."""
    conftest = _conftest()
    for item in request.session.items:
        if TESTS not in Path(str(item.path)).parents:
            continue
        mark = item.get_closest_marker("xdist_group")
        grouped = mark is not None and mark.args == (conftest.DOCS_SITE_XDIST_GROUP,)
        assert grouped == conftest.module_builds_the_site(str(item.path)), item.nodeid
