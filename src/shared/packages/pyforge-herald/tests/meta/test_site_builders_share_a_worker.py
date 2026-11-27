"""Stories 58.1 and 59.1 (spec-pyforge-steward:CAP-175): herald's suite runs under pytest-xdist, and its site builds
run side by side without seeing each other's files.

Every Astro build rewrites ``public/`` and Astro's caches under the ``docs-site/`` it runs in. Story 58.1 kept every
build in one xdist worker, in the one real ``docs-site/``. Since Story 59.1 each test process builds in its own copy
(``pages_astro.build_site_dir``), and ``tests/conftest.py`` keeps on one worker only the tests of a builder module that
share a module-scoped fixture, so that fixture builds once. This module holds the rules: nothing starts Astro without
the build helper, every build runs in the process's copy, a copy writes nothing of the real tree, the conftest
groups exactly the tests that share a module fixture of a module that builds, and a test in such a group starts no
build of its own (Story 63.1).
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
    # A link inside the site, as ``src/content/docs`` links to the repository's ``docs/``.
    (root / SITE / "src" / "shelf").symlink_to(Path("..") / ".." / "notes")
    return root


#: What a build writes in the tree it runs in. A test reading one of these under the real ``docs-site/`` reads what no
#: test's build writes any more (Story 59.1): in a fresh checkout nothing, on a laptop whatever an old build left.
_BUILD_OUTPUTS = frozenset({"public", "build", ".astro"})


def _reads_a_real_build_output(path: Path) -> list[int]:
    """The lines of ``path`` that join ``DOCS_SITE`` (or the agent-surface module's ``_docs_site()``) with a build
    output's name."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        left, right = node.left, node.right
        real = (
            (isinstance(left, ast.Name) and left.id == "DOCS_SITE")
            or (isinstance(left, ast.Attribute) and left.attr == "DOCS_SITE")
            or (isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "_docs_site")
        )
        if real and isinstance(right, ast.Constant) and right.value in _BUILD_OUTPUTS:
            found.append(node.lineno)
    return found


def test_no_test_reads_a_build_output_of_the_real_tree() -> None:
    """Story 59.1: a test reads what its build wrote in this process's copy (``build_site_dir()``), never the real
    ``docs-site/public``, ``build`` or ``.astro``."""
    offenders = {
        str(path.relative_to(TESTS)): lines
        for path in [BUILD_HELPER, *_test_modules()]
        if (lines := _reads_a_real_build_output(path))
    }
    assert offenders == {}


def test_the_build_output_rule_sees_a_real_read(tmp_path: Path) -> None:
    probe = tmp_path / "test_probe.py"
    probe.write_text("from pages_astro import DOCS_SITE\n\npublic = DOCS_SITE / 'public'\nsrc = DOCS_SITE / 'src'\n")
    assert _reads_a_real_build_output(probe) == [3]


def test_a_build_tree_links_the_repository_and_copies_the_site(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path / "repo")
    tree = pages_astro.make_build_tree(tmp_path / "copy", repo=repo)

    assert (tree / "notes").is_symlink() and (tree / "notes").resolve() == (repo / "notes").resolve()
    assert (tree / "top.toml").is_symlink()
    site = tree / SITE
    assert site.is_dir() and not site.is_symlink()
    assert (site / "src" / "x.ts").is_file() and not (site / "src").is_symlink()
    # A link stays a link, and resolves through the copy's own link to the real entry.
    assert (site / "src" / "shelf").is_symlink() and (site / "src" / "shelf" / "a.md").resolve() == (
        repo / "notes" / "a.md"
    ).resolve()
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
    """The hook ran on this session's own collection. A test of a builder module that uses a module fixture of its
    module carries a group of that module; two such tests that share a fixture carry the same group; every other herald
    test carries none. Checked on what this run selected, which pytest-split may have cut to one shard."""
    conftest = _conftest()
    by_fixture: dict[tuple[str, str], set[str]] = {}
    grouped = ungrouped_builders = 0
    for item in request.session.items:
        if TESTS not in Path(str(item.path)).parents:
            continue
        mark = item.get_closest_marker("xdist_group")
        fixtures = conftest.module_fixtures_of(item) if conftest.module_builds_the_site(str(item.path)) else ()
        if not fixtures:
            assert mark is None, item.nodeid
            ungrouped_builders += conftest.module_builds_the_site(str(item.path))
            continue
        assert mark is not None, item.nodeid
        (group,) = mark.args
        assert group.startswith(f"{conftest.DOCS_SITE_XDIST_GROUP}:{Path(str(item.path)).name}:"), (item.nodeid, group)
        assert set(fixtures) <= set(group.rsplit(":", 1)[1].split("+")), (item.nodeid, group)
        grouped += 1
        for name in fixtures:
            by_fixture.setdefault((str(item.path), name), set()).add(group)
    assert all(len(found) == 1 for found in by_fixture.values()), by_fixture
    if not any(Path(str(i.path)).name == "test_agent_surface_and_changes.py" for i in request.session.items):
        pytest.skip("the agent-surface module is not in this run")
    assert grouped >= 5 and ungrouped_builders > 0


def test_tests_that_share_any_module_fixture_share_one_group() -> None:
    """A test using fixtures ``a`` and ``b`` joins the tests that use only ``a`` and only ``b`` in one group."""
    conftest = _conftest()

    class Fake:
        def __init__(self, nodeid: str, fixtures: tuple[str, ...]) -> None:
            self.nodeid, self.path, self._fixtures = nodeid, BUILD_HELPER.parent / "test_probe.py", fixtures

    items = [
        Fake("a", ("built",)),
        Fake("b", ("built", "marketplace")),
        Fake("c", ("marketplace",)),
        Fake("d", ("other",)),
    ]
    original_builds, original_fixtures = conftest.module_builds_the_site, conftest.module_fixtures_of
    conftest.module_builds_the_site = lambda path: True
    conftest.module_fixtures_of = lambda item: item._fixtures
    try:
        groups = conftest.docs_site_groups(items)
    finally:
        conftest.module_builds_the_site, conftest.module_fixtures_of = original_builds, original_fixtures
    assert groups["a"] == groups["b"] == groups["c"] == "docs-site:test_probe.py:built+marketplace"
    assert groups["d"] == "docs-site:test_probe.py:other"


# --- Herald Story 63.1: a grouped test builds nothing of its own ----------------------------------------------------
#
# A test that takes a module fixture of a builder module runs in that fixture's xdist group, on the worker that built
# it. A build the test starts itself then runs after the group's, on the same worker, and lengthens the group: on CI,
# test_site_shell.py's `shell` group held its fixture's build, a test's own build and two pages-check runs in turn, most
# of its shard's 66 s. A test that builds a site of its own takes no module fixture, so it runs on any free worker.

#: The build helper's entry point; a module function that calls it, directly or through another, builds too.
_BUILD_ENTRY = "astro_build"


def _called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for call in ast.walk(node):
        if isinstance(call, ast.Call):
            func = call.func
            names.add(func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else "")
    return names


def _is_module_fixture(function: ast.FunctionDef) -> bool:
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if name == "fixture" and any(
            keyword.arg == "scope" and isinstance(keyword.value, ast.Constant) and keyword.value.value == "module"
            for keyword in decorator.keywords
        ):
            return True
    return False


def grouped_tests_that_build(source: str) -> list[str]:
    """The tests in ``source`` that take one of its module fixtures and also start a build: a call to the helper's
    ``astro_build``, or to a module function that reaches it."""
    functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    fixtures = {name for name, node in functions.items() if _is_module_fixture(node)}
    builders = {_BUILD_ENTRY}
    grew = True
    while grew:
        grew = False
        for name, node in functions.items():
            if name in builders or name in fixtures or name.startswith("test_"):
                continue
            if _called_names(node) & builders:
                builders.add(name)
                grew = True
    found = []
    for name, node in functions.items():
        if not name.startswith("test_"):
            continue
        takes = {arg.arg for arg in node.args.args} & fixtures
        if takes and _called_names(node) & builders:
            found.append(f"{name} takes {sorted(takes)} and builds")
    return found


def test_no_grouped_test_starts_a_build_of_its_own() -> None:
    conftest = _conftest()
    offenders = {
        path.name: found
        for path in _test_modules()
        if conftest.module_builds_the_site(str(path))
        and (found := grouped_tests_that_build(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}, offenders


def test_the_grouped_build_rule_fires() -> None:
    source = (
        "import pytest\n"
        "from pages_astro import astro_build\n"
        "@pytest.fixture(scope='module')\n"
        "def built(tmp_path_factory):\n"
        "    return astro_build(tmp_path_factory.mktemp('a'))\n"
        "def _rebuild(out):\n"
        "    return astro_build(out)\n"
        "def test_reads(built):\n"
        "    assert built\n"
        "def test_builds_alone(tmp_path):\n"
        "    assert _rebuild(tmp_path)\n"
        "def test_builds_in_the_group(built, tmp_path):\n"
        "    assert built and astro_build(tmp_path)\n"
        "def test_builds_through_a_helper(built, tmp_path):\n"
        "    assert built and _rebuild(tmp_path)\n"
    )
    assert grouped_tests_that_build(source) == [
        "test_builds_in_the_group takes ['built'] and builds",
        "test_builds_through_a_helper takes ['built'] and builds",
    ]
