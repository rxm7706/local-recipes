"""Shared offline-session seeding helper for the trending_candidates test suite.

Mirrors ``tests/mcp/test_read_surface.py``'s ``real_catalog_session`` pattern (AD-11):
a REAL ``kedro.io.DataCatalog`` seeded with a ``MemoryDataset``, and a monkeypatched
``pyforge.atlas.mcp.session.bootstrapped_session`` — proves the real ``catalog.load``
path end-to-end without any live Kedro project / network / real data.
"""

from __future__ import annotations

import contextlib

import pandas as pd
import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro_datasets.pandas import ParquetDataset

from pyforge.atlas.mcp import session as _session_mod

DATASET_NAME = "trending_candidates_classified"


class _FakeContext:
    def __init__(self, catalog):
        self.catalog = catalog


class _FakeSession:
    def __init__(self, catalog):
        self._context = _FakeContext(catalog)

    def load_context(self):
        return self._context


@pytest.fixture()
def seed_catalog(monkeypatch):
    """Returns a callable ``seed(df=None)``: seeds a real ``DataCatalog`` with ``df``
    under ``trending_candidates_classified`` (or leaves it UNDECLARED when ``df`` is
    ``None``, to exercise the missing-dataset degradation) and fakes
    ``_session.bootstrapped_session`` to yield it."""

    def _seed(df: pd.DataFrame | None = None) -> DataCatalog:
        datasets = {}
        if df is not None:
            datasets[DATASET_NAME] = MemoryDataset(df, copy_mode="assign")
        catalog = DataCatalog(datasets=datasets)
        fake = _FakeSession(catalog)

        @contextlib.contextmanager
        def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
            yield fake

        monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_bootstrapped_session)
        return catalog

    return _seed


@pytest.fixture()
def seed_parquet_catalog(monkeypatch, tmp_path):
    """Like ``seed_catalog``, but backs ``trending_candidates_classified`` with a REAL
    ``kedro_datasets.pandas.ParquetDataset`` (mirrors
    ``tests/mcp/test_read_surface.py::test_read_dataset_pandas_parquet_reports_file_mtime_not_read_time``)
    instead of a ``MemoryDataset``. Two things only a real file-backed dataset can prove:

    - the provenance envelope (``build_stamp``/``provenance_kind``) actually propagates
      through ``query_trending_candidates`` for the dataset TYPE the real catalog.yml
      entry declares (``MemoryDataset`` always resolves to ``provenance_kind:
      "unavailable"`` — it can't exercise this path at all).
    - the REALISTIC "never ingested" production shape: a catalog entry that IS declared
      (unlike ``seed_catalog(None)``'s undeclared-key shortcut) whose backing ``.parquet``
      file simply doesn't exist yet — pass ``df=None`` to get this shape without writing
      the file.
    """

    def _seed(df: pd.DataFrame | None = None) -> DataCatalog:
        path = tmp_path / DATASET_NAME / f"{DATASET_NAME}.parquet"
        if df is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path)
        ds = ParquetDataset(filepath=str(path))
        catalog = DataCatalog(datasets={DATASET_NAME: ds})
        fake = _FakeSession(catalog)

        @contextlib.contextmanager
        def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
            yield fake

        monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_bootstrapped_session)
        return catalog

    return _seed
