"""Story 20.1 (CAP-5) — the one-launch-site gate: NO second ``duckdb-server`` boot path.

The 2026-08-26 ``query-plane-face`` ruling committed the Mosaic ``duckdb-server``
HTTP/Arrow face behind ONE pixi-sourced boot script. This gate makes "no second
boot path exists" a first-class, grep/AST-verifiable invariant (mirroring the F1
sole-engine gate beside it):

(a) any module in the ``pyforge/atlas`` surface containing a subprocess-launch
    call whose AST also references the string constant ``"duckdb-server"`` must
    be exactly ``query_plane_boot.py``;
(b) within ``query_plane_boot.py`` exactly ONE launch call site exists — a
    POSITIVE assertion pinning the one legitimate site, so the gate fails loud
    (rather than silently no-oping) if the boot module stopped launching;
(c) the boot module's AST contains no SQL ``INSTALL`` string reaching an
    ``.execute`` call (the spec-34-1 string/AST-gate precedent: the boot path
    never network-INSTALLs a DuckDB extension).

Hardened against the review-pass evasions (finding 6, Story 20.1): module
``as``-aliases of subprocess/os count, ``os.posix_spawn*`` counts, importing
the boot module's launch machinery (``SERVER_EXECUTABLE`` /
``_launch_duckdb_server``) counts as a duckdb-server mention, and the INSTALL
gate inspects keyword arguments too.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ATLAS_SRC = Path(importlib.import_module("pyforge.atlas").__file__).resolve().parent

BOOT_MODULE = "query_plane_boot.py"

_SUBPROCESS_LAUNCHERS = frozenset({"Popen", "run", "call", "check_call", "check_output"})

# Importing the boot module's launch machinery is a duckdb-server mention even
# without the literal string (review finding 6c, Story 20.1: ``from
# pyforge.atlas.query_plane_boot import SERVER_EXECUTABLE`` + a Popen carries
# no ``"duckdb-server"`` constant and must not slip past gate (a)).
_BOOT_LAUNCH_REEXPORTS = frozenset({"SERVER_EXECUTABLE", "_launch_duckdb_server"})


def _is_os_launcher(name: str) -> bool:
    """``os``-namespace process launchers: ``system``/``popen`` exactly, plus
    the ``exec*``/``spawn*``/``posix_spawn*`` families (review finding 6b,
    Story 20.1: ``posix_spawn`` starts with neither ``exec`` nor ``spawn``)."""
    return name in ("system", "popen") or name.startswith(("exec", "spawn", "posix_spawn"))


def _names_imported_from(tree: ast.AST, module: str) -> dict[str, str]:
    """Local-name -> original-name for ``from <module> import …`` bindings."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            for alias in node.names:
                bound[alias.asname or alias.name] = alias.name
    return bound


def _module_aliases(tree: ast.AST, module: str) -> set[str]:
    """Every local name the whole module is bound to — the plain name plus any
    ``import <module> as <alias>`` (review finding 6a, Story 20.1:
    ``import subprocess as sp; sp.Popen(…)`` must count)."""
    aliases = {module}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    aliases.add(alias.asname or alias.name)
    return aliases


def _launch_hits(tree: ast.AST) -> list[str]:
    """Every subprocess-launch call in a module, statically, via AST.

    Attribute form: ``<subprocess>.Popen``/``run``/``call``/``check_*`` and
    ``<os>.system``/``popen``/``exec*``/``spawn*``/``posix_spawn*`` — where
    the base resolves through ``import subprocess`` / ``import os``
    INCLUDING ``as`` aliases. Bare-name form is counted only when the name
    was imported FROM ``subprocess``/``os`` — keyed on the ORIGINAL name so
    an ``as`` alias cannot hide a launcher, and an unrelated local function
    named ``run`` is not a false positive.
    """
    sub_bases = _module_aliases(tree, "subprocess")
    os_bases = _module_aliases(tree, "os")
    sub_imported = {
        local
        for local, original in _names_imported_from(tree, "subprocess").items()
        if original in _SUBPROCESS_LAUNCHERS
    }
    os_imported = {local for local, original in _names_imported_from(tree, "os").items() if _is_os_launcher(original)}
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
            base, attr = fn.value.id, fn.attr
            if base in sub_bases and attr in _SUBPROCESS_LAUNCHERS:
                hits.append(f"{base}.{attr}")
            elif base in os_bases and _is_os_launcher(attr):
                hits.append(f"{base}.{attr}")
        elif isinstance(fn, ast.Name):
            if fn.id in sub_imported:
                hits.append(fn.id)
            elif fn.id in os_imported:
                hits.append(f"os:{fn.id}")
    return hits


def _mentions_duckdb_server(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "duckdb-server" in node.value:
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.rpartition(".")[2] == "query_plane_boot"
            and any(alias.name in _BOOT_LAUNCH_REEXPORTS for alias in node.names)
        ):
            return True
    return False


def _execute_calls_install(tree: ast.AST) -> list[str]:
    """SQL ``INSTALL`` strings reaching an ``.execute`` call (spec-34-1 shape;
    positional AND keyword argument values — ``execute(query="INSTALL …")``
    must not slip past, review finding 6d, Story 20.1)."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name != "execute":
            continue
        for arg in [*node.args, *(kw.value for kw in node.keywords)]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.lstrip().upper().startswith("INSTALL"):
                    found.append(arg.value)
            if isinstance(arg, ast.JoinedStr):
                raw = ast.unparse(arg)
                if "INSTALL" in raw.upper():
                    found.append(raw)
    return found


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_only_the_boot_module_launches_duckdb_server() -> None:
    """(a) exactly one module may both launch a subprocess AND name
    ``"duckdb-server"``: the one boot script. A second boot path fails here."""
    offenders = {
        str(p.relative_to(ATLAS_SRC)): hits
        for p in sorted(ATLAS_SRC.rglob("*.py"))
        if _mentions_duckdb_server(tree := _parse(p)) and (hits := _launch_hits(tree))
    }
    assert offenders == {BOOT_MODULE: ["subprocess.Popen"]}, (
        f"Story 20.1 violation — the ONE duckdb-server launch site is {BOOT_MODULE}; found: {offenders}"
    )


def test_exactly_one_launch_call_site_in_the_boot_module() -> None:
    """(b) the positive pin: the boot module exists and carries exactly ONE
    subprocess-launch call — if it stopped launching, this gate would
    otherwise silently no-op (comparator-pinning style)."""
    boot_path = ATLAS_SRC / BOOT_MODULE
    assert boot_path.is_file(), "the one boot script is missing"
    hits = _launch_hits(_parse(boot_path))
    assert hits == ["subprocess.Popen"], (
        f"the boot module must contain exactly one launch call site (subprocess.Popen); found: {hits}"
    )


def test_boot_module_never_installs_extensions() -> None:
    """(c) no SQL ``INSTALL`` reaches an ``.execute`` call in the boot module
    (AD-13 / spec-34-1 LOAD-only discipline; the Block-If is a HALT, never a
    silent network INSTALL)."""
    installs = _execute_calls_install(_parse(ATLAS_SRC / BOOT_MODULE))
    assert installs == [], installs
