"""JSON seed datasets that degrade on malformed content (Story 27.2, AD-13)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from kedro.io import AbstractDataset
from kedro_datasets.json import JSONDataset
from pyforge.core.atomic_write import atomic_write

from .refresh import StalenessMarker

logger = logging.getLogger(__name__)


class DegradedJsonSeedDataset(AbstractDataset):
    """Malformed / missing JSON → empty dict + staleness marker, never DatasetError."""

    STALENESS_SUFFIX = ".staleness.json"

    def __init__(self, *, filepath: str, metadata: dict[str, Any] | None = None) -> None:
        self._filepath = str(filepath)
        self._inner = JSONDataset(filepath=filepath, metadata=metadata)
        self.metadata = metadata

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

    def load(self) -> dict:
        path = Path(self._filepath)
        if not path.is_file():
            self._mark_stale("seed file absent")
            return {}
        try:
            data = self._inner.load()
        except Exception as exc:
            logger.warning("degraded json seed load for %s: %s", self._filepath, exc)
            self._mark_stale(f"seed unreadable: {type(exc).__name__}")
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "type": "DegradedJsonSeedDataset"}
