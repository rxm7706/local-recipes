"""Meta test -- seed module layer import rules (Story 12.4, architecture §4).

AST-scan every module under ``pyforge.marshal.seed`` and enforce:

1. **``detect`` never imports ``apply`` or ``engine``** (P-pattern table,
   architecture module-dependency rules).
2. **No upward imports** from lower layers: ``model``/``state``/``regions``/
   ``engine``/``derive``/``fs``/``errors`` must not import ``detect``,
   ``plan``, ``apply``, ``migrate``, or ``verbs``.
3. **``fs`` imports nothing from the package except ``errors``** (the
   architecture's leaf write primitive).

Mirrors ``tests/unit/test_seed_detect_optout.py::test_optout_imports_nothing_
upward_from_detect`` but generalises the guard to the whole ``seed/`` tree
and lives in ``tests/meta/`` as a build-breaking pattern rule.

Bounds (stated, not aspirational): TYPE_CHECKING-only imports are ignored,
matching ``test_p07_no_hash_comparison_in_apply.py``'s precedent. Relative
imports are resolved to absolute module names before comparison.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_SEED_DIR = PACKAGE_DIR / "seed"

_DETECT_FORBIDDEN = (
    "pyforge.marshal.seed.apply",
    "pyforge.marshal.seed.engine",
)

_UPWARD_FORBIDDEN = (
    "pyforge.marshal.seed.detect",
    "pyforge.marshal.seed.plan",
    "pyforge.marshal.seed.apply",
    "pyforge.marshal.seed.migrate",
    "pyforge.marshal.seed.verbs",
)

_LOWER_LAYER_DIRS = (
    _SEED_DIR / "model",
    _SEED_DIR / "state",
    _SEED_DIR / "regions",
    _SEED_DIR / "engine",
    _SEED_DIR / "derive",
    _SEED_DIR / "fs",
    _SEED_DIR / "errors",
)


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _package_for(path: Path) -> str:
    """Absolute package name for the directory that owns ``path``."""
    parts = list(path.relative_to(PACKAGE_DIR).with_suffix("").parts)
    if parts:
        parts = parts[:-1]
    return ".".join(("pyforge.marshal", *parts)) if parts else "pyforge.marshal"


def _is_type_checking_test(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _imported_modules(tree: ast.AST, package: str) -> set[str]:
    """Every runtime-imported module name, relative imports resolved."""
    modules: set[str] = set()

    def visit(node: ast.AST, guarded: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking_test(child.test):
                for stmt in child.body:
                    visit(stmt, True)
                for stmt in child.orelse:
                    visit(stmt, guarded)
                continue
            if not guarded:
                if isinstance(child, ast.Import):
                    modules.update(alias.name for alias in child.names)
                elif isinstance(child, ast.ImportFrom):
                    if child.level == 0:
                        if child.module is not None:
                            modules.add(child.module)
                    else:
                        modules.add(
                            importlib.util.resolve_name(
                                "." * child.level + (child.module or ""),
                                package,
                            )
                        )
            visit(child, guarded)

    visit(tree, False)
    return modules


def _forbidden_hits(modules: set[str], forbidden: tuple[str, ...]) -> list[str]:
    return sorted(
        module for module in modules if any(module == layer or module.startswith(f"{layer}.") for layer in forbidden)
    )


def _lower_layer_modules() -> list[Path]:
    modules: list[Path] = []
    for directory in _LOWER_LAYER_DIRS:
        if directory.is_file() and directory.suffix == ".py":
            modules.append(directory)
        elif directory.is_dir():
            modules.extend(sorted(directory.rglob("*.py")))
    # fs.py and errors.py live as files under seed/, not as packages.
    for leaf in ("fs.py", "errors.py"):
        path = _SEED_DIR / leaf
        if path.is_file() and path not in modules:
            modules.append(path)
    return sorted(set(modules))


def _detect_modules() -> list[Path]:
    detect_dir = _SEED_DIR / "detect"
    return sorted(detect_dir.rglob("*.py")) if detect_dir.is_dir() else []


def test_layer_scan_surfaces_are_not_empty():
    assert _lower_layer_modules(), "layer-import guard found no lower-layer modules to scan"
    assert _detect_modules(), "layer-import guard found no detect modules to scan"


@pytest.mark.parametrize("module_path", _lower_layer_modules(), ids=_module_id)
def test_lower_layers_never_import_upward(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    hits = _forbidden_hits(
        _imported_modules(tree, _package_for(module_path)),
        _UPWARD_FORBIDDEN,
    )
    assert not hits, (
        f"{_module_id(module_path)} imports forbidden upward module(s): {hits} "
        "-- lower seed layers must not import detect/plan/apply/migrate/verbs"
    )


@pytest.mark.parametrize("module_path", _detect_modules(), ids=_module_id)
def test_detect_never_imports_apply_or_engine(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    hits = _forbidden_hits(
        _imported_modules(tree, _package_for(module_path)),
        _DETECT_FORBIDDEN,
    )
    assert not hits, (
        f"{_module_id(module_path)} imports forbidden module(s): {hits} -- detect must never import apply/engine"
    )


def test_fs_imports_only_errors_from_the_seed_package():
    fs_path = _SEED_DIR / "fs.py"
    tree = ast.parse(fs_path.read_text(encoding="utf-8"), filename=str(fs_path))
    modules = _imported_modules(tree, _package_for(fs_path))
    seed_imports = sorted(
        module for module in modules if module == "pyforge.marshal.seed" or module.startswith("pyforge.marshal.seed.")
    )
    assert seed_imports == ["pyforge.marshal.seed.errors"], (
        f"seed/fs.py must import only seed.errors from the package, saw: {seed_imports}"
    )


def test_guard_is_alive_on_synthetic_upward_import():
    tree = ast.parse("from pyforge.marshal.seed.apply import run_apply\n")
    hits = _forbidden_hits(
        _imported_modules(tree, "pyforge.marshal.seed.detect"),
        _DETECT_FORBIDDEN,
    )
    assert hits == ["pyforge.marshal.seed.apply"]
