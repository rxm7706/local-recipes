"""Story 123.2 (spec-pyforge-steward:CAP-182): one module names this root's layout and repository.

``pyforge.steward.root_layout`` is the one steward module that states where station packages live in
this checkout (`src/shared/packages`) and which repository this estate is. This module reds when any
other steward source module gains a string constant (docstrings aside) that names either one, or spells
the station-packages directory out one path segment at a time; when a module imports another station's
package, statically, relatively or by a computed name (a verdict another station owns is read from that
station's command by exit code, never by import); when an entry in an exception list no longer applies;
and when ``root_layout.py`` stops being assignments only.

It scans the package's own source, located from the imported package, so it runs in the package
half; the ``fires`` tests plant each breach in a scratch tree and prove the scan names it.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

LAYOUT_MODULE = "root_layout.py"
# Story 124.2: tracked paths are spelled as joins here -- steward's trigger-map scan counts a bare
# tracked-path literal as a read of the live tree, and this module reads none.
#: Text only ``root_layout.py`` may hold in a string constant: the station-packages directory and
#: the repository owner (which every slug, clone URL and owner name of this estate contains).
ROOT_MARKERS: tuple[str, ...] = ("/".join(("src", "shared", "packages")), "rxm7706")
#: The station-packages directory as path segments: a chain that spells it out one segment at a time
#: (``root / "src" / "shared" / "packages"``) names this root as surely as the one string does.
STATION_PACKAGES_SEGMENTS: tuple[str, ...] = ("src", "shared", "packages")
#: Every station but steward. Steward reads their verdicts through their commands, never by import.
OTHER_STATIONS: frozenset[str] = frozenset({"atlas", "doctor", "herald", "marshal", "mason", "scribe", "warden"})
#: The package this test holds, as the import path a relative import climbs from.
STEWARD_PACKAGE: tuple[str, ...] = ("pyforge", "steward")
#: Steward modules allowed a cross-station import, each with the deferred-work id that tracks its
#: removal. Empty: Story 123.3 took ``session.py``'s ``pyforge.doctor`` import out (operator ruling
#: 2026-11-10), so the exception the first plan named no longer exists.
CROSS_STATION_EXCEPTIONS: Mapping[str, str] = {}
#: Steward modules that still spell the station-packages directory out segment by segment, each with
#: the deferred-work id that tracks deriving it from ``root_layout.STATION_PACKAGES_DIR``. Neither file
#: was in Story 123.2's files_owned in the cutover-readiness build (round-1 review), so the build could
#: not move them; an entry admits segment runs only, never a whole-string literal, and the test fails
#: when an entry no longer applies.
LAYOUT_EXCEPTIONS: Mapping[str, str] = {
    "five_tier.py": "DW-steward-123-2-2",
    "preflight_suite_reduction.py": "DW-steward-123-2-2",
}

_DEFERRED_WORK_ID = re.compile(r"^DW-[A-Za-z0-9.-]+$")
_IMPORT_CALLS = frozenset({"import_module", "__import__"})
_PATH_CALLS = frozenset({"Path", "PurePath", "PurePosixPath", "PureWindowsPath", "join"})
#: What ``cross_station_imports`` reports for an import whose module name is not a string literal.
COMPUTED_MODULE = "<computed module name>"


def _steward_source_dir() -> Path:
    """The imported ``pyforge.steward`` package's directory: the source this test holds."""
    import pyforge.steward

    return Path(pyforge.steward.__file__).resolve().parent


def _modules(package_dir: Path) -> list[Path]:
    return sorted(path for path in package_dir.rglob("*.py") if "__pycache__" not in path.parts)


def _relative(path: Path, package_dir: Path) -> str:
    return path.relative_to(package_dir).as_posix()


def _docstring_ids(tree: ast.AST) -> set[int]:
    """Every docstring: a string expression standing alone as a statement (module, class, function or attribute)."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }


def root_literals(source: str) -> list[tuple[int, str]]:
    """``(line, value)`` for each string constant naming a root marker, docstrings aside (f-string parts included)."""
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and any(marker in node.value for marker in ROOT_MARKERS)
    ]


def _operands(node: ast.AST) -> list[ast.AST]:
    """The operands a path is built from: a ``/`` or ``+`` chain, a path or join call, an f-string, flattened."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
        return _operands(node.left) + _operands(node.right)
    if isinstance(node, ast.Call) and _call_name(node) in _PATH_CALLS:
        return [leaf for argument in node.args for leaf in _operands(argument)]
    if isinstance(node, ast.JoinedStr):
        return [leaf for value in node.values for leaf in _operands(value)]
    return [node]


def _call_name(node: ast.Call) -> str | None:
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)


def segment_runs(source: str) -> list[int]:
    """Lines where the station-packages directory is spelled out over more than one operand, string or path.

    One whole-string ``"src/shared/packages"`` is ``root_literals``' to report; this catches the same
    directory assembled from pieces (``root / "src" / "shared" / "packages"``, ``Path("src", "shared",
    "packages")``, ``("src", "shared", "packages")``, ``"src/shared/" + "packages"``).
    """
    width = len(STATION_PACKAGES_SEGMENTS)
    seen: set[tuple[int, ...]] = set()
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Tuple, ast.List)):
            leaves = [leaf for element in node.elts for leaf in _operands(element)]
        elif isinstance(node, (ast.BinOp, ast.Call, ast.JoinedStr)):
            leaves = _operands(node)
        else:
            continue
        tokens: list[tuple[str | None, int]] = []
        for leaf in leaves:
            if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str):
                tokens += [(part, id(leaf)) for part in leaf.value.split("/") if part]
            else:
                tokens.append((None, id(leaf)))
        for start in range(len(tokens) - width + 1):
            window = tokens[start : start + width]
            owners = tuple(owner for _, owner in window)
            if tuple(part for part, _ in window) == STATION_PACKAGES_SEGMENTS and len(set(owners)) > 1:
                if owners not in seen:
                    seen.add(owners)
                    lines.append(node.lineno)
    return lines


def _other_station(module: str) -> bool:
    parts = module.split(".")
    return len(parts) > 1 and parts[0] == "pyforge" and parts[1] in OTHER_STATIONS


def _relative_targets(node: ast.ImportFrom, package: tuple[str, ...]) -> list[str]:
    """The absolute modules a relative ``from`` import names, resolved against the importing module's package."""
    if node.level > len(package):
        return []
    anchor = list(package[: len(package) - (node.level - 1)])
    if node.module:
        return [".".join([*anchor, *node.module.split(".")])]
    return [".".join([*anchor, alias.name]) for alias in node.names]


def cross_station_imports(source: str, package: tuple[str, ...] = STEWARD_PACKAGE) -> list[tuple[int, str]]:
    """``(line, module)`` for each import of another station's package: static, relative or by ``import_module``.

    ``package`` is the importing module's package (``pyforge.steward`` or a subpackage of it), which a
    relative import climbs from. An ``import_module``/``__import__`` whose name is not a string literal is
    reported as ``COMPUTED_MODULE``: the scan cannot prove it stays inside steward.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names if _other_station(alias.name)]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            if node.module and _other_station(node.module):
                found.append((node.lineno, node.module))
        elif isinstance(node, ast.ImportFrom):
            found += [(node.lineno, target) for target in _relative_targets(node, package) if _other_station(target)]
        elif isinstance(node, ast.Call) and _call_name(node) in _IMPORT_CALLS and node.args:
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                found.append((node.lineno, COMPUTED_MODULE))
            elif _other_station(first.value):
                found.append((node.lineno, first.value))
    return found


def layout_breaches(source: str) -> list[str]:
    """Why ``root_layout.py`` is not assignments only, or not importable by every steward module."""
    breaches: list[str] = []
    tree = ast.parse(source)
    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue  # the module docstring, or an attribute's
        if isinstance(statement, ast.ImportFrom) and statement.level == 0 and statement.module:
            if statement.module == "pyforge.steward" or statement.module.startswith("pyforge.steward."):
                breaches.append(f"line {statement.lineno}: imports {statement.module}, a steward module")
            continue
        if isinstance(statement, ast.Import):
            breaches += [
                f"line {statement.lineno}: imports {alias.name}, a steward module"
                for alias in statement.names
                if alias.name == "pyforge.steward" or alias.name.startswith("pyforge.steward.")
            ]
            continue
        if isinstance(statement, ast.ImportFrom):
            breaches.append(f"line {statement.lineno}: a relative import, which reaches a steward module")
            continue
        breaches.append(f"line {statement.lineno}: a {type(statement).__name__}, not an assignment")
    breaches += [
        f"line {node.lineno}: a lambda, a function in an assignment"
        for node in ast.walk(tree)
        if isinstance(node, ast.Lambda)
    ]
    return breaches


def _stale_or_unkeyed(exceptions: Mapping[str, str], applies: Mapping[str, bool], what: str) -> list[str]:
    findings: list[str] = []
    for relative, deferred_id in exceptions.items():
        if not _DEFERRED_WORK_ID.match(deferred_id):
            findings.append(f"exception {relative}: {deferred_id!r} is not a deferred-work id")
        if not applies.get(relative):
            findings.append(f"exception {relative} ({deferred_id}) no longer applies: no {what} there")
    return findings


def scan(
    package_dir: Path,
    exceptions: Mapping[str, str],
    layout_exceptions: Mapping[str, str] | None = None,
) -> list[str]:
    """Every portability finding under ``package_dir``; empty when the package holds to CAP-182.

    ``exceptions`` admits a module's cross-station imports, ``layout_exceptions`` its segment-by-segment
    station-packages path; each maps a module to the deferred-work id that tracks it, and an entry that
    no longer applies is itself a finding.
    """
    layout_exceptions = layout_exceptions or {}
    findings: list[str] = []
    imports_by_module: dict[str, bool] = {}
    segments_by_module: dict[str, bool] = {}
    for path in _modules(package_dir):
        relative = _relative(path, package_dir)
        source = path.read_text(encoding="utf-8")
        if relative == LAYOUT_MODULE:
            findings += [f"{relative}: {breach}" for breach in layout_breaches(source)]
        else:
            findings += [
                f"{relative}:{line}: string constant {value!r} names this root; take it from {LAYOUT_MODULE}"
                for line, value in root_literals(source)
            ]
            runs = segment_runs(source)
            segments_by_module[relative] = bool(runs)
            if relative not in layout_exceptions:
                findings += [
                    f"{relative}:{line}: spells out {'/'.join(STATION_PACKAGES_SEGMENTS)} segment by segment; "
                    f"take it from {LAYOUT_MODULE}"
                    for line in runs
                ]
        package = (*STEWARD_PACKAGE, *Path(relative).parent.parts)
        imports = cross_station_imports(source, package)
        imports_by_module[relative] = bool(imports)
        if relative not in exceptions:
            findings += [
                f"{relative}:{line}: imports {module}; read that station's verdict from its command"
                for line, module in imports
            ]
    findings += _stale_or_unkeyed(exceptions, imports_by_module, "cross-station import")
    findings += _stale_or_unkeyed(layout_exceptions, segments_by_module, "segment-by-segment station-packages path")
    return findings


# ---------------------------------------------------------------------------
# The live package
# ---------------------------------------------------------------------------


def test_steward_source_holds_to_one_root_layout_module() -> None:
    """No root literal outside root_layout.py, no cross-station import, no stale exception."""
    package_dir = _steward_source_dir()
    assert (package_dir / LAYOUT_MODULE).is_file()
    assert scan(package_dir, CROSS_STATION_EXCEPTIONS, LAYOUT_EXCEPTIONS) == []


def test_the_scan_reads_the_whole_package() -> None:
    """A scan that found no module would pass vacuously: it reads the modules the story moved, subpackages too."""
    package_dir = _steward_source_dir()
    scanned = {_relative(path, package_dir) for path in _modules(package_dir)}
    assert {LAYOUT_MODULE, "upgrade.py", "session.py", "catalog.py", "sync.py", "dashboard/__init__.py"} <= scanned


def test_root_layout_names_each_estate_bound_constant_once() -> None:
    """The four identity sites are one constant each, and the layout constants derive from one directory."""
    from pyforge.steward import root_layout

    assert root_layout.STATION_PACKAGES == "/".join(("src", "shared", "packages"))
    assert root_layout.STEWARD_PACKAGE_DIR == Path(root_layout.STATION_PACKAGES) / "pyforge-steward"
    assert root_layout.MARSHAL_PACKAGE_DIR == Path(root_layout.STATION_PACKAGES) / "pyforge-marshal"
    assert root_layout.CI_DEFAULT_REPOSITORY == "rxm7706/local-recipes"
    assert root_layout.BOOTSTRAP_DEFAULT_URL == "https://github.com/rxm7706/local-recipes.git"
    assert root_layout.MARKETPLACE_GIT_URL == "https://github.com/rxm7706/local-recipes.git"
    assert root_layout.MARKETPLACE_OWNER == "rxm7706"


def test_each_moved_site_derives_from_root_layout_and_keeps_its_value() -> None:
    """The refactor changes no value on A: every site the story moved reads root_layout and still says the same."""
    from pyforge.core.cutover_root import LOCAL_DEV_RELATIVE

    from pyforge.steward import (
        bootstrap,
        catalog,
        ci,
        corridor,
        marketplace_pages,
        measures,
        preflight_ci,
        root_layout,
        sync,
        upgrade,
        workspace,
    )

    assert catalog.CATALOG_RELATIVE == Path("src", "shared", "packages", "pyforge-steward", "catalog")
    assert corridor.CORRIDOR_RELATIVE == Path("src", "shared", "packages", "pyforge-steward", "corridor")
    assert measures.MEASURES_RELATIVE == Path("src", "shared", "packages", "pyforge-steward", "measures")
    assert upgrade._MARSHAL_PKG is root_layout.MARSHAL_PACKAGE_DIR
    assert root_layout.MARSHAL_PACKAGE_DIR == Path("src", "shared", "packages", "pyforge-marshal")
    assert preflight_ci.STATION_PACKAGES is root_layout.STATION_PACKAGES
    assert ci.DEFAULT_REPO is root_layout.CI_DEFAULT_REPOSITORY
    assert bootstrap._DEFAULT_REPO_URL is root_layout.BOOTSTRAP_DEFAULT_URL
    assert catalog.PUBLIC_MARKETPLACE_GIT_URL is root_layout.MARKETPLACE_GIT_URL
    assert '"owner": {\n    "name": "rxm7706"\n  }' in marketplace_pages._marketplace_document([], lambda row: row)
    assert workspace.default_flags_path() == workspace.repo_root() / LOCAL_DEV_RELATIVE
    assert sync.default_transport is sync._default_transport


def test_preflight_ci_station_paths_are_unchanged(tmp_path: Path) -> None:
    """preflight_ci builds its station-package paths from the moved prefix; each answer is what it was."""
    from pyforge.steward.preflight_ci import is_packaging_test_input, station_package_dirs

    assert is_packaging_test_input("pixi.toml") and is_packaging_test_input("Containerfile.guild")
    assert is_packaging_test_input("/".join(("src", "shared", "packages", "pyforge-core", "pyproject.toml")))
    assert is_packaging_test_input(
        "/".join(("src", "shared", "packages", "pyforge-core", "src", "pyforge", "core", "flags.py"))
    )
    assert not is_packaging_test_input("/".join(("src", "shared", "packages", "pyforge-core", "README.md")))
    assert not is_packaging_test_input(
        "/".join(("src", "shared", "packages", "pyforge-core", "tests", "unit", "test_flags.py"))
    )
    assert not is_packaging_test_input("src/shared/packages/django-core/pyproject.toml")
    assert not is_packaging_test_input("/".join(("docs", "MAP.md")))
    for name in ("pyforge-x", "django-x"):
        (tmp_path / "src" / "shared" / "packages" / name).mkdir(parents=True)
    assert station_package_dirs(tmp_path, "pyforge-x") == (
        "src/shared/packages/pyforge-x",
        "src/shared/packages/django-x",
    )
    assert station_package_dirs(tmp_path, "pyforge-") == ()
    assert station_package_dirs(tmp_path, "local-recipes") == ()


# ---------------------------------------------------------------------------
# The scan fires on each planted breach
# ---------------------------------------------------------------------------


def _plant(tmp_path: Path, files: Mapping[str, str]) -> Path:
    package_dir = tmp_path / "steward"
    package_dir.mkdir()
    (package_dir / LAYOUT_MODULE).write_text(
        '"""Layout."""\nSTATION_PACKAGES = "src/shared/packages"\n', encoding="utf-8"
    )
    for name, text in files.items():
        (package_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (package_dir / name).write_text(text, encoding="utf-8")
    return package_dir


def test_a_clean_tree_and_the_layout_module_itself_are_not_reported(tmp_path: Path) -> None:
    package_dir = _plant(
        tmp_path,
        {
            "clean.py": (
                '"""Reads `src/shared/packages` and `rxm7706` in prose only."""\n'
                "from .root_layout import STATION_PACKAGES\n"
                "PREFIX = STATION_PACKAGES\n"
                "# a comment naming src/shared/packages is not a constant\n"
            )
        },
    )
    assert scan(package_dir, {}) == []


def test_fires_on_a_planted_path_constant(tmp_path: Path) -> None:
    package_dir = _plant(tmp_path, {"sub/catalog.py": 'from pathlib import Path\nP = Path("src/shared/packages/x")\n'})
    findings = scan(package_dir, {})
    assert len(findings) == 1
    assert findings[0].startswith("sub/catalog.py:2: string constant 'src/shared/packages/x'")


def test_fires_on_a_planted_slug(tmp_path: Path) -> None:
    package_dir = _plant(
        tmp_path,
        {"ci.py": 'def url(name: str) -> str:\n    return f"https://github.com/rxm7706/{name}.git"\n'},
    )
    findings = scan(package_dir, {})
    assert len(findings) == 1
    assert "ci.py:2:" in findings[0] and "rxm7706" in findings[0]


@pytest.mark.parametrize(
    "line",
    [
        "from pyforge.doctor.models import DoctorStatus",
        "import pyforge.marshal.cli",
        "import importlib\nM = importlib.import_module('pyforge.herald.cli')",
    ],
    ids=["from-import", "import", "import-module"],
)
def test_fires_on_a_planted_cross_station_import(tmp_path: Path, line: str) -> None:
    package_dir = _plant(tmp_path, {"upgrade.py": f"def gate() -> None:\n    pass\n{line}\n"})
    findings = scan(package_dir, {})
    assert len(findings) == 1
    assert findings[0].startswith("upgrade.py:") and "read that station's verdict from its command" in findings[0]


def test_a_named_exception_admits_its_import(tmp_path: Path) -> None:
    package_dir = _plant(tmp_path, {"session.py": "from pyforge.doctor.sources import factory\n"})
    assert scan(package_dir, {"session.py": "DW-example-1"}) == []


def test_fires_on_an_exception_entry_that_no_longer_applies(tmp_path: Path) -> None:
    package_dir = _plant(tmp_path, {"session.py": "from .upgrade import gate\n"})
    findings = scan(package_dir, {"session.py": "DW-example-1", "gone.py": "DW-example-2"})
    assert findings == [
        "exception session.py (DW-example-1) no longer applies: no cross-station import there",
        "exception gone.py (DW-example-2) no longer applies: no cross-station import there",
    ]


def test_fires_on_an_exception_without_a_deferred_work_id(tmp_path: Path) -> None:
    package_dir = _plant(tmp_path, {"session.py": "from pyforge.doctor.sources import factory\n"})
    assert scan(package_dir, {"session.py": "later"}) == ["exception session.py: 'later' is not a deferred-work id"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('"""Layout."""\ndef packages() -> str:\n    return "x"\n', "line 2: a FunctionDef, not an assignment"),
        ('"""Layout."""\nfrom .catalog import CATALOG_RELATIVE\n', "line 2: a relative import"),
        ('"""Layout."""\nfrom pyforge.steward.ci import DEFAULT_REPO\n', "line 2: imports pyforge.steward.ci"),
        ('"""Layout."""\nimport pyforge.steward.bootstrap\n', "line 2: imports pyforge.steward.bootstrap"),
        ('"""Layout."""\nclass Layout:\n    pass\n', "line 2: a ClassDef, not an assignment"),
        ('"""Layout."""\nROOT = lambda: "src"\n', "line 2: a lambda"),
    ],
    ids=["function", "relative-import", "steward-from-import", "steward-import", "class", "lambda"],
)
def test_fires_when_root_layout_is_more_than_assignments(tmp_path: Path, text: str, expected: str) -> None:
    package_dir = _plant(tmp_path, {})
    (package_dir / LAYOUT_MODULE).write_text(text, encoding="utf-8")
    findings = scan(package_dir, {})
    assert len(findings) == 1
    assert findings[0].startswith(f"{LAYOUT_MODULE}: {expected}")


@pytest.mark.parametrize(
    "line",
    [
        'P = Path("src") / "shared" / "packages" / "pyforge-marshal"',
        'P = root / "src" / "shared" / "packages" / f"pyforge-{station}"',
        'P = Path("src", "shared", "packages")',
        'P = os.path.join(root, "src", "shared", "packages")',
        'P = Path("src/shared") / "packages"',
        'P = "src/shared/" + "packages"',
        'P = ("src", "shared", "packages")',
        'P = "/".join(["src", "shared", "packages"])',
    ],
    ids=["path-chain", "root-chain", "path-args", "os-path-join", "partial-string", "concat", "tuple", "str-join"],
)
def test_fires_on_a_station_packages_path_spelled_out_segment_by_segment(tmp_path: Path, line: str) -> None:
    """The round-1 review's mutant (`_MARSHAL_PKG = Path("src") / "shared" / "packages" / ...`) and its kin."""
    package_dir = _plant(tmp_path, {"upgrade.py": f"import os\nfrom pathlib import Path\n{line}\n"})
    findings = scan(package_dir, {})
    assert len(findings) == 1, findings
    assert findings[0].startswith("upgrade.py:3: spells out src/shared/packages segment by segment")


def test_a_path_that_only_shares_a_segment_is_not_reported(tmp_path: Path) -> None:
    package_dir = _plant(
        tmp_path,
        {
            "revoke.py": (
                "from pathlib import Path\n"
                'MANAGE = ("src", "platform", "manage.py")\n'
                'SCRIPTS = Path("pkg") / "src" / "scripts"\n'
                'SHARED = {"packages": [], "shared": "src"}\n'
            )
        },
    )
    assert scan(package_dir, {}) == []


def test_a_named_layout_exception_admits_its_segments_only(tmp_path: Path) -> None:
    package_dir = _plant(
        tmp_path,
        {"five_tier.py": 'def root(r):\n    return r / "src" / "shared" / "packages"\n'},
    )
    assert scan(package_dir, {}, {"five_tier.py": "DW-example-3"}) == []
    (package_dir / "five_tier.py").write_text('P = "src/shared/packages/pyforge-x"\n', encoding="utf-8")
    assert scan(package_dir, {}, {"five_tier.py": "DW-example-3"}) == [
        "five_tier.py:1: string constant 'src/shared/packages/pyforge-x' names this root; take it from root_layout.py",
        "exception five_tier.py (DW-example-3) no longer applies: no segment-by-segment station-packages path there",
    ]


def test_fires_on_a_layout_exception_that_no_longer_applies(tmp_path: Path) -> None:
    package_dir = _plant(tmp_path, {"five_tier.py": "from .root_layout import STATION_PACKAGES_DIR\n"})
    assert scan(package_dir, {}, {"five_tier.py": "DW-example-3", "gone.py": "later"}) == [
        "exception five_tier.py (DW-example-3) no longer applies: no segment-by-segment station-packages path there",
        "exception gone.py: 'later' is not a deferred-work id",
        "exception gone.py (later) no longer applies: no segment-by-segment station-packages path there",
    ]


@pytest.mark.parametrize(
    ("module", "line", "expected"),
    [
        ("upgrade.py", "from ..doctor.models import DoctorStatus", "pyforge.doctor.models"),
        ("upgrade.py", "from .. import marshal", "pyforge.marshal"),
        ("dashboard/views.py", "from ...herald import cli", "pyforge.herald"),
        (
            "upgrade.py",
            "import importlib\nM = importlib.import_module(f'pyforge.{name}.cli')",
            "<computed module name>",
        ),
        ("upgrade.py", "M = __import__(name)", "<computed module name>"),
    ],
    ids=["relative-from", "relative-name", "relative-subpackage", "import-module-fstring", "dunder-import-name"],
)
def test_fires_on_a_relative_or_computed_cross_station_import(
    tmp_path: Path, module: str, line: str, expected: str
) -> None:
    package_dir = _plant(tmp_path, {module: f"name = 'doctor'\n{line}\n"})
    findings = scan(package_dir, {})
    assert len(findings) == 1, findings
    assert findings[0].startswith(f"{module}:") and f"imports {expected};" in findings[0]


def test_a_relative_import_inside_steward_is_not_reported(tmp_path: Path) -> None:
    package_dir = _plant(
        tmp_path,
        {
            "dashboard/views.py": "from .. import catalog\nfrom ..upgrade import gate\nfrom . import models\n",
            "quarantine.py": "import importlib\nM = importlib.import_module('pyforge.steward.dashboard.x')\n",
        },
    )
    assert scan(package_dir, {}) == []
