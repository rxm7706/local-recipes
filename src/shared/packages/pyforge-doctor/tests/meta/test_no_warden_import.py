"""Meta test -- AD-3 one-way dependency guard (Story 1.1, narrowed 1.2).

Doctor's taxonomy structurally mirrors ``pyforge.warden``'s but never
imports from it (see ``models.py``'s module docstring for the rationale).
The ONE sanctioned exception is ``sources/warden.py`` (architecture spine
AD-1): it is the sole gather filter allowed to import
``pyforge.warden.engines`` (Story 1.2, FR-1), so it is exempted from this
scan. AST-scan every OTHER module in the installed ``pyforge.doctor``
package and fail if any of them imports ``pyforge.warden`` or any of its
submodules -- in absolute OR relative form: ``pyforge`` is a namespace
package shared by both dists, so ``from .. import warden`` reaches
pyforge.warden just as surely as the absolute spelling, and relative
imports are this package's own house style.

Positively proves the detector fires on a synthetic violation -- the guard
is alive, not vacuous -- mirroring the sole-ownership meta-test's own style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The one sanctioned import site (AD-1) -- exempted from this scan; its own
# narrower guard (test_sources_warden_no_subprocess.py) restricts it to the
# ``engines`` submodule only and forbids it from ever shelling out itself.
_EXEMPT_RELATIVE_PATHS = frozenset({Path("sources") / "warden.py"})


def _package_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_DIR.rglob("*.py")
        if path.relative_to(PACKAGE_DIR) not in _EXEMPT_RELATIVE_PATHS
    )


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_package_parts(path: Path) -> tuple[str, ...]:
    """The package that relative imports in the module at ``path`` resolve
    against: its containing package -- which for an ``__init__.py`` is the
    directory itself, so ``path.parent`` serves both cases."""
    rel = path.relative_to(PACKAGE_DIR)
    return ("pyforge", "doctor", *rel.parent.parts)


def _resolve_import_from(
    node: ast.ImportFrom, package_parts: tuple[str, ...]
) -> str | None:
    """The absolute dotted module a ``from ... import`` targets, resolving
    relative forms against ``package_parts``. None when the relative level
    climbs beyond the top-level package (a runtime error anyway)."""
    if not node.level:
        return node.module or ""
    if node.level - 1 >= len(package_parts):
        return None
    base = package_parts[: len(package_parts) - (node.level - 1)]
    if node.module:
        return ".".join((*base, node.module))
    return ".".join(base)


def _warden_import_violations(
    tree: ast.Module, package_parts: tuple[str, ...] = ("pyforge", "doctor")
) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pyforge.warden" or alias.name.startswith(
                    "pyforge.warden."
                ):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            # Resolve relative forms (`from .. import warden`,
            # `from ..warden.models import X`) to their absolute target
            # first -- they reach pyforge.warden through the shared
            # namespace package without ever spelling it absolutely
            # (review finding, 2026-07-30).
            module = _resolve_import_from(node, package_parts)
            if module is None:
                continue
            if module == "pyforge.warden" or module.startswith("pyforge.warden."):
                violations.append(node.lineno)
            # `from pyforge import warden` names the submodule as an alias
            # under the PARENT module ("pyforge"), not "pyforge.warden" --
            # the two checks above miss this form entirely (review finding,
            # 2026-07-30).
            elif module == "pyforge" and any(
                alias.name == "warden" for alias in node.names
            ):
                violations.append(node.lineno)
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "no-warden-import guard found no modules to scan"


def test_no_module_imports_pyforge_warden():
    for module_path in _package_modules():
        violations = _warden_import_violations(
            _parse(module_path), _module_package_parts(module_path)
        )
        assert not violations, (
            f"{module_path.name} imports pyforge.warden at line(s) "
            f"{violations} -- only sources/warden.py may import "
            "pyforge.warden (AD-1), and only its engines submodule"
        )


def test_sources_warden_is_exempted_from_this_scan():
    """The one sanctioned exception (AD-1) is excluded here by design --
    its own narrower guard (test_sources_warden_no_subprocess.py) covers
    it instead."""
    modules = {path.relative_to(PACKAGE_DIR) for path in _package_modules()}
    assert Path("sources") / "warden.py" not in modules


def test_guard_fires_on_synthetic_import_violation():
    plain = "import pyforge.warden\n"
    assert _warden_import_violations(ast.parse(plain)) == [1]
    submodule = "import pyforge.warden.models\n"
    assert _warden_import_violations(ast.parse(submodule)) == [1]
    from_import = "from pyforge.warden import models\n"
    assert _warden_import_violations(ast.parse(from_import)) == [1]
    from_submodule = "from pyforge.warden.verdict import exit_code_for\n"
    assert _warden_import_violations(ast.parse(from_submodule)) == [1]
    parent_alias = "from pyforge import warden\n"
    assert _warden_import_violations(ast.parse(parent_alias)) == [1]


def test_guard_fires_on_synthetic_relative_import_violation():
    # Resolved against the default package parts ("pyforge", "doctor"):
    # two dots climb to `pyforge`, so each of these reaches pyforge.warden
    # without ever spelling it absolutely (review finding, 2026-07-30).
    parent_alias = "from .. import warden\n"
    assert _warden_import_violations(ast.parse(parent_alias)) == [1]
    submodule = "from ..warden import models\n"
    assert _warden_import_violations(ast.parse(submodule)) == [1]
    deep = "from ..warden.verdict import exit_code_for\n"
    assert _warden_import_violations(ast.parse(deep)) == [1]


def test_guard_does_not_fire_on_unrelated_imports():
    benign = (
        "import pyforge.doctor.models\n"
        "from pyforge.doctor import verdict\n"
        "from . import models\n"
        "from .models import Finding\n"
        "import json\n"
    )
    assert _warden_import_violations(ast.parse(benign)) == []
