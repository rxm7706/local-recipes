"""Parquet datasets that degrade to empty + stale when absent (Story 27.2, AD-13)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.pandas import ParquetDataset
from pyforge.core.atomic_write import atomic_write

from .refresh import StalenessMarker

logger = logging.getLogger(__name__)


class DegradingParquetDataset(AbstractDataset):
    """Read-only cross-pipeline inputs: missing file → empty frame + staleness marker."""

    STALENESS_SUFFIX = ".staleness.json"

    def __init__(
        self,
        *,
        filepath: str,
        columns: list[str] | None = None,
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._filepath = str(filepath)
        self._columns = list(columns or [])
        self._inner = ParquetDataset(
            filepath=filepath,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
        )

    @property
    def _staleness_path(self) -> Path:
        p = Path(self._filepath)
        return p.with_name(p.name + self.STALENESS_SUFFIX)

    def _mark_stale(self, reason: str) -> None:
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=Path(self._filepath).is_file())
        try:
            atomic_write(
                self._staleness_path,
                lambda target: target.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8"),
            )
        except OSError as exc:
            logger.warning("could not write staleness marker for %s: %s", self._filepath, exc)

    def load(self) -> pd.DataFrame:
        path = Path(self._filepath)
        if not path.is_file():
            self._mark_stale("cross-pipeline parquet absent on data root")
            cols = self._columns or []
            return pd.DataFrame(columns=cols)
        try:
            return self._inner.load()
        except Exception as exc:
            logger.warning("degrading parquet load for %s: %s", self._filepath, exc)
            self._mark_stale(f"parquet unreadable: {type(exc).__name__}")
            return pd.DataFrame(columns=self._columns or [])

    def save(self, data: pd.DataFrame) -> None:
        self._inner.save(data)
        try:
            self._staleness_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "type": "DegradingParquetDataset"}
