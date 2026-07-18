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
            "conda_name": Dimension(expr=lambda t: t.conda_name, is_entity=True),
            "is_actionable": Dimension(expr=metrics.is_actionable),
            "staleness_age_days": Dimension(
                expr=lambda t: metrics.staleness_age_days(t, now)
            ),
            "adoption_stage": Dimension(expr=metrics.adoption_stage),
        },
        measures={
            "package_count": Measure(expr=lambda t: t.conda_name.count()),
            # count of matching rows → 0 (not NULL) over an empty table: sum(CASE…) is
            # NULL on 0 rows, so fill_null(0) restores the legacy count-of-matches semantics.
            "actionable_count": Measure(
                expr=lambda t: metrics.is_actionable(t).ifelse(1, 0).sum().fill_null(0)
            ),
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
            "feedstock_name": Dimension(expr=lambda t: t.feedstock_name, is_entity=True),
            "ci_red": Dimension(expr=metrics.ci_red),
            "has_open_prs": Dimension(expr=metrics.has_open_prs),
            "has_open_issues": Dimension(expr=metrics.has_open_issues),
        },
        measures={
            "feedstock_count": Measure(expr=lambda t: t.feedstock_name.count()),
            # count of matching rows → 0 (not NULL) over an empty table (see packages).
            "ci_red_count": Measure(
                expr=lambda t: metrics.ci_red(t).ifelse(1, 0).sum().fill_null(0)
            ),
            "open_prs_count": Measure(
                expr=lambda t: metrics.has_open_prs(t).ifelse(1, 0).sum().fill_null(0)
            ),
            "open_issues_count": Measure(
                expr=lambda t: metrics.has_open_issues(t).ifelse(1, 0).sum().fill_null(0)
            ),
        },
    )


# ---------------------------------------------------------------------------
# maintainer ⋈ — first-class maintainer dimension (AC-2)
# ---------------------------------------------------------------------------


def build_package_maintainers_model(table: Any) -> SemanticModel:
    """The maintainer ⋈ long form (``vcs_package_maintainers``: conda_name, maintainer).

    ``maintainer`` is a FIRST-CLASS declared dimension (AC-2) — the anchor that turns
    the raw-SQL ``package_maintainers`` JOINs into declared BSL queries.
    """
    return SemanticModel(
        table=table,
        name="package_maintainers",
        dimensions={
            "conda_name": Dimension(expr=lambda t: t.conda_name, is_entity=True),
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
            "maintainer": Dimension(expr=lambda t: t.maintainer, is_entity=True),
        },
        measures={"maintainer_count": Measure(expr=lambda t: t.maintainer.nunique())},
    )


def join_packages_by_maintainer(
    packages: SemanticModel, package_maintainers: SemanticModel
) -> Any:
    """Declare the packages ⋈ maintainer relationship as a BSL semantic join.

    Returns the join whose dimensions include ``maintainer`` and whose measures include
    the packages metrics (namespaced ``packages.*``) — so a maintainer-scoped query
    (``staleness-report --maintainer X``) is ``join.query(dimensions=["maintainer"],
    measures=["packages.downloads_total"], filters=[...])`` instead of raw SQL (AD-8).

    ``join_many``: one maintainer maintains many packages / one package has many
    maintainers — the long-form ``package_maintainers`` is the many side keyed on
    ``conda_name``.
    """
    return package_maintainers.join_many(packages, on="conda_name")
