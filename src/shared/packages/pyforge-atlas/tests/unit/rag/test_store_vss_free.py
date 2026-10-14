"""Story 31.1 — vss-free unit tests for ``DuckdbVssRagStore`` (coverage without extension)."""

from __future__ import annotations

import re
from typing import Any

import duckdb

from pyforge.atlas.rag.store import DuckdbVssRagStore, HashingEmbedder

_VSS_STMT = re.compile(
    r"(?i)(SET\s+hnsw_enable_experimental_persistence|CREATE\s+INDEX.*USING\s+HNSW|DROP\s+INDEX)"
)


class _VssFreeConnection:
    """Drop only the three statements the vss extension owns; ranking stays in core DuckDB."""

    def __init__(self) -> None:
        self._con = duckdb.connect()

    def execute(self, sql: str, parameters: Any = None) -> duckdb.DuckDBPyRelation:
        if _VSS_STMT.search(sql):
            return self._con.execute("SELECT 1 WHERE false")
        if parameters is None:
            return self._con.execute(sql)
        return self._con.execute(sql, parameters)

    def executemany(self, sql: str, parameters: Any) -> None:
        if _VSS_STMT.search(sql):
            return
        self._con.executemany(sql, parameters)

    def fetchone(self) -> tuple[Any, ...] | None:
        raise AttributeError("use execute().fetchone() on the relation")

    def close(self) -> None:
        self._con.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._con, name)


def test_store_index_and_search_without_vss_extension() -> None:
    con = _VssFreeConnection()
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=8),
        connection=con,  # type: ignore[arg-type]
        vss_loader=lambda _c: None,
        table="rag_test",
    )
    n = store.index([("a", "python packaging"), ("b", "rust cargo")])
    assert n == 2
    assert store.count() == 2
    hits = store.similarity_search("python conda", k=1)
    assert len(hits) == 1
    assert hits[0]["id"] in {"a", "b"}
    store.close()
