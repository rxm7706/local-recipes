"""Scan the FR-47 Parquet cache without an OLTP writer role."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

PIPELINE_NAME = "query_plane_cache"
ESTATE_CACHE_DATASET = "query_plane_estate"


def scan_estate_parquet(path: Path | str) -> list[tuple[Any, ...]]:
    """Read compressed Parquet through in-process DuckDB.

    Takes only a file path. Does not accept or open an OLTP DSN.
    """
    parquet = Path(path)
    if not parquet.is_file():
        raise FileNotFoundError(parquet)
    con = duckdb.connect(":memory:")
    try:
        return list(con.execute("SELECT * FROM read_parquet(?)", [str(parquet)]).fetchall())
    finally:
        con.close()
