"""Steward 36.1: Lane 3 BSL reads the estate Parquet cache."""

from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd

from pyforge.atlas.dashboard.data import load_estate_cache
from pyforge.atlas.semantic.models import build_estate_cache_model


def test_bsl_query_returns_planted_estate_rows(tmp_path: Path) -> None:
    cache = tmp_path / "query_plane_estate.parquet"
    pd.DataFrame({"sku": ["widget-a", "widget-b"], "units": [12, 7]}).to_parquet(cache, compression="zstd")
    frame = load_estate_cache(cache)
    assert set(frame.columns) >= {"sku", "units_total"}
    by_sku = {row.sku: int(row.units_total) for row in frame.itertuples(index=False)}
    assert by_sku["widget-a"] == 12
    assert by_sku["widget-b"] == 7


def test_loader_does_not_take_oltp_dsn() -> None:
    sig = inspect.signature(load_estate_cache)
    assert "dsn" not in sig.parameters
    source = inspect.getsource(load_estate_cache)
    assert "postgresql" not in source
    assert "return SemanticModel(" in inspect.getsource(build_estate_cache_model)
