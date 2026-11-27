"""Stories 58.1 and 59.1 (spec-pyforge-steward:CAP-175): herald's suite runs under pytest-xdist, and its site builds
run side by side without seeing each other's files.

Every Astro build rewrites ``public/`` and Astro's caches under the ``docs-site/`` it runs in. Story 58.1 kept every
build in one xdist worker, in the one real ``docs-site/``. Since Story 59.1 each test process builds in its own copy
(``pages_astro.build_site_dir``), and ``tests/conftest.py`` keeps on one worker only the tests of a builder module that
share a module-scoped fixture, so that fixture builds once. This module holds the rules: nothing starts Astro without
the build helper, every build runs in the process's copy, a copy writes nothing of the real tree, and the conftest
groups exactly the tests that share a module fixture of a module that builds.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import tempfile
from pathlib import Path

import pages_astro
import pytest

# Story 59.1: this module imports the build helper, which reads the repository's docs-site/ and hands its root to the
# build, so it runs in the live-tree half, beside the modules whose builds it governs (steward Story 124.2).
pytestmark = pytest.mark.live_tree

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


def _subprocess_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        owner = func.value.id if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else ""
        if owner == "subprocess":
            calls.append(node)
    return calls


def _argv_strings(call: ast.Call) -> list[str]:
    """The string constants a ``subprocess`` call hands over as a literal argument list."""
    found: list[str] = []
    for arg in call.args[:1]:
        if isinstance(arg, ast.List | ast.Tuple):
            found.extend(e.value for e in arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str))
    return found


def _is_astro_build(call: ast.Call) -> bool:
    argv = _argv_strings(call)
    return "build" in argv and "--outDir" in argv


def _cwd_is_the_copy(call: ast.Call) -> bool:
    for keyword in call.keywords:
        if keyword.arg == "cwd" and isinstance(keyword.value, ast.Call):
            func = keyword.value.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            return name == "build_site_dir"
    return False


def test_the_build_helper_is_the_module_that_runs_astro() -> None:
    source = BUILD_HELPER.read_text(encoding="utf-8")
    assert "def astro_build(" in source and "cwd=build_site_dir()" in source


def test_no_test_module_starts_a_build_without_the_helper() -> None:
    """A module that ran Astro or a node package runner itself, without naming the helper, would build in the real
    tree, beside another build."""
    conftest = _conftest()
    offenders = []
    for path in _test_modules():
        if conftest.module_builds_the_site(str(path)):
            continue
        argv = [a for call in _subprocess_calls(path) for a in _argv_strings(call)]
        if any(a in _BUILD_COMMANDS or _STARTS_A_BUILD.search(a) for a in argv):
            offenders.append(str(path.relative_to(TESTS)))
    assert not offenders, f"these modules start a build without tests/meta/pages_astro.py: {offenders}"


def test_every_astro_build_runs_in_the_process_s_copy() -> None:
    """Story 59.1: each ``astro build`` a test module or the helper starts has the process's copy as its working
    directory, never the real ``docs-site/``. Non-vacuous: the helper and the agent-surface module each start one."""
    builders = {}
    for path in [BUILD_HELPER, *_test_modules()]:
        calls = [call for call in _subprocess_calls(path) if _is_astro_build(call)]
        if calls:
            builders[path.name] = all(_cwd_is_the_copy(call) for call in calls)
    assert {"pages_astro.py", "test_agent_surface_and_changes.py"} <= set(builders)
    assert [name for name, in_copy in builders.items() if not in_copy] == []


#: The site directory's name, read from the helper rather than written out (a fixture tree below uses it).
SITE = pages_astro.DOCS_SITE.name


def _fake_repo(root: Path) -> Path:
    """A repository shaped as the real one is around its site: two entries beside it, and in it sources, an install,
    and what a build writes."""
    for rel in (
        "notes/a.md",
        "top.toml",
        f"{SITE}/src/x.ts",
        f"{SITE}/package.json",
        f"{SITE}/public/old.html",
        f"{SITE}/build/site/index.html",
        f"{SITE}/.astro/data-store.json",
        f"{SITE}/node_modules/astro/bin/astro.mjs",
        f"{SITE}/node_modules/.astro/cache",
        f"{SITE}/node_modules/.vite/deps",
        f"{SITE}/node_modules/.bin/astro",
    ):
        pages_astro.write(root / rel, "x")
    return root


def test_a_build_tree_links_the_repository_and_copies_the_site(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path / "repo")
    tree = pages_astro.make_build_tree(tmp_path / "copy", repo=repo)

    assert (tree / "notes").is_symlink() and (tree / "notes").resolve() == (repo / "notes").resolve()
    assert (tree / "top.toml").is_symlink()
    site = tree / SITE
    assert site.is_dir() and not site.is_symlink()
    assert (site / "src" / "x.ts").is_file() and not (site / "src").is_symlink()
    # What a build or the install writes is not copied, and the build's caches are its own.
    assert not (site / "public").exists() and not (site / "build").exists() and not (site / ".astro").exists()
    modules = site / "node_modules"
    assert modules.is_dir() and not modules.is_symlink()
    assert (modules / "astro").is_symlink() and (modules / ".bin").is_symlink()
    assert not (modules / ".astro").exists() and not (modules / ".vite").exists()
    # A write in the copy, as a build makes, leaves the real tree as it was.
    pages_astro.write(site / "public" / "new.html", "y")
    pages_astro.write(modules / ".astro" / "cache", "z")
    assert not (repo / SITE / "public" / "new.html").exists()
    assert (repo / SITE / "node_modules" / ".astro" / "cache").read_text(encoding="utf-8") == "x"


def test_this_process_builds_in_a_copy_of_its_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The copy is made on first use from the repository the helper builds, kept for the process, and placed under
    ``TMPDIR``, never in the tree it copies."""
    repo = _fake_repo(tmp_path / "repo")
    monkeypatch.setattr(pages_astro, "REPO_ROOT", repo)
    monkeypatch.setattr(pages_astro, "_BUILD_TREE", None)
    site = pages_astro.build_site_dir()
    assert site == pages_astro.build_site_dir(), "one copy per process"
    assert site.name == SITE and (site / "src" / "x.ts").is_file()
    assert repo.resolve() not in site.resolve().parents
    assert Path(tempfile.gettempdir()).resolve() in site.resolve().parents
    assert pages_astro.build_astro_bin() == site / "node_modules" / "astro" / "bin" / "astro.mjs"


def test_the_conftest_marks_the_modules_that_name_the_helper() -> None:
    conftest = _conftest()
    names = {p.name for p in _test_modules() if conftest.module_builds_the_site(str(p))}
    assert {"test_one_generator.py", "test_site_shell.py", "test_pages_artifact.py", "test_docs_site_nav.py"} <= names
    # A module that only names the docs-site pixi tasks builds nothing.
    assert "test_preflight_pages_lane.py" not in names
    assert conftest.DOCS_SITE_XDIST_GROUP


def test_a_builder_s_tests_share_a_worker_by_the_module_fixtures_they_use(request: pytest.FixtureRequest) -> None:
    """The hook ran on this session's own collection: a test of a builder module that uses a module fixture of its
    module carries that fixture's group; every other herald test carries none. Non-vacuous: the agent-surface tests
    that use its ``build`` fixture share one group, and some builder tests carry none."""
    conftest = _conftest()
    groups: dict[str, set[str]] = {}
    ungrouped_builders = 0
    for item in request.session.items:
        if TESTS not in Path(str(item.path)).parents:
            continue
        mark = item.get_closest_marker("xdist_group")
        expected = conftest.docs_site_group(item)
        assert (mark.args if mark is not None else None) == ((expected,) if expected else None), item.nodeid
        if expected:
            groups.setdefault(expected, set()).add(item.name)
        elif conftest.module_builds_the_site(str(item.path)):
            ungrouped_builders += 1
    if not any(Path(str(i.path)).name == "test_agent_surface_and_changes.py" for i in request.session.items):
        pytest.skip("the agent-surface module is not in this run")
    assert len(groups.get("docs-site:test_agent_surface_and_changes.py:build", ())) >= 5
    assert ungrouped_builders > 0
