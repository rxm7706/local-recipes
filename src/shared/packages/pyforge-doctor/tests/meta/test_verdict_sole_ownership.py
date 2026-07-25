"""Meta test — the ``pyforge.doctor`` ``verdict.py`` sole-ownership guard
(Story 1.1). Mirrors ``pyforge-warden``'s sibling
``tests/meta/test_verdict_sole_ownership.py`` AST-scan technique, adapted to
Doctor's own domain.

AST-scan every module in the installed package EXCEPT ``verdict.py`` and
fail if any of them:

(a) calls an exit primitive (``sys.exit`` / ``os._exit`` / ``SystemExit``,
    including ``from sys import exit as <alias>`` / ``from os import _exit
    as <alias>`` aliases, positional or keyword args, or an aliased
    ``import sys as s`` / ``import os as o`` module reference) with an int
    literal in Doctor's frozen exit-code domain ``{0, 2, 130}`` (AD-2) or
    with a simple module-level ``NAME = <int literal>`` constant resolving
    to one;
(b) imports (or dereferences) a ``_``-private name from ``verdict`` —
    through ANY local name bound to the verdict module, not just the
    literal name ``verdict``.

UNLIKE warden's sibling guard, there is no 7-rung status lattice here
(``DoctorStatus`` is just ``ok``/``warn``/``fail``, with no ordering claim
to protect), so the lattice-order-literal detector is deliberately dropped
entirely — only (a) and (b) remain.

Also unlike warden's domain ``{1, 2, 130}``, Doctor's domain includes ``0``:
even a "clean exit" literal must be sole-owned by ``verdict.py`` here.

Positively proves the exit-literal detector fires on a SYNTHETIC violation
and that ``verdict.py`` itself structurally defines the exit-projection
function + the SIGINT constant — the guard is alive, not vacuous.
(``verdict.py``'s own body never itself CALLS an exit primitive — it is a
pure projection function returning plain ints — so "the detector fires on
verdict.py itself", warden's own non-vacuous proof technique for its
lattice-order check, isn't the applicable proof here.)

Bounds (stated, not aspirational): this is a best-effort STATIC check.
Indirection through helper functions (``exit(code())``), values built via
f-strings/arithmetic, dynamic attribute access (``getattr``), and
argparse's ``parser.error()`` (which exits 2 internally) are out of scope;
the runtime contract tests in ``tests/unit`` are the behavioral backstop.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
GUARDED_EXIT_LITERALS = frozenset({0, 2, 130})


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_verdict_modules() -> list[Path]:
    return [path for path in _package_modules() if path.name != "verdict.py"]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _exit_call_aliases(tree: ast.Module) -> frozenset[str]:
    """Bare names that invoke an exit primitive: the builtins plus any
    ``from sys import exit as X`` / ``from os import _exit as Y`` alias."""
    aliases = {"exit", "SystemExit"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "sys":
            for alias in node.names:
                if alias.name == "exit":
                    aliases.add(alias.asname or alias.name)
        elif node.module == "os":
            for alias in node.names:
                if alias.name == "_exit":
                    aliases.add(alias.asname or alias.name)
    return frozenset(aliases)


def _exit_module_aliases(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    """Names bound to the sys / os MODULES themselves — ``import sys as s``
    makes ``s.exit(2)`` an exit call the attribute check must see."""
    sys_names = {"sys"}
    os_names = {"os"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == "sys":
                sys_names.add(alias.asname or alias.name)
            elif alias.name == "os":
                os_names.add(alias.asname or alias.name)
    return (frozenset(sys_names), frozenset(os_names))


def _module_int_constants(tree: ast.Module) -> dict[str, int]:
    """Simple module-level ``NAME = <int literal>`` bindings (top level only
    — a best-effort constant table, not a dataflow analysis)."""
    constants: dict[str, int] = {}
    for stmt in tree.body:
        value: ast.expr | None
        targets: list[ast.expr]
        if isinstance(stmt, ast.Assign):
            value, targets = stmt.value, stmt.targets
        elif isinstance(stmt, ast.AnnAssign):
            value, targets = stmt.value, [stmt.target]
        else:
            continue
        if (
            isinstance(value, ast.Constant)
            and isinstance(value.value, int)
            and not isinstance(value.value, bool)
        ):
            for target in targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value.value
    return constants


def _is_exit_callable(
    func: ast.expr,
    exit_aliases: frozenset[str],
    sys_names: frozenset[str],
    os_names: frozenset[str],
) -> bool:
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if (func.value.id in sys_names and func.attr == "exit") or (
                func.value.id in os_names and func.attr == "_exit"
            ):
                return True
        return func.attr == "SystemExit"
    return isinstance(func, ast.Name) and func.id in exit_aliases


def _exit_literal_violations(tree: ast.Module) -> list[int]:
    exit_aliases = _exit_call_aliases(tree)
    sys_names, os_names = _exit_module_aliases(tree)
    constants = _module_int_constants(tree)
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_exit_callable(
            node.func, exit_aliases, sys_names, os_names
        ):
            continue
        arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
        for arg in arguments:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, int)
                and not isinstance(arg.value, bool)
                and arg.value in GUARDED_EXIT_LITERALS
            ):
                violations.append(node.lineno)
            elif (
                isinstance(arg, ast.Name)
                and constants.get(arg.id) in GUARDED_EXIT_LITERALS
            ):
                violations.append(node.lineno)
    return violations


def _verdict_bound_names(tree: ast.Module) -> frozenset[str]:
    """Every local name bound to the verdict module: ``import ...verdict as
    v``, ``from . import verdict [as w]``, ``from pkg import verdict [as
    w]``."""
    names = {"verdict"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "verdict" or alias.name.endswith(".verdict"):
                    if alias.asname is not None:
                        names.add(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "verdict":
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _private_verdict_references(tree: ast.Module) -> list[str]:
    verdict_names = _verdict_bound_names(tree)
    references: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_tail = (node.module or "").split(".")[-1]
            if module_tail == "verdict":
                references.extend(
                    alias.name for alias in node.names if alias.name.startswith("_")
                )
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            # x._priv where x is any name bound to the verdict module ...
            if isinstance(node.value, ast.Name) and node.value.id in verdict_names:
                references.append(node.attr)
            # ... or pkg.verdict._priv via a plain `import pkg.verdict`.
            elif (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "verdict"
            ):
                references.append(node.attr)
    return references


def test_package_scan_surface_is_not_empty():
    modules = _non_verdict_modules()
    assert modules, "sole-ownership guard found no modules to scan"
    names = {path.name for path in _package_modules()}
    assert "verdict.py" in names, "verdict.py missing from the installed package"


@pytest.mark.parametrize(
    "module_path", _non_verdict_modules(), ids=lambda p: p.name
)
def test_no_exit_literal_projection_outside_verdict(module_path: Path):
    violations = _exit_literal_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} calls an exit primitive with a value from "
        f"{sorted(GUARDED_EXIT_LITERALS)} at line(s) {violations} — only "
        "verdict.py projects"
    )


@pytest.mark.parametrize(
    "module_path", _non_verdict_modules(), ids=lambda p: p.name
)
def test_no_private_verdict_import_outside_verdict(module_path: Path):
    references = _private_verdict_references(_parse(module_path))
    assert not references, (
        f"{module_path.name} references private verdict name(s) {references}"
    )


def test_exit_detector_sees_aliases_keywords_and_constants():
    """The detector's own coverage: aliased imports, keyword args, and
    module-level int constants all fire; benign (non-guarded) values do
    not."""
    aliased = "from sys import exit as bail\nbail(2)\n"
    assert _exit_literal_violations(ast.parse(aliased)) == [2]
    os_alias = "from os import _exit as die\ndie(130)\n"
    assert _exit_literal_violations(ast.parse(os_alias)) == [2]
    keyword = "import sys\nsys.exit(code=0)\n"
    assert _exit_literal_violations(ast.parse(keyword)) == [2]
    module_alias = "import sys as s\ns.exit(2)\n"
    assert _exit_literal_violations(ast.parse(module_alias)) == [2]
    constant = "import sys\nFAIL = 2\nsys.exit(FAIL)\n"
    assert _exit_literal_violations(ast.parse(constant)) == [3]
    # 1 is NOT in Doctor's guarded domain {0, 2, 130} (unlike warden's,
    # which guards 1) — a bare sys.exit(1) elsewhere is out of this guard's
    # scope by design.
    benign = "import sys\nOK = 1\nsys.exit(OK)\nsys.exit(1)\n"
    assert _exit_literal_violations(ast.parse(benign)) == []


def test_private_detector_sees_verdict_module_aliases():
    aliased = "from pyforge.doctor import verdict as v\nx = v._SOME_PRIVATE\n"
    assert _private_verdict_references(ast.parse(aliased)) == ["_SOME_PRIVATE"]
    plain_import = (
        "import pyforge.doctor.verdict\n"
        "x = pyforge.doctor.verdict._SOME_PRIVATE\n"
    )
    assert _private_verdict_references(ast.parse(plain_import)) == ["_SOME_PRIVATE"]
    public_only = (
        "from pyforge.doctor import verdict\ncode = verdict.exit_code_for\n"
    )
    assert _private_verdict_references(ast.parse(public_only)) == []


def test_guard_is_alive_synthetic_violation_fires_and_verdict_defines_projection():
    """Non-vacuous proof: (1) the exit-literal detector demonstrably fires
    on a synthetic violation, and (2) verdict.py structurally defines the
    exit-projection function + the SIGINT constant. (verdict.py's own body
    never calls an exit primitive itself — it's a pure projection function
    — so proving the detector 'fires on verdict.py', warden's own technique
    for its lattice-order check, isn't applicable here; there is no lattice
    to encode in the first place.)"""
    synthetic_violation = "import sys\nsys.exit(2)\n"
    assert _exit_literal_violations(ast.parse(synthetic_violation)) == [2]

    verdict_path = PACKAGE_DIR / "verdict.py"
    tree = _parse(verdict_path)
    assigned: set[str] = set()
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assigned.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)
    assert "EXIT_SIGINT" in assigned
    assert "exit_code_for" in functions
