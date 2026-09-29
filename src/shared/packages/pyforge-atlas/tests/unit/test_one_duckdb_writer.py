"""Steward 25.2: one writer on atlas.duckdb (FR-27, BS-5, canopy AD-15)."""

from __future__ import annotations

import ast
from pathlib import Path

import duckdb
import pytest

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME, SecondWriterRefused, connect_reader, connect_writer

WRITER_MODULE = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "atlas" / "duckdb_writer.py"


def _atlas_path(tmp_path: Path) -> Path:
    return tmp_path / ATLAS_DUCKDB_NAME


def test_second_writer_is_refused(tmp_path: Path) -> None:
    path = _atlas_path(tmp_path)
    first = connect_writer(path)
    first.execute("CREATE TABLE t (x INTEGER)")
    first.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(SecondWriterRefused):
        connect_writer(path)
    first.close()
    # After release, a later writer may proceed.
    second = connect_writer(path)
    assert second.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    second.close()


def test_readers_use_read_only(tmp_path: Path) -> None:
    path = _atlas_path(tmp_path)
    writer = connect_writer(path)
    writer.execute("CREATE TABLE t (x INTEGER)")
    writer.close()

    reader = connect_reader(path)
    mode = reader.execute("SELECT current_setting('access_mode')").fetchone()[0]
    assert mode == "read_only"
    with pytest.raises(duckdb.Error):
        reader.execute("INSERT INTO t VALUES (1)")
    reader.close()


def test_wrong_filename_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="atlas.duckdb"):
        connect_writer(tmp_path / "other.duckdb")


def test_removing_boundary_makes_the_test_fail() -> None:
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
    assert "FileLock" in writer_src, "writer must take an exclusive filelock"
    assert "timeout" in writer_src

    reader_src = ast.dump(reader_fn)
    assert "read_only" in reader_src
    assert "True" in reader_src
