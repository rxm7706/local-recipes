"""Shared fixtures for GraphStore tests (Story 28.1)."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore, GraphStore

_DEFAULT_PG_DSN = "postgres://postgres:scribe@127.0.0.1:5433/scribe_graph"


def require_pg_dsn() -> str:
    dsn = (os.environ.get("SCRIBE_GRAPH_DSN") or _DEFAULT_PG_DSN).split("?", 1)[0]
    try:
        import psycopg

        with psycopg.connect(dsn) as conn:
            conn.execute("SELECT 1")
            row = conn.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
            ).fetchone()
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"durable GraphStore requires PostgreSQL with pgvector at {dsn}: {exc}"
        )
    if row is None:
        pytest.fail(f"durable GraphStore requires CREATE EXTENSION vector at {dsn}")
    return dsn


@pytest.fixture
def pg_dsn() -> str:
    return require_pg_dsn()


StoreFactory = Callable[[], GraphStore]


@pytest.fixture(params=["flatfile", "postgres"])
def graph_store_factory(request: pytest.FixtureRequest, tmp_path: Path) -> StoreFactory:
    kind = request.param
    if kind == "flatfile":
        path = tmp_path / "graph.json"

        def _flat() -> GraphStore:
            return FlatFileGraphStore(path)

        return _flat

    from pyforge.scribe.graph_store_pg import PostgresGraphStore

    dsn = require_pg_dsn()
    path = tmp_path / "durable-must-not-be-json"

    def _pg() -> GraphStore:
        return PostgresGraphStore(dsn, path)

    return _pg
