"""``catalog_index`` pipeline nodes (Story 37.10, CAP-69). PURE: the catalog index arrives as a frame
(``CatalogIndexDataset`` owns the file reads)."""

from __future__ import annotations

from typing import Any

import pandas as pd

CATALOG_INDEX_HEALTH_COLUMNS = [
    "catalog_entry",
    "tier",
    "layer",
    "regenerated_at",
    "row_count",
    "floor",
    "status",
    "stale_reason",
]
#: an entry the catalog-sources tier matrix does not name
UNTIERED = "untiered"
#: this pipeline's own output: its row would only report the previous run's write
SELF = "catalog_index_health"


def _status(written: Any, stale: bool, rows: Any, floor: Any) -> str:
    if written is None or pd.isna(written):
        return "missing"
    if stale:
        return "stale"
    if rows is None or pd.isna(rows):
        return "ok"  # a store that is not Parquet: its write is known, its count is not
    if int(rows) == 0:
        return "empty"
    if floor is not None and not pd.isna(floor) and int(rows) < int(floor):
        return "below_floor"
    return "ok"


def report_catalog_index_health(catalog_index_raw: pd.DataFrame | None, params: dict | None) -> pd.DataFrame:
    """The bootstrap-index-health board's table: each catalog entry the data root holds, its tier, last write and
    row count, and a status.

    ``params`` (``catalog_index_health``) carries ``tiers`` (entry to "Tier 0".."Tier 3", the catalog-sources tier
    matrix, each source by the dataset that persists it) and ``floors`` (entry to the scale sanity gate's minimum
    row count). ``status`` is ``missing`` (never written), ``stale`` (its staleness marker says so), ``empty``,
    ``below_floor`` or ``ok``. Tiered entries sort first, by tier."""
    index = catalog_index_raw
    if index is None or index.empty or "catalog_entry" not in index.columns:
        return _empty_health()
    params = params or {}
    tiers: dict[str, str] = dict(params.get("tiers") or {})
    floors: dict[str, int] = {k: int(v) for k, v in (params.get("floors") or {}).items()}
    records = []
    for row in index.to_dict("records"):
        name = str(row["catalog_entry"])
        if name == SELF:
            continue
        rows = row.get("row_count")
        written = row.get("regenerated_at")
        floor = floors.get(name)
        records.append(
            {
                "catalog_entry": name,
                "tier": tiers.get(name, UNTIERED),
                "layer": row.get("layer") or None,
                "regenerated_at": written,
                "row_count": rows,
                "floor": floor,
                "status": _status(written, bool(row.get("stale")), rows, floor),
                "stale_reason": row.get("stale_reason") or None,
            }
        )
    out = pd.DataFrame.from_records(records, columns=CATALOG_INDEX_HEALTH_COLUMNS)
    out = _typed(out)
    order = out["tier"].where(out["tier"] != UNTIERED, "~")
    return (
        out.assign(_order=order).sort_values(["_order", "catalog_entry"]).drop(columns="_order").reset_index(drop=True)
    )


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("catalog_entry", "tier", "layer", "status", "stale_reason"):
        frame[column] = frame[column].astype("string")
    frame["regenerated_at"] = pd.to_datetime(frame["regenerated_at"], utc=True)
    for column in ("row_count", "floor"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    return frame


def _empty_health() -> pd.DataFrame:
    return _typed(pd.DataFrame({column: [] for column in CATALOG_INDEX_HEALTH_COLUMNS}))
