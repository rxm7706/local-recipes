"""Lifecycle projections for the semantic store and the version-downloads board (Story 38.1, CAP-69).

Two PURE nodes over datasets the pipelines already produce or fetch:

- ``project_graph_archived_feedstocks``: every feedstock the conda-forge bot's graph flags archived. Legacy reads the
  flag from Phase E.5's GitHub query (``vcs_archived_feedstocks``), which a public run leaves empty; core's Phase J
  skip-set and Story 37.7's scorer already read the graph's flag. ``semantic_packages`` reads both sets.
- ``project_version_downloads``: ``core_version_download_history`` with each version's upload date, the UTC date of
  its earliest file in the full repodata (legacy ``version_downloads.py`` prints ``upload_unix``'s date).
"""

from __future__ import annotations

import pandas as pd

GRAPH_ARCHIVED_COLUMNS = ["feedstock_name", "archived"]
VERSION_DOWNLOADS_COLUMNS = ["conda_name", "version", "downloads", "upload_date"]


def _flag(value: object) -> bool:
    """The cf-graph's archived flag as core's Phase J reads it (``_as_bool_series``): the string ``"false"`` is not
    archived, and a null is not; kept local so the pipelines stay import-independent."""
    if isinstance(value, bool):
        return value
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return False
    return str(value).strip().lower() in ("true", "1", "t", "yes")


def project_graph_archived_feedstocks(core_cf_graph_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase E.5 (phase_e5_archived_feedstocks CFA:2504), read from the graph as core's Phase J does
    """The feedstocks the cf-graph flags archived, one row each, sorted; ``archived`` is always true."""
    graph = core_cf_graph_raw
    if graph is None or graph.empty or not {"feedstock_name", "feedstock_archived"} <= set(graph.columns):
        return pd.DataFrame({"feedstock_name": pd.Series([], dtype=object), "archived": pd.Series([], dtype=bool)})
    flagged = graph.loc[graph["feedstock_archived"].map(_flag), "feedstock_name"].dropna().astype(str)
    names = sorted(set(flagged))
    return pd.DataFrame({"feedstock_name": pd.Series(names, dtype=object), "archived": [True] * len(names)})


def project_version_downloads(
    core_version_download_history: pd.DataFrame,
    core_repodata_uploads_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: version_downloads.py (package_version_downloads.upload_unix, Phase I)
    """Each (package, version) download row with its upload date; null when the version has no timed file."""
    history = core_version_download_history
    if history is None or history.empty or not {"conda_name", "version", "downloads"} <= set(history.columns):
        return _typed_downloads(pd.DataFrame(columns=VERSION_DOWNLOADS_COLUMNS))
    out = history[["conda_name", "version", "downloads"]].copy()
    uploads = core_repodata_uploads_raw
    if uploads is not None and not uploads.empty and {"conda_name", "version", "upload_unix"} <= set(uploads.columns):
        times = uploads[["conda_name", "version", "upload_unix"]].drop_duplicates(["conda_name", "version"])
        out = out.merge(times, on=["conda_name", "version"], how="left")
        stamps = pd.to_datetime(out["upload_unix"].astype("Int64").astype("float64"), unit="s", utc=True)
        out["upload_date"] = [None if pd.isna(t) else t.date() for t in stamps]
        out = out.drop(columns="upload_unix")
    else:
        out["upload_date"] = None
    return _typed_downloads(out[VERSION_DOWNLOADS_COLUMNS])


def _typed_downloads(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype({"conda_name": object, "version": object, "downloads": "Int64", "upload_date": object})
