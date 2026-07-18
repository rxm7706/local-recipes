"""Story F1 (FR-5, AD-4) — the DuckDB Singularity gate: DuckDB/Parquet is the SOLE store.

The migration retires the legacy hand-rolled ``cf_atlas.db`` (a SQLite store). This gate
makes "DuckDB is the only engine" a first-class, named invariant rather than a claim: NO
``sqlite3`` read/write path may exist anywhere in the migrated SURFACE (the ``pyforge/atlas``
src package). It is deliberately stronger-in-intent than — and complementary to — the AC-2
no-inline-IO ban (which also lists ``sqlite3`` among many IO clients): this test exists ONLY
to assert the FR-5 sole-engine property, so a future reintroduction of a SQLite path fails a
test whose name says exactly why.

THE ONE LEGITIMATE EXCEPTION (documented, asserted): the B4 credentialed parity comparator
``tests/parity/parity_runner.py`` reads the EXTERNAL legacy ``cf_atlas.db`` to prove dataset
parity BEFORE retirement (AD-19, attended). That reads the OLD store to retire it — it is not
the migrated engine, and it lives in ``tests/`` (never shipped in the package). This gate
asserts that boundary holds: the legacy-SQLite reader is in tests/, never in src/.

The **cold-start / warm-incremental benchmark** (the FR-5 performance claim) is the ATTENDED
half of F1 — threshold fixed in the story spec first (SM-3), adjudicated at the attended event
by operator sign-off. It is DEFERRED here (DW-F1-1); this gate is the offline, always-on half.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ATLAS_SRC = Path(importlib.import_module("pyforge.atlas").__file__).resolve().parent


def _sqlite_hits(path: Path) -> list[str]:
    """Any ``import sqlite3`` / ``from sqlite3 import …`` / dynamic ``import_module('sqlite3')``
    in a module — statically, via AST (a string literal mentioning ``cf_atlas.db`` in a
    docstring is NOT a hit, so the parity/audit provenance comments don't false-positive)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits += [a.name for a in node.names if a.name == "sqlite3" or a.name.startswith("sqlite3.")]
        elif isinstance(node, ast.ImportFrom):
            if node.module == "sqlite3":
                hits.append("sqlite3")
        elif isinstance(node, ast.Call):
            fn = node.func
            is_dyn = (isinstance(fn, ast.Name) and fn.id in ("__import__", "import_module")) or (
                isinstance(fn, ast.Attribute) and fn.attr == "import_module"
            )
            if is_dyn and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "sqlite3":
                hits.append("sqlite3(dynamic)")
    return hits


def test_no_sqlite_in_the_migrated_surface():
    """FR-5 / AD-4: DuckDB is the sole engine — the migrated ``pyforge/atlas`` src package
    contains NO sqlite3 read/write path (import, from-import, or dynamic import)."""
    offenders = {
        str(p.relative_to(ATLAS_SRC)): hits
        for p in sorted(ATLAS_SRC.rglob("*.py"))
        if (hits := _sqlite_hits(p))
    }
    assert not offenders, (
        "FR-5 violation — the DuckDB-singularity surface must have NO sqlite3 path; "
        f"found: {offenders}"
    )


def test_the_only_legacy_sqlite_reader_is_the_parity_comparator_in_tests():
    """The ONE legitimate SQLite reader — the B4 credentialed comparator reading the external
    legacy cf_atlas.db to prove parity before retirement — lives in tests/, never in src/.
    This pins the boundary: retirement-verification tooling may read the OLD store; the
    migrated ENGINE never does."""
    # src/: zero sqlite readers (the assertion above); tests/parity: exactly the comparator.
    # ATLAS_SRC = <member>/src/pyforge/atlas → parents[2] is the member root holding tests/.
    member_root = ATLAS_SRC.parents[2]
    parity_runner = member_root / "tests" / "parity" / "parity_runner.py"
    assert parity_runner.is_file(), "the credentialed parity comparator is missing"
    assert _sqlite_hits(parity_runner), (
        "the parity comparator is the sole legacy-SQLite reader — if it stopped importing "
        "sqlite3 the credentialed retirement check would silently no-op"
    )
    # and it is under tests/, NOT under the shipped src package.
    assert "tests" in parity_runner.parts and str(ATLAS_SRC) not in str(parity_runner)


def test_duckdb_is_present_as_the_engine():
    """The sole engine is actually available (the store side of FR-5)."""
    import duckdb  # noqa: F401 — presence is the assertion

    assert duckdb.__version__  # a real DuckDB, the compute/graph/vector engine
