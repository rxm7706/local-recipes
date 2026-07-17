"""``IncrementalParquetDataset`` — the ONE reusable TTL/checkpoint primitive.

Story A3 (spec § 9; FR-3 per-dataset TTLs; FR-4 the dataset is the resumability
primitive; AD-5 incremental state is a dataset concern). This class encapsulates
the legacy ``*_fetched_at`` row-level TTL gate (cf-atlas-legacy
``atlas_phase._TTL_GATED`` — ``F→downloads_fetched_at``, ``H→pypi_version_fetched_at``,
``K→github_version_fetched_at``, …; reset = timestamps NULLed, nothing deleted)
into a single Kedro dataset so that **no node ever re-implements checkpoint / TTL /
backoff** and resumability is Kedro-native (runner + persisted Parquet — there is
NO ``phase_state`` table anywhere in the migrated surface, FR-4).

Design (Dev Notes "Kedro 1.5.0 dataset API", verified live):
- Subclasses ``kedro.io.AbstractVersionedDataset`` (implementing the kedro 1.x
  PUBLIC abstract methods ``load`` / ``save`` / ``_describe`` — NOT the pre-1.0
  ``_load`` / ``_save``).
- COMPOSES an internal ``kedro_datasets.pandas.ParquetDataset`` for the physical
  Parquet IO (fsspec + versioning are inherited from the composed dataset rather
  than re-implemented). Parquet file IO is catalog-owned IO (AD-2) and is NOT on
  the ``kedro-catalog-check`` no-inline-IO denylist (which bans HTTP/DB clients,
  not ``pandas``/``pyarrow``/``kedro_datasets``).
- ``ttl_seconds`` is OPTIONAL (default ``None``): the A2 ``kedro-catalog-check``
  resolution test constructs each flipped entry from config that carries only
  ``type``/``filepath``/``metadata`` (no ttl), so a required ttl arg would fail the
  gate. The runtime ttl is injected by ``pyforge.atlas.hooks.ProjectHooks`` from
  ``params:ttls.<dataset-name>`` (see hooks.py). With ``ttl_seconds is None`` the
  dataset never reports a row as stale (documented below).

Imports are restricted to ``pandas`` / ``kedro`` / ``kedro_datasets`` /
``pathlib`` / ``time`` / stdlib-non-IO — NO ``IO_DENYLIST`` HTTP/DB client and no
``dagster`` / ``kedro_mcp`` (the whole ``datasets/`` subpackage is scanned by A2's
``test_no_inline_io.py``).
"""

from __future__ import annotations

import time
from pathlib import PurePosixPath
from typing import Any

import pandas as pd
from kedro.io import AbstractVersionedDataset
from kedro_datasets.pandas import ParquetDataset


class IncrementalParquetDataset(AbstractVersionedDataset[pd.DataFrame, pd.DataFrame]):
    """Parquet dataset that stamps + round-trips a per-row ``fetched_at`` epoch
    timestamp and owns the TTL freshness verdict (fresh → skip, stale → re-fetch).

    Parameters
    ----------
    filepath:
        Path to the Parquet payload (``data/<layer>/<name>/<name>.parquet``).
    ttl_seconds:
        Per-dataset time-to-live in seconds. OPTIONAL — when ``None`` the dataset
        treats every persisted row as fresh (``stale_mask`` is all-``False``); a
        runtime value is injected from ``params:ttls.<name>`` by the project hook.
    fetched_at_column:
        Name of the epoch-seconds fetch-timestamp column (default ``fetched_at``,
        the Spine timestamp convention).
    load_args / save_args / version / credentials / fs_args / metadata:
        Forwarded verbatim to the composed ``pandas.ParquetDataset``.
    """

    DEFAULT_FETCHED_AT_COLUMN = "fetched_at"

    def __init__(
        self,
        *,
        filepath: str,
        ttl_seconds: int | None = None,
        fetched_at_column: str = DEFAULT_FETCHED_AT_COLUMN,
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        version: Any = None,
        credentials: dict[str, Any] | None = None,
        fs_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._fetched_at_column = fetched_at_column
        self.metadata = metadata

        # Compose the physical Parquet IO (fsspec + versioning owned here).
        self._inner = ParquetDataset(
            filepath=filepath,
            load_args=load_args,
            save_args=save_args,
            version=version,
            credentials=credentials,
            fs_args=fs_args,
            metadata=metadata,
        )

        # Wire the versioned base minimally, delegating existence to the inner
        # dataset's fsspec probe. No network/disk touch at construction time.
        super().__init__(
            filepath=PurePosixPath(filepath),
            version=version,
            exists_function=self._inner._exists,
            glob_function=None,
        )

    # -- kedro 1.5.0 public abstract methods -------------------------------

    def save(self, data: pd.DataFrame) -> None:
        """Persist ``data`` as Parquet, stamping the ``fetched_at`` column with the
        current epoch seconds on every row when the caller did not already supply
        it. A caller-provided ``fetched_at`` is PRESERVED (so upstream fetch times
        survive), enabling the freshness verdict to round-trip save→load."""
        df = data.copy()
        if self._fetched_at_column not in df.columns:
            df[self._fetched_at_column] = int(time.time())
        self._inner.save(df)

    def load(self) -> pd.DataFrame:
        """Read the persisted frame back with ``fetched_at`` intact (round-trip).
        A node combines this with :meth:`stale_mask` to re-fetch only stale rows
        and skip fresh ones — the resumability primitive (FR-4/AD-5)."""
        return self._inner.load()

    def _describe(self) -> dict[str, Any]:
        inner = self._inner._describe()
        return {
            "filepath": inner.get("filepath"),
            "ttl_seconds": self._ttl_seconds,
            "fetched_at_column": self._fetched_at_column,
            "version": inner.get("version"),
            "protocol": inner.get("protocol"),
        }

    # -- freshness API (AD-5: the dataset OWNS the check) -------------------

    @property
    def ttl_seconds(self) -> int | None:
        return self._ttl_seconds

    @ttl_seconds.setter
    def ttl_seconds(self, value: int | None) -> None:
        # Runtime injection point for pyforge.atlas.hooks.ProjectHooks
        # (params:ttls.<name>). Keeps parameters.yml the single source of truth.
        self._ttl_seconds = value

    @property
    def fetched_at_column(self) -> str:
        return self._fetched_at_column

    def stale_mask(self, df: pd.DataFrame, now: int | None = None) -> pd.Series:
        """Boolean Series aligned to ``df.index``: ``True`` where a row is STALE
        (its ``fetched_at`` is older than ``now - ttl_seconds`` → surfaced for
        re-fetch), ``False`` where it is FRESH (within the window → skipped).

        ``now`` defaults to the current epoch seconds. When ``ttl_seconds`` is
        ``None`` (no runtime ttl injected) every row is treated as FRESH — an
        all-``False`` mask — so an un-wired dataset never forces a re-fetch.
        Rows whose ``fetched_at`` is missing/NaN are treated as STALE (they have
        no proof of freshness), matching the legacy NULL-gate-column semantics.
        """
        if now is None:
            now = int(time.time())
        col = self._fetched_at_column
        if self._ttl_seconds is None:
            return pd.Series(False, index=df.index)
        if col not in df.columns:
            # No fetch timestamp at all → nothing can be proven fresh.
            return pd.Series(True, index=df.index)
        fetched_at = pd.to_numeric(df[col], errors="coerce")
        cutoff = now - self._ttl_seconds
        # A row is stale if its timestamp is older than the cutoff OR missing.
        # (A comparison against NaN yields False, not NaN — so the missing case
        # must be OR-ed in explicitly rather than left to fillna.)
        stale = (fetched_at < cutoff) | fetched_at.isna()
        return stale.astype(bool)

    def fresh_mask(self, df: pd.DataFrame, now: int | None = None) -> pd.Series:
        """Complement of :meth:`stale_mask` — ``True`` for rows that may be skipped."""
        return ~self.stale_mask(df, now=now)

    def is_stale(self, df: pd.DataFrame, now: int | None = None) -> bool:
        """``True`` if ANY row is stale (convenience for whole-frame gating)."""
        return bool(self.stale_mask(df, now=now).any())
