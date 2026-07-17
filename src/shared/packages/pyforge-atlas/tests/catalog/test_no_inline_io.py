"""Gate checks 2 + 3 (AC-2 / AC-3): structural import meta-tests.

Check 2 — no-inline-IO: no direct HTTP/DB client imports in node code;
data access happens ONLY via catalog datasets (AC-2, enforced
structurally). Polices every later wave's node code (Wave B lands nodes
against an already-armed gate).

Check 3 — AD-1 import direction: no ``dagster`` / ``kedro_mcp`` imports in
the same four dirs (the spine pairs this meta-test with
``kedro-catalog-check`` explicitly).

Both walks tolerate not-yet-existing dirs so the gate stays green against
the A1 scaffold state.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .conftest import ATLAS_PKG, NODE_DIRS

# AC-2 denylist (verbatim from the story).
IO_DENYLIST = (
    "requests",
    "urllib.request",
    "httpx",
    "aiohttp",
    "sqlite3",
    "google.cloud.bigquery",
)

# AD-1 import-direction denylist.
AD1_DENYLIST = ("dagster", "kedro_mcp")


def _iter_node_files():
    for sub in NODE_DIRS:
        base = ATLAS_PKG / sub
        if not base.is_dir():
            continue  # scaffold state — dir not landed yet
        yield from sorted(base.rglob("*.py"))


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:  # relative import — package-internal
                continue
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _violations(denylist) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _iter_node_files():
        hits = [
            name
            for name in sorted(_imported_names(path))
            if any(name == d or name.startswith(d + ".") for d in denylist)
        ]
        if hits:
            found[str(path.relative_to(ATLAS_PKG.parents[2]))] = hits
    return found


def test_no_inline_io_in_node_code():
    violations = _violations(IO_DENYLIST)
    assert not violations, (
        "direct HTTP/DB client imports found in node code — data access must "
        f"go through catalog datasets (AC-2): {violations}"
    )


def test_ad1_import_direction():
    violations = _violations(AD1_DENYLIST)
    assert not violations, (
        "AD-1 violation — pipeline code must not import the orchestration "
        f"(dagster) or MCP layers: {violations}"
    )
