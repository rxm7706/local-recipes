"""``semantic_packages`` node (Story 20.3, CAP-6 / `query-plane-catalog` ruling).

PURE pandas function: DataFrames in -> DataFrame out, NO inline IO (the whole-package
no-inline-IO scan bans HTTP/DB clients here exactly like every other pipeline's nodes).
DOWNSTREAM ONLY of the sealed `core` + `vcs_health` pipelines' OWN, ALREADY-PRODUCED
catalog outputs -- read here by their existing catalog dataset names (AD-3: execution
order resolves from those names, never a procedural call order); this module does not
touch `pipelines/core/` or `pipelines/vcs_health/`.
"""

from __future__ import annotations

import pandas as pd

# The `metrics.METRIC_PROVENANCE` columns whose legacy source is not yet in the migrated
# store (`data_wiring: "deferred-input-not-in-migrated-store"`) -- declared here as
# explicit NULL (nullable Int64) columns, NEVER fabricated. `staleness_age_days` /
# `adoption_stage` (semantic/metrics.py) already null-coalesce these inputs
# (`ts.isnull()`, `.fill_null(0)`), so a downstream BSL query degrades to an honest
# NULL / "unknown" instead of crashing on a missing column.
_DEFERRED_INPUT_COLUMNS = (
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
) -> pd.DataFrame:
    """Compose the `semantic_packages` primary store `build_packages_model`
    (semantic/models.py) binds to (DW-D2-2).

    - ``conda_name`` -- the Phase B population (`core_packages_enumerated`). This node
      does NOT pre-filter; the `is_actionable` BSL predicate narrows downstream, mirroring
      the legacy `v_actionable_packages` scope discipline (core/nodes.py).
    - ``latest_status`` -- LEFT-joined from `core_latest_status`
      (`migrated-column`, `metrics.METRIC_PROVENANCE["is_actionable"]`).
    - ``feedstock_archived`` -- derived by joining `core_feedstock_attribution`
      (conda_name -> feedstock_name) against `vcs_archived_feedstocks` (the
      archived-feedstock skip-set) -- exactly the join
      `METRIC_PROVENANCE["is_actionable"]` names ("feedstock_archived joinable from
      vcs_archived_feedstocks"). A package with no attribution, or whose feedstock never
      appears in the skip-set, is NOT archived (0) -- matching the legacy
      ``COALESCE(feedstock_archived, 0) = 0`` default.
    - ``downloads_total`` / ``downloads_30d`` -- LEFT-joined from `core_downloads`
      (`migrated-column`).
    - ``latest_conda_upload`` / ``latest_upload_age_days`` / ``releases_30d`` /
      ``total_versions`` -- see `_DEFERRED_INPUT_COLUMNS` above: declared NULL, never
      fabricated.

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

    # Deferred inputs -- never fabricated (see docstring / _DEFERRED_INPUT_COLUMNS).
    for col in _DEFERRED_INPUT_COLUMNS:
        out[col] = pd.array([pd.NA] * len(out), dtype="Int64")

    return out[list(_OUTPUT_COLUMNS)].reset_index(drop=True)
