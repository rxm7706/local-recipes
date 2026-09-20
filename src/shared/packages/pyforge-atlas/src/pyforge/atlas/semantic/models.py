"""Boring Semantic Layer models over the migrated atlas catalog (Story D1, AD-8).

These ``SemanticModel`` builders are the SINGLE translation interface (AD-8):
downstream read surfaces (D2 pages, D3 MCP reads, agents) query THESE models, never
raw SQL. Each model binds the pure Ibis metric expressions from ``metrics.py`` to an
Ibis table read — via DuckDB (AD-4) — from the migrated canonical Parquet store.

Builders take an already-constructed Ibis table so model DEFINITION (the D1 metric
semantics) is decoupled from data LOCATION (D2 wires the catalog Parquet paths, the
gate wires small fixtures). ``duckdb_table_from_parquet`` is the query-time seam that
reads a Parquet file as an Ibis/DuckDB table with NO network — mirroring how the 5
legacy SQL views are query-time constructs (spec § 3.3, not catalog datasets).

The **maintainer ⋈ is a first-class BSL dimension** (AC-2): ``package_maintainers``
declares ``maintainer`` as a queryable dimension over ``vcs_package_maintainers``, and
``join_packages_by_maintainer`` declares the packages ⋈ maintainer relationship as a
BSL semantic join — so ``staleness-report --maintainer X`` / ``feedstock-health
--maintainer X`` become DECLARED BSL queries (filter/group-by on the ``maintainer``
dimension) instead of the hand-written SQL JOINs consumers write today.
"""

from __future__ import annotations

import time
from typing import Any

import ibis
from boring_semantic_layer import Dimension, Measure, SemanticModel

from . import metrics


def duckdb_table_from_parquet(path: str, *, connection: Any | None = None) -> Any:
    """Read a Parquet file as an Ibis DuckDB table (AD-4, offline, query-time seam).

    The D2 wiring point: pass a catalog Parquet ``filepath`` and get the Ibis table a
    model binds to. No network — DuckDB reads local Parquet directly.
    """
    con = connection if connection is not None else ibis.duckdb.connect()
    return con.read_parquet(path)


# ---------------------------------------------------------------------------
# packages — per-package metric surface (staleness / adoption / actionable / downloads)
# ---------------------------------------------------------------------------


def build_packages_model(table: Any, *, now_unix: int | None = None) -> SemanticModel:
    """Per-package (grain: ``conda_name``) semantic model.

    Declares the core per-package metrics: ``is_actionable``, ``staleness_age_days``,
    ``adoption_stage`` (dimensions) and ``downloads_total`` / ``downloads_30d``
    (measures). ``now_unix`` is injected for deterministic staleness (defaults to wall
    clock for live use; the gate pins it).

    Expected input columns: ``conda_name``, ``latest_status``, ``feedstock_archived``,
    ``latest_conda_upload``, ``downloads_total``, ``downloads_30d``,
    ``latest_upload_age_days``, ``releases_30d``, ``total_versions``. Columns whose
    legacy source is not yet in the migrated store (``latest_conda_upload`` and the
    per-version fields) are ``deferred-input-not-in-migrated-store`` in
    ``metrics.METRIC_PROVENANCE`` — the FORMULA lands in D1, the live column in D2.
    """
    now = int(time.time()) if now_unix is None else now_unix
    return SemanticModel(
        table=table,
        name="packages",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "is_actionable": Dimension(expr=metrics.is_actionable),
            "staleness_age_days": Dimension(expr=lambda t: metrics.staleness_age_days(t, now)),
            "adoption_stage": Dimension(expr=metrics.adoption_stage),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.conda_name.count()),
            # count of matching rows → 0 (not NULL) over an empty table: sum(CASE…) is
            # NULL on 0 rows, so fill_null(0) restores the legacy count-of-matches semantics.
            "actionable_count": Measure(expr=lambda t: metrics.is_actionable(t).ifelse(1, 0).sum().fill_null(0)),
            "downloads_total": Measure(expr=lambda t: t.downloads_total.sum()),
            "downloads_30d": Measure(expr=lambda t: t.downloads_30d.sum()),
        },
    )


# ---------------------------------------------------------------------------
# feedstock_health — per-feedstock health (core_feedstock_health)
# ---------------------------------------------------------------------------


def build_feedstock_health_model(table: Any) -> SemanticModel:
    """Per-feedstock (grain: ``feedstock_name``) health semantic model.

    Declares the feedstock-health filters expressible over the migrated
    ``core_feedstock_health`` shape (``feedstock_name``, ``ci_status``, ``open_prs``,
    ``open_issues``): ``ci_red`` / ``has_open_prs`` / ``has_open_issues`` dimensions and
    their counts. The legacy ``stuck`` / ``bad`` filters need Phase M columns absent
    from the migrated shape — deliberately NOT declared, documented in
    ``metrics.DEFERRED_FEEDSTOCK_HEALTH_FILTERS`` (no fabricated legacy signal).
    """
    return SemanticModel(
        table=table,
        name="feedstock_health",
        dimensions={
            "feedstock_name": Dimension(expr=lambda t: t.feedstock_name),
            "ci_red": Dimension(expr=metrics.ci_red),
            "has_open_prs": Dimension(expr=metrics.has_open_prs),
            "has_open_issues": Dimension(expr=metrics.has_open_issues),
        },
        measures={
            "feedstock_count": Measure(expr=lambda t: t.feedstock_name.count()),
            # count of matching rows → 0 (not NULL) over an empty table (see packages).
            "ci_red_count": Measure(expr=lambda t: metrics.ci_red(t).ifelse(1, 0).sum().fill_null(0)),
            "open_prs_count": Measure(expr=lambda t: metrics.has_open_prs(t).ifelse(1, 0).sum().fill_null(0)),
            "open_issues_count": Measure(expr=lambda t: metrics.has_open_issues(t).ifelse(1, 0).sum().fill_null(0)),
        },
    )


# ---------------------------------------------------------------------------
# maintainer ⋈ — first-class maintainer dimension (AC-2)
# ---------------------------------------------------------------------------


def build_package_maintainers_model(table: Any) -> SemanticModel:
    """The maintainer ⋈ long form (``vcs_package_maintainers``: conda_name, maintainer).

    ``maintainer`` is a FIRST-CLASS declared dimension (AC-2) — the anchor that turns
    the raw-SQL ``package_maintainers`` JOINs into declared BSL queries.

    Duplicate ``(conda_name, maintainer)`` rows in the upstream long form are collapsed
    before any join so maintainer-scoped download sums cannot double-count a package.
    """
    return SemanticModel(
        table=table.distinct(),
        name="package_maintainers",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "maintainer": Dimension(expr=lambda t: t.maintainer),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.conda_name.nunique()),
            "maintainer_count": Measure(expr=lambda t: t.maintainer.nunique()),
        },
    )


def build_maintainers_model(table: Any) -> SemanticModel:
    """The unique maintainer universe (``vcs_maintainers``: maintainer)."""
    return SemanticModel(
        table=table,
        name="maintainers",
        dimensions={
            "maintainer": Dimension(expr=lambda t: t.maintainer),
        },
        measures={"maintainer_count": Measure(expr=lambda t: t.maintainer.nunique())},
    )


def build_estate_cache_model(table: Any) -> SemanticModel:
    """CAP-19 estate cache (``query_plane_estate``) — Lane 3 over FR-47 Parquet."""
    return SemanticModel(
        table=table,
        name="estate_cache",
        dimensions={
            "sku": Dimension(expr=lambda t: t.sku),
        },
        measures={
            "units_total": Measure(expr=lambda t: t.units.sum()),
            "sku_count": Measure(expr=lambda t: t.sku.count()),
        },
    )


def join_packages_by_maintainer(packages: SemanticModel, package_maintainers: SemanticModel) -> Any:
    """Declare the packages ⋈ maintainer relationship as a BSL semantic join.

    Returns the join whose dimensions include ``maintainer`` and whose measures include
    the packages metrics (namespaced ``packages.*``) — so a maintainer-scoped query
    (``staleness-report --maintainer X``) is ``join.query(dimensions=["maintainer"],
    measures=["packages.downloads_total"], filters=[...])`` instead of raw SQL (AD-8).

    ``join_many``: one maintainer maintains many packages / one package has many
    maintainers — the long-form ``package_maintainers`` is the many side keyed on
    ``conda_name``.
    """
    return package_maintainers.join_many(packages, left_on="conda_name", right_on="conda_name")


# ===========================================================================
# Story 20.5 (CAP-7) — BSL models for the remaining 19 Vizro pages, per the
# CIS two-spine `DESIGN.md` § 3-5. Each model is declared exactly like the
# ones above: an Ibis table read via `duckdb_table_from_parquet` binds to
# dimensions/measures the page's loader (`dashboard/data.py`) queries through
# `_bsl_query_or_empty`. None of these source datasets are migrated yet (the
# named Kedro pipeline that materializes each is future work, exactly the
# DW-D2-2 lifecycle the 3 original bsl-shell pages went through) — the model
# declares the shape today; the honest-empty seam degrades to zero rows until
# the pipeline lands.
# ===========================================================================

# ---------------------------------------------------------------------------
# cve-watcher — vuln_history (DESIGN.md § 3.1)
# ---------------------------------------------------------------------------


def build_vuln_history_model(table: Any) -> SemanticModel:
    """`cve-watcher` — per-(package,severity) CVE-count delta over a since-days window."""
    return SemanticModel(
        table=table,
        name="vuln_history",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "severity": Dimension(expr=lambda t: t.severity),
            "since_days": Dimension(expr=lambda t: t.since_days),
            "vuln_kev_affecting_current": Dimension(expr=lambda t: t.vuln_kev_affecting_current),
        },
        measures={
            "then_count": Measure(expr=lambda t: t.then_count.sum()),
            "now_count": Measure(expr=lambda t: t.now_count.sum()),
            "delta": Measure(expr=lambda t: (t.now_count - t.then_count).sum()),
        },
    )


# ---------------------------------------------------------------------------
# version-downloads — per-version download history (DESIGN.md § 3.2)
# ---------------------------------------------------------------------------


def build_version_downloads_model(table: Any) -> SemanticModel:
    """`version-downloads` — per-version adoption curve."""
    return SemanticModel(
        table=table,
        name="version_downloads",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "version": Dimension(expr=lambda t: t.version),
            "upload_date": Dimension(expr=lambda t: t.upload_date),
        },
        measures={
            "downloads": Measure(expr=lambda t: t.downloads.sum()),
        },
    )


# ---------------------------------------------------------------------------
# release-cadence — rolling-window release counts (DESIGN.md § 3.3)
# ---------------------------------------------------------------------------


def build_release_cadence_model(table: Any) -> SemanticModel:
    """`release-cadence` — the honest label (metrics.release_trend_label) plus the
    3 rolling-window release counts it's derived from."""
    return SemanticModel(
        table=table,
        name="release_cadence",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "trend_label": Dimension(expr=metrics.release_trend_label),
        },
        measures={
            "release_count_30d": Measure(expr=lambda t: t.releases_30d.sum()),
            "release_count_90d": Measure(expr=lambda t: t.releases_90d.sum()),
            "release_count_365d": Measure(expr=lambda t: t.releases_365d.sum()),
        },
    )


# ---------------------------------------------------------------------------
# find-alternative — archived -> candidate similarity ranking (DESIGN.md § 3.4)
# ---------------------------------------------------------------------------


def build_alternative_candidates_model(table: Any) -> SemanticModel:
    """`find-alternative` — ranked replacement candidates for an archived package.

    ``similarity_score`` is a pre-computed composite (keyword/summary/dependent/
    maintainer-overlap Jaccard x recency x downloads — ``find_alternative.py``'s own
    in-memory scorer) — a Phase-E/J pipeline output column, not a BSL-derived formula
    (mirrors ``downloads_total`` being a pre-aggregated measure, not re-summed logic).
    """
    return SemanticModel(
        table=table,
        name="alternative_candidates",
        dimensions={
            "archived_name": Dimension(expr=lambda t: t.archived_name),
            "candidate_name": Dimension(expr=lambda t: t.candidate_name),
            "adoption_stage": Dimension(expr=lambda t: t.adoption_stage),
        },
        measures={
            "similarity_score": Measure(expr=lambda t: t.similarity_score.mean()),
            "downloads_total": Measure(expr=lambda t: t.downloads_total.sum()),
        },
    )


# ---------------------------------------------------------------------------
# scan-project / env-inspect — per-invocation report models (DESIGN.md § 3.6-3.7)
# ---------------------------------------------------------------------------


def build_scan_result_model(table: Any) -> SemanticModel:
    """`scan-project` — the LATEST per-invocation manifest/lock/SBOM scan result."""
    return SemanticModel(
        table=table,
        name="scan_result",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "severity": Dimension(expr=lambda t: t.severity),
            "license_spdx": Dimension(expr=lambda t: t.license_spdx),
            "fix_available": Dimension(expr=lambda t: t.fix_available),
            "scan_status": Dimension(expr=lambda t: t.scan_status),
        },
        measures={
            "finding_count": Measure(expr=lambda t: t.conda_name.count()),
        },
    )


def build_env_inspect_model(table: Any) -> SemanticModel:
    """`env-inspect` — the LATEST per-invocation live-environment rollup."""
    return SemanticModel(
        table=table,
        name="env_inspect",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "license_spdx": Dimension(expr=lambda t: t.license_spdx),
            "non_permissive_flag": Dimension(expr=lambda t: t.non_permissive_flag),
        },
        measures={
            "vuln_critical": Measure(expr=lambda t: t.vuln_critical.sum()),
            "vuln_high": Measure(expr=lambda t: t.vuln_high.sum()),
        },
    )


# ---------------------------------------------------------------------------
# distribution-breakdown — merged platform/pyver/channel facet (DESIGN.md § 3.8)
# ---------------------------------------------------------------------------


def build_distribution_breakdown_model(table: Any) -> SemanticModel:
    """`distribution-breakdown` — merges `platform-breakdown` / `pyver-breakdown` /
    `channel-split` behind one `facet` dimension; the python-version facet's
    `--policy-check` bump-safety classifier (metrics.python_min_bump_status) rides
    along as a 4th dimension, populated only on rows where the facet is
    `python-version` (NULL declared/empirical inputs elsewhere resolve to "unknown",
    never fabricated)."""
    return SemanticModel(
        table=table,
        name="distribution_breakdown",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "facet": Dimension(expr=lambda t: t.facet),
            "bucket": Dimension(expr=lambda t: t.bucket),
            "python_min_bump_status": Dimension(expr=metrics.python_min_bump_status),
        },
        measures={
            "downloads_90d": Measure(expr=lambda t: t.downloads_90d.sum()),
        },
    )


# ---------------------------------------------------------------------------
# Cyclonedx-suite pages (DESIGN.md § 4)
# ---------------------------------------------------------------------------


def build_purl_export_model(table: Any) -> SemanticModel:
    """`export-purls` — the artifact-freshness index (one row per output artifact)."""
    return SemanticModel(
        table=table,
        name="purl_export",
        dimensions={
            "artifact_name": Dimension(expr=lambda t: t.artifact_name),
            "regenerated_at": Dimension(expr=lambda t: t.regenerated_at),
        },
        measures={
            "row_count": Measure(expr=lambda t: t.row_count.sum()),
        },
    )


def build_mapping_gap_model(table: Any) -> SemanticModel:
    """`mapping-gap` — conda<->PyPI mapping classification gap, READ-ONLY."""
    return SemanticModel(
        table=table,
        name="mapping_gap",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "classification": Dimension(expr=lambda t: t.classification),
            "match_source": Dimension(expr=lambda t: t.match_source),
            "match_confidence": Dimension(expr=lambda t: t.match_confidence),
        },
        measures={
            "gap_count": Measure(expr=lambda t: t.conda_name.count()),
        },
    )


def build_universe_sbom_summary_model(table: Any) -> SemanticModel:
    """`universe-sbom` — universe-scale BOM SUMMARY (never a full ~856k-row browse)."""
    return SemanticModel(
        table=table,
        name="universe_sbom_summary",
        dimensions={
            "component_purl": Dimension(expr=lambda t: t.component_purl),
            "slice": Dimension(expr=lambda t: t.slice),
        },
        measures={
            "with_vulns_count": Measure(expr=lambda t: t.with_vulns_count.sum()),
        },
    )


def build_inventory_match_report_model(table: Any) -> SemanticModel:
    """`inventory-match` (FR-9 exception) — the LATEST per-invocation match report,
    never a live re-match."""
    return SemanticModel(
        table=table,
        name="inventory_match_report",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "bucket": Dimension(expr=lambda t: t.bucket),
            "freshness_percentile": Dimension(expr=lambda t: t.freshness_percentile),
            "match_confidence": Dimension(expr=lambda t: t.match_confidence),
        },
        measures={
            "row_count": Measure(expr=lambda t: t.conda_name.count()),
        },
    )


def build_add_handoff_report_model(table: Any) -> SemanticModel:
    """`add-handoff` (FR-9 exception) — the LATEST ADD-bucket worklist, READ-ONLY."""
    return SemanticModel(
        table=table,
        name="add_handoff_report",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name),
            "readiness": Dimension(expr=lambda t: t.readiness),
            "license_blocker": Dimension(expr=lambda t: t.license_blocker),
        },
        measures={
            "row_count": Measure(expr=lambda t: t.conda_name.count()),
        },
    )


def build_library_futures_report_model(table: Any) -> SemanticModel:
    """`library-futures` (FR-9 exception) — the LATEST cached futures scorecard
    (in-memory/inventory-scoped by design — no live catalog column)."""
    return SemanticModel(
        table=table,
        name="library_futures_report",
        dimensions={
            "package_name": Dimension(expr=lambda t: t.package_name),
            "futures_tier": Dimension(expr=lambda t: t.futures_tier),
            "py314_readiness": Dimension(expr=lambda t: t.py314_readiness),
        },
        measures={
            "futures_score": Measure(expr=lambda t: t.futures_score.mean()),
        },
    )


def build_recommend_2027_model(table: Any) -> SemanticModel:
    """`recommend-2027` — the S5->S7 per-signal scorecard."""
    return SemanticModel(
        table=table,
        name="recommend_2027",
        dimensions={
            "package_name": Dimension(expr=lambda t: t.package_name),
            "futures_tier": Dimension(expr=lambda t: t.futures_tier),
            "lts_status": Dimension(expr=lambda t: t.lts_status),
            "eol_date": Dimension(expr=lambda t: t.eol_date),
        },
        measures={
            "futures_score": Measure(expr=lambda t: t.futures_score.mean()),
        },
    )


# ---------------------------------------------------------------------------
# Seed-gap-suggester pages (DESIGN.md § 5) — all four READ-ONLY proposal lists
# against a hand-curated source-of-truth file; the dashboard never writes it.
# ---------------------------------------------------------------------------


def build_lts_registry_gap_model(table: Any) -> SemanticModel:
    """`lts-registry-gap` — endoflife.date products not yet in `lts-registry.yaml`."""
    return SemanticModel(
        table=table,
        name="lts_registry_gap",
        dimensions={
            "product_name": Dimension(expr=lambda t: t.product_name),
            "tier": Dimension(expr=lambda t: t.tier),
            "matched_conda_name": Dimension(expr=lambda t: t.matched_conda_name),
        },
        measures={
            "candidate_count": Measure(expr=lambda t: t.product_name.count()),
        },
    )


def build_cwe_seed_gap_model(table: Any) -> SemanticModel:
    """`cwe-seed-gap` — `Other`-bucketed CWEs ranked by real package impact."""
    return SemanticModel(
        table=table,
        name="cwe_seed_gap",
        dimensions={
            "cwe_id": Dimension(expr=lambda t: t.cwe_id),
            "tier": Dimension(expr=lambda t: t.tier),
            "suggested_category": Dimension(expr=lambda t: t.suggested_category),
        },
        measures={
            "package_impact_count": Measure(expr=lambda t: t.package_impact_count.sum()),
        },
    )


def build_spdx_schema_gap_model(table: Any) -> SemanticModel:
    """`spdx-schema-gap` — vendored SPDX enum diffed against upstream SPDX."""
    return SemanticModel(
        table=table,
        name="spdx_schema_gap",
        dimensions={
            "license_id": Dimension(expr=lambda t: t.license_id),
            "tier": Dimension(expr=lambda t: t.tier),
        },
        measures={
            "package_usage_count": Measure(expr=lambda t: t.package_usage_count.sum()),
        },
    )


def build_identity_catalog_model(table: Any) -> SemanticModel:
    """`identity-catalog` — ranked OpenTeams universe (Story 22.1 bridge export)."""
    return SemanticModel(
        table=table,
        name="identity_catalog",
        dimensions={
            "P": Dimension(expr=lambda t: t.P),
            "Rank": Dimension(expr=lambda t: t.Rank),
            "Score": Dimension(expr=lambda t: t.Score),
            "Package": Dimension(expr=lambda t: t.Package),
            "Work": Dimension(expr=lambda t: t.Work),
            "Core_Python_Package_Name": Dimension(expr=lambda t: t.Core_Python_Package_Name),
            "Platforms": Dimension(expr=lambda t: t.Platforms),
            "Apps": Dimension(expr=lambda t: t.Apps),
            "Downloads": Dimension(expr=lambda t: t.Downloads),
            "Versions": Dimension(expr=lambda t: t.Versions),
            "Vuln": Dimension(expr=lambda t: t.Vuln),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.Core_Python_Package_Name.count()),
        },
    )


def build_identity_ops_model(table: Any) -> SemanticModel:
    """`identity-ops` — four-pane aggregates over identity_complete_export (Story 22.3/23.5)."""
    return SemanticModel(
        table=table,
        name="identity_ops",
        dimensions={
            "P": Dimension(expr=lambda t: t.P.fill_null("?")),
            "Work": Dimension(expr=lambda t: t.Work.fill_null("?")),
            "has_open_issue": Dimension(expr=metrics.has_open_teams_issue),
            "Local_Build_Status": Dimension(expr=metrics.identity_local_build_status),
            "has_feedstock": Dimension(expr=metrics.has_feedstock),
            "has_staged_pr": Dimension(expr=metrics.has_staged_pr),
            "has_local_recipe": Dimension(expr=metrics.has_local_recipe),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.Core_Python_Package_Name.count()),
        },
    )


def build_identity_workbook_model(table: Any) -> SemanticModel:
    """`identity-workbook` — JFROG consumption ⋈ ranked identity (Story 22.4)."""
    return SemanticModel(
        table=table,
        name="identity_workbook",
        dimensions={
            "match_bucket": Dimension(expr=metrics.verification_match_bucket),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.core_python_package_name.count()),
            "artifactory_downloads_total": Measure(expr=lambda t: t.artifactory_downloads.sum().fill_null(0)),
        },
    )


def build_license_map_gap_model(table: Any) -> SemanticModel:
    """`license-map-gap` — unmapped `pypi_intelligence.license_raw` strings ranked by
    package impact, with a HINT (non-authoritative) suggested SPDX candidate."""
    return SemanticModel(
        table=table,
        name="license_map_gap",
        dimensions={
            "license_raw": Dimension(expr=lambda t: t.license_raw),
            "tier": Dimension(expr=lambda t: t.tier),
            "suggested_spdx": Dimension(expr=lambda t: t.suggested_spdx),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.package_count.sum()),
        },
    )


# ---------------------------------------------------------------------------
# identity_complete_export — gist/dashboard aggregates (Story 23.6, CAP-8d)
# ---------------------------------------------------------------------------


def _identity_status(t: Any) -> Any:
    """Normalize blank ``Local_Build_Status`` to ``blank`` (legacy gist semantics)."""
    raw = t.Local_Build_Status.fill_null("")
    return (raw == "").ifelse("blank", raw)


def _identity_filled(t: Any, col: str) -> Any:
    return (t[col].fill_null("") != "").ifelse(1, 0).sum().fill_null(0)


def build_identity_complete_export_model(table: Any, *, gist_columns: tuple[str, ...] | None = None) -> SemanticModel:
    """Per-package identity complete export (Story 23.5 grain) for gist aggregates.

    Declares the dimensions/measures the identity gist renderer queries — every
    count/crosstab in ``identity_gist.render_identity_gist_markdown`` binds here
    instead of re-implementing ``Counter``/dict logic in ``scripts/``.
    """
    feedstock_col = "Conda-Forge_FeedStock_URL"
    measures: dict[str, Measure] = {
        "identity_row_count": Measure(expr=lambda t: t.Core_Python_Package_Name.count()),
        "has_issue_count": Measure(
            expr=lambda t: (t.OpenTeams_Issue_URL.fill_null("") != "").ifelse(1, 0).sum().fill_null(0)
        ),
        "feedstock_count": Measure(
            expr=lambda t: (t[feedstock_col].fill_null("") != "").ifelse(1, 0).sum().fill_null(0)
        ),
        "local_recipe_count": Measure(
            expr=lambda t: (t.Local_Recipes_URL.fill_null("") != "").ifelse(1, 0).sum().fill_null(0)
        ),
        "staged_pr_count": Measure(
            expr=lambda t: (t.Staged_Recipes_PR_URL.fill_null("") != "").ifelse(1, 0).sum().fill_null(0)
        ),
        "build_success_count": Measure(
            expr=lambda t: (_identity_status(t) == "success").ifelse(1, 0).sum().fill_null(0)
        ),
        "build_skipped_count": Measure(
            expr=lambda t: (
                _identity_status(t)
                .isin(["build-clean-test-blocked", "blocked-missing-ortools"])
                .ifelse(1, 0)
                .sum()
                .fill_null(0)
            )
        ),
        "build_failed_count": Measure(expr=lambda t: (_identity_status(t) == "failed").ifelse(1, 0).sum().fill_null(0)),
    }
    if gist_columns:
        for col in gist_columns:
            key = f"filled_{col.replace('-', '_').replace(' ', '_')}"
            measures[key] = Measure(expr=lambda t, c=col: _identity_filled(t, c))

    return SemanticModel(
        table=table,
        name="identity_complete_export",
        dimensions={
            "core_python_package_name": Dimension(expr=lambda t: t.Core_Python_Package_Name),
            "P": Dimension(expr=lambda t: t.P.fill_null("?")),
            "Work": Dimension(expr=lambda t: t.Work.fill_null("?")),
            "identity_source": Dimension(expr=lambda t: t.identity_source.fill_null("")),
            "Local_Build_Status": Dimension(expr=_identity_status),
            "has_openteams_issue": Dimension(
                expr=lambda t: (t.OpenTeams_Issue_URL.fill_null("") != "").ifelse("yes", "no")
            ),
            "has_feedstock": Dimension(expr=lambda t: (t[feedstock_col].fill_null("") != "").ifelse("yes", "no")),
            "has_local_recipe": Dimension(expr=lambda t: (t.Local_Recipes_URL.fill_null("") != "").ifelse("yes", "no")),
            "has_staged_pr": Dimension(
                expr=lambda t: (t.Staged_Recipes_PR_URL.fill_null("") != "").ifelse("yes", "no")
            ),
            "is_pypi": Dimension(
                expr=lambda t: (
                    (t.primary_type.fill_null("") == "pypi") | t.primary_purl.fill_null("").startswith("pkg:pypi/")
                ).ifelse("yes", "no")
            ),
            "is_cf": Dimension(
                expr=lambda t: ((t[feedstock_col].fill_null("") != "") | (t.conda_purl.fill_null("") != "")).ifelse(
                    "yes", "no"
                )
            ),
        },
        measures=measures,
    )


# ---------------------------------------------------------------------------
# Story 21.9 (CAP-5) — Epic 21 bootstrap verification operator pages
# ---------------------------------------------------------------------------


def build_bootstrap_index_health_model(table: Any) -> SemanticModel:
    """`bootstrap-index-health` — Tier 0/1 catalog index row counts (Story 21.9)."""
    return SemanticModel(
        table=table,
        name="bootstrap_index_health",
        dimensions={
            "catalog_entry": Dimension(expr=lambda t: t.catalog_entry),
            "tier": Dimension(expr=lambda t: t.tier),
            "regenerated_at": Dimension(expr=lambda t: t.regenerated_at),
        },
        measures={
            "row_count": Measure(expr=lambda t: t.row_count.sum()),
        },
    )


def build_identity_export_snapshot_model(table: Any) -> SemanticModel:
    """`identity-export-snapshot` — identity join quality over identity_export_parquet."""
    return SemanticModel(
        table=table,
        name="identity_export_snapshot",
        dimensions={
            "identity_source": Dimension(expr=lambda t: t.identity_source),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.Core_Python_Package_Name.count()),
            "primary_purl_coverage_count": Measure(expr=lambda t: _identity_filled(t, "primary_purl")),
            "openteams_issue_url_coverage_count": Measure(expr=lambda t: _identity_filled(t, "OpenTeams_Issue_URL")),
        },
    )


def build_live_catalog_coverage_model(table: Any) -> SemanticModel:
    """`live-catalog-coverage` — verification-matrix BOOL coverage summary (Story 21.9)."""
    return SemanticModel(
        table=table,
        name="live_catalog_coverage",
        dimensions={
            "field_name": Dimension(expr=lambda t: t.field_name),
        },
        measures={
            "true_count": Measure(expr=lambda t: t.true_count.sum()),
            "total_count": Measure(expr=lambda t: t.total_count.sum()),
        },
    )
