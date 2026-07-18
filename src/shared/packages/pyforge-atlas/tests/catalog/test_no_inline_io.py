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

# AD-1 import-direction denylist. ``kedro_dagster`` joins ``dagster`` /
# ``kedro_mcp`` (Story C1): the orchestration glue is a replaceable dependency
# that ONLY the glue module may touch.
AD1_DENYLIST = ("dagster", "kedro_dagster", "kedro_mcp")

# The SINGLE glue module (Story C1, AD-1/AD-6) allowed to import the
# orchestration libs. Paths are relative to ATLAS_PKG. This is the AD-1-only
# exemption — the glue is STILL covered by the no-inline-IO scan (it imports no
# HTTP/DB client) and by ``test_scan_covers_the_whole_package`` (it is NOT in
# ``NO_INLINE_IO_EXEMPT``). ``kedro_mcp`` stays banned everywhere, including here.
AD1_GLUE_EXEMPT = frozenset({"orchestration/definitions.py"})


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
            if not is_dynamic_import:
                continue
            # Resolve the module name from positional OR keyword form —
            # `import_module(name="requests")` would otherwise slip the gate
            # (Gemini PR-71).
            arg = None
            if node.args:
                arg = node.args[0]
            else:
                for kw in node.keywords:
                    if kw.arg == "name":
                        arg = kw.value
                        break
            if arg is not None and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.add(arg.value)
    return names


def _violations(denylist, exempt: frozenset[str] = frozenset()) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _iter_scanned_files():
        if str(path.relative_to(ATLAS_PKG)) in exempt:
            continue
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


# The orchestration libs the glue IS the seam for (exempt in the glue only).
AD1_GLUE_LIBS = ("dagster", "kedro_dagster")
# Banned EVERYWHERE, glue included — the glue is an orchestration seam, never an
# MCP seam (Reviewer-A F1: a whole-denylist exemption silently let kedro_mcp into
# the glue, contradicting the AD-1 intent + this module's own comments).
AD1_EVERYWHERE = ("kedro_mcp",)


def test_ad1_import_direction():
    """AD-1: only the single ``orchestration/definitions.py`` glue module may
    import the orchestration libs (dagster / kedro_dagster) — Story C1, AD-6 —
    and ``kedro_mcp`` stays banned in EVERY package file, the glue included.

    Two separate scans so the glue exemption can NOT widen to kedro_mcp: the
    orchestration libs are checked with the glue exempt; kedro_mcp is checked
    across the whole package with NO exemption."""
    orch_violations = _violations(AD1_GLUE_LIBS, exempt=AD1_GLUE_EXEMPT)
    assert not orch_violations, (
        "AD-1 violation — only pyforge/atlas/orchestration/definitions.py may "
        f"import dagster/kedro_dagster: {orch_violations}"
    )
    # kedro_mcp: no exemption — banned everywhere, including the glue.
    mcp_violations = _violations(AD1_EVERYWHERE)
    assert not mcp_violations, (
        f"AD-1 violation — kedro_mcp must not be imported by any package file: {mcp_violations}"
    )


# AD-8 (Story D1): boring_semantic_layer is the SINGLE metric-translation seam. Only
# the semantic/ subpackage declares BSL dimensions/measures (Ibis→DuckDB metric
# arithmetic, AD-4); every other module queries those models, never constructs its own.
# Mirrors the C1 dagster-glue exemption, scoped to a subtree instead of one file.
BSL_DENYLIST = ("boring_semantic_layer",)
BSL_SEMANTIC_PREFIX = "semantic/"


def _bsl_violations() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _iter_scanned_files():
        rel = str(path.relative_to(ATLAS_PKG))
        if rel.startswith(BSL_SEMANTIC_PREFIX):
            continue
        hits = [n for n in sorted(_imported_names(path)) if _denylisted(n, BSL_DENYLIST)]
        if hits:
            found[str(path.relative_to(ATLAS_PKG.parents[2]))] = hits
    return found


def test_bsl_only_in_semantic_layer():
    """AD-8: only ``pyforge/atlas/semantic/*`` may import ``boring_semantic_layer`` —
    the BSL models are the single metric-translation interface, so no other package
    module re-declares metric semantics (Story D1, FR-8)."""
    violations = _bsl_violations()
    assert not violations, (
        "AD-8 violation — only the semantic/ subpackage may import "
        f"boring_semantic_layer: {violations}"
    )
    # positive: the semantic layer DOES import it (the seam genuinely lives there).
    sem_models = ATLAS_PKG / "semantic" / "models.py"
    assert sem_models.is_file(), "semantic/models.py missing"
    assert any(_denylisted(n, BSL_DENYLIST) for n in _imported_names(sem_models)), (
        "semantic/models.py does not import boring_semantic_layer"
    )


# AD-1/AD-6 (Story D2): ``vizro`` is REPLACEABLE visualization glue — only the
# ``dashboard/`` subpackage may import it, so the read-surface UI stays contained to one
# swappable layer (mirrors the C1 dagster-glue file exemption and the D1 BSL subtree
# exemption above, scoped to the dashboard subtree). The dashboard consumes the BSL MODELS
# (``pyforge.atlas.semantic``) — never ``boring_semantic_layer`` directly — so the AD-8 ban
# above still covers it.
VIZRO_DENYLIST = ("vizro",)
DASHBOARD_PREFIX = "dashboard/"


def _vizro_violations() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _iter_scanned_files():
        rel = str(path.relative_to(ATLAS_PKG))
        if rel.startswith(DASHBOARD_PREFIX):
            continue
        hits = [n for n in sorted(_imported_names(path)) if _denylisted(n, VIZRO_DENYLIST)]
        if hits:
            found[str(path.relative_to(ATLAS_PKG.parents[2]))] = hits
    return found


def test_vizro_only_in_dashboard_layer():
    """AD-1/AD-6 (Story D2): only ``pyforge/atlas/dashboard/*`` may import ``vizro`` — the
    Vizro read surface is replaceable glue confined to one subpackage."""
    violations = _vizro_violations()
    assert not violations, (
        "AD-1 violation — only the dashboard/ subpackage may import vizro: "
        f"{violations}"
    )
    # positive: the dashboard app factory DOES import vizro (the glue genuinely lives there).
    app_mod = ATLAS_PKG / "dashboard" / "app.py"
    assert app_mod.is_file(), "dashboard/app.py missing"
    assert any(_denylisted(n, VIZRO_DENYLIST) for n in _imported_names(app_mod)), (
        "dashboard/app.py does not import vizro"
    )
    # AD-8 crossover: the dashboard data layer consumes the semantic seam, not raw BSL.
    data_mod = ATLAS_PKG / "dashboard" / "data.py"
    assert not any(_denylisted(n, BSL_DENYLIST) for n in _imported_names(data_mod)), (
        "dashboard/data.py imports boring_semantic_layer directly — must go through semantic/"
    )


def test_dagster_only_in_glue():
    """Positive AD-1 assertion: the glue module DOES import the orchestration
    libs (so it is genuinely the seam) and NO OTHER package file does — the
    exemption is not masking a second importer, and the glue path really exists."""
    # the exempt glue file exists (a typo would silently exempt nothing).
    for rel in AD1_GLUE_EXEMPT:
        assert (ATLAS_PKG / rel).is_file(), f"glue exempt path missing: {rel}"
    # the glue actually imports dagster + kedro_dagster.
    glue_imports = _imported_names(ATLAS_PKG / "orchestration" / "definitions.py")
    assert any(_denylisted(n, ("dagster",)) for n in glue_imports), "glue does not import dagster"
    assert any(_denylisted(n, ("kedro_dagster",)) for n in glue_imports), "glue does not import kedro_dagster"
    # …but even the glue must NOT import kedro_mcp (orchestration seam, not MCP seam).
    assert not any(_denylisted(n, ("kedro_mcp",)) for n in glue_imports), "glue imports kedro_mcp"
    # every OTHER package file is dagster/kedro_dagster-free (scan minus the glue).
    for path in _iter_scanned_files():
        if str(path.relative_to(ATLAS_PKG)) in AD1_GLUE_EXEMPT:
            continue
        hits = [n for n in _imported_names(path) if _denylisted(n, ("dagster", "kedro_dagster"))]
        assert not hits, f"non-glue module imports orchestration libs: {path.name}: {hits}"
