"""A Parquet store that each run appends to (Story 37.5, AD-13)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from kedro.io.core import DatasetError
from pyforge.core.atomic_write import atomic_write, atomic_write_text

from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

#: the AD-13 marker beside the store: ``<filepath>.staleness.json`` (Story 37.13)
STALENESS_SUFFIX = ".staleness.json"


def staleness_path(filepath: str | Path) -> Path:
    """Where the store at ``filepath`` keeps its AD-13 marker."""
    path = Path(filepath)
    return path.with_name(path.name + STALENESS_SUFFIX)


def read_staleness(filepath: str | Path) -> StalenessMarker | None:
    """The store's AD-13 marker: ``None`` when there is none, and a stale marker when one exists but cannot be read
    (a garbled marker never reads as fresh, as the bootstrap-index-health reads it)."""
    marker = staleness_path(filepath)
    try:
        if not marker.is_file():
            return None
        raw = json.loads(marker.read_text(encoding="utf-8"))
    except OSError, ValueError, RecursionError:
        raw = None
    if not isinstance(raw, dict):
        return StalenessMarker(stale=True, reason="staleness marker unreadable", marked_at=0)
    return StalenessMarker(
        stale=bool(raw.get("stale", True)),
        reason=str(raw.get("reason", "")),
        marked_at=_safe_int(raw.get("marked_at", 0)),
        last_good_exists=bool(raw.get("last_good_exists", False)),
    )


class SnapshotHistoryDataset(AbstractDataset):
    """An append-only Parquet store keyed on ``key_columns``.

    ``load`` returns every row the store holds, or an empty frame with ``columns`` when the file is absent or
    unreadable (AD-13). ``save`` appends: the stored rows and the new ones, deduplicated on ``key_columns`` with
    the new row winning, written atomically. An empty save keeps the store as it is, and so does a save over a
    store that cannot be read, so a bad read never overwrites the history. Either save appends no snapshot, so it
    leaves the AD-13 marker ``<filepath>.staleness.json`` beside the store, and the next save that appends removes
    it (Story 37.13): the latest snapshot is then not the latest run's. The parameter is not ``keys``:
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

    def _mark_stale(self, reason: str) -> None:
        """Write the AD-13 marker; a marker that cannot be written is logged, never a failed save."""
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=Path(self._filepath).is_file())
        try:
            atomic_write_text(staleness_path(self._filepath), json.dumps(marker.to_dict(), indent=2))
        except OSError as exc:
            logger.warning("could not write the staleness marker for %s: %s", self._filepath, exc)

    def _clear_stale(self) -> None:
        try:
            staleness_path(self._filepath).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("could not remove the staleness marker for %s: %s", self._filepath, exc)

    def staleness(self) -> StalenessMarker | None:
        """The store's AD-13 marker, if its last save appended no snapshot."""
        return read_staleness(self._filepath)

    def load(self) -> pd.DataFrame:
        frame = self._read()
        if frame is None:
            return pd.DataFrame(columns=self._columns)
        return frame

    def save(self, data: pd.DataFrame) -> None:
        if data.empty:  # kedro refuses a None save before it reaches here
            self._mark_stale("no snapshot appended: the frame saved was empty")
            return
        missing = [k for k in self._keys if k not in data.columns]
        if missing:
            raise DatasetError(f"SnapshotHistoryDataset {self._filepath}: rows lack key columns {missing}")
        path = Path(self._filepath)
        stored = self._read()
        if stored is None and path.is_file():
            logger.warning("snapshot store %s unreadable; keeping it and skipping this append", self._filepath)
            self._mark_stale("no snapshot appended: the store could not be read")
            return
        combined = data if stored is None or stored.empty else pd.concat([stored, data], ignore_index=True)
        combined = (
            combined.drop_duplicates(subset=self._keys, keep="last")
            .sort_values(self._keys, kind="stable")
            .reset_index(drop=True)
        )
        atomic_write(path, lambda tmp: combined.to_parquet(tmp, index=False))
        self._clear_stale()

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "key_columns": self._keys, "type": "SnapshotHistoryDataset"}
