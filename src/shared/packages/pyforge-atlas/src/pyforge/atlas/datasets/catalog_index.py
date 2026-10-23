"""Every catalog entry's last write and row count on the data root (Story 37.10, AD-13)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml
from kedro.io import AbstractDataset

logger = logging.getLogger(__name__)

DATA_ROOT_PREFIX = "${globals:paths.data_root}/"
STALENESS_SUFFIX = ".staleness.json"
STORE_STALENESS = ".staleness.json"
COLUMNS = ["catalog_entry", "layer", "relpath", "regenerated_at", "row_count", "stale", "stale_reason"]


def _parquet_rows(path: Path) -> int | None:
    try:
        return int(pq.read_metadata(path).num_rows)
    except Exception as exc:
        logger.warning("catalog index: %s has no readable Parquet footer: %s", path, exc)
        return None


def _marker(path: Path) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return True, "staleness marker unreadable"
    if not isinstance(raw, dict):
        return True, "staleness marker unreadable"
    return bool(raw.get("stale", True)), str(raw.get("reason", "")) or None


def entry_stats(data_root: Path, relpath: str) -> dict[str, Any]:
    """The persisted state of one catalog entry: the file it was last written to (for a store directory, its newest
    ``*.parquet``), when, how many rows that Parquet footer counts, and its staleness marker (a sibling
    ``<file>.staleness.json``, or the directory's ``.staleness.json``). An absent file gives no write and no count."""
    target = data_root / relpath
    if target.is_dir():
        parquets = [p for p in target.glob("*.parquet") if p.is_file()]
        written = max(parquets, key=lambda p: p.stat().st_mtime) if parquets else None
        stale, reason = _marker(target / STORE_STALENESS)
    else:
        written = target if target.is_file() else None
        stale, reason = _marker(target.with_name(target.name + STALENESS_SUFFIX))
    regenerated_at = None
    row_count = None
    if written is not None:
        regenerated_at = datetime.fromtimestamp(written.stat().st_mtime, tz=UTC).replace(microsecond=0)
        if written.suffix == ".parquet":
            row_count = _parquet_rows(written)
    return {"regenerated_at": regenerated_at, "row_count": row_count, "stale": stale, "stale_reason": reason}


class CatalogIndexDataset(AbstractDataset):
    """Read-only: one row per catalog entry whose ``filepath`` lies under the data root, with its last write, its
    Parquet row count and its staleness marker (``entry_stats``). Entries that fetch live and persist nothing
    (an ``url``, or a path outside the data root) have no row. An unreadable catalog gives an empty frame (AD-13)."""

    def __init__(self, *, catalog_path: str, data_root: str, metadata: dict[str, Any] | None = None) -> None:
        self._catalog_path = str(catalog_path)
        self._data_root = str(data_root)
        self.metadata = metadata

    def _entries(self) -> list[tuple[str, str, str]]:
        try:
            catalog = yaml.safe_load(Path(self._catalog_path).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("catalog index: %s unreadable: %s", self._catalog_path, exc)
            return []
        if not isinstance(catalog, dict):
            return []
        entries = []
        for name, spec in catalog.items():
            if not isinstance(name, str) or name.startswith("_") or not isinstance(spec, dict):
                continue
            filepath = spec.get("filepath")
            if not isinstance(filepath, str) or not filepath.startswith(DATA_ROOT_PREFIX):
                continue
            layer = (spec.get("metadata") or {}).get("layer") if isinstance(spec.get("metadata"), dict) else None
            entries.append((name, str(layer or ""), filepath[len(DATA_ROOT_PREFIX) :]))
        return entries

    def load(self) -> pd.DataFrame:
        root = Path(self._data_root)
        rows = [
            {"catalog_entry": name, "layer": layer, "relpath": relpath, **entry_stats(root, relpath)}
            for name, layer, relpath in self._entries()
        ]
        frame = pd.DataFrame(rows, columns=COLUMNS)
        frame["row_count"] = frame["row_count"].astype("Int64")
        frame["stale"] = frame["stale"].astype("bool")
        return frame

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"catalog_path": self._catalog_path, "data_root": self._data_root}
