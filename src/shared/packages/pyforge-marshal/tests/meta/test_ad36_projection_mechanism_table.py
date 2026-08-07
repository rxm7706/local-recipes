"""Meta test -- the AD-36 "projection mechanism is declared in ONE table,
no module branches on platform outside it" guard (Story 6.2). Mirrors
``test_ad19_no_adapter_branch.py``'s AST-scan technique exactly, adapted to
a different structural signature: platform comparisons instead of
adapter-name comparisons.

AST-scan every module in ``pyforge.marshal.cli``/``core`` (EXCLUDING
``core/skill_projection.py`` itself, the one module AD-36 designates as the
table's owner)/``supervisor``/``ports`` -- EXCLUDING ``pyforge.marshal.
adapters`` entirely, mirroring AD-19's own identical carve-out (this repo
already declares ``adapters/process_posix.py``/``adapters/observer_mux.py``
the legitimate POSIX-only seam; this guard does not relitigate that
pre-existing, differently-scoped commitment) -- and fail if any of them
contains an ``ast.Compare`` node testing equality (``==``) or membership
(``in``) between ``os.name``/``sys.platform`` (an ``Attribute`` node
``<Name>.name`` where the ``Name`` is ``os``, or ``<Name>.platform`` where
the ``Name`` is ``sys``) and a string constant (or, for ``in``, a
collection of string constants). This is the exact shape AD-36 forbids: a
module outside ``core/skill_projection.py`` deciding "on this platform, do
X" itself, rather than calling ``core.skill_projection.
mechanism_for_platform``.

Bounds (stated, not aspirational): a best-effort STATIC check, like the
AD-7/AD-19/AD-23 guards it mirrors. It only recognizes a direct
``os.name``/``sys.platform`` reference -- an indirect alias assigned to a
local variable under some other name is out of scope, exactly as AD-19's
own detector documents for adapter-name aliases. The detector's own
aliveness is proven via a synthetic violation it is asserted to catch."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

_ADAPTERS_DIR = PACKAGE_DIR / "adapters"
_OWNER_MODULE = PACKAGE_DIR / "core" / "skill_projection.py"

_SCANNED_SUBPACKAGES = ("cli", "core", "supervisor", "ports")


def _package_modules() -> list[Path]:
    modules: list[Path] = []
    for subpackage in _SCANNED_SUBPACKAGES:
        modules.extend(sorted((PACKAGE_DIR / subpackage).rglob("*.py")))
    return [path for path in modules if path.resolve() != _OWNER_MODULE.resolve()]


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_platform_attr(node: ast.expr) -> bool:
    """``True`` for ``os.name`` or ``sys.platform`` -- an ``Attribute``
    whose value is a bare ``Name`` ``os``/``sys`` and whose own ``attr``
    matches the corresponding platform field."""
    if not isinstance(node, ast.Attribute):
        return False
    if not isinstance(node.value, ast.Name):
        return False
    return (node.value.id == "os" and node.attr == "name") or (
        node.value.id == "sys" and node.attr == "platform"
    )


def _is_string_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_string_constant_collection(node: ast.expr) -> bool:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_string_constant(elt) for elt in node.elts)
    return False


def _platform_branch_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if len(node.ops) != 1:
            continue
        op = node.ops[0]
        left = node.left
        [right] = node.comparators
        if isinstance(op, ast.Eq) and (
            (_is_platform_attr(left) and _is_string_constant(right))
            or (_is_string_constant(left) and _is_platform_attr(right))
        ):
            violations.append(node.lineno)
        elif isinstance(op, ast.In) and _is_platform_attr(left) and _is_string_constant_collection(right):
            violations.append(node.lineno)
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "AD-36 projection-mechanism-table guard found no modules to scan"


def test_adapters_package_is_excluded_from_the_scan_surface():
    scanned = {path.resolve() for path in _package_modules()}
    assert not any(_ADAPTERS_DIR in path.parents for path in scanned)


def test_owner_module_is_excluded_from_its_own_scan_surface():
    scanned = {path.resolve() for path in _package_modules()}
    assert _OWNER_MODULE.resolve() not in scanned


@pytest.mark.parametrize("module_path", _package_modules(), ids=_module_id)
def test_no_platform_branch_outside_skill_projection(module_path: Path):
    violations = _platform_branch_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} branches on os.name/sys.platform directly at "
        f"line(s) {violations} -- only core/skill_projection.py's "
        "PROJECTION_MECHANISM_BY_PLATFORM table / mechanism_for_platform is "
        "structurally permitted to decide this (AD-36); every other module "
        "must call mechanism_for_platform instead"
    )


# --- detector self-test: non-vacuous proof -----------------------------------


def test_detector_fires_on_synthetic_os_name_equality():
    synthetic_violation = 'import os\nif os.name == "posix":\n    pass\n'
    assert _platform_branch_violations(ast.parse(synthetic_violation)) == [2]


def test_detector_fires_on_synthetic_sys_platform_equality_reversed_operands():
    synthetic_violation = 'import sys\nif "darwin" == sys.platform:\n    pass\n'
    assert _platform_branch_violations(ast.parse(synthetic_violation)) == [2]


def test_detector_fires_on_membership_form():
    synthetic_violation = 'import sys\nif sys.platform in ("win32", "cygwin"):\n    pass\n'
    assert _platform_branch_violations(ast.parse(synthetic_violation)) == [2]


def test_detector_does_not_fire_on_an_unrelated_equality_comparison():
    tree = ast.parse('mechanism = "symlink"\nif mechanism == "symlink":\n    pass\n')
    assert _platform_branch_violations(tree) == []


def test_detector_does_not_fire_on_an_unrelated_attribute():
    tree = ast.parse('import os\nif os.getcwd() == "/tmp":\n    pass\n')
    assert _platform_branch_violations(tree) == []
