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
PACKAGE_MAINTAINERS_PARQUET = (
    "intermediate/vcs_package_maintainers/vcs_package_maintainers.parquet"
)

# BSL-WIRED SHELL — the composed per-package "packages" table that
# ``build_packages_model`` binds to (conda_name + latest_status + feedstock_archived +
# latest_conda_upload + downloads_* + per-version fields) is NOT one migrated Parquet: it
# is the join of core_packages_enumerated ⋈ core_latest_status ⋈ core_downloads ⋈ … that
# the migrated store does not yet materialize as a single table, and ``latest_conda_upload``
# / the per-version inputs are themselves ``deferred-input-not-in-migrated-store`` (D1
# ``metrics.METRIC_PROVENANCE``). Until that composed store lands, the packages-backed
# pages (staleness-report / query-atlas / detail-cf-atlas) are BSL-wired shells: the loader
# queries ``build_packages_model`` when a composed frame is supplied (proven by the gate's
# fixture), else returns an empty result. Recorded in DW-D2.
PACKAGES_PARQUET = "primary/semantic_packages/semantic_packages.parquet"


def default_data_root() -> Path:
    """The catalog ``data_root`` (env-overridable, mirrors globals.yml `paths.data_root`).

    Defaults to ``<repo>/data`` — the repo-root-relative default the catalog resolves
    against the process CWD (review-pass P9). ``PYFORGE_ATLAS_DATA_ROOT`` overrides it.
    """
    env = os.environ.get("PYFORGE_ATLAS_DATA_ROOT")
    if env:
        return Path(env)
    # data.py -> dashboard -> atlas -> pyforge -> src -> pyforge-atlas -> packages ->
    # shared -> src -> <repo root>
    return Path(__file__).resolve().parents[8] / "data"


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
        return model.query(dimensions=dimensions, measures=measures).execute()
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
# BSL-wired SHELL pages (packages composed store not yet materialized — DW-D2)
# ---------------------------------------------------------------------------


def load_staleness(
    parquet: str | os.PathLike[str] | None = None, *, now: int
) -> pd.DataFrame:
    """`staleness-report` — build_packages_model.staleness_age_days (+ adoption stage)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "staleness_age_days", "adoption_stage"],
        model_kwargs={"now_unix": now},
    )


def load_query_atlas(
    parquet: str | os.PathLike[str] | None = None, *, now: int
) -> pd.DataFrame:
    """`query-atlas` — the actionable-scope surface: is_actionable + adoption stage per
    package with the downloads measure (build_packages_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "is_actionable", "adoption_stage"],
        ["downloads_total"],
        model_kwargs={"now_unix": now},
    )


def load_detail(
    parquet: str | os.PathLike[str] | None = None, *, now: int
) -> pd.DataFrame:
    """`detail-cf-atlas` — the full per-package metric row (build_packages_model)."""
    return _bsl_query_or_empty(
        parquet,
        models.build_packages_model,
        ["conda_name", "is_actionable", "adoption_stage", "staleness_age_days"],
        ["downloads_total", "downloads_30d"],
        model_kwargs={"now_unix": now},
    )
