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
pandas/kedro_datasets in the MCP surface, so this is the one place both the
MCP read surface AND the dashboard route their catalog/dataset introspection
through (a single seam call each), free to use pandas/kedro_datasets.
"""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kedro_datasets.api import APIDataset
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


def resolve_for_file(path: str | os.PathLike[str]) -> ProvenanceInfo:
    """``file-mtime`` provenance: the materialized file's own mtime, or
    ``unavailable`` when the file does not (yet) exist — a missing backing
    file is an honest, non-error state (e.g. the composed store not yet
    populated), never a crash. A single ``stat()`` call (no separate
    ``exists()`` check) avoids a TOCTOU race where the file disappears
    between the check and the read."""
    p = Path(path)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"backing file not found: {p}",
        )
    return ProvenanceInfo(kind="file-mtime", build_stamp=_iso(mtime))


def _resolve_row_fetched_at(loaded_value: Any, column: str) -> ProvenanceInfo:
    """``row-fetched-at`` provenance: the OLDEST/newest ``fetched_at`` values
    actually recorded in the loaded frame. Millisecond-magnitude values are
    normalized to seconds via ``IncrementalParquetDataset``'s OWN documented
    ms-guard (DW-A3-P10) before conversion — reused directly (not
    reimplemented) so the two stay in lockstep by construction; skipping this
    would crash on real ms-source data (Phase F/I writers) with
    ``ValueError: year ... out of range`` instead of returning a stamp.
    An empty frame or an all-NULL column degrades to ``unavailable`` — never
    a crash on a 0-row/degenerate column."""
    if column not in loaded_value.columns:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"no {column!r} column in the loaded frame",
        )
    seconds = IncrementalParquetDataset._to_epoch_seconds(loaded_value[column]).dropna()
    if seconds.empty:
        return ProvenanceInfo(
            kind="unavailable",
            build_stamp=None,
            reason=f"no {column!r} values recorded (0 rows or all-NULL)",
        )
    return ProvenanceInfo(
        kind="row-fetched-at",
        build_stamp=_iso(float(seconds.min())),
        build_stamp_newest=_iso(float(seconds.max())),
    )


def resolve_for_catalog_dataset(catalog: Any, name: str, loaded_value: Any) -> ProvenanceInfo:
    """Dispatch on ``catalog[name]``'s actual TYPE (never an enumerated/
    hardcoded name list) to derive ``loaded_value``'s genuine provenance."""
    dataset = catalog[name]
    if isinstance(dataset, IncrementalParquetDataset):
        column = dataset._describe()["fetched_at_column"]
        return _resolve_row_fetched_at(loaded_value, column)
    if isinstance(dataset, ParquetDataset):
        return resolve_for_file(dataset._describe()["filepath"])
    if isinstance(dataset, APIDataset):
        # The read IS the fetch — "now" is the genuine provenance, not a
        # fabricated stand-in (the one kind where wall-clock-now is correct).
        return ProvenanceInfo(kind="live-fetch", build_stamp=_iso(datetime.datetime.now(tz=datetime.UTC).timestamp()))
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
    unchanged — the envelope wraps only the success path."""
    value = catalog.load(name)
    return value, resolve_for_catalog_dataset(catalog, name, value)
