"""Shared fixtures for the BSL metric-parity gate (Story D1, bsl-metric-check).

Offline by construction: a local DuckDB connection over Parquet written to a tmp dir;
the network is never touched. The ``parquet_table`` helper round-trips a hand-authored
pandas frame through Parquet — so the parity assertions run against the SAME DuckDB
type coercion (nullable int → float64, etc.) the live catalog Parquet path produces.
"""

from __future__ import annotations

import ibis
import pandas as pd
import pytest


@pytest.fixture()
def duck():
    return ibis.duckdb.connect()


@pytest.fixture()
def parquet_table(tmp_path, duck):
    """Write ``df`` to Parquet and read it back as an Ibis DuckDB table.

    Round-tripping (not ``con.create_table(df)``) is deliberate: it reproduces the
    on-disk Parquet → DuckDB coercion the live models hit, so a coercion bug (e.g. a
    nullable integer becoming float) is caught by the parity gate, not in production.
    """
    counter = {"n": 0}

    def _make(df: pd.DataFrame, name: str = "t"):
        counter["n"] += 1
        path = tmp_path / f"{name}_{counter['n']}.parquet"
        df.to_parquet(path)
        return duck.read_parquet(str(path))

    return _make
