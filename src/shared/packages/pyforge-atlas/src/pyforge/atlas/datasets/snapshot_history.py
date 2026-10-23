"""A Parquet store that each run appends to (Story 37.5, AD-13)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from kedro.io.core import DatasetError
from pyforge.core.atomic_write import atomic_write

logger = logging.getLogger(__name__)


class SnapshotHistoryDataset(AbstractDataset):
    """An append-only Parquet store keyed on ``key_columns``.

    ``load`` returns every row the store holds, or an empty frame with ``columns`` when the file is absent or
    unreadable (AD-13). ``save`` appends: the stored rows and the new ones, deduplicated on ``key_columns`` with
    the new row winning, written atomically. An empty save keeps the store as it is, and so does a save over a
    store that cannot be read, so a bad read never overwrites the history. The parameter is not ``keys``:
    kedro-dagster builds a config model from a dataset's parameters, and a field named ``keys`` shadows its
    ``keys()``."""

    def __init__(
        self,
        *,
        filepath: str,
        key_columns: list[str],
        columns: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not key_columns:
            raise ValueError("SnapshotHistoryDataset needs at least one key column")
        self._filepath = str(filepath)
        self._keys = list(key_columns)
        self._columns = list(columns or [])
        self.metadata = metadata

    def _read(self) -> pd.DataFrame | None:
        """The stored rows; ``None`` when the store is absent or cannot be read."""
        path = Path(self._filepath)
        if not path.is_file():
            return None
        try:
            return pd.read_parquet(path)
        except Exception as exc:
            logger.warning("snapshot store %s unreadable: %s", self._filepath, exc)
            return None

    def load(self) -> pd.DataFrame:
        frame = self._read()
        if frame is None:
            return pd.DataFrame(columns=self._columns)
        return frame

    def save(self, data: pd.DataFrame) -> None:
        if data.empty:  # kedro refuses a None save before it reaches here
            return
        missing = [k for k in self._keys if k not in data.columns]
        if missing:
            raise DatasetError(f"SnapshotHistoryDataset {self._filepath}: rows lack key columns {missing}")
        path = Path(self._filepath)
        stored = self._read()
        if stored is None and path.is_file():
            logger.warning("snapshot store %s unreadable; keeping it and skipping this append", self._filepath)
            return
        combined = data if stored is None or stored.empty else pd.concat([stored, data], ignore_index=True)
        combined = (
            combined.drop_duplicates(subset=self._keys, keep="last")
            .sort_values(self._keys, kind="stable")
            .reset_index(drop=True)
        )
        atomic_write(path, lambda tmp: combined.to_parquet(tmp, index=False))

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "key_columns": self._keys, "type": "SnapshotHistoryDataset"}
