"""PURE extract node — catalog owns Parquet IO (AC-2)."""

from __future__ import annotations

import pandas as pd


def extract_estate_to_cache(query_plane_estate_source: pd.DataFrame) -> pd.DataFrame:
    """Copy the estate frame for the catalog Parquet writer.

    No file, network, or OLTP handle. Compression and path live on the
    ``query_plane_estate`` catalog entry.
    """
    if query_plane_estate_source is None:
        return pd.DataFrame()
    return query_plane_estate_source.copy()
