"""Steward 25.2 estate gate: atlas.duckdb writer boundary (canopy AD-15).

Parses atlas source on disk — does not import ``pyforge.*`` (host import-linter).
"""

from __future__ import annotations

import ast
from pathlib import Path

WRITER_MODULE = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "packages"
    / "pyforge-atlas"
    / "src"
    / "pyforge"
    / "atlas"
    / "duckdb_writer.py"
)


def test_removing_boundary_makes_the_test_fail() -> None:
    assert WRITER_MODULE.is_file(), "atlas opener must exist"
    tree = ast.parse(WRITER_MODULE.read_text(encoding="utf-8"))
    writer_fn = None
    reader_fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "connect_writer":
            writer_fn = node
        if isinstance(node, ast.FunctionDef) and node.name == "connect_reader":
            reader_fn = node
    assert writer_fn is not None, "connect_writer is the writer boundary"
    assert reader_fn is not None, "connect_reader is the reader boundary"
    writer_src = ast.dump(writer_fn)
    assert "FileLock" in writer_src
    assert "timeout" in writer_src
    reader_src = ast.dump(reader_fn)
    assert "read_only" in reader_src
    assert "True" in reader_src
