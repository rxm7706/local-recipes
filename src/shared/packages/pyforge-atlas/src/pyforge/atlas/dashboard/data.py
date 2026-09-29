"""Page data loaders — every read goes THROUGH the D1 BSL models (AD-8).

Each loader builds an Ibis/DuckDB table from a migrated-catalog Parquet file (via the D1
query-time seam ``models.duckdb_table_from_parquet``), binds it to the relevant
``SemanticModel``, and runs a DECLARED BSL query (dimensions / measures). There is NO raw
SQL and NO re-implemented metric arithmetic here — that is the whole point of AD-8: the
metric logic lives once in ``semantic/metrics.py`` + ``semantic/models.py``.

Offline / data-gap discipline (honest core): when the backing Parquet is absent — which
is the state of the migrated store until the attended B4 population event — a loader
returns an EMPTY DataFrame with the query's declared columns. It never fabricates rows.
Pages whose backing dataset is not yet materialized are therefore BSL-wired shells that
render empty and carry a documented gap note (see ``app.py`` + DW-D2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from ..semantic import models

# ---------------------------------------------------------------------------
# Migrated-catalog Parquet relpaths (mirror conf/base/catalog.yml `filepath`s,
# minus the `data/` root which `default_data_root()` supplies).
# ---------------------------------------------------------------------------

# GROUNDED — single migrated datasets the BSL models bind to directly.
FEEDSTOCK_HEALTH_PARQUET = "primary/core_feedstock_health/core_feedstock_health.parquet"
PACKAGE_MAINTAINERS_PARQUET = "intermediate/vcs_package_maintainers/vcs_package_maintainers.parquet"

# COMPOSED — the per-package "packages" table ``build_packages_model`` binds to
# (conda_name + latest_status + feedstock_archived + latest_conda_upload +
# downloads_* + per-version fields) is derived by the named, downstream-only
# ``semantic_packages`` Kedro pipeline (Story 20.3, CAP-6 / ``query-plane-catalog``
# ruling) from the sealed ``core`` + ``vcs_health`` pipelines' own catalog outputs —
# run it (after ``core`` + ``vcs_health``) with ``kedro run --pipeline
# semantic_packages`` to materialize this Parquet. ``latest_conda_upload`` / the
# per-version inputs are themselves ``deferred-input-not-in-migrated-store`` (D1
# ``metrics.METRIC_PROVENANCE``) — the pipeline node declares them NULL, never
# fabricated. In a checkout where the pipeline has not yet run, the loader still
# degrades honestly to an empty result via the same ``_bsl_query_or_empty`` seam
# every page uses. Closes DW-D2-2.
PACKAGES_PARQUET = "primary/semantic_packages/semantic_packages.parquet"
ESTATE_CACHE_PARQUET = "primary/query_plane_estate/query_plane_estate.parquet"

# UNMIGRATED (Story 20.5, CAP-7) — the 19 remaining CLI pages' BSL models bind to
# these relpaths, exactly like the 3 packages-backed shells above did before Story
# 20.3 materialized them. None of these datasets exist yet (no Kedro pipeline
# produces them) — the loader below degrades honestly to an empty typed frame via
# the SAME `_bsl_query_or_empty` seam until a future pipeline lands each one.
VULN_HISTORY_PARQUET = "primary/vuln_history/vuln_history.parquet"
VERSION_DOWNLOADS_PARQUET = "primary/version_downloads/version_downloads.parquet"
RELEASE_CADENCE_PARQUET = "primary/release_cadence/release_cadence.parquet"
ALTERNATIVE_CANDIDATES_PARQUET = "primary/alternative_candidates/alternative_candidates.parquet"
SCAN_RESULT_LATEST_PARQUET = "primary/scan_project_latest/scan_project_latest.parquet"
ENV_INSPECT_LATEST_PARQUET = "primary/env_inspect_latest/env_inspect_latest.parquet"
DISTRIBUTION_BREAKDOWN_PARQUET = "primary/distribution_breakdown/distribution_breakdown.parquet"
PURL_EXPORT_MANIFEST_PARQUET = "primary/purl_export_manifest/purl_export_manifest.parquet"
MAPPING_GAP_PARQUET = "primary/mapping_gap/mapping_gap.parquet"
UNIVERSE_SBOM_SUMMARY_PARQUET = "primary/universe_sbom_summary/universe_sbom_summary.parquet"
INVENTORY_MATCH_LATEST_PARQUET = "primary/inventory_match_latest/inventory_match_latest.parquet"
ADD_HANDOFF_LATEST_PARQUET = "primary/add_handoff_latest/add_handoff_latest.parquet"
LIBRARY_FUTURES_LATEST_PARQUET = "primary/library_futures_latest/library_futures_latest.parquet"
RECOMMEND_2027_PARQUET = "primary/recommend_2027/recommend_2027.parquet"
LTS_REGISTRY_GAP_PARQUET = "primary/lts_registry_gap/lts_registry_gap.parquet"
CWE_SEED_GAP_PARQUET = "primary/cwe_seed_gap/cwe_seed_gap.parquet"
SPDX_SCHEMA_GAP_PARQUET = "primary/spdx_schema_gap/spdx_schema_gap.parquet"
LICENSE_MAP_GAP_PARQUET = "primary/license_map_gap/license_map_gap.parquet"
IDENTITY_COMPLETE_EXPORT_PARQUET = "derived/identity_complete_export/identity_complete_export.parquet"
ENTERPRISE_JFROG_CONSUMPTION_PARQUET = "derived/enterprise_jfrog_consumption/enterprise_jfrog_consumption.parquet"
# Story 21.9 (CAP-5) — Epic 21 bootstrap verification operator pages
BOOTSTRAP_INDEX_HEALTH_PARQUET = "derived/bootstrap_index_health/bootstrap_index_health.parquet"
IDENTITY_EXPORT_PARQUET = "derived/identity_export_parquet/identity_export_parquet.parquet"
LIVE_CATALOG_COVERAGE_PARQUET = "derived/live_catalog_coverage/live_catalog_coverage.parquet"

# Mirrors ``scripts/openteams_identity_dashboards.py::EXTERNAL_LIVE`` — static reference rows.
IDENTITY_WORKBOOK_EXTERNAL_COUNTS: tuple[tuple[str, str, str, str], ...] = (
    ("Anaconda Dist 2026.x", "639", "HTML 2026.x table", "639 (Anaaconda-Dist)"),
    ("Anaconda main", "5461", "pkgs/main channeldata.json", "5,458 (Anaconda-Main)"),
    ("conda-forge", "33875", "conda-forge channeldata.json", "33,875 (Conda-Forge)"),
    ("Basilisk /v1/packages", "33853", "api.basilisk.prefix.dev", "33,853 (Basilisk)"),
    ("AOSS free Python", "1466", "docs #python list", "1,474 (GAOSS-Free)"),
    ("AOSS premium Python", "2114", "Wayback Python <ul>", "2,114 (GAOSS-Premium)"),
    ("about maintainers", "559", "README As Maintainer", "n/a"),
    ("about co-maintainers", "255", "README As Co-Maintainer", "n/a"),
)

_IDENTITY_WORKBOOK_DIMENSIONS = ["match_bucket"]
_IDENTITY_WORKBOOK_MEASURES = ["package_count", "artifactory_downloads_total"]


def default_data_root() -> Path:
    """The catalog ``data_root`` (env-overridable, mirrors globals.yml `paths.data_root`).

    Defaults to ``<repo>/data`` — the repo-root-relative default the catalog resolves
    against the process CWD (review-pass P9). ``PYFORGE_ATLAS_DATA_ROOT`` overrides it.
    """
    env = os.environ.get("PYFORGE_ATLAS_DATA_ROOT")
    if env:
        return Path(env)
    # Walk up to the repo root so this resolves whether run from the source tree or an installed
    # layout. Anchor on ``.git`` (a UNIQUE repo-root marker) — NOT ``pixi.toml``, which the
    # pyforge-atlas member also ships, so a pixi.toml walk would stop at the member dir.
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent / "data"
    return (current.parents[8] if len(current.parents) > 8 else current.parent) / "data"


def _bsl_query_or_empty(
    parquet: str | os.PathLike[str] | None,
    build_model: Callable[..., Any],
    dimensions: list[str],
    measures: list[str] | None = None,
    *,
    model_kwargs: dict[str, Any] | None = None,
    connection: Any | None = None,
) -> pd.DataFrame:
    """Run a declared BSL query, or return an empty typed shell when the Parquet is absent.

    The single AD-8 seam for the data pages: missing file → empty DataFrame with exactly
    the query's declared columns (no fabrication); present file → the BSL model's query
    result. Never re-implements a metric.
    """
    measures = measures or []
    columns = [*dimensions, *measures]
    if parquet is None or not os.path.exists(str(parquet)):
        return pd.DataFrame(columns=columns)
    table = models.duckdb_table_from_parquet(str(parquet), connection=connection)
    model = build_model(table, **(model_kwargs or {}))
    try:
        from pyforge.atlas.semantic.query_helpers import bsl_query

        return bsl_query(
            model,
            dimensions=dimensions,
            measures=measures,
        )
    except TypeError:
        # A PRESENT but degenerate Parquet — e.g. a 0-row store whose column round-tripped
        # untyped/all-null, so a metric predicate like `latest_status.fill_null("active")`
        # raises IbisTypeError (an ibis TypeError subclass) on int-vs-string. Degrade to the
        # declared-column empty shell rather than crash the page build (Reviewer-B S2; the
        # migration writes typed schemas, but the shell pages may hit a first, sparse store).
        return pd.DataFrame(columns=columns)


# ---------------------------------------------------------------------------
# GROUNDED data pages (BSL query over a migrated single dataset)
# ---------------------------------------------------------------------------


def load_feedstock_health(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`feedstock-health` — build_feedstock_health_model over core_feedstock_health."""
    return _bsl_query_or_empty(
        parquet,
        models.build_feedstock_health_model,
        ["feedstock_name", "ci_red", "has_open_prs", "has_open_issues"],
    )


def load_my_feedstocks(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`my-feedstocks` — the maintainer ⋈ (first-class ``maintainer`` dimension, AC-2)
    over vcs_package_maintainers: each maintainer's package list as a declared BSL query."""
    return _bsl_query_or_empty(
        parquet,
        models.build_package_maintainers_model,
        ["maintainer", "conda_name"],
    )


# ---------------------------------------------------------------------------
# BSL-wired data pages over the composed ``semantic_packages`` store (materialized
# by the ``semantic_packages`` pipeline — Story 20.3 / CAP-6 — DW-D2-2 closed)
# ---------------------------------------------------------------------------


def load_staleness(parquet: str | os.PathLike[str] | None = None, *, now: int) -> pd.DataFrame:
    """`staleness-report` — build_packages_model.staleness_age_days (+ adoption stage)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "staleness_age_days", "adoption_stage"],
        model_kwargs={"now_unix": now},
    )


def load_query_atlas(parquet: str | os.PathLike[str] | None = None, *, now: int) -> pd.DataFrame:
    """`query-atlas` — the actionable-scope surface: is_actionable + adoption stage per
    package with the downloads measure (build_packages_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "is_actionable", "adoption_stage"],
        ["downloads_total"],
        model_kwargs={"now_unix": now},
    )


def load_estate_cache(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """Lane 3 / FR-47 — BSL over the named estate Parquet cache."""
    path = parquet
    if path is None:
        path = default_data_root() / ESTATE_CACHE_PARQUET
    return _bsl_query_or_empty(
        path,
        models.build_estate_cache_model,
        ["sku"],
        ["units_total"],
    )


def load_detail(parquet: str | os.PathLike[str] | None = None, *, now: int) -> pd.DataFrame:
    """`detail-cf-atlas` — the full per-package metric row (build_packages_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "is_actionable", "adoption_stage", "staleness_age_days"],
        ["downloads_total", "downloads_30d"],
        model_kwargs={"now_unix": now},
    )


# ---------------------------------------------------------------------------
# Story 20.5 (CAP-7) — the 19 remaining CLI pages, BSL-routed via the SAME
# `_bsl_query_or_empty` seam. Every one of these datasets is unmigrated (no
# Kedro pipeline produces it yet), so every loader degrades honestly to an
# empty typed frame today — exactly the DW-D2-2 lifecycle the 3 shells above
# already proved out.
# ---------------------------------------------------------------------------


def load_cve_watcher(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`cve-watcher` — build_vuln_history_model."""
    return _bsl_query_or_empty(
        parquet,
        models.build_vuln_history_model,
        ["conda_name", "severity", "since_days", "vuln_kev_affecting_current"],
        ["then_count", "now_count", "delta"],
    )


def load_version_downloads(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`version-downloads` — build_version_downloads_model."""
    return _bsl_query_or_empty(
        parquet,
        models.build_version_downloads_model,
        ["conda_name", "version", "upload_date"],
        ["downloads"],
    )


def load_release_cadence(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`release-cadence` — build_release_cadence_model (metrics.release_trend_label)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_release_cadence_model,
        ["conda_name", "trend_label"],
        ["release_count_30d", "release_count_90d", "release_count_365d"],
    )


def load_find_alternative(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`find-alternative` — build_alternative_candidates_model."""
    return _bsl_query_or_empty(
        parquet,
        models.build_alternative_candidates_model,
        ["archived_name", "candidate_name", "adoption_stage"],
        ["similarity_score", "downloads_total"],
    )


def load_adoption_stage(parquet: str | os.PathLike[str] | None = None, *, now: int) -> pd.DataFrame:
    """`adoption-stage` — the dedicated portfolio-wide lifecycle VIEW; re-uses
    build_packages_model (no new model — the dimension already exists, AC-2 style
    reuse), over the SAME composed semantic_packages store `detail-cf-atlas` binds to."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "adoption_stage"],
        ["package_count"],
        model_kwargs={"now_unix": now},
    )


def load_scan_project(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`scan-project` — the LATEST per-invocation scan result (build_scan_result_model).

    The dashboard does not itself submit a NEW scan (no live subprocess invocation is
    wired from a Dash callback here) — it reads the latest cached result the same
    honest way every other shell page does. An absent Parquet renders the page's
    "no scan run yet, submit one from the CLI" state (EXPERIENCE.md § 1.6); wiring an
    actual in-dashboard submit control is forward-looking work (mirrors the
    add-handoff/library-futures "not implemented now" notes in DESIGN.md § 4.5/4.6).
    """
    return _bsl_query_or_empty(
        parquet,
        models.build_scan_result_model,
        ["conda_name", "severity", "license_spdx", "fix_available", "scan_status"],
        ["finding_count"],
    )


def load_env_inspect(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`env-inspect` — the LATEST per-invocation environment rollup (same per-invocation
    shape as `scan-project`; see its loader's docstring)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_env_inspect_model,
        ["conda_name", "license_spdx", "non_permissive_flag"],
        ["vuln_critical", "vuln_high"],
    )


def load_distribution_breakdown(
    parquet: str | os.PathLike[str] | None = None,
) -> pd.DataFrame:
    """`distribution-breakdown` — build_distribution_breakdown_model (merges
    platform-breakdown / pyver-breakdown / channel-split behind one `facet` column;
    metrics.python_min_bump_status rides along for the python-version facet)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_distribution_breakdown_model,
        ["conda_name", "facet", "bucket", "python_min_bump_status"],
        ["downloads_90d"],
    )


def load_export_purls(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`export-purls` — build_purl_export_model (an artifact-freshness index)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_purl_export_model,
        ["artifact_name", "regenerated_at"],
        ["row_count"],
    )


def load_mapping_gap(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`mapping-gap` — build_mapping_gap_model, READ-ONLY (--write stays CLI-only)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_mapping_gap_model,
        ["conda_name", "classification", "match_source", "match_confidence"],
        ["gap_count"],
    )


def load_universe_sbom(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`universe-sbom` — build_universe_sbom_summary_model (summary-first, never a
    full ~856k-row render)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_universe_sbom_summary_model,
        ["component_purl", "slice"],
        ["with_vulns_count"],
    )


def load_inventory_match(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`inventory-match` (FR-9 exception) — the LATEST cached match report, never a
    live re-match (build_inventory_match_report_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_inventory_match_report_model,
        ["conda_name", "bucket", "freshness_percentile", "match_confidence"],
        ["row_count"],
    )


def load_add_handoff(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`add-handoff` (FR-9 exception) — the LATEST ADD-bucket worklist, READ-ONLY
    (build_add_handoff_report_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_add_handoff_report_model,
        ["conda_name", "readiness", "license_blocker"],
        ["row_count"],
    )


def load_library_futures(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`library-futures` (FR-9 exception) — the LATEST cached futures scorecard
    (build_library_futures_report_model; in-memory/inventory-scoped by design)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_library_futures_report_model,
        ["package_name", "futures_tier", "py314_readiness"],
        ["futures_score"],
    )


def load_recommend_2027(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`recommend-2027` — build_recommend_2027_model (the S5->S7 per-signal scorecard)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_recommend_2027_model,
        ["package_name", "futures_tier", "lts_status", "eol_date"],
        ["futures_score"],
    )


def load_lts_registry_gap(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`lts-registry-gap` — build_lts_registry_gap_model, READ-ONLY suggester."""
    return _bsl_query_or_empty(
        parquet,
        models.build_lts_registry_gap_model,
        ["product_name", "tier", "matched_conda_name"],
        ["candidate_count"],
    )


def load_cwe_seed_gap(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`cwe-seed-gap` — build_cwe_seed_gap_model, READ-ONLY suggester."""
    return _bsl_query_or_empty(
        parquet,
        models.build_cwe_seed_gap_model,
        ["cwe_id", "tier", "suggested_category"],
        ["package_impact_count"],
    )


def load_spdx_schema_gap(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`spdx-schema-gap` — build_spdx_schema_gap_model, READ-ONLY suggester."""
    return _bsl_query_or_empty(
        parquet,
        models.build_spdx_schema_gap_model,
        ["license_id", "tier"],
        ["package_usage_count"],
    )


def load_license_map_gap(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`license-map-gap` — build_license_map_gap_model, READ-ONLY suggester."""
    return _bsl_query_or_empty(
        parquet,
        models.build_license_map_gap_model,
        ["license_raw", "tier", "suggested_spdx"],
        ["package_count"],
    )


def load_bootstrap_index_health(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`bootstrap-index-health` — Tier 0/1 catalog index row counts (Story 21.9)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_bootstrap_index_health_model,
        ["catalog_entry", "tier", "regenerated_at"],
        ["row_count"],
    )


def load_identity_export_snapshot(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-export-snapshot` — identity join quality over identity_export_parquet."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_export_snapshot_model,
        ["identity_source"],
        ["package_count", "primary_purl_coverage_count", "openteams_issue_url_coverage_count"],
    )


def load_live_catalog_coverage(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`live-catalog-coverage` — verification-matrix BOOL coverage summary (Story 21.9)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_live_catalog_coverage_model,
        ["field_name"],
        ["true_count", "total_count"],
    )


def load_identity_catalog(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-catalog` — build_identity_catalog_model over identity_complete_export."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_catalog_model,
        [
            "P",
            "Rank",
            "Score",
            "Package",
            "Work",
            "Core_Python_Package_Name",
            "Platforms",
            "Apps",
            "Downloads",
            "Versions",
            "Vuln",
        ],
    )


def load_identity_ops_priority(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-ops` Priority pane — P × Work counts."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_ops_model,
        ["P", "Work"],
        ["package_count"],
    )


def load_identity_ops_issues(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-ops` Issues pane — P × has-issue have/miss counts."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_ops_model,
        ["P", "has_open_issue"],
        ["package_count"],
    )


def load_identity_ops_builds(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-ops` Builds pane — Local_Build_Status totals (no recipe-type breakdown)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_ops_model,
        ["Local_Build_Status"],
        ["package_count"],
    )


def load_identity_ops_census(parquet: str | os.PathLike[str] | None = None) -> pd.DataFrame:
    """`identity-ops` Census pane — feedstock / staged-PR / local-recipe presence."""
    return _bsl_query_or_empty(
        parquet,
        models.build_identity_ops_model,
        ["has_feedstock", "has_staged_pr", "has_local_recipe"],
        ["package_count"],
    )


def _ibis_pep503(col: Any) -> Any:
    """PEP-503 join key — mirrors ``pep503_name`` in the identity scripts."""
    s = col.fill_null("").lower()
    s = s.re_replace(r"[_.]+", "-")
    return s.re_replace(r"^-+|-+$", "")


def identity_workbook_gap_message(
    complete_parquet: str | os.PathLike[str] | None,
    enterprise_parquet: str | os.PathLike[str] | None,
) -> str | None:
    """Human-readable gap note naming WHICH backing Parquet is absent (Story 22.4)."""
    complete_path = Path(complete_parquet) if complete_parquet is not None else None
    enterprise_path = Path(enterprise_parquet) if enterprise_parquet is not None else None
    complete_ok = complete_path is not None and complete_path.is_file()
    enterprise_ok = enterprise_path is not None and enterprise_path.is_file()
    if complete_ok and enterprise_ok:
        return None
    if not complete_ok and not enterprise_ok:
        return (
            f"Both backing files are missing: `{IDENTITY_COMPLETE_EXPORT_PARQUET}` and "
            f"`{ENTERPRISE_JFROG_CONSUMPTION_PARQUET}`."
        )
    if not enterprise_ok:
        return (
            f"Enterprise JFROG overlay missing: `{ENTERPRISE_JFROG_CONSUMPTION_PARQUET}` "
            "(Story 23.2 — page renders empty until this lands)."
        )
    return f"Complete identity export missing: `{IDENTITY_COMPLETE_EXPORT_PARQUET}` (Story 23.5)."


def load_identity_workbook(
    complete_parquet: str | os.PathLike[str] | None = None,
    enterprise_parquet: str | os.PathLike[str] | None = None,
) -> pd.DataFrame:
    """`identity-workbook` — JFROG consumption ⋈ complete identity verification buckets."""
    columns = [*_IDENTITY_WORKBOOK_DIMENSIONS, *_IDENTITY_WORKBOOK_MEASURES]
    complete_path = str(complete_parquet) if complete_parquet is not None else None
    enterprise_path = str(enterprise_parquet) if enterprise_parquet is not None else None
    if (
        complete_path is None
        or enterprise_path is None
        or not os.path.exists(complete_path)
        or not os.path.exists(enterprise_path)
    ):
        return pd.DataFrame(columns=columns)

    import ibis

    con = ibis.duckdb.connect()
    complete = models.duckdb_table_from_parquet(complete_path, connection=con)
    enterprise = models.duckdb_table_from_parquet(enterprise_path, connection=con)

    if "repository_source" in enterprise.columns:
        enterprise = enterprise.filter(enterprise.repository_source == "CDO-ENT-JFROG")

    join_key = _ibis_pep503
    ent = enterprise.mutate(_join_key=join_key(enterprise.core_python_package_name))
    ent = ent.filter(ent._join_key.length() >= 2).distinct(on=["_join_key"], keep="first")
    complete_side = complete.mutate(_join_key=join_key(complete.Core_Python_Package_Name)).distinct(
        on=["_join_key"], keep="last"
    )
    feedstock_col = "Conda-Forge_FeedStock_URL"
    complete_pick = complete_side.select(
        "_join_key",
        "primary_type",
        "primary_purl",
        "conda_purl",
        **{feedstock_col: complete_side[feedstock_col]},
    )
    joined = ent.left_join(complete_pick, "_join_key")
    try:
        from pyforge.atlas.semantic.query_helpers import bsl_query

        return bsl_query(
            models.build_identity_workbook_model(joined),
            dimensions=_IDENTITY_WORKBOOK_DIMENSIONS,
            measures=_IDENTITY_WORKBOOK_MEASURES,
        )
    except TypeError:
        return pd.DataFrame(columns=columns)
