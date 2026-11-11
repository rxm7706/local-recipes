"""Story 38.2 (spec-pyforge-mason CAP-7, relaying spec-pyforge-steward:CAP-175): the suite is two halves.

A module under ``tests/unit`` or ``tests/meta`` that derives the repository root reads the tree outside
``src/shared/packages/pyforge-mason/`` and must carry ``pytestmark = pytest.mark.live_tree``, so the package half
(``-m "not slow and not live_tree"``) never reaches past the package and passes from a copy outside any repository.
"Derives the repository root" means, read from the module's syntax tree:

- ``Path(__file__)`` climbed past the package root: ``.parents[N]``, a ``.parent`` chain or ``os.path.dirname``,
  directly or through a variable it was assigned to;
- an upward walk with no fixed end: a ``for`` loop or comprehension over ``<path>.parents``, or a ``while`` loop that
  re-assigns ``p = p.parent``, where the path starts at ``__file__`` or the current directory;
- ``git rev-parse --show-toplevel``.

A marked module must also derive the root inside a function or fixture, never at import: pytest imports a module
before ``-m`` deselects it, so a marked module whose import-time code (module-level statements, class bodies,
decorators, default argument values) derives the root stops collection of the whole package half run from a copy
outside the repository. The second check below reports that case, and also a call made at import to a module-level
function of the same module whose body derives the root, directly or through another such function
(``CONTRACT = _repo_root() / "contract.md"``, or a ``parametrize`` decorator over ``_root() / "docs"``). It does not
follow a helper imported from another module, a method or a call through any other name, so the out-of-tree run stays
authoritative for those.

The out-of-tree run (Story 38.2 AC4) is the real test for any other way of reaching the tree; this module guards the
common derivations so a new reader cannot slip into the package half unmarked, and a marked one cannot break it at
import. It reads only the package's own tests directory, so it runs in the package half itself. ``tests/integration``
is outside both halves (its one outside reader is the ``slow`` delegation-fidelity test).
"""

from __future__ import annotations

import ast
from collections import deque
from collections.abc import Iterator
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parents[1]
HALVES = ("unit", "meta")
_PATH_CONSTRUCTORS = frozenset({"Path", "PurePath", "PosixPath"})
_NO_CLIMB_METHODS = frozenset({"resolve", "absolute", "expanduser"})
_NO_CLIMB_FUNCTIONS = frozenset({"abspath", "realpath", "normpath", "fspath"})

# The six modules Story 38.2 marked: each reads the repository outside the package. The detector must see every one,
# or the guard below is vacuous.
KNOWN_READERS = (
    "meta/test_cfe_import_floor_env_sync.py",
    "meta/test_mason_skills.py",
    "meta/test_persona_consults_cfe.py",
    "meta/test_portal_last_diagnose.py",
    "meta/test_skf_mason_skill.py",
    "unit/test_cfe_rebuild_guard_merges.py",
)


def _is_live_tree_mark(node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        node = node.func
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "live_tree"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def carries_live_tree_mark(tree: ast.Module) -> bool:
    """True when a module-level ``pytestmark`` is, or lists, ``pytest.mark.live_tree``."""
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            targets, value = stmt.targets, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets, value = [stmt.target], stmt.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets):
            continue
        values = value.elts if isinstance(value, (ast.List, ast.Tuple)) else [value]
        if any(_is_live_tree_mark(v) for v in values):
            return True
    return False


def _segments(text: str) -> int:
    """How many levels ``path / text`` descends (``..`` climbs one)."""
    depth = 0
    for part in text.split("/"):
        if part in ("", "."):
            continue
        depth += -1 if part == ".." else 1
    return depth


class _Climb:
    """Heights above the module file: ``Path(__file__)`` is 0, its ``.parent`` 1, ``.parents[N]`` N + 1."""

    def __init__(self) -> None:
        self.names: dict[str, int] = {}
        self.cwd_names: set[str] = set()

    def height(self, node: ast.AST) -> int | None:
        if isinstance(node, ast.Name):
            return 0 if node.id == "__file__" else self.names.get(node.id)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _PATH_CONSTRUCTORS and len(node.args) == 1:
                return self.height(node.args[0])
            if isinstance(func, ast.Attribute) and func.attr in _PATH_CONSTRUCTORS and len(node.args) == 1:
                return self.height(node.args[0])
            if isinstance(func, ast.Attribute) and func.attr in _NO_CLIMB_METHODS:
                return self.height(func.value)
            if isinstance(func, (ast.Name, ast.Attribute)) and len(node.args) == 1:
                name = func.id if isinstance(func, ast.Name) else func.attr
                if name in _NO_CLIMB_FUNCTIONS:
                    return self.height(node.args[0])
            if isinstance(func, ast.Attribute) and func.attr == "dirname" and len(node.args) == 1:
                inner = self.height(node.args[0])
                return None if inner is None else inner + 1
            return None
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            inner = self.height(node.value)
            return None if inner is None else inner + 1
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            inner = self.height(node.value.value)
            index = node.slice
            if inner is None or not (isinstance(index, ast.Constant) and isinstance(index.value, int)):
                return None
            return inner + index.value + 1
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            inner = self.height(node.left)
            right = node.right
            if inner is None or not (isinstance(right, ast.Constant) and isinstance(right.value, str)):
                return None
            return inner - _segments(right.value)
        return None

    def from_cwd(self, node: ast.AST) -> bool:
        """True when ``node`` is the current directory (``Path.cwd()``, ``os.getcwd()``) or a name bound to it."""
        if isinstance(node, ast.Name):
            return node.id in self.cwd_names
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("cwd", "getcwd"):
                return True
            if isinstance(func, ast.Attribute) and func.attr in _NO_CLIMB_METHODS:
                return self.from_cwd(func.value)
            if isinstance(func, (ast.Name, ast.Attribute)) and len(node.args) == 1:
                name = func.id if isinstance(func, ast.Name) else func.attr
                return name in _PATH_CONSTRUCTORS and self.from_cwd(node.args[0])
        return False

    def anchored(self, node: ast.AST) -> bool:
        return self.height(node) is not None or self.from_cwd(node)


def _import_time_nodes(tree: ast.Module) -> Iterator[ast.AST]:
    """Every node Python evaluates when it imports the module, in ``ast.walk`` order.

    Module-level statements and class bodies run at import, and so do a function's decorators and default argument
    values; a function or lambda body does not.
    """
    todo: deque[ast.AST] = deque([tree])
    while todo:
        node = todo.popleft()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if not isinstance(node, ast.Lambda):
                todo.extend(node.decorator_list)
            todo.extend(node.args.defaults)
            todo.extend(d for d in node.args.kw_defaults if d is not None)
            continue
        todo.extend(ast.iter_child_nodes(node))


def root_derivations(source: str, depth: int, *, at_import: bool = False) -> list[str]:
    """Each way ``source`` derives the repository root, as ``line N: <how>``.

    ``depth`` is the module's path length below the package root (``tests/meta/test_x.py`` is 3), so a climb higher
    than ``depth`` levels above the file leaves the package. With ``at_import`` only the code that runs when the module
    is imported is read (see ``_import_time_nodes``), and a call made there to a module-level function of the same
    module whose body derives the root (directly or through another such function) counts as a derivation at import.
    """
    tree = ast.parse(source)
    if not at_import:
        return [how for _, how in _derivations(list(ast.walk(tree)), depth)]
    nodes = list(_import_time_nodes(tree))
    found = [how for _, how in _derivations(nodes, depth)]
    helpers = _deriving_helpers(tree, depth)
    for node in nodes:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in helpers:
            found.append(f"line {node.lineno}: calls {node.func.id}(), which derives the repository root")
    return found


def _deriving_helpers(tree: ast.Module, depth: int) -> set[str]:
    """The module-level functions whose body derives the repository root, directly or by calling another one."""
    functions = {stmt.name: stmt for stmt in tree.body if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))}
    lines = [line for line, _ in _derivations(list(ast.walk(tree)), depth)]
    deriving = {
        name
        for name, fn in functions.items()
        if any(fn.lineno <= line <= (fn.end_lineno or fn.lineno) for line in lines)
    }
    calls = {
        name: {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        for name, fn in functions.items()
    }
    changed = True
    while changed:
        changed = False
        for name, called in calls.items():
            if name not in deriving and called & deriving:
                deriving.add(name)
                changed = True
    return deriving


def _derivations(nodes: list[ast.AST], depth: int) -> list[tuple[int, str]]:
    """``(line, "line N: <how>")`` for each root derivation among ``nodes`` (see ``root_derivations``)."""
    climb = _Climb()
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in climb.names or name in climb.cwd_names:
                continue
            height = climb.height(node.value)
            if height is not None:
                climb.names[name] = height
            elif climb.from_cwd(node.value):
                climb.cwd_names.add(name)

    found: list[tuple[int, str]] = []
    for node in nodes:
        line = getattr(node, "lineno", 0)
        if isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
            climbs = (
                (isinstance(node, ast.Attribute) and node.attr == "parent")
                or isinstance(node, ast.Subscript)
                or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "dirname")
            )
            height = climb.height(node) if climbs else None
            if height is not None and height > depth:
                found.append(
                    (line, f"line {line}: climbs {height} levels above the file, past the package root ({depth})")
                )
        if isinstance(node, (ast.For, ast.comprehension)):
            source_iter = node.iter
            if (
                isinstance(source_iter, ast.Attribute)
                and source_iter.attr == "parents"
                and climb.anchored(source_iter.value)
            ):
                at = getattr(source_iter, "lineno", line)
                found.append((at, f"line {at}: walks upward over .parents"))
        if isinstance(node, ast.While):
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Assign)
                    and isinstance(inner.value, ast.Attribute)
                    and inner.value.attr == "parent"
                    and climb.anchored(inner.value.value)
                ):
                    found.append((inner.lineno, f"line {inner.lineno}: walks upward with .parent in a while loop"))
        if _asks_git_for_the_toplevel(node):
            found.append((line, f"line {line}: asks git for its top-level directory"))
    return found


def _asks_git_for_the_toplevel(node: ast.AST) -> bool:
    """An argv list or a shell string running ``git rev-parse --show-toplevel`` (prose in a docstring is neither)."""
    if isinstance(node, (ast.List, ast.Tuple)):
        words = {e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        return {"rev-parse", "--show-toplevel"} <= words
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        words = node.value.split()
        return words[:2] == ["git", "rev-parse"] and "--show-toplevel" in words
    return False


def _modules(tests_dir: Path) -> Iterator[tuple[str, int, str, bool]]:
    """Each module in the two halves as ``(<half>/<module>, depth below the package root, source, marked)``."""
    package_root = tests_dir.parent
    for half in HALVES:
        for path in sorted((tests_dir / half).rglob("test_*.py")):
            source = path.read_text(encoding="utf-8")
            depth = len(path.relative_to(package_root).parts)
            yield path.relative_to(tests_dir).as_posix(), depth, source, carries_live_tree_mark(ast.parse(source))


def unmarked_readers(tests_dir: Path) -> tuple[list[str], int]:
    """Every module in the two halves that derives the repository root without the ``live_tree`` mark.

    Returns the findings (``<half>/<module>: line N: <how>``) and how many modules were read.
    """
    findings: list[str] = []
    scanned = 0
    for rel, depth, source, marked in _modules(tests_dir):
        scanned += 1
        if not marked:
            findings.extend(f"{rel}: {how}" for how in root_derivations(source, depth))
    return findings, scanned


def import_time_readers(tests_dir: Path) -> tuple[list[str], int]:
    """Every marked module in the two halves whose import-time code derives the repository root.

    Returns the findings (``<half>/<module>: line N: <how>``) and how many marked modules were read.
    """
    findings: list[str] = []
    marked_count = 0
    for rel, depth, source, marked in _modules(tests_dir):
        if marked:
            marked_count += 1
            findings.extend(f"{rel}: {how}" for how in root_derivations(source, depth, at_import=True))
    return findings, marked_count


def test_every_module_that_derives_the_repository_root_is_marked_live_tree() -> None:
    findings, scanned = unmarked_readers(TESTS_DIR)
    assert scanned >= 30, f"the split guard read only {scanned} modules under {TESTS_DIR} -- did the tree move?"
    assert not findings, (
        "these modules read the repository outside the package but are not marked "
        "`pytestmark = pytest.mark.live_tree` (add the mark and the module to Story 38.2's live_tree_modules, "
        "or read a fixture inside the package instead):\n" + "\n".join(findings)
    )


def test_no_marked_module_derives_the_repository_root_at_import() -> None:
    findings, marked = import_time_readers(TESTS_DIR)
    assert marked >= len(KNOWN_READERS), f"the split guard found only {marked} marked modules under {TESTS_DIR}"
    assert not findings, (
        "these live_tree modules derive the repository root when they are imported; pytest imports a module before "
        "`-m` deselects it, so the package half run from a copy outside the repository stops at collection. Move the "
        "derivation into a function or fixture:\n" + "\n".join(findings)
    )


@pytest.mark.parametrize("rel", KNOWN_READERS)
def test_the_detector_sees_each_known_reader(rel: str) -> None:
    path = TESTS_DIR / rel
    source = path.read_text(encoding="utf-8")
    assert carries_live_tree_mark(ast.parse(source)), f"{rel} reads the live tree and must stay marked live_tree"
    depth = len(path.relative_to(TESTS_DIR.parent).parts)
    assert root_derivations(source, depth), f"the detector no longer sees how {rel} derives the repository root"


_PLANTED_READERS = {
    "for-loop over Path(__file__).parents": (
        "from pathlib import Path\n"
        "\n"
        "def _repo_root():\n"
        "    for candidate in Path(__file__).resolve().parents:\n"
        "        if (candidate / 'pixi.toml').is_file():\n"
        "            return candidate\n"
    ),
    "for-loop over a variable's parents": (
        "from pathlib import Path\n"
        "\n"
        "def _repo_root():\n"
        "    here = Path(__file__).resolve()\n"
        "    for candidate in here.parents:\n"
        "        if (candidate / '.claude' / 'skills').is_dir():\n"
        "            return candidate\n"
    ),
    "next() over a comprehension": (
        "from pathlib import Path\n\nROOT = next(p for p in Path(__file__).parents if (p / 'AGENTS.md').is_file())\n"
    ),
    "parents[N] past the package": (
        "from pathlib import Path\n"
        "\n"
        "_GUARD = Path(__file__).resolve().parents[6] / 'scripts' / 'cfe_rebuild_guard_check.py'\n"
    ),
    "parents[N] then into a sibling package": (
        "from pathlib import Path\n"
        "\n"
        "DOCTOR = Path(__file__).resolve().parents[3] / 'pyforge-doctor' / 'pyproject.toml'\n"
    ),
    ".parent chain past the package": (
        "from pathlib import Path\n\nROOT = Path(__file__).resolve().parent.parent.parent.parent\n"
    ),
    "os.path.dirname chain past the package": (
        "import os\n"
        "\n"
        "ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))\n"
    ),
    "while loop climbing from the current directory": (
        "from pathlib import Path\n"
        "\n"
        "def _repo_root():\n"
        "    p = Path.cwd()\n"
        "    while not (p / 'pixi.toml').is_file():\n"
        "        p = p.parent\n"
        "    return p\n"
    ),
    "git asked for its top-level directory (argv)": (
        "import subprocess\n"
        "\n"
        "ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout\n"
    ),
    "git asked for its top-level directory (shell)": (
        "import subprocess\n\nROOT = subprocess.check_output('git rev-parse --show-toplevel', shell=True, text=True)\n"
    ),
}


def _plant(tmp_path: Path, source: str) -> Path:
    tests = tmp_path / "pkg" / "tests"
    for half in HALVES:
        (tests / half).mkdir(parents=True)
    (tests / "meta" / "test_planted.py").write_text(source, encoding="utf-8")
    return tests


@pytest.mark.parametrize("source", list(_PLANTED_READERS.values()), ids=list(_PLANTED_READERS))
def test_an_unmarked_module_that_walks_to_the_repository_root_is_reported(tmp_path: Path, source: str) -> None:
    findings, scanned = unmarked_readers(_plant(tmp_path, source))
    assert scanned == 1
    assert findings and all(f.startswith("meta/test_planted.py: ") for f in findings), findings


@pytest.mark.parametrize(
    "mark",
    ["pytestmark = pytest.mark.live_tree", "pytestmark = [pytest.mark.live_tree, pytest.mark.slow]"],
)
@pytest.mark.parametrize("source", list(_PLANTED_READERS.values()), ids=list(_PLANTED_READERS))
def test_the_same_module_marked_live_tree_is_not_reported(tmp_path: Path, source: str, mark: str) -> None:
    findings, _ = unmarked_readers(_plant(tmp_path, f"import pytest\n\n{mark}\n\n{source}"))
    assert findings == []


_PACKAGE_LOCAL = {
    "the package's own src": (
        "from pathlib import Path\n\nPKG_ROOT = Path(__file__).resolve().parents[2] / 'src' / 'pyforge' / 'mason'\n"
    ),
    "down then back up to the package's pyproject": (
        "from pathlib import Path\n"
        "\n"
        "PKG_ROOT = Path(__file__).resolve().parents[2] / 'src' / 'pyforge'\n"
        "MANIFEST = PKG_ROOT.parents[1] / 'pyproject.toml'\n"
    ),
    "a fixture beside the tests": (
        "from pathlib import Path\n\nFIXTURE = Path(__file__).resolve().parent.parent / 'fixtures' / 'fake_cfe_root'\n"
    ),
    "a tmp_path walk": ("def test_x(tmp_path):\n    for p in tmp_path.parents:\n        assert p\n"),
    "a docstring that names the derivation": (
        '"""Reads Path(__file__).resolve().parents[6] and `git rev-parse --show-toplevel` -- in prose only."""\n'
    ),
}


@pytest.mark.parametrize("source", list(_PACKAGE_LOCAL.values()), ids=list(_PACKAGE_LOCAL))
def test_a_module_that_stays_inside_the_package_is_not_reported(tmp_path: Path, source: str) -> None:
    findings, _ = unmarked_readers(_plant(tmp_path, source))
    assert findings == []


_MARKED = "import subprocess\n\nimport pytest\nfrom pathlib import Path\n\npytestmark = pytest.mark.live_tree\n\n"

_DERIVES_AT_IMPORT = {
    "module level, parents[N]": "_HERE = Path(__file__).resolve()\n_REPO_ROOT = _HERE.parents[6]\n",
    "module level, through the package root": (
        "PKG_ROOT = Path(__file__).resolve().parents[2]\nREPO_ROOT = PKG_ROOT.parents[3]\n"
    ),
    "module level, an upward walk": "ROOT = next(p for p in Path(__file__).parents if (p / 'AGENTS.md').is_file())\n",
    "module level, git": (
        "ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout\n"
    ),
    "a class body": "class TestX:\n    ROOT = Path(__file__).resolve().parents[6]\n",
    "a decorator": (
        "@pytest.mark.skipif(not (Path(__file__).resolve().parents[6] / 'pixi.toml').is_file(), reason='tree')\n"
        "def test_x():\n"
        "    pass\n"
    ),
    "a default argument": "def _root(start=Path(__file__).resolve().parents[6]):\n    return start\n",
    "a helper called at module level": (
        "def _repo_root():\n    return Path(__file__).resolve().parents[6]\n\nCONTRACT = _repo_root() / 'x.md'\n"
    ),
    "a helper called in a decorator": (
        "def _root():\n"
        "    return Path(__file__).resolve().parents[6]\n"
        "\n"
        "@pytest.mark.parametrize('p', sorted((_root() / 'docs').glob('*.md')))\n"
        "def test_x(p):\n"
        "    pass\n"
    ),
    "a helper that walks upward, called at module level": (
        "def _root():\n"
        "    for candidate in Path(__file__).resolve().parents:\n"
        "        if (candidate / 'pixi.toml').is_file():\n"
        "            return candidate\n"
        "\n"
        "ROOT = _root()\n"
    ),
    "a helper calling a helper, called at module level": (
        "def _root():\n"
        "    return Path(__file__).resolve().parents[6]\n"
        "\n"
        "def _docs():\n"
        "    return _root() / 'docs'\n"
        "\n"
        "DOCS = _docs()\n"
    ),
}

_NOT_AT_IMPORT = {
    "a helper": "def _repo_root():\n    return Path(__file__).resolve().parents[6]\n",
    "a fixture walking upward": (
        "@pytest.fixture\n"
        "def repo_root():\n"
        "    here = Path(__file__).resolve()\n"
        "    for candidate in here.parents:\n"
        "        if (candidate / 'pixi.toml').is_file():\n"
        "            return candidate\n"
    ),
    "a lambda": "ROOT = lambda: Path(__file__).resolve().parents[6]\n",
    "a method": "class TestX:\n    def test_root(self):\n        assert Path(__file__).resolve().parents[6]\n",
    "a package-local path at module level": "PKG_ROOT = Path(__file__).resolve().parents[2]\n",
    "a helper called only inside a test": (
        "def _root():\n    return Path(__file__).resolve().parents[6]\n\ndef test_x():\n    assert _root()\n"
    ),
    "a helper called only inside a lambda": (
        "def _root():\n    return Path(__file__).resolve().parents[6]\n\nROOT = lambda: _root()\n"
    ),
    "a package-local helper called at module level": (
        "def _pkg():\n    return Path(__file__).resolve().parents[2]\n\nPKG = _pkg()\n"
    ),
}


@pytest.mark.parametrize("source", list(_DERIVES_AT_IMPORT.values()), ids=list(_DERIVES_AT_IMPORT))
def test_a_marked_module_that_derives_the_root_at_import_is_reported(tmp_path: Path, source: str) -> None:
    findings, marked = import_time_readers(_plant(tmp_path, _MARKED + source))
    assert marked == 1
    assert findings and all(f.startswith("meta/test_planted.py: ") for f in findings), findings


@pytest.mark.parametrize("source", list(_NOT_AT_IMPORT.values()), ids=list(_NOT_AT_IMPORT))
def test_a_marked_module_that_derives_the_root_only_in_a_function_is_not_reported(tmp_path: Path, source: str) -> None:
    findings, marked = import_time_readers(_plant(tmp_path, _MARKED + source))
    assert marked == 1
    assert findings == []


def test_the_import_check_reads_only_marked_modules(tmp_path: Path) -> None:
    findings, marked = import_time_readers(_plant(tmp_path, _DERIVES_AT_IMPORT["module level, parents[N]"]))
    assert (findings, marked) == ([], 0)
