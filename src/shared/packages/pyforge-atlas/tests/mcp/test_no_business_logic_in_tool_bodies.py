"""AC-5 — AST scan: NO metric/business logic in MCP tool bodies (AD-7).

Structural, defensible assertions over ``mcp/tools.py`` (and the sibling
``session.py`` / ``audit.py``):

1. none of the business-logic libraries is imported;
2. no business-logic library name ever appears as a Name/Attribute;
3. every call made inside a tool body in ``tools.py`` resolves to the
   session seam (``_session.*`` / the yielded session / the catalog) or a
   small stdlib allowlist (datetime/sorted/isinstance/...).
"""

from __future__ import annotations

import ast
from pathlib import Path

MCP_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "atlas"
    / "mcp"
)

BUSINESS_LOGIC_LIBS = {
    "pandas",
    "numpy",
    "duckdb",
    "sqlite3",
    "sqlalchemy",
    "ibis",
    "pyarrow",
}

# Common aliases too — `import pandas as pd` would rename the Name nodes.
BUSINESS_LOGIC_NAMES = BUSINESS_LOGIC_LIBS | {"pd", "np"}

# Call roots a THIN tool body may use (AD-7): the single session seam +
# trivial stdlib. `s` is the yielded session (s.run / catalog access);
# `result` is session.run's return dict (`result.keys()` — name plumbing,
# not aggregation).
ALLOWED_CALL_ROOTS = {
    "_session",
    "_nl",  # D3: the NL-interface seam (pyforge.atlas.nl) — like _session, a delegated
            # seam; the query_vizro_ai tool body only calls _nl.query_vizro_ai (AD-7), the
            # backend-resolution + BSL-grounded (deferred) Vizro-AI logic lives in nl/.
    "s",
    "result",
    "sorted",
    "isinstance",
    "datetime",
    "AtlasMCPError",
    "Path",
    "dict",
    "list",
    "str",
}


def _tree(filename: str) -> ast.Module:
    path = MCP_DIR / filename
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def _call_root(func: ast.expr) -> str | None:
    """The base identifier of a call target, recursing through attribute
    chains and chained calls (`_session.loaded_catalog(s).load(...)`)."""
    node = func
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return None


def test_no_business_logic_imports_in_mcp_modules():
    for filename in ("tools.py", "session.py", "audit.py", "__init__.py", "server.py"):
        imported = _imported_modules(_tree(filename))
        hits = imported & BUSINESS_LOGIC_LIBS
        assert not hits, f"mcp/{filename} imports business-logic libs: {hits}"


def test_no_business_logic_names_anywhere_in_tools_py():
    hits = set()
    for node in ast.walk(_tree("tools.py")):
        if isinstance(node, ast.Name) and node.id in BUSINESS_LOGIC_NAMES:
            hits.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in BUSINESS_LOGIC_LIBS:
            hits.add(node.attr)
    assert not hits, f"business-logic identifiers found in mcp/tools.py: {hits}"


def test_tool_bodies_only_call_the_session_seam_and_trivial_stdlib():
    tree = _tree("tools.py")
    offending: list[str] = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            root = _call_root(node.func)
            if root not in ALLOWED_CALL_ROOTS:
                offending.append(f"{fn.name}: call root {root!r}")
    assert not offending, (
        "tool bodies must only call the session/catalog seam + trivial "
        f"stdlib (AD-7): {offending}"
    )
