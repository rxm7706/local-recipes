"""Every catalog entry's last write and row count on the data root (Story 37.10, AD-13)."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml
from kedro.io import AbstractDataset

logger = logging.getLogger(__name__)

#: the catalog keys Kedro treats as paths (``_convert_paths_to_absolute_posix``)
PATH_KEYS = ("filepath", "path", "filename")
#: ``${globals:paths.<key>}`` in the catalog, ``${paths.<key>}`` inside globals.yml
_PATH_REF = re.compile(r"\$\{(?:globals:)?paths\.([A-Za-z0-9_]+)\}")
_ROOT = "\x00data_root"
#: the data root's shipped default (``paths.data_root: ${env_or:PYFORGE_ATLAS_DATA_ROOT,data}``), which a few
#: entries spell literally
DEFAULT_ROOT = "data"
STALENESS_SUFFIX = ".staleness.json"
COLUMNS = ["catalog_entry", "layer", "relpath", "regenerated_at", "row_count", "stale", "stale_reason"]


def data_root_relpath(value: str, paths: dict[str, Any]) -> str | None:
    """The data-root-relative path a catalog path names, or ``None`` when it lies elsewhere. Path globals are
    expanded through globals.yml (``${globals:paths.vdb_store}`` is ``${paths.data_root}/stores/vdb``), and a
    literal ``data/...`` is the shipped data root."""
    for _ in range(16):
        match = _PATH_REF.search(value)
        if match is None:
            break
        key = match.group(1)
        replacement = _ROOT if key == "data_root" else paths.get(key)
        if not isinstance(replacement, str):
            return None
        value = value[: match.start()] + replacement + value[match.end() :]
    for prefix in (_ROOT + "/", DEFAULT_ROOT + "/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return None


def _parquet_rows(path: Path) -> int | None:
    try:
        return int(pq.read_metadata(path).num_rows)
    except Exception as exc:
        logger.warning("catalog index: %s has no readable Parquet footer: %s", path, exc)
        return None


def _marker(path: Path) -> tuple[bool, str | None]:
    try:
        if not path.is_file():
            return False, None
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return True, "staleness marker unreadable"
    if not isinstance(raw, dict):
        return True, "staleness marker unreadable"
    return bool(raw.get("stale", True)), str(raw.get("reason", "")) or None


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _data_files(directory: Path) -> list[Path]:
    """A store directory's data files, at any depth: not staleness markers, not dotfiles (temp writes)."""
    try:
        return [
            p
            for p in directory.rglob("*")
            if p.is_file() and not p.name.startswith(".") and not p.name.endswith(STALENESS_SUFFIX)
        ]
    except OSError:
        return []


def entry_stats(data_root: Path, relpath: str) -> dict[str, Any]:
    """The persisted state of one catalog entry.

    A file gives its own mtime, and its Parquet footer's row count. A store directory gives its newest data file's
    mtime (JSON, Parquet, any depth), and the sum of its Parquet footers' row counts, or no count when it holds no
    Parquet or a footer cannot be read. The staleness marker is a sibling ``<file>.staleness.json`` or the
    directory's ``.staleness.json``. Anything absent or vanishing mid-scan reads as not written (AD-13)."""
    target = data_root / relpath
    stamps: list[float] = []
    row_count: int | None = None
    if target.is_dir():
        files = _data_files(target)
        stamps = [m for m in map(_mtime, files) if m is not None]
        counts = [_parquet_rows(p) for p in files if p.suffix == ".parquet"]
        row_count = sum(counts) if counts and None not in counts else None  # type: ignore[arg-type]
        stale, reason = _marker(target / STALENESS_SUFFIX)
    else:
        stamp = _mtime(target) if target.is_file() else None
        stamps = [stamp] if stamp is not None else []
        if stamps and target.suffix == ".parquet":
            row_count = _parquet_rows(target)
        stale, reason = _marker(target.with_name(target.name + STALENESS_SUFFIX))
    regenerated_at = datetime.fromtimestamp(max(stamps), tz=UTC).replace(microsecond=0) if stamps else None
    return {
        "regenerated_at": regenerated_at,
        "row_count": row_count if stamps else None,
        "stale": stale,
        "stale_reason": reason,
    }


class CatalogIndexDataset(AbstractDataset):
    """Read-only: one row per catalog entry whose path lies under the data root, with its last write, its Parquet
    row count and its staleness marker (``entry_stats``).

    ``filepath`` is the catalog (its sibling ``globals.yml`` expands the path globals) and ``path`` the data root;
    Kedro makes both absolute against the project, so the index reads the same files from any working directory.
    Entries that fetch live and persist nothing (an ``url`` only, or a path outside the data root) have no row. An
    unreadable catalog gives an empty frame (AD-13)."""

    def __init__(self, *, filepath: str, path: str, metadata: dict[str, Any] | None = None) -> None:
        self._filepath = str(filepath)
        self._data_root = str(path)
        self.metadata = metadata

    def _load_yaml(self, path: Path) -> Any:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("catalog index: %s unreadable: %s", path, exc)
            return None

    def _entries(self) -> list[tuple[str, str, str]]:
        catalog = self._load_yaml(Path(self._filepath))
        if not isinstance(catalog, dict):
            return []
        globals_ = self._load_yaml(Path(self._filepath).with_name("globals.yml"))
        paths = globals_.get("paths") if isinstance(globals_, dict) else None
        paths = paths if isinstance(paths, dict) else {}
        entries = []
        for name, spec in catalog.items():
            if not isinstance(name, str) or name.startswith("_") or not isinstance(spec, dict):
                continue
            value = next((spec[k] for k in PATH_KEYS if isinstance(spec.get(k), str)), None)
            relpath = data_root_relpath(value, paths) if value is not None else None
            if relpath is None:
                continue
            metadata = spec.get("metadata")
            layer = metadata.get("layer") if isinstance(metadata, dict) else None
            entries.append((name, str(layer or ""), relpath))
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
        return {"filepath": self._filepath, "path": self._data_root}
