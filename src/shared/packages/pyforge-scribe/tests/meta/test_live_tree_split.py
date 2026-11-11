"""Story 33.1 -- the suite splits on ``live_tree`` and ``postgres``, and no test skips the branch it names.

spec-pyforge-scribe CAP-31, the oracle clause (the live-tree half is the relay of spec-pyforge-steward:CAP-175). The
guard reads every module under ``tests/`` statically, so it runs in the package half with the package copied alone:

* a test module that resolves the repository root carries ``pytestmark = pytest.mark.live_tree``, and a marked module
  resolves it. A module resolves the root when it walks up ``__file__``'s parents, counts ``parents[n]`` past the
  package (n >= 3), or references a resolver: conftest's ``find_repo_root()`` or any helper module's function that
  reaches one. A test or fixture that requests a fixture reading the host tree resolves it too: ``live_repo_root``,
  ``pg_dsn``, ``apply_changesets``, or any helper fixture that reaches one;
* no module under ``tests/``, helper or test, resolves the root at import: in the module body, a class body, a
  decorator or a default value, unless the resolution sits in a ``try`` that handles its failure. With the package
  copied alone every module must still import, so the package half collects;
* a test that needs the server carries ``postgres``, is ``live_tree`` as well (the server fixture provisions from the
  host's changesets) and sits under no skip: it fails, never skips, when nothing answers on SCRIBE_GRAPH_DSN. It
  needs the server when it requests ``pg_dsn`` or a fixture that reaches it, transitively, or calls ``require_pg_dsn``
  or a helper that does. A fixture whose server param carries ``postgres`` itself (``graph_store_factory``) leaves
  the marks with that param;
* a skip because an extra is installed is never legal, listed or not -- simulate the absence instead with
  ``monkeypatch.setitem(sys.modules, "<module>", None)``;
* every other skip site is on the closed list ``SKIP_SITES`` with its reason, each entry stands for exactly one site,
  and every listed site exists.

Each failure mode is planted below and named by the guard.
"""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest

TESTS = Path(__file__).resolve().parents[1]

#: Fixtures that read the host tree: conftest's ``live_repo_root`` returns it, and the server fixtures provision the
#: database from the host's Liquibase changesets. A helper fixture that reaches one joins them.
ROOT_FIXTURES = frozenset({"live_repo_root", "pg_dsn", "apply_changesets"})
#: Fixtures that need the PostgreSQL server. A fixture that reaches one joins them.
SERVER_FIXTURES = frozenset({"pg_dsn"})
FINDER = "find_repo_root"
SERVER_PROBE = "require_pg_dsn"

_PLANE_TESTS = (
    "test_stale_round_trips_against_live_duckdb",
    "test_read_only_open_never_calls_connect_writer",
    "test_plugin_honors_write_false",
    "test_plugin_write_string_false_is_not_writer",
)
_PLANE_REASON = (
    "the plane store needs duckdb and atlas's DuckDB writer, which -e pyforge-scribe does not carry "
    "(DW-scribe-cutover-2026-11-10-2)"
)
_WIN32_STUB = "win32: the stub claude is a shebang script"
_NO_GIT = "no git binary on PATH: the git-listed skill glob cannot be staged"

#: The closed list: (module under tests/, enclosing function, site) -> why the skip stays. Each entry is one site.
SKIP_SITES: Mapping[tuple[str, str, str], str] = {
    **{
        ("unit/test_graph_store_plane.py", test, f"importorskip({module})"): _PLANE_REASON
        for test in _PLANE_TESTS
        for module in ("duckdb", "pyforge.atlas.duckdb_writer")
    },
    (
        "meta/test_first_portal_slice.py",
        "test_chrome_home_post_renders_cited_recall_results",
        "importorskip(django)",
    ): "the portal render needs django, which -e pyforge-scribe does not carry; a django-scribe lane is requested "
    "from steward-station (DW-scribe-cutover-2026-11-10-2)",
    (
        "meta/test_instruction_surface_parity.py",
        "test_runtime_mode_check_is_silent_without_claude_on_path",
        "mark.skipif",
    ): _WIN32_STUB,
    (
        "meta/test_instruction_surface_parity.py",
        "test_runtime_mode_check_branches_with_a_stub_claude",
        "mark.skipif",
    ): _WIN32_STUB,
    (
        "unit/test_compile.py",
        "test_transcript_surface_unreadable_root_warns_and_contributes_zero_nodes",
        "mark.skipif",
    ): "win32 or root: chmod(0o000) does not deny listing there, so the unreadable root cannot be staged",
    ("unit/test_catalog_bmad_estate.py", "test_read_skills_matches_the_git_tree_not_the_dirty_disk", "mark.skipif"): (
        _NO_GIT
    ),
    ("unit/test_catalog_bmad_estate.py", "test_read_skills_falls_back_to_disk_walk_when_git_fails", "mark.skipif"): (
        _NO_GIT
    ),
}

Func = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Site:
    path: str
    function: str
    kind: str
    line: int

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.path, self.function, self.kind)


def _is_pytest(node: ast.expr, names: frozenset[str]) -> bool:
    return isinstance(node, ast.Name) and node.id in names


def _pytest_names(tree: ast.Module) -> tuple[frozenset[str], dict[str, str]]:
    """The names ``pytest`` is bound to, and ``from pytest import skip as s`` aliases (alias -> name)."""
    modules = {"pytest"}
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.asname or a.name for a in node.names if a.name == "pytest")
        elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
            aliases.update({a.asname or a.name: a.name for a in node.names})
    return frozenset(modules), aliases


def _mark_names(node: ast.AST | None, modules: frozenset[str]) -> set[str]:
    """Every ``pytest.mark.<name>`` under ``node`` (a decorator, a ``pytestmark`` value, a ``marks=`` list)."""
    if node is None:
        return set()
    return {
        sub.attr
        for sub in ast.walk(node)
        if isinstance(sub, ast.Attribute)
        and isinstance(sub.value, ast.Attribute)
        and sub.value.attr == "mark"
        and _is_pytest(sub.value.value, modules)
    }


def _pytestmark(body: list[ast.stmt], modules: frozenset[str]) -> set[str]:
    marks: set[str] = set()
    for stmt in body:
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets):
            marks |= _mark_names(stmt.value, modules)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "pytestmark":
            marks |= _mark_names(stmt.value, modules)
    return marks


def _skip_kind(node: ast.AST, modules: frozenset[str], aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        name = None
        if isinstance(func, ast.Attribute) and _is_pytest(func.value, modules):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = aliases.get(func.id)
        if name == "skip":
            return "skip"
        if name == "importorskip":
            arg = node.args[0] if node.args else None
            target = arg.value if isinstance(arg, ast.Constant) else "?"
            return f"importorskip({target})"
    if (
        isinstance(node, ast.Attribute)
        and node.attr in ("skip", "skipif")
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and _is_pytest(node.value.value, modules)
    ):
        return f"mark.{node.attr}"
    if isinstance(node, ast.Attribute) and node.attr in ("skip", "skipif") and isinstance(node.value, ast.Name):
        if aliases.get(node.value.id) == "mark":
            return f"mark.{node.attr}"
    return None


def _catches_import_error(handlers: list[ast.ExceptHandler]) -> bool:
    for handler in handlers:
        if handler.type is None:
            return True
        names = {n.id for n in ast.walk(handler.type) if isinstance(n, ast.Name)}
        if names & {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}:
            return True
    return False


def _sites(rel: str, tree: ast.Module) -> tuple[list[Site], list[Site]]:
    """Every skip site, and the subset that skips because a module imports (an installed extra)."""
    modules, aliases = _pytest_names(tree)
    sites: list[Site] = []
    installed: list[Site] = []

    def visit(node: ast.AST, owner: str, extra_branch: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
        kind = _skip_kind(node, modules, aliases)
        if kind is not None:
            site = Site(rel, owner, kind, getattr(node, "lineno", 0))
            sites.append(site)
            message = node.args[0] if isinstance(node, ast.Call) and node.args else None
            says_installed = isinstance(message, ast.Constant) and "is installed" in str(message.value)
            if kind == "skip" and (extra_branch or says_installed):
                installed.append(site)
        if (
            isinstance(node, ast.Try)
            and any(isinstance(s, (ast.Import, ast.ImportFrom)) for s in node.body)
            and _catches_import_error(node.handlers)
        ):
            for child in node.body:
                visit(child, owner, extra_branch)
            for handler in node.handlers:
                visit(handler, owner, extra_branch)
            for child in node.orelse:
                visit(child, owner, True)
            for child in node.finalbody:
                visit(child, owner, extra_branch)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, owner, extra_branch)

    visit(tree, "<module>", False)
    return sites, installed


def _file_names(tree: ast.Module) -> set[str]:
    """Names bound to an expression built from ``__file__`` (``here = Path(__file__).resolve()``)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
        if value is None or not any(isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(value)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names.update(t.id for t in targets if isinstance(t, ast.Name))
    return names


def _args(func: Func) -> set[str]:
    return {a.arg for a in (*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs)}


def _at_import(body: list[ast.stmt]) -> Iterator[ast.AST]:
    """Every node that runs when the module imports: the module and class bodies, decorators and default values,
    never the body of a function or a lambda."""
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if not isinstance(node, ast.Lambda):
                stack.extend(node.decorator_list)
            stack.extend(node.args.defaults)
            stack.extend(d for d in node.args.kw_defaults if d is not None)
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def _params(node: ast.AST, modules: frozenset[str]) -> Iterator[tuple[int, set[str]]]:
    """Each ``pytest.param(..., marks=...)`` under ``node``, with the marks it carries."""
    for sub in ast.walk(node):
        if not (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "param"
            and _is_pytest(sub.func.value, modules)
        ):
            continue
        marks: set[str] = set()
        for kw in sub.keywords:
            if kw.arg == "marks":
                marks |= _mark_names(kw.value, modules)
        yield sub.lineno, marks


class Module:
    """One module under ``tests/``, parsed once, with what every check reads from it."""

    def __init__(self, rel: str, source: str) -> None:
        self.rel = rel
        self.tree = ast.parse(source, filename=rel)
        self.modules, self.aliases = _pytest_names(self.tree)
        self.file_names = _file_names(self.tree) | {"__file__"}
        self.parent_of = {child: node for node in ast.walk(self.tree) for child in ast.iter_child_nodes(node)}
        self.functions: dict[str, Func] = {
            stmt.name: stmt for stmt in self.tree.body if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        #: Nodes inside a ``try`` body whose failure a handler takes: they never raise out of the import.
        self.handled = {
            id(sub)
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.Try, ast.TryStar)) and node.handlers
            for stmt in node.body
            for sub in ast.walk(stmt)
        }

    @property
    def is_test(self) -> bool:
        return PurePosixPath(self.rel).name.startswith("test_")

    def is_fixture(self, func: Func) -> bool:
        for dec in func.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "fixture"
                and _is_pytest(target.value, self.modules)
            ):
                return True
            if isinstance(target, ast.Name) and target.id == "fixture":
                return True
        return False

    def requests_fixtures(self, func: Func) -> bool:
        """A test or a fixture: pytest fills its parameters with fixtures (a helper's parameters are its own)."""
        return func.name.startswith("test") or self.is_fixture(func)

    def carries_on_param(self, fixture: Func, mark: str) -> bool:
        """The fixture's own ``params`` carry ``mark`` on a ``pytest.param``: the marks travel with that param."""
        for dec in fixture.decorator_list:
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == "params" and any(mark in marks for _, marks in _params(kw.value, self.modules)):
                        return True
        return False

    def parents_use(self, node: ast.AST) -> str | None:
        """How ``node`` reaches past the package through ``__file__``'s parents (``parents[0..2]`` stay inside)."""
        if not (isinstance(node, ast.Attribute) and node.attr == "parents"):
            return None
        if not any(isinstance(n, ast.Name) and n.id in self.file_names for n in ast.walk(node.value)):
            return None
        parent = self.parent_of.get(node)
        if isinstance(parent, ast.Subscript) and parent.value is node:
            index = parent.slice
            if isinstance(index, ast.Constant) and isinstance(index.value, int) and index.value < 3:
                return None
            return "counts __file__'s parents past the package"
        return "walks up __file__'s parents"

    def how(
        self, nodes: Iterable[ast.AST], names: Mapping[str, str], *, parents: bool = True, raising: bool = False
    ) -> str | None:
        """How ``nodes`` reach the root (``parents``) or one of ``names``; with ``raising``, a handled reach is none."""
        for node in nodes:
            if raising and id(node) in self.handled:
                continue
            found = self.parents_use(node) if parents else None
            if found:
                return found
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in names:
                return names[node.id]
        return None

    def helpers_reaching(self, names: Mapping[str, str], *, parents: bool, raising: bool = False) -> dict[str, str]:
        """``names`` plus this module's top-level helpers (never a fixture) that reach one of them, transitively."""
        found = dict(names)
        pending = {name: func for name, func in self.functions.items() if not self.is_fixture(func)}
        while True:
            hit = {
                name: f"calls {name}()"
                for name, func in pending.items()
                if name not in found and self.how(ast.walk(func), found, parents=parents, raising=raising)
            }
            if not hit:
                return found
            found.update(hit)

    def fixtures_reaching(
        self, base: frozenset[str], reaches: Callable[[Module, Func], bool], mark: str
    ) -> frozenset[str]:
        """``base`` plus this module's fixtures that request one of them or reach it, transitively; a fixture whose
        own param carries ``mark`` leaves the marks with that param."""
        found = set(base)
        fixtures = [f for f in self.functions.values() if self.is_fixture(f) and not self.carries_on_param(f, mark)]
        while True:
            hit = {f.name for f in fixtures if f.name not in found and (_args(f) & found or reaches(self, f))}
            if not hit:
                return frozenset(found)
            found |= hit


def _closure(helpers: list[Module], step: Callable[[Module, dict[str, str]], dict[str, str]]) -> dict[str, str]:
    """Iterate ``step`` over the helper modules until no name joins (a helper may call another module's helper)."""
    found: dict[str, str] = {}
    while True:
        before = len(found)
        for module in helpers:
            found |= step(module, found)
        if len(found) == before:
            return found


def _fixture_closure(
    helpers: list[Module], base: frozenset[str], reaches: Callable[[Module, Func], bool], mark: str
) -> frozenset[str]:
    """``base`` plus every helper fixture that reaches it, across helper modules (a conftest fixture may request
    another conftest's)."""
    found = base
    while True:
        grown = found.union(*(m.fixtures_reaching(found, reaches, mark) for m in helpers))
        if grown == found:
            return found
        found = grown


def _root_resolution(module: Module, resolvers: Mapping[str, str], root_fixtures: frozenset[str]) -> str | None:
    """How the module resolves the repository root, anywhere in it, or None when it never does."""
    for node in ast.walk(module.tree):
        found = module.parents_use(node)
        if found:
            return found
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in resolvers:
            return resolvers[node.id]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and module.requests_fixtures(node):
            fixture = sorted(_args(node) & root_fixtures)
            if fixture:
                return f"takes the {fixture[0]} fixture"
    return None


def _tests(module: Module) -> Iterator[tuple[Func, set[str]]]:
    """Each test function with the marks it carries from its decorators, its class and its module."""
    modules = module.modules

    def walk(body: list[ast.stmt], inherited: set[str]) -> Iterator[tuple[Func, set[str]]]:
        for stmt in body:
            if isinstance(stmt, ast.ClassDef) and stmt.name.startswith("Test"):
                marks = inherited | _pytestmark(stmt.body, modules)
                for dec in stmt.decorator_list:
                    marks |= _mark_names(dec, modules)
                yield from walk(stmt.body, marks)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name.startswith("test"):
                marks = set(inherited)
                for dec in stmt.decorator_list:
                    marks |= _mark_names(dec, modules)
                yield stmt, marks

    yield from walk(module.tree.body, _pytestmark(module.tree.body, modules))


def _postgres_params(tree: ast.Module) -> Iterator[tuple[int, set[str]]]:
    """``pytest.param(..., marks=...)`` entries that carry ``postgres``, with all their marks."""
    modules, _ = _pytest_names(tree)
    for line, marks in _params(tree, modules):
        if "postgres" in marks:
            yield line, marks


def problems(tests: Path, skip_sites: Mapping[tuple[str, str, str], str]) -> list[str]:
    """Every breach of the split under ``tests``, as one named line each."""
    parsed = [
        Module(p.relative_to(tests).as_posix(), p.read_text(encoding="utf-8")) for p in sorted(tests.rglob("*.py"))
    ]
    helpers = [m for m in parsed if not m.is_test]

    finder = {FINDER: f"calls {FINDER}()"}
    resolvers = _closure(helpers, lambda m, found: m.helpers_reaching(finder | found, parents=True))
    resolvers |= finder
    raisers = _closure(helpers, lambda m, found: m.helpers_reaching(finder | found, parents=True, raising=True))
    raisers |= finder
    probe = {SERVER_PROBE: f"calls {SERVER_PROBE}()"}
    probes = _closure(helpers, lambda m, found: m.helpers_reaching(probe | found, parents=False)) | probe
    root_fixtures = _fixture_closure(
        helpers, ROOT_FIXTURES, lambda m, f: m.how(ast.walk(f), resolvers) is not None, "live_tree"
    )
    server_fixtures = _fixture_closure(
        helpers, SERVER_FIXTURES, lambda m, f: m.how(ast.walk(f), probes, parents=False) is not None, "postgres"
    )

    out: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for module in parsed:
        rel, tree = module.rel, module.tree

        at_import = module.how(
            _at_import(tree.body), module.helpers_reaching(raisers, parents=True, raising=True), raising=True
        )
        if at_import:
            out.append(
                f"{rel}: resolves the repository root at import ({at_import}); resolve it inside the tests, so the "
                "package copied alone still collects"
            )

        if module.is_test:
            how = _root_resolution(module, resolvers, root_fixtures)
            marked = "live_tree" in _pytestmark(tree.body, module.modules)
            if how and not marked:
                out.append(f"{rel}: resolves the repository root ({how}) but is not marked live_tree")
            if marked and not how:
                out.append(f"{rel}: is marked live_tree but never resolves the repository root")

        sites, installed = _sites(rel, tree)
        for site in installed:
            out.append(
                f"{rel}:{site.line} {site.function}: skips because an extra is installed; simulate its absence "
                "with monkeypatch.setitem(sys.modules, <module>, None)"
            )
        for site in sites:
            seen.add(site.key)
            if site.key not in skip_sites:
                out.append(f"{rel}:{site.line} {site.function}: skip site {site.kind} is not on the closed list")
        for key, count in sorted(Counter(site.key for site in sites).items()):
            if key in skip_sites and count > 1:
                out.append(f"{rel} {key[1]}: skip site {key[2]} occurs {count} times; a closed-list entry is one site")

        local_probes = module.helpers_reaching(probes, parents=False)
        local_servers = module.fixtures_reaching(
            server_fixtures, lambda m, f: m.how(ast.walk(f), local_probes, parents=False) is not None, "postgres"
        )
        skipped_tests = {site.function for site in sites}
        for func, marks in _tests(module):
            needs_server = bool(_args(func) & local_servers) or bool(
                module.how(ast.walk(func), local_probes, parents=False)
            )
            if needs_server and "postgres" not in marks:
                out.append(f"{rel}:{func.lineno} {func.name}: needs the server but carries no postgres marker")
            if "postgres" in marks:
                if "live_tree" not in marks:
                    out.append(f"{rel}:{func.lineno} {func.name}: is marked postgres but not live_tree")
                if marks & {"skip", "skipif"} or func.name in skipped_tests:
                    out.append(
                        f"{rel}:{func.lineno} {func.name}: a postgres-marked test sits under a skip; "
                        "it must fail, never skip, when the server is absent"
                    )
        for line, marks in _postgres_params(tree):
            if "live_tree" not in marks:
                out.append(f"{rel}:{line}: a postgres param is not marked live_tree")
            if marks & {"skip", "skipif"}:
                out.append(f"{rel}:{line}: a postgres param sits under a skip")
    for key in sorted(set(skip_sites) - seen):
        out.append(f"{key[0]} {key[1]}: listed skip site {key[2]} no longer exists; drop it from the closed list")
    return out


# --- the live suite --------------------------------------------------------------------------------------------


def test_the_suite_splits_on_live_tree_and_postgres_and_skips_only_listed_sites() -> None:
    assert problems(TESTS, SKIP_SITES) == []


def test_every_listed_skip_site_says_why() -> None:
    assert all(reason.strip() for reason in SKIP_SITES.values())


def test_the_server_param_of_graph_store_factory_carries_both_marks() -> None:
    tree = ast.parse((TESTS / "unit" / "conftest.py").read_text(encoding="utf-8"))
    params = list(_postgres_params(tree))
    assert len(params) == 1, params
    assert params[0][1] >= {"live_tree", "postgres"}


# --- the guard proves itself: each failure mode is planted and named --------------------------------------------


def _plant(root: Path, rel: str, source: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


_HEADER = "from pathlib import Path\n\nimport pytest\n\n"
_MARKED = _HEADER + "pytestmark = pytest.mark.live_tree\n\n"
_WALK_UP = "def {name}():\n    for c in Path(__file__).resolve().parents:\n        return c\n\n\n"


@pytest.mark.parametrize(
    ("body", "how"),
    (
        (_WALK_UP.format(name="_root") + "def test_x():\n    assert _root()\n", "walks up __file__'s parents"),
        (f"def test_x():\n    assert Path(__file__).resolve().parents[{6}]\n", "counts"),
        ("def test_x(live_repo_root):\n    assert live_repo_root\n", "takes the live_repo_root fixture"),
        ("def test_x():\n    assert find_repo_root()\n", "calls find_repo_root()"),
    ),
    ids=("walk-up", "parent-count", "repo-root-fixture", "finder"),
)
def test_a_module_that_resolves_the_root_without_the_marker_is_named(tmp_path: Path, body: str, how: str) -> None:
    _plant(tmp_path, "unit/test_planted.py", _HEADER + body)
    found = problems(tmp_path, {})
    assert any(p.startswith("unit/test_planted.py: resolves the repository root") and how in p for p in found), found


@pytest.mark.parametrize(
    ("helper", "body", "how"),
    (
        (_WALK_UP.format(name="repo_root"), "def test_x():\n    assert repo_root()\n", "calls repo_root()"),
        (
            _WALK_UP.format(name="repo_root") + "@pytest.fixture\ndef tree_root():\n    return repo_root()\n",
            "def test_x(tree_root):\n    assert tree_root\n",
            "takes the tree_root fixture",
        ),
    ),
    ids=("helper-function", "helper-fixture"),
)
def test_a_module_that_resolves_the_root_through_a_helper_module_is_named(
    tmp_path: Path, helper: str, body: str, how: str
) -> None:
    _plant(tmp_path, "unit/conftest.py", _HEADER + helper)
    _plant(tmp_path, "unit/test_planted.py", _HEADER + body)
    assert problems(tmp_path, {}) == [
        f"unit/test_planted.py: resolves the repository root ({how}) but is not marked live_tree"
    ]


@pytest.mark.parametrize(
    ("rel", "source", "how"),
    (
        (
            "meta/test_planted.py",
            _MARKED + _WALK_UP.format(name="_repo_root") + "ROOT = _repo_root()\n\n\ndef test_x():\n    assert ROOT\n",
            "calls _repo_root()",
        ),
        (
            "meta/test_planted.py",
            _MARKED + '@pytest.mark.parametrize("p", [find_repo_root()])\ndef test_x(p):\n    assert p\n',
            "calls find_repo_root()",
        ),
        ("unit/helpers.py", _HEADER + f"ROOT = Path(__file__).resolve().parents[{6}]\n", "counts"),
    ),
    ids=("module-level-call", "parametrize-argument", "helper-module"),
)
def test_a_module_that_resolves_the_root_at_import_is_named(tmp_path: Path, rel: str, source: str, how: str) -> None:
    _plant(tmp_path, rel, source)
    found = problems(tmp_path, {})
    assert len(found) == 1 and found[0].startswith(f"{rel}: resolves the repository root at import ("), found
    assert how in found[0], found


def test_a_marked_module_that_never_resolves_the_root_is_named(tmp_path: Path) -> None:
    _plant(tmp_path, "meta/test_planted.py", _MARKED + "def test_x(tmp_path):\n    assert tmp_path\n")
    assert problems(tmp_path, {}) == [
        "meta/test_planted.py: is marked live_tree but never resolves the repository root"
    ]


@pytest.mark.parametrize(
    ("decorators", "body", "kind"),
    (
        ('@pytest.mark.skipif(True, reason="planted")\n', "    assert pg_dsn\n", "mark.skipif"),
        ("", '    pytest.skip("planted")\n', "skip"),
    ),
    ids=("skipif-mark", "skip-call"),
)
def test_a_postgres_marked_test_under_a_skip_is_named(tmp_path: Path, decorators: str, body: str, kind: str) -> None:
    source = _MARKED + f"@pytest.mark.postgres\n{decorators}def test_planted(pg_dsn):\n{body}"
    _plant(tmp_path, "unit/test_planted.py", source)
    listed = {("unit/test_planted.py", "test_planted", kind): "planted, so only the postgres breach is left"}
    found = problems(tmp_path, listed)
    assert len(found) == 1 and "test_planted: a postgres-marked test sits under a skip" in found[0], found


@pytest.mark.parametrize(
    ("conftest", "body"),
    (
        ("", "def test_planted(pg_dsn):\n    assert pg_dsn\n"),
        (
            "@pytest.fixture\ndef store(pg_dsn):\n    return pg_dsn\n",
            "def test_planted(store):\n    assert store\n",
        ),
        (
            "",
            "@pytest.fixture\ndef store(pg_dsn):\n    return pg_dsn\n\n\ndef test_planted(store):\n    assert store\n",
        ),
        (
            "def connect():\n    return require_pg_dsn()\n",
            "def test_planted(live_repo_root):\n    assert connect() and live_repo_root\n",
        ),
    ),
    ids=("server-fixture", "helper-fixture-takes-it", "local-fixture-takes-it", "helper-calls-the-probe"),
)
def test_a_server_test_without_the_postgres_marker_is_named(tmp_path: Path, conftest: str, body: str) -> None:
    if conftest:
        _plant(tmp_path, "unit/conftest.py", _HEADER + conftest)
    _plant(tmp_path, "unit/test_planted.py", _MARKED + body)
    found = problems(tmp_path, {})
    assert len(found) == 1 and "test_planted: needs the server but carries no postgres marker" in found[0], found


def test_a_postgres_param_without_live_tree_is_named(tmp_path: Path) -> None:
    source = _HEADER + '@pytest.fixture(params=[pytest.param("postgres", marks=[pytest.mark.postgres])])\n'
    source += "def factory(request):\n    return request.param\n"
    _plant(tmp_path, "unit/conftest.py", source)
    found = problems(tmp_path, {})
    assert len(found) == 1 and "a postgres param is not marked live_tree" in found[0], found


@pytest.mark.parametrize(
    "body",
    (
        "    try:\n        import planted_extra  # noqa: F401\n    except ImportError:\n        pass\n"
        '    else:\n        pytest.skip("planted_extra present")\n',
        '    pytest.skip("planted_extra is installed in this environment")\n',
    ),
    ids=("try-import-else-skip", "skip-message"),
)
def test_a_skip_on_an_installed_extra_is_named_even_when_listed(tmp_path: Path, body: str) -> None:
    _plant(tmp_path, "unit/test_planted.py", _HEADER + f"def test_planted_unavailable():\n{body}")
    listed = {("unit/test_planted.py", "test_planted_unavailable", "skip"): "listing cannot legalize it"}
    found = problems(tmp_path, listed)
    assert len(found) == 1 and "test_planted_unavailable: skips because an extra is installed" in found[0], found


@pytest.mark.parametrize(
    ("source", "kind"),
    (
        (_HEADER + 'def test_planted():\n    pytest.importorskip("planted_module")\n', "importorskip(planted_module)"),
        (_HEADER + '@pytest.mark.skipif(True, reason="planted")\ndef test_planted():\n    pass\n', "mark.skipif"),
        (_HEADER + '@pytest.mark.skip(reason="planted")\ndef test_planted():\n    pass\n', "mark.skip"),
        ("from pytest import skip\n\n\ndef test_planted():\n    skip('planted')\n", "skip"),
    ),
    ids=("importorskip", "skipif", "skip-mark", "aliased-skip"),
)
def test_a_skip_site_missing_from_the_closed_list_is_named(tmp_path: Path, source: str, kind: str) -> None:
    _plant(tmp_path, "unit/test_planted.py", source)
    found = problems(tmp_path, {})
    assert len(found) == 1 and f"test_planted: skip site {kind} is not on the closed list" in found[0], found
    assert problems(tmp_path, {("unit/test_planted.py", "test_planted", kind): "planted and listed"}) == []


def test_a_second_skip_under_a_listed_entry_is_named(tmp_path: Path) -> None:
    source = _HEADER + '@pytest.mark.skipif(True, reason="a")\n@pytest.mark.skipif(True, reason="b")\n'
    _plant(tmp_path, "unit/test_planted.py", source + "def test_planted():\n    pass\n")
    found = problems(tmp_path, {("unit/test_planted.py", "test_planted", "mark.skipif"): "listed once"})
    assert found == [
        "unit/test_planted.py test_planted: skip site mark.skipif occurs 2 times; a closed-list entry is one site"
    ]


def test_a_listed_skip_site_that_no_longer_exists_is_named(tmp_path: Path) -> None:
    _plant(tmp_path, "unit/test_planted.py", _HEADER + "def test_planted():\n    pass\n")
    found = problems(tmp_path, {("unit/test_planted.py", "test_planted", "mark.skipif"): "stale"})
    assert found == [
        "unit/test_planted.py test_planted: listed skip site mark.skipif no longer exists; drop it from the closed list"
    ]


def test_a_clean_planted_tree_has_no_problem(tmp_path: Path) -> None:
    """The guard's negative control: a package-half module, a marked server module, a module that resolves the root
    lazily, a handled resolution at import, and a factory whose server param carries the marks itself all pass."""
    conftest = _WALK_UP.format(name="find_repo_root") + "def require_pg_dsn():\n    return find_repo_root()\n\n\n"
    conftest += '@pytest.fixture(params=["flat", pytest.param("pg", marks=[pytest.mark.live_tree, '
    conftest += "pytest.mark.postgres])])\ndef factory(request):\n    return require_pg_dsn()\n"
    _plant(tmp_path, "unit/conftest.py", _HEADER + conftest)
    _plant(tmp_path, "unit/test_pkg.py", _HEADER + "def test_x(tmp_path, factory):\n    assert tmp_path and factory\n")
    server = (
        _MARKED
        + "@pytest.mark.postgres\ndef test_server(pg_dsn, live_repo_root):\n    assert pg_dsn and live_repo_root\n"
    )
    _plant(tmp_path, "unit/test_server.py", server)
    within = "PKG = Path(__file__).resolve().parents[2]\n\n\ndef test_x():\n    assert PKG\n"
    _plant(tmp_path, "unit/test_within.py", _HEADER + within)
    lazy = "import functools\n\n\n@functools.cache\n" + _WALK_UP.format(name="_repo_root")
    lazy += (
        "def _rules():\n    try:\n        return [_repo_root()]\n    except AssertionError:\n        return []\n\n\n"
    )
    lazy += (
        'RULES = _rules()\n\n\n@pytest.mark.parametrize("r", RULES)\ndef test_x(r):\n    assert _repo_root() and r\n'
    )
    _plant(tmp_path, "meta/test_lazy.py", _MARKED + lazy)
    assert problems(tmp_path, {}) == []
