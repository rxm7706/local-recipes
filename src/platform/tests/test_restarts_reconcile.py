"""Steward 25.4 estate gate: Mason boot reconcile (canopy AD-15, parent AD-1).

Parses mason source on disk — does not import ``pyforge.*`` (host import-linter).
"""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

import pytest

BOOT_MODULE = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "packages"
    / "pyforge-mason"
    / "src"
    / "pyforge"
    / "mason"
    / "boot.py"
)

_FORBIDDEN_MODULES = frozenset({"boto3", "botocore", "minio", "s3", "boto"})
_BOOT_ERROR_TAXONOMY = "pyforge.core.errors"
_THREE = 3


def _sql_constant(tree: ast.AST, name: str) -> str:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
    pytest.fail(name)


def _boot_tree() -> ast.AST:
    assert BOOT_MODULE.is_file()
    return ast.parse(BOOT_MODULE.read_text(encoding="utf-8"), filename=str(BOOT_MODULE))


def test_interrupted_boot_then_restart_applies_once() -> None:
    tree = _boot_tree()
    conn = sqlite3.connect(":memory:")
    conn.execute(_sql_constant(tree, "_CREATE_INDEX"))
    upsert = _sql_constant(tree, "_UPSERT")
    keys = ("a.bin", "c.bin", "nested/b.bin")
    conn.execute(upsert, (keys[0], 3, "rwx"))
    assert conn.execute("SELECT COUNT(*) FROM mason_index").fetchone()[0] == 1
    for key in keys:
        conn.execute(upsert, (key, 1, "rwx"))
    rows = conn.execute(
        "SELECT artifact_key FROM mason_index ORDER BY artifact_key",
    ).fetchall()
    assert len(rows) == _THREE
    assert tuple(r[0] for r in rows) == keys


def test_removing_reconciliation_makes_the_test_fail() -> None:
    tree = _boot_tree()
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
    }
    assert "reconcile_boot" in names
    assert "SqliteIndexStore" in names
    sql = _sql_constant(tree, "_UPSERT")
    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    assert "PRIMARY KEY" in _sql_constant(tree, "_CREATE_INDEX")
    upsert = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SqliteIndexStore":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "upsert":
                    upsert = item
    assert upsert is not None
    assert "_UPSERT" in ast.dump(upsert)


def test_boot_does_not_import_object_store_clients() -> None:
    tree = _boot_tree()
    imported: set[str] = set()
    dotted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
                dotted.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
            dotted.add(node.module)
    assert imported.isdisjoint(_FORBIDDEN_MODULES)
    # Boot stays a self-contained sqlite reconcile -- no pyforge machinery --
    # with one sanctioned exception: Mason Story 14.3 (CAP-5) makes
    # BootInterrupted subclass PyforgeError, and pyforge-core's meta suite
    # requires every error to. The taxonomy base is the only pyforge import.
    assert {m for m in dotted if m.startswith("pyforge")} <= {_BOOT_ERROR_TAXONOMY}
