"""``semantic_packages`` node (Story 20.3, CAP-6 / `query-plane-catalog` ruling).

PURE pandas function: DataFrames in -> DataFrame out, NO inline IO (the whole-package
no-inline-IO scan bans HTTP/DB clients here exactly like every other pipeline's nodes).
DOWNSTREAM ONLY of ALREADY-PRODUCED catalog outputs, never a `_raw` source: the sealed
`core` + `vcs_health` pipelines' own, and (Story 38.1) `derived_artifacts`'
`derived_release_cadence` and `derived_graph_archived_feedstocks` -- read here by their
existing catalog dataset names (AD-3: execution order resolves from those names, never a
procedural call order); this module does not touch `pipelines/core/` or
`pipelines/vcs_health/`.
"""

from __future__ import annotations

import time

import pandas as pd

# Story 38.1: the upload-time inputs `metrics.adoption_stage` / `staleness_age_days` read, as
# legacy adoption_stage.py derives them; NULL for a package the release cadence lacks, never
# fabricated (the metrics null-coalesce them to an honest NULL / "unknown").
_UPLOAD_COLUMNS = (
    "latest_conda_upload",
    "latest_upload_age_days",
    "releases_30d",
    "total_versions",
)

# Column order mirrors the shipped `packages_parquet` test fixture
# (tests/dashboard/conftest.py) -- the shape `build_packages_model` already expects.
_OUTPUT_COLUMNS = (
    "conda_name",
    "latest_status",
    "feedstock_archived",
    "latest_conda_upload",
    "downloads_total",
    "downloads_30d",
    "latest_upload_age_days",
    "releases_30d",
    "total_versions",
)


def compose_semantic_packages(
    core_packages_enumerated: pd.DataFrame,
    core_latest_status: pd.DataFrame,
    core_feedstock_attribution: pd.DataFrame,
    vcs_archived_feedstocks: pd.DataFrame,
    core_downloads: pd.DataFrame,
    derived_release_cadence: pd.DataFrame | None = None,
    derived_graph_archived_feedstocks: pd.DataFrame | None = None,
    now: int | None = None,
) -> pd.DataFrame:
    """Compose the `semantic_packages` primary store `build_packages_model`
    (semantic/models.py) binds to (DW-D2-2).

    - ``conda_name`` -- the Phase B population (`core_packages_enumerated`). This node
      does NOT pre-filter; the `is_actionable` BSL predicate narrows downstream, mirroring
      the legacy `v_actionable_packages` scope discipline (core/nodes.py).
    - ``latest_status`` -- LEFT-joined from `core_latest_status`
      (`migrated-column`, `metrics.METRIC_PROVENANCE["is_actionable"]`).
    - ``feedstock_archived`` -- derived by joining `core_feedstock_attribution`
      (conda_name -> feedstock_name) against the archived feedstocks: legacy Phase E.5's
      `vcs_archived_feedstocks` and (Story 38.1) the cf-graph's own flag,
      `derived_graph_archived_feedstocks`, which a public run fills where the GitHub query
      does not. A package with no attribution, or whose feedstock is in neither set, is NOT
      archived (0) -- matching the legacy ``COALESCE(feedstock_archived, 0) = 0`` default.
    - ``downloads_total`` / ``downloads_30d`` -- LEFT-joined from `core_downloads`
      (`migrated-column`).
    - ``latest_conda_upload`` / ``releases_30d`` / ``total_versions`` -- LEFT-joined from
      `derived_release_cadence` (Story 38.1; legacy Phase B and adoption_stage.py's
      ``package_version_downloads`` counts); ``latest_upload_age_days`` is
      ``(now - latest_conda_upload) // 86400``, NULL with no upload time (legacy
      adoption_stage.py:103). A package the cadence lacks, or whose newest build the cadence does not know,
      keeps all four NULL.

    Every join is LEFT off the Phase B population -- an unmatched row degrades to
    NULL/absent, never a fabricated value (mirrors `dashboard/data.py::_bsl_query_or_empty`).
    """
    if (
        core_packages_enumerated is None
        or core_packages_enumerated.empty
        or "conda_name" not in core_packages_enumerated.columns
    ):
        return pd.DataFrame(
            {
                "conda_name": pd.Series([], dtype="object"),
                "latest_status": pd.Series([], dtype="object"),
                **{
                    col: pd.array([], dtype="Int64")
                    for col in _OUTPUT_COLUMNS
                    if col not in ("conda_name", "latest_status")
                },
            }
        )[list(_OUTPUT_COLUMNS)]

    out = (
        core_packages_enumerated[["conda_name"]].dropna(subset=["conda_name"]).drop_duplicates().reset_index(drop=True)
    )

    # latest_status (migrated-column).
    if (
        core_latest_status is not None
        and not core_latest_status.empty
        and {"conda_name", "latest_status"} <= set(core_latest_status.columns)
    ):
        out = out.merge(
            core_latest_status[["conda_name", "latest_status"]].drop_duplicates("conda_name"),
            on="conda_name",
            how="left",
        )
    else:
        out["latest_status"] = None

    # feedstock_archived (migrated-column, joinable from vcs_archived_feedstocks).
    archived_feedstocks: set = set()
    if (
        vcs_archived_feedstocks is not None
        and not vcs_archived_feedstocks.empty
        and "feedstock_name" in vcs_archived_feedstocks.columns
    ):
        archived_feedstocks = set(vcs_archived_feedstocks["feedstock_name"].dropna())
    if (
        derived_graph_archived_feedstocks is not None
        and not derived_graph_archived_feedstocks.empty
        and "feedstock_name" in derived_graph_archived_feedstocks.columns
    ):
        archived_feedstocks |= set(derived_graph_archived_feedstocks["feedstock_name"].dropna())
    if (
        core_feedstock_attribution is not None
        and not core_feedstock_attribution.empty
        and {"conda_name", "feedstock_name"} <= set(core_feedstock_attribution.columns)
    ):
        attribution = core_feedstock_attribution[["conda_name", "feedstock_name"]].drop_duplicates("conda_name")
        out = out.merge(attribution, on="conda_name", how="left")
        out["feedstock_archived"] = out["feedstock_name"].isin(archived_feedstocks).astype("Int64")
        out = out.drop(columns=["feedstock_name"])
    else:
        out["feedstock_archived"] = pd.array([0] * len(out), dtype="Int64")

    # downloads_total / downloads_30d (migrated-column).
    if core_downloads is not None and not core_downloads.empty and "conda_name" in core_downloads.columns:
        keep = [c for c in ("conda_name", "downloads_total", "downloads_30d") if c in core_downloads.columns]
        out = out.merge(core_downloads[keep].drop_duplicates("conda_name"), on="conda_name", how="left")
    for col in ("downloads_total", "downloads_30d"):
        if col in out.columns:
            out[col] = out[col].astype("Int64")
        else:
            out[col] = pd.array([pd.NA] * len(out), dtype="Int64")

    # Upload-time inputs (Story 38.1) -- from the release cadence, never fabricated.
    cadence_columns = ["latest_conda_upload", "releases_30d", "total_versions"]
    if (
        derived_release_cadence is not None
        and not derived_release_cadence.empty
        and {"conda_name", "latest_build_known", *cadence_columns} <= set(derived_release_cadence.columns)
    ):
        cadence = derived_release_cadence[["conda_name", "latest_build_known", *cadence_columns]]
        cadence = cadence.drop_duplicates("conda_name")
        # a newest build of unknown provenance (a copy cached before Story 38.1) leaves all three NULL, so the stage
        # reads unknown; with the counts kept and the time NULL, legacy's `age or 99999` would read it silent
        known = cadence["latest_build_known"].fillna(False).astype(bool)
        cadence = cadence.assign(**{col: cadence[col].astype("Int64").where(known) for col in cadence_columns})
        out = out.merge(cadence.drop(columns="latest_build_known"), on="conda_name", how="left")
    for col in cadence_columns:
        out[col] = out[col].astype("Int64") if col in out.columns else pd.array([pd.NA] * len(out), dtype="Int64")
    now_ts = int(time.time()) if now is None else now
    upload = out["latest_conda_upload"]
    # legacy `(now - latest_conda_upload) // 86400 if latest_conda_upload else None`: 0 is no upload time
    out["latest_upload_age_days"] = ((now_ts - upload) // 86400).where(upload.notna() & (upload != 0)).astype("Int64")

    return out[list(_OUTPUT_COLUMNS)].reset_index(drop=True)
