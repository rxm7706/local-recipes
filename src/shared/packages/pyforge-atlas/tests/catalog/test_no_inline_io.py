"""Gate checks 2 + 3 (AC-2 / AC-3): structural import meta-tests.

Check 2 — no-inline-IO: no direct HTTP/DB client imports in package code;
data access happens ONLY via catalog datasets (AC-2, enforced
structurally). Polices every later wave's node code (Wave B lands nodes
against an already-armed gate).

Check 3 — AD-1 import direction: no ``dagster`` / ``kedro_mcp`` imports in
package code (the spine pairs this meta-test with ``kedro-catalog-check``
explicitly).

Review-pass P3: the scan is ``ATLAS_PKG.rglob('*.py')`` minus the four
exempt root-level framework files (conftest ``NO_INLINE_IO_EXEMPT``) — NOT
a hardcoded dir list, so coverage is complete by construction: any new
module anywhere in the package (including subpackage ``__init__.py``
files) is scanned automatically, and a not-yet-existing dir needs no
tolerance logic. Dynamic imports (``importlib.import_module`` /
``__import__`` with a denylisted string literal) are detected too.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .conftest import ATLAS_PKG, NO_INLINE_IO_EXEMPT

# AC-2 denylist (story core + review-pass P3 extensions: urllib3 —
# requests' engine used directly; sqlalchemy — DB access; subprocess —
# shelling out to curl/wget/sqlite3 bypasses any import denylist).
IO_DENYLIST = (
    "requests",
    "urllib.request",
    "urllib3",
    "httpx",
    "aiohttp",
    "sqlite3",
    "sqlalchemy",
    "subprocess",
    "google.cloud.bigquery",
)

# AD-1 import-direction denylist.
AD1_DENYLIST = ("dagster", "kedro_mcp")


def _iter_scanned_files():
    """Every .py in the package except the exempt root-level framework
    files — exempt + scanned = the whole package, by construction."""
    for path in sorted(ATLAS_PKG.rglob("*.py")):
        if str(path.relative_to(ATLAS_PKG)) in NO_INLINE_IO_EXEMPT:
            continue
        yield path


def _denylisted(name: str, denylist) -> bool:
    return any(name == d or name.startswith(d + ".") for d in denylist)


def _imported_names(path: Path) -> set[str]:
    """Statically imported module names + dynamic-import string literals
    (P3: ``importlib.import_module("x")`` / ``__import__("x")``)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None or node.level:
                # `from . import X` (module=None) and any relative import
                # (level > 0) are package-internal — never a denylist hit.
                continue
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            is_dynamic_import = (
                isinstance(func, ast.Name) and func.id in ("__import__", "import_module")
            ) or (isinstance(func, ast.Attribute) and func.attr == "import_module")
            if not is_dynamic_import or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.add(arg.value)
    return names


def _violations(denylist) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _iter_scanned_files():
        hits = [
            name
            for name in sorted(_imported_names(path))
            if _denylisted(name, denylist)
        ]
        if hits:
            found[str(path.relative_to(ATLAS_PKG.parents[2]))] = hits
    return found


def test_scan_covers_the_whole_package():
    """P3 coverage invariant: exempt + scanned == every .py in the package
    (trivially true with rglob — this pins the exempt set against growth)."""
    all_files = {str(p.relative_to(ATLAS_PKG)) for p in ATLAS_PKG.rglob("*.py")}
    scanned = {str(p.relative_to(ATLAS_PKG)) for p in _iter_scanned_files()}
    assert all_files == scanned | (NO_INLINE_IO_EXEMPT & all_files)
    # the exempt set must not silently exempt files that do not exist
    # at the root (e.g. a typo'd entry would exempt nothing forever)
    missing_exempt = {e for e in NO_INLINE_IO_EXEMPT if not (ATLAS_PKG / e).is_file()}
    assert not missing_exempt, f"exempt entries with no matching file: {missing_exempt}"


def test_no_inline_io_in_package_code():
    violations = _violations(IO_DENYLIST)
    assert not violations, (
        "direct HTTP/DB/process client imports found in package code — data "
        f"access must go through catalog datasets (AC-2): {violations}"
    )


def test_ad1_import_direction():
    violations = _violations(AD1_DENYLIST)
    assert not violations, (
        "AD-1 violation — pipeline code must not import the orchestration "
        f"(dagster) or MCP layers: {violations}"
    )
