"""Meta test -- Story 2.1 sole-``mcp``-import guard.

``sources/atlas.py`` is the ONE sanctioned site in ``pyforge.doctor`` that
may import the ``mcp`` SDK (mirrors ``sources/warden.py``'s sole
``pyforge.warden``-import pattern, applied to the ``mcp`` surface instead).
AST-scan every OTHER module in the installed ``pyforge.doctor`` package and
fail if any of them imports ``mcp`` or any of its submodules -- absolute
``import mcp[.submodule]`` and ``from mcp[.submodule] import ...`` forms,
aliased or not.

Unlike the warden guard, no relative-import resolution is needed: ``mcp``
is a third-party top-level distribution, not part of the ``pyforge``
namespace package, so there is no relative-dotted spelling that reaches it
the way ``from .. import warden`` reaches ``pyforge.warden``.

Positively proves the detector fires on a synthetic violation -- the guard
is alive, not vacuous -- mirroring ``test_no_warden_import.py``'s own
style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The one sanctioned mcp import site (Story 2.1) -- exempted from this scan.
_EXEMPT_RELATIVE_PATHS = frozenset({Path("sources") / "atlas.py"})


def _package_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_DIR.rglob("*.py")
        if path.relative_to(PACKAGE_DIR) not in _EXEMPT_RELATIVE_PATHS
    )


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _mcp_import_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "mcp" or alias.name.startswith("mcp."):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (module == "mcp" or module.startswith("mcp.")):
                violations.append(node.lineno)
    return sorted(set(violations))


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "sole-mcp-import guard found no modules to scan"


def test_sources_atlas_module_exists():
    atlas_path = PACKAGE_DIR / "sources" / "atlas.py"
    assert atlas_path.is_file(), (
        f"expected {atlas_path} -- the sanctioned mcp import site "
        "(Story 2.1) is missing"
    )


def test_sources_atlas_is_exempted_from_this_scan():
    modules = {path.relative_to(PACKAGE_DIR) for path in _package_modules()}
    assert Path("sources") / "atlas.py" not in modules


def test_no_module_outside_atlas_imports_mcp():
    for module_path in _package_modules():
        violations = _mcp_import_violations(_parse(module_path))
        assert not violations, (
            f"{module_path.relative_to(PACKAGE_DIR)} imports mcp at "
            f"line(s) {violations} -- only sources/atlas.py may import "
            "the mcp SDK (Story 2.1)"
        )


def test_sources_atlas_itself_imports_mcp():
    """Non-vacuous proof: the sanctioned site actually imports mcp
    somewhere (lazily, inside the async helper) -- so this guard is
    testing a real narrowing, not an accidentally-unused permission."""
    violations = _mcp_import_violations(
        _parse(PACKAGE_DIR / "sources" / "atlas.py")
    )
    assert violations, "sources/atlas.py does not import mcp at all"


# --- synthetic-violation positive proof (the guard is alive, not vacuous) --


def test_guard_fires_on_synthetic_plain_import():
    plain = "import mcp\n"
    assert _mcp_import_violations(ast.parse(plain)) == [1]
    submodule = "import mcp.client.stdio\n"
    assert _mcp_import_violations(ast.parse(submodule)) == [1]


def test_guard_fires_on_synthetic_from_import():
    from_import = "from mcp import ClientSession\n"
    assert _mcp_import_violations(ast.parse(from_import)) == [1]
    from_submodule = "from mcp.client.stdio import stdio_client\n"
    assert _mcp_import_violations(ast.parse(from_submodule)) == [1]


def test_guard_fires_on_synthetic_aliased_import():
    aliased = "import mcp as m\n"
    assert _mcp_import_violations(ast.parse(aliased)) == [1]
    aliased_from = "from mcp import ClientSession as CS\n"
    assert _mcp_import_violations(ast.parse(aliased_from)) == [1]


def test_guard_does_not_fire_on_unrelated_imports():
    benign = (
        "import json\n"
        "from pathlib import Path\n"
        "from ..models import Finding\n"
        "from .warden import gather as warden_gather\n"
    )
    assert _mcp_import_violations(ast.parse(benign)) == []
