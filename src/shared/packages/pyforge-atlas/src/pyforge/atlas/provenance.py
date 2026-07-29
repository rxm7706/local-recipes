"""Dataset build-provenance resolution (Story I4, AD-17, AUD-ATLAS-043/044).

A payload's provenance is the data's OWN recorded build time, never a
read-time clock stand-in (a read-time stamp cannot distinguish fresh data
from a month-old dataset that simply got read "now" — the bad_spec pass 1
of this story was rejected for exactly that fabrication). This module derives
the real provenance by dataset KIND, dispatched via ``isinstance`` on the
catalog's own dataset object — never a hardcoded name list:

- ``IncrementalParquetDataset`` -> its own ``fetched_at`` column (oldest +
  newest recorded row timestamp).
- ``kedro_datasets.pandas.ParquetDataset`` -> the materialized file's mtime.
- ``kedro_datasets.api.APIDataset`` -> ``now`` (the read genuinely IS the
  fetch for a live API source).
- anything else -> ``null`` + a stated reason (a REQUIRED, valid, non-error
  response — never a fabricated value).

Lives OUTSIDE ``mcp/`` on purpose: ``mcp/tools.py``'s AD-7 AST gate
(``tests/mcp/test_no_business_logic_in_tool_bodies.py``) denies importing
pandas/numpy/duckdb/sqlite3/sqlalchemy/ibis/pyarrow in the gated MCP files
and pins every call in a tool body to an allowlisted seam root, so this is
the one place both the MCP read surface AND the dashboard route their
catalog/dataset introspection through (a single seam call each), free to use
pandas/kedro_datasets.

Provenance is ADVISORY: resolution failure must never abort a read that
already succeeded — every resolver degrades to ``unavailable`` + a reason,
and ``load_with_provenance`` backstops the whole dispatch.
"""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from kedro_datasets.pandas import ParquetDataset

from pyforge.atlas.datasets import IncrementalParquetDataset

SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class ProvenanceInfo:
    """The provenance verdict for one dataset read: a KIND + timestamp(s), or
    an honest ``unavailable`` + reason. Never a computed staleness VERDICT —
    the consumer judges staleness from the timestamp(s) itself."""

    kind: str
    build_stamp: str | None
    build_stamp_newest: str | None = None
    reason: str | None = None


def _iso(epoch_seconds: float) -> str:
    """Epoch seconds -> ISO-8601 (UTC)."""
    return datetime.datetime.fromtimestamp(epoch_seconds, tz=datetime.UTC).isoformat()


def _api_dataset_cls() -> type | None:
    """``kedro_datasets.api.APIDataset``, imported lazily: that module hard-
    imports ``requests`` (a kedro-datasets extra the member manifests do not
    declare), so a module-level import here would make ``requests`` an
    undeclared import-time dependency of the whole MCP surface + dashboard —
    the AUD-ATLAS-010 failure class. The catalog machinery imports it anyway
    the moment an ``api.APIDataset`` catalog entry is instantiated, so the
    lazy import only ever pays what the read already required."""
    try:
        from kedro_datasets.api import APIDataset
    except ImportError:
        return None
    return APIDataset


def resolve_for_file(path: str | os.PathLike[str]) -> ProvenanceInfo:
    """``file-mtime`` provenance: the materialized file's own mtime, or
    ``unavailable`` when the file does not (yet) exist — a missing backing
    file is an honest, non-error state (e.g. the composed store not yet
    populated), never a crash. A single ``stat()`` call (no separate
    ``exists()`` check) avoids a TOCTOU race where the file disappears
    between the check and the read; a non-ENOENT failure (permissions, a
    symlink loop) states what actually happened instead of a false
    "not found"."""
    p = Path(path)
    try:
        mtime = p.stat().st_mtime
    except FileNotFoundError:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"backing file not found: {p}",
        )
    except OSError as exc:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"backing file not readable: {p} ({type(exc).__name__})",
        )
    return ProvenanceInfo(kind="file-mtime", build_stamp=_iso(mtime))


def _resolve_row_fetched_at(loaded_value: Any, column: str) -> ProvenanceInfo:
    """``row-fetched-at`` provenance: the OLDEST/newest ``fetched_at`` values
    actually recorded in the loaded frame. A datetime-typed column (a bypass
    writer persisting ``pd.Timestamp``s) converts unit-independently first —
    ``to_numeric`` on datetime64 yields raw µs/ns integers that the ms-guard's
    single division cannot bring into range. Numeric millisecond-magnitude
    values are then normalized to seconds via ``IncrementalParquetDataset``'s
    OWN documented ms-guard (DW-A3-P10) — reused directly (not reimplemented)
    so the two stay in lockstep by construction. Anything still outside
    ``datetime.fromtimestamp``'s range after that (e.g. raw epoch-µs/ns
    integers) degrades to ``unavailable`` — never a crash — as does an empty
    frame or an all-NULL column."""
    if column not in loaded_value.columns:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"no {column!r} column in the loaded frame",
        )
    col = loaded_value[column]
    if pd.api.types.is_datetime64_any_dtype(col):
        # A genuine recorded time in datetime form — convert via unit-aware
        # arithmetic (datetime64[ns]/[us]/[s], tz-aware or naive-as-UTC all
        # collapse correctly), not via to_numeric magnitude guessing.
        col = (
            pd.to_datetime(col, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")
        ).dt.total_seconds()
    seconds = IncrementalParquetDataset._to_epoch_seconds(col).dropna()
    if seconds.empty:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"no {column!r} values recorded (0 rows or all-NULL)",
        )
    try:
        return ProvenanceInfo(
            kind="row-fetched-at",
            build_stamp=_iso(float(seconds.min())),
            build_stamp_newest=_iso(float(seconds.max())),
        )
    except (ValueError, OverflowError, OSError):
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=(
                f"{column!r} values out of convertible range "
                f"(min {seconds.min()!r}, max {seconds.max()!r})"
            ),
        )


def resolve_for_catalog_dataset(catalog: Any, name: str, loaded_value: Any) -> ProvenanceInfo:
    """Dispatch on ``catalog[name]``'s actual TYPE (never an enumerated/
    hardcoded name list) to derive ``loaded_value``'s genuine provenance."""
    dataset = catalog[name]
    if isinstance(dataset, IncrementalParquetDataset):
        column = dataset._describe()["fetched_at_column"]
        return _resolve_row_fetched_at(loaded_value, column)
    if isinstance(dataset, ParquetDataset):
        described = dataset._describe()
        protocol = described.get("protocol")
        if protocol not in (None, "", "file", "local"):
            # ``_describe()["filepath"]`` is protocol-STRIPPED — a local stat
            # on it would either fail (a FALSE "not found" for data that
            # exists remotely) or, worse, stat an unrelated local path and
            # report its mtime as the data's. Degrade honestly instead.
            return ProvenanceInfo(
                kind="unavailable",
                build_stamp=None,
                reason=f"non-local protocol {protocol!r}: cannot stat the backing file locally",
            )
        return resolve_for_file(described["filepath"])
    api_dataset = _api_dataset_cls()
    if api_dataset is not None and isinstance(dataset, api_dataset):
        # The read IS the fetch — "now" is the genuine provenance, not a
        # fabricated stand-in (the one kind where wall-clock-now is correct).
        return ProvenanceInfo(
            kind="live-fetch",
            build_stamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
        )
    return ProvenanceInfo(
        kind="unavailable",
        build_stamp=None,
        reason=f"no provenance available for dataset type {type(dataset).__name__}",
    )


def load_with_provenance(catalog: Any, name: str) -> tuple[Any, ProvenanceInfo]:
    """Load ``name`` from ``catalog`` AND resolve its provenance in ONE
    function — the ``.load(name)`` call itself lives HERE (not in
    ``mcp/tools.py``) so a caller under the AD-7 AST gate only touches the
    session seam (``_session.loaded_catalog(s)``) ONCE per read, instead of
    binding ``catalog`` and then calling ``catalog.load(name)`` a second time
    (each ``loaded_catalog(s)`` access rebuilds a fresh ``DataCatalog`` from
    ``catalog.yml`` — kedro's ``KedroContext.catalog`` is an uncached
    property). An unknown ``name`` still raises here and propagates up
    unchanged — the envelope wraps only the success path. Provenance itself
    is ADVISORY: once the load has succeeded, ANY resolution failure degrades
    to ``unavailable`` + a reason instead of aborting the read (C4)."""
    value = catalog.load(name)
    try:
        info = resolve_for_catalog_dataset(catalog, name, value)
    except Exception as exc:  # the whole point: never abort a succeeded read
        info = ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"provenance resolution failed ({type(exc).__name__}: {exc})",
        )
    return value, info
