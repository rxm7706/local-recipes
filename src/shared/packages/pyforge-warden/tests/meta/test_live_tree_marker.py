"""Story 27.1 -- every warden test module that reads outside the package carries ``live_tree``.

A relay of ``spec-pyforge-steward:CAP-175``: the suite runs as two halves, the
package half (``-m "not live_tree"``, which must pass from an export of this
package alone, so the suite can serve a second root as an oracle) and the
live-tree half (``-m live_tree``, run in the repository, where a missing input
is a failure, never a skip). This guard holds the split:

(a) the ``live_tree`` marker is registered in this package's ``pyproject.toml``;
(b) an AST scan of every unmarked module finds no outside read;
(c) every marked module does have one -- a marker with nothing to read is a
    module the package half should be running.

An outside read is a path climbed above the package root from ``__file__`` or
``pyforge.warden.__file__``, a ``_repo_root`` walker, ``changed_paths_since``,
or a literal naming ``.claude/``, ``_bmad-output/``, ``docs/``,
``src/platform``, another package, or the root ``pixi.lock`` or ``pixi.toml``.

The scan reads only this package's own files, so it runs in the package half.
This module is left out of its own scan: its literals are the rule, not reads.
"""

from __future__ import annotations

import ast
import re
import textwrap
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = PACKAGE_ROOT / "tests"
PYPROJECT = PACKAGE_ROOT / "pyproject.toml"
THIS_MODULE = Path(__file__).resolve().relative_to(PACKAGE_ROOT).as_posix()
PACKAGE_NAME = PACKAGE_ROOT.name  # pyforge-warden
OWN_MODULE = "pyforge.warden"

# The fixture data trees under tests/fixtures/ hold synthetic projects and planted SAST trips, not test code.
_FIXTURE_TREES = "tests/fixtures/"

_OTHER_PACKAGE = re.compile(r"^(?:pyforge|django)-[a-z][a-z0-9-]*$")
_PATH_CALLS = frozenset({"Path", "pathlib.Path", "PurePath", "pathlib.PurePath", "open"})
_ROOT_MANIFESTS = frozenset({"pixi.lock", "pixi.toml"})
_WALKER_NAME = "repo_root"
_GIT_DIFF_READER = "changed_paths_since"


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------


def _segments(text: str) -> list[str]:
    return [seg for seg in text.replace("\\", "/").split("/") if seg not in ("", ".")]


def _other_package(segments: list[str]) -> str | None:
    """A path segment naming a sibling package (``django-warden``, ``pyforge-core``), never this one or a
    name derived from it (``pyforge-warden-seeded``, a tmp copy)."""
    for seg in segments:
        if _OTHER_PACKAGE.match(seg) and seg != PACKAGE_NAME and not seg.startswith(PACKAGE_NAME + "-"):
            return seg
    return None


def _dotted(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    """Each name a module binds by import, mapped to the dotted module (or object) it names."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    head = alias.name.split(".")[0]
                    aliases[head] = head
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


class _Scanner:
    """One module's outside reads, as ``"<line>: <what>"`` strings."""

    def __init__(self, rel: str, source: str, package_root: Path) -> None:
        self.rel = rel
        self.tree = ast.parse(source)
        self.package_root = package_root
        self.aliases = _import_aliases(self.tree)
        self.heights: dict[str, int] = {}
        self.reads: list[str] = []
        self._bind_names()

    # -- heights: how many directories below the package root a path expression sits ------------

    def _module_file_height(self, module: str) -> int:
        """``src/pyforge/warden/__init__.py`` is 4 below the root; ``src/pyforge/warden/cli.py`` is 4 too."""
        parts = module.split(".")
        package_dir = self.package_root / "src" / Path(*parts)
        return len(parts) + 2 if (package_dir / "__init__.py").is_file() else len(parts) + 1

    def _file_of(self, node: ast.Attribute) -> int | None:
        dotted = _dotted(node.value)
        if not dotted:
            return None
        head, _, rest = dotted.partition(".")
        if head not in self.aliases:
            return None  # a local object's __file__ (a frame, a fixture): no module path to climb from
        module = self.aliases[head] + (f".{rest}" if rest else "")
        if module == OWN_MODULE or module.startswith(OWN_MODULE + "."):
            return self._module_file_height(module)
        self.reads.append(f"{node.lineno}: the __file__ of {module}, another package")
        return None

    def height(self, node: ast.AST) -> int | None:
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return len(self.rel.split("/"))
            return self.heights.get(node.id)
        if isinstance(node, ast.Attribute):
            if node.attr == "__file__":
                return self._file_of(node)
            if node.attr == "parent":
                base = self.height(node.value)
                return None if base is None else base - 1
            return None
        if isinstance(node, ast.Subscript):
            value = node.value
            if isinstance(value, ast.Attribute) and value.attr == "parents":
                base = self.height(value.value)
                index = node.slice
                if base is not None and isinstance(index, ast.Constant) and isinstance(index.value, int):
                    return base - (index.value + 1)
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            base = self.height(node.left)
            return None if base is None else self._join(base, [node.right])
        if isinstance(node, ast.Call):
            func = _dotted(node.func)
            if func in _PATH_CALLS - {"open"} and node.args:
                base = self.height(node.args[0])
                return None if base is None else self._join(base, node.args[1:])
            if func in ("os.path.dirname",) and node.args:
                base = self.height(node.args[0])
                return None if base is None else base - 1
            if func in ("os.path.abspath", "os.path.realpath", "os.path.normpath") and node.args:
                return self.height(node.args[0])
            if func == "os.path.join" and node.args:
                base = self.height(node.args[0])
                return None if base is None else self._join(base, node.args[1:])
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("resolve", "absolute", "expanduser"):
                    return self.height(node.func.value)
                if node.func.attr == "joinpath":
                    base = self.height(node.func.value)
                    return None if base is None else self._join(base, node.args)
            return None
        return None

    @staticmethod
    def _join(base: int, parts: list[ast.expr]) -> int:
        """Join segments onto a height; once a ``..`` climbs above the root the path stays outside."""
        for part in parts:
            if base < 0:
                return base
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                for seg in _segments(part.value):
                    base += -1 if seg == ".." else 1
                    if base < 0:
                        return base
            else:
                base += 1
        return base

    def _bind_names(self) -> None:
        """Names bound to a path expression (module- or function-level; the lowest height wins)."""
        for _ in range(3):  # a name built from a name built from a name
            for node in ast.walk(self.tree):
                targets: list[ast.expr] = []
                value: ast.expr | None = None
                if isinstance(node, ast.Assign):
                    targets, value = node.targets, node.value
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    targets, value = [node.target], node.value
                if value is None:
                    continue
                saved = list(self.reads)
                found = self.height(value)
                self.reads = saved  # binding is a dry run; the walk below records each read once
                if found is None:
                    continue
                for target in targets:
                    if isinstance(target, ast.Name):
                        current = self.heights.get(target.id)
                        self.heights[target.id] = found if current is None else min(current, found)

    # -- the rules ---------------------------------------------------------------------------------

    def _path_operands(self) -> set[int]:
        """The string constants used as path parts: a ``/`` operand or an argument of a path call."""
        ids: set[int] = set()
        for node in ast.walk(self.tree):
            operands: list[ast.expr] = []
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                operands = [node.left, node.right]
            elif isinstance(node, ast.Call):
                func = _dotted(node.func)
                if func in _PATH_CALLS or func == "os.path.join" or func.endswith(".joinpath"):
                    operands = list(node.args)
            ids.update(id(op) for op in operands if isinstance(op, ast.Constant))
        return ids

    def scan(self) -> list[str]:
        docstrings = _docstring_ids(self.tree)
        path_operands = self._path_operands()
        climbed: set[int] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.expr) and not isinstance(node, ast.Constant):
                found = self.height(node)
                if found is not None and found < 0 and node.lineno not in climbed:
                    climbed.add(node.lineno)
                    self.reads.append(f"{node.lineno}: a path climbed above the package root")
            self._walker(node)
            self._git_diff_reader(node)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                self._literal(node, id(node) in path_operands)
            if isinstance(node, ast.Call):
                self._cwd_manifest(node)
        return sorted(set(self.reads), key=lambda read: (int(read.split(":", 1)[0]), read))

    def _walker(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.lstrip("_").lower() == _WALKER_NAME:
            self.reads.append(f"{node.lineno}: a {node.name} walker")
        elif isinstance(node, ast.Call) and _dotted(node.func).split(".")[-1].lstrip("_").lower() == _WALKER_NAME:
            self.reads.append(f"{node.lineno}: a call to {_dotted(node.func)}")
        iterables: list[ast.expr] = []
        if isinstance(node, (ast.For, ast.AsyncFor)):
            iterables.append(node.iter)
        elif isinstance(node, ast.comprehension):
            iterables.append(node.iter)
        for iterable in iterables:
            if isinstance(iterable, ast.Attribute) and iterable.attr == "parents":
                self.reads.append(f"{iterable.lineno}: a walk up the parents of a path (a repo-root walker)")

    def _git_diff_reader(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name) and node.id == _GIT_DIFF_READER:
            self.reads.append(f"{node.lineno}: {_GIT_DIFF_READER} (the repository's git diff)")
        elif isinstance(node, ast.Attribute) and node.attr == _GIT_DIFF_READER:
            self.reads.append(f"{node.lineno}: {_GIT_DIFF_READER} (the repository's git diff)")
        elif isinstance(node, ast.ImportFrom):
            if any((alias.name == _GIT_DIFF_READER) for alias in node.names):
                self.reads.append(f"{node.lineno}: imports {_GIT_DIFF_READER} (the repository's git diff)")

    def _literal(self, node: ast.Constant, path_operand: bool) -> None:
        text = str(node.value)
        segments = _segments(text)
        if not segments:
            return
        named: str | None = None
        if ".claude" in segments:
            named = ".claude/"
        elif "_bmad-output" in segments:
            named = "_bmad-output/"
        elif segments[0] == "docs" and "/" in text.replace("\\", "/").lstrip("./"):
            named = "docs/"
        elif any(a == "src" and b == "platform" for a, b in zip(segments, segments[1:])):
            named = "src/platform"
        elif (path_operand or len(segments) > 1) and (other := _other_package(segments)):
            named = f"another package ({other})"
        elif segments[-1] in _ROOT_MANIFESTS and ".." in segments:
            named = f"the root {segments[-1]}"
        if named is not None:
            self.reads.append(f"{node.lineno}: a literal naming {named}: {text!r}")

    def _cwd_manifest(self, node: ast.Call) -> None:
        """``Path("pixi.lock")`` reads the root lock when the suite runs from the repository root."""
        if _dotted(node.func) not in _PATH_CALLS or not node.args:
            return
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return
        segments = _segments(first.value)
        if len(segments) == 1 and segments[0] in _ROOT_MANIFESTS:
            self.reads.append(f"{node.lineno}: a cwd-relative {first.value} (the root manifest)")


def outside_reads(rel: str, source: str, package_root: Path = PACKAGE_ROOT) -> list[str]:
    """Every outside read in one module's source; ``rel`` is its path under the package root."""
    return _Scanner(rel, source, package_root).scan()


def is_live_tree_marked(source: str) -> bool:
    """Does the module carry ``pytestmark = pytest.mark.live_tree`` (alone or in a list) at module level?"""
    for node in ast.parse(source).body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        if value is None or not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets):
            continue
        return any(
            isinstance(sub, ast.Attribute)
            and sub.attr == "live_tree"
            and isinstance(sub.value, ast.Attribute)
            and sub.value.attr == "mark"
            for sub in ast.walk(value)
        )
    return False


def audit(modules: Mapping[str, str], package_root: Path = PACKAGE_ROOT) -> tuple[list[str], list[str]]:
    """``(unmarked readers, marked modules with no read)`` over ``{rel: source}``."""
    unmarked_readers: list[str] = []
    marked_without_read: list[str] = []
    for rel, source in sorted(modules.items()):
        reads = outside_reads(rel, source, package_root)
        if is_live_tree_marked(source):
            if not reads:
                marked_without_read.append(rel)
        elif reads:
            unmarked_readers.extend(f"{rel}:{read}" for read in reads)
    return unmarked_readers, marked_without_read


def _package_modules() -> Iterator[tuple[str, str]]:
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        if rel == THIS_MODULE or (rel.startswith(_FIXTURE_TREES) and rel.count("/") > 2):
            continue
        yield rel, path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (a) the marker, (b) the unmarked modules, (c) the marked modules
# ---------------------------------------------------------------------------


def test_the_live_tree_marker_is_registered_in_pyproject():
    with PYPROJECT.open("rb") as stream:
        markers = tomllib.load(stream)["tool"]["pytest"]["ini_options"]["markers"]
    assert any(str(marker).startswith("live_tree:") for marker in markers), markers
    assert any(str(marker).startswith("slow:") for marker in markers), markers


def test_the_scan_sees_the_whole_suite():
    modules = dict(_package_modules())
    assert "tests/conftest.py" in modules
    assert any(rel.startswith("tests/unit/") for rel in modules)
    assert any(rel.startswith("tests/integration/") for rel in modules)
    assert any(rel.startswith("tests/meta/") for rel in modules)
    assert THIS_MODULE not in modules
    assert not any(rel.startswith(_FIXTURE_TREES) and rel.count("/") > 2 for rel in modules)


def test_every_unmarked_module_reads_nothing_outside_the_package():
    unmarked_readers, _ = audit(dict(_package_modules()))
    assert not unmarked_readers, (
        "these modules read outside the package but are not marked live_tree -- add "
        "`pytestmark = pytest.mark.live_tree` or split the reader into a marked module:\n" + "\n".join(unmarked_readers)
    )


def test_every_marked_module_has_an_outside_read():
    _, marked_without_read = audit(dict(_package_modules()))
    assert not marked_without_read, (
        "these modules are marked live_tree but read nothing outside the package -- drop the marker "
        "so the package half runs them:\n" + "\n".join(marked_without_read)
    )


def test_the_live_half_is_not_empty():
    marked = [rel for rel, source in _package_modules() if is_live_tree_marked(source)]
    assert marked


# ---------------------------------------------------------------------------
# The rule on synthetic source: each outside-read form is found; package-local paths are not
# ---------------------------------------------------------------------------

_SYNTHETIC_REL = "tests/unit/test_synthetic.py"

_READERS = {
    "climb from __file__": """
        from pathlib import Path
        ROOT_LOCK = Path(__file__).resolve().parents[6] / "pixi.lock"
    """,
    "climb by .parent": """
        from pathlib import Path
        ABOVE = Path(__file__).resolve().parent.parent.parent.parent
    """,
    "climb from pyforge.warden.__file__": """
        from pathlib import Path
        import pyforge.warden
        PACKAGE_ROOT = Path(pyforge.warden.__file__).resolve().parent.parent.parent.parent
        ROOT_TOML = PACKAGE_ROOT.parents[3] / "pixi.toml"
    """,
    "climb through a string": """
        from pathlib import Path
        ROOT_TOML = Path(__file__).parent / "../../../../pixi.toml"
    """,
    "climb out and back down": """
        from pathlib import Path
        OTHER = Path(__file__).parent / "../../../../elsewhere/src/x"
    """,
    "a _repo_root walker": """
        from pathlib import Path
        def _repo_root():
            for candidate in Path.cwd().parents:
                if (candidate / "pixi.toml").is_file():
                    return candidate
    """,
    "changed_paths_since": """
        from pyforge.testing_kit import changed_paths_since
        def test_x(root):
            assert changed_paths_since(root, pathspec="x") == []
    """,
    "a .claude literal": """
        SKILL = ".claude/skills/pyforge-warden/SKILL.md"
    """,
    "an _bmad-output literal": """
        def test_x(root):
            assert (root / "_bmad-output/projects").is_dir()
    """,
    "a docs literal": """
        MAP = "docs/map.yaml"
    """,
    "a src/platform literal": """
        PLATFORM = "src/platform/tests"
    """,
    "another package literal": """
        def fabric(root):
            return root / "src" / "shared" / "packages" / "django-warden"
    """,
    "a cwd-relative root lock": """
        from pathlib import Path
        LOCK = Path("pixi.lock")
    """,
    "another package's __file__": """
        from pathlib import Path
        import pyforge.core
        CORE = Path(pyforge.core.__file__).parent
    """,
}

_PACKAGE_LOCAL = """
    \"\"\"A docstring may say .claude/skills, docs/map.yaml or src/platform: it is not a read.\"\"\"
    from pathlib import Path
    import pyforge.warden
    FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
    SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
    PACKAGE_ROOT = Path(pyforge.warden.__file__).resolve().parent.parent.parent.parent
    OWN_PIXI = PACKAGE_ROOT / "pixi.toml"
    def test_x(tmp_path, components):
        assert next(c for c in components if c.name == "pyforge-core")
        assert (tmp_path / "pyforge-warden-seeded").name
        (tmp_path / "pixi.toml").write_text("[workspace]\\n")
        (tmp_path / "pixi.lock").write_text("")
        assert OWN_PIXI.name == "pixi.toml"
"""


def _source(snippet: str) -> str:
    return textwrap.dedent(snippet).lstrip("\n")


@pytest.mark.parametrize("form", sorted(_READERS))
def test_each_outside_read_form_is_found(form: str):
    assert outside_reads(_SYNTHETIC_REL, _source(_READERS[form])), form


def test_package_local_paths_are_not_outside_reads():
    assert outside_reads(_SYNTHETIC_REL, _source(_PACKAGE_LOCAL)) == []


def test_a_synthetic_unmarked_reader_is_reported():
    """The negative test: an unmarked module with an outside read fails the audit, by name."""
    reader = _source(_READERS["climb from __file__"])
    unmarked_readers, marked_without_read = audit({_SYNTHETIC_REL: reader})
    assert unmarked_readers and all(line.startswith(f"{_SYNTHETIC_REL}:") for line in unmarked_readers)
    assert marked_without_read == []


def test_a_synthetic_marked_reader_passes_in_either_marker_form():
    reader = _source(_READERS["climb from __file__"])
    alone = "import pytest\npytestmark = pytest.mark.live_tree\n" + reader
    listed = "import pytest\npytestmark = [pytest.mark.slow, pytest.mark.live_tree]\n" + reader
    assert audit({_SYNTHETIC_REL: alone}) == ([], [])
    assert audit({_SYNTHETIC_REL: listed}) == ([], [])


def test_a_synthetic_marked_module_with_no_read_is_reported():
    local = "import pytest\npytestmark = pytest.mark.live_tree\n" + _source(_PACKAGE_LOCAL)
    assert audit({_SYNTHETIC_REL: local}) == ([], [_SYNTHETIC_REL])


def test_another_marker_is_not_live_tree():
    reader = "import pytest\npytestmark = [pytest.mark.slow]\n" + _source(_READERS["a .claude literal"])
    assert not is_live_tree_marked(reader)
    unmarked_readers, _ = audit({_SYNTHETIC_REL: reader})
    assert unmarked_readers
