"""Meta test -- P-02's sole-import-site guard for `copier` (Stories 10.1 / 12.4).
Mirrors `tests/meta/test_ad7_verdict_sole_ownership.py`'s AST-scan-
excluding-target-module technique exactly, scoped to a much narrower rule:
`import copier` / `from copier import ...` (any alias) may appear in the
installed package ONLY inside `seed/engine/copier.py`. Story 12.4 additionally
bans private/deprecated ``copier._*`` imports anywhere, including that sole
owner.

AST-scan every module in the installed `pyforge.marshal` package EXCEPT
`seed/engine/copier.py` and fail if any of them imports the `copier`
library, absolutely, under any alias:

- `import copier`, `import copier as cp`, `import copier.errors` -- an
  `ast.Import` node is ALWAYS an absolute reference (Python has no relative
  spelling of `import X`), so a bare name/alias/dotted-submodule check is
  unambiguous.
- `from copier import ...`, `from copier.errors import ...` -- but ONLY
  when `node.level == 0` (an absolute `from` import). A RELATIVE import --
  `from .copier import materialize` (exactly what `seed/engine/__init__.py`
  itself does to re-export this module's own public API) -- refers to this
  PACKAGE's own same-named submodule, not the external `copier` library,
  and must never fire. Python's own grammar disambiguates the two forms via
  `level` (0 = absolute, >0 = relative); this guard trusts that field
  rather than a same-named-suffix heuristic that could not tell them apart.

Bounds (stated, not aspirational, matching the AD-7 guard's own framing):
this is a best-effort STATIC check. Dynamic import (`importlib.import_module
("copier")`) is out of scope; `tests/unit/test_seed_engine_copier.py`'s own
plain-text scan is the independent second technique the story asks for
(belt-and-suspenders), and the real behavioral proof that `materialize()`
works lives in that same file's functional tests against real Copier.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_COPIER_ENGINE_MODULE = PACKAGE_DIR / "seed" / "engine" / "copier.py"


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_copier_engine_modules() -> list[Path]:
    # Full-path comparison, not basename -- mirrors the AD-7 guard's own
    # rationale: only seed/engine/copier.py is the sole owner -- a future
    # same-named file elsewhere in the tree must NOT inherit the exemption.
    return [path for path in _package_modules() if path != _COPIER_ENGINE_MODULE]


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _copier_import_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "copier" or alias.name.startswith("copier."):
                    violations.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if (
                node.level == 0
                and node.module is not None
                and (node.module == "copier" or node.module.startswith("copier."))
            ):
                violations.append(node.module)
    return violations


def _is_private_or_deprecated_copier_module(dotted: str) -> bool:
    """``True`` for ``copier._*`` private submodules (any depth).

    Public top-level ``copier`` and documented public submodules such as
    ``copier.errors`` are allowed *inside* ``seed/engine/copier.py`` only;
    private ``copier._*`` names are forbidden everywhere, including that
    sole-owner module (Story 12.4 / P-02).
    """
    parts = dotted.split(".")
    return len(parts) >= 2 and parts[0] == "copier" and any(part.startswith("_") for part in parts[1:])


def _private_copier_import_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_private_or_deprecated_copier_module(alias.name):
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            if _is_private_or_deprecated_copier_module(node.module):
                violations.append(node.module)
            # ``from copier import _main`` — private name on a public module.
            if node.module == "copier" or node.module.startswith("copier."):
                for alias in node.names:
                    if alias.name.startswith("_"):
                        violations.append(f"{node.module}.{alias.name}")
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _non_copier_engine_modules()
    assert modules, "sole-ownership guard found no modules to scan"
    assert _COPIER_ENGINE_MODULE.exists(), "seed/engine/copier.py missing from the installed package"


@pytest.mark.parametrize("module_path", _non_copier_engine_modules(), ids=_module_id)
def test_no_copier_import_outside_engine_module(module_path: Path):
    violations = _copier_import_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} imports the `copier` library ({violations}) -- only seed/engine/copier.py may (P-02)"
    )


def test_relative_import_of_the_local_copier_submodule_does_not_fire():
    """`seed/engine/__init__.py` legitimately does
    `from .copier import materialize` -- a RELATIVE reference to this
    package's own `copier.py`, not the external `copier` library. Only an
    ABSOLUTE `from copier import ...` (or `import copier`) may fire."""
    relative = "from .copier import materialize\n"
    assert _copier_import_violations(ast.parse(relative)) == []
    relative_dotted = "from ..engine.copier import materialize\n"
    assert _copier_import_violations(ast.parse(relative_dotted)) == []


def test_guard_is_alive_synthetic_violation_fires_and_copier_engine_module_imports_copier():
    """Non-vacuous proof: (1) the detector demonstrably fires on synthetic
    absolute-import violations in every shape the guard claims to catch,
    and (2) `seed/engine/copier.py` itself DOES import `copier` -- the
    exemption is real, not vacuous."""
    assert _copier_import_violations(ast.parse("import copier\n")) == ["copier"]
    assert _copier_import_violations(ast.parse("import copier as cp\n")) == ["cp"]
    assert _copier_import_violations(ast.parse("import copier.errors\n")) == ["copier.errors"]
    assert _copier_import_violations(ast.parse("from copier import run_copy\n")) == ["copier"]
    assert _copier_import_violations(ast.parse("from copier.errors import CopierError\n")) == ["copier.errors"]
    # A same-prefixed but unrelated package must never fire.
    assert _copier_import_violations(ast.parse("import copier_reference\n")) == []
    assert _copier_import_violations(ast.parse("from copiersomething import x\n")) == []

    tree = _parse(_COPIER_ENGINE_MODULE)
    assert _copier_import_violations(tree), (
        "seed/engine/copier.py must itself import copier -- the guard would be vacuous otherwise"
    )


@pytest.mark.parametrize("module_path", _package_modules(), ids=_module_id)
def test_no_private_copier_imports_anywhere(module_path: Path):
    """P-02: even ``seed/engine/copier.py`` must not import ``copier._*``."""
    violations = _private_copier_import_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} imports private/deprecated Copier module(s) "
        f"{violations} -- P-02 allows only public ``copier`` APIs via "
        "seed/engine/copier.py"
    )


def test_private_copier_detector_is_alive():
    assert _private_copier_import_violations(ast.parse("import copier._main\n")) == ["copier._main"]
    assert _private_copier_import_violations(ast.parse("from copier._user_data import AnswersMap\n")) == [
        "copier._user_data"
    ]
    assert _private_copier_import_violations(ast.parse("from copier import _main\n")) == ["copier._main"]
    assert _private_copier_import_violations(ast.parse("import copier\n")) == []
    assert _private_copier_import_violations(ast.parse("from copier.errors import CopierError\n")) == []
    assert _private_copier_import_violations(ast.parse("import copier_private\n")) == []
