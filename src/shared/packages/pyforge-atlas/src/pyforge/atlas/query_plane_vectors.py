"""FR-48: persist vectors on the CAP-19 plane writer (canopy AD-22)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME, LockedDuckDB, connect_writer
from pyforge.atlas.rag.store import DuckdbVssRagStore, load_vss_offline

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
DEFAULT_VECTOR_TABLE = "plane_vectors"


def _ident(value: str, what: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise ValueError(f"invalid {what} identifier {value!r}")
    return value


def extract_real_arrays_onto_plane(
    path: Path | str,
    rows: Sequence[tuple[str, Sequence[float]]],
    *,
    dim: int,
    table: str = DEFAULT_VECTOR_TABLE,
) -> LockedDuckDB:
    """Cast ``REAL[]``-shaped rows to ``FLOAT[N]`` on ``atlas.duckdb`` and index with ``vss``.

    Consumer path: ``LOAD vss`` only. Caller owns the returned writer (close it).
    """
    db_path = Path(path)
    if db_path.name != ATLAS_DUCKDB_NAME:
        raise ValueError(f"plane writer must be {ATLAS_DUCKDB_NAME}, got {db_path.name!r}")
    table_name = _ident(table, "table")
    writer = connect_writer(db_path)
    try:
        load_vss_offline(writer)
        writer.execute("SET hnsw_enable_experimental_persistence = true")
        writer.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id VARCHAR, emb FLOAT[{int(dim)}])")
        writer.execute(f"DELETE FROM {table_name}")
        for row_id, vec in rows:
            if len(vec) != dim:
                raise ValueError(f"vector {row_id!r} has dim {len(vec)}, expected {dim}")
            as_real = [float(x) for x in vec]
            writer.execute(
                f"INSERT INTO {table_name} VALUES (?, CAST(? AS FLOAT[{int(dim)}]))",
                [row_id, as_real],
            )
        writer.execute(f"DROP INDEX IF EXISTS {table_name}_hnsw")
        writer.execute(f"CREATE INDEX {table_name}_hnsw ON {table_name} USING HNSW (emb) WITH (metric = 'l2sq')")
    except Exception:
        writer.close()
        raise
    return writer


def nearest_neighbor(
    con: Any,
    query: Sequence[float],
    *,
    dim: int,
    table: str = DEFAULT_VECTOR_TABLE,
    k: int = 1,
) -> list[tuple[str, float]]:
    table_name = _ident(table, "table")
    rows = con.execute(
        f"SELECT id, array_distance(emb, CAST(? AS FLOAT[{int(dim)}])) AS distance "
        f"FROM {table_name} ORDER BY distance ASC, id ASC LIMIT ?",
        [list(map(float, query)), int(k)],
    ).fetchall()
    return [(str(row[0]), float(row[1])) for row in rows]


def open_plane_rag_store(path: Path | str, **kwargs: Any) -> DuckdbVssRagStore:
    """Production RAG default: inject the plane writer, never a second file or implicit memory."""
    db_path = Path(path)
    if db_path.name != ATLAS_DUCKDB_NAME:
        raise ValueError(f"plane writer must be {ATLAS_DUCKDB_NAME}, got {db_path.name!r}")
    writer = connect_writer(db_path)
    return DuckdbVssRagStore(connection=writer, **kwargs)
