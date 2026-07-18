"""Boring Semantic Layer (BSL) for the migrated atlas catalog (Story D1, FR-8).

The single semantic translation interface (AD-8) over the canonical Parquet store:
the metric / business logic of the 28 read CLIs declared ONCE as Ibis → DuckDB (AD-4)
dimensions + measures. Downstream read surfaces (D2 pages, D3 MCP reads, agents) import
these models and query them; they never re-write raw SQL.

D1 lands the CORE metric set (staleness, adoption stage, feedstock health, downloads /
actionable) + the maintainer ⋈ as a first-class dimension + the ``bsl-metric-check``
parity gate. The full 28-CLI metric surface is completed as D2 ports the pages.
"""

from __future__ import annotations

from .metrics import (
    DEFERRED_FEEDSTOCK_HEALTH_FILTERS,
    METRIC_PROVENANCE,
    adoption_stage,
    ci_red,
    has_open_issues,
    has_open_prs,
    is_actionable,
    staleness_age_days,
)
from .models import (
    build_feedstock_health_model,
    build_maintainers_model,
    build_package_maintainers_model,
    build_packages_model,
    duckdb_table_from_parquet,
    join_packages_by_maintainer,
)

__all__ = [
    "DEFERRED_FEEDSTOCK_HEALTH_FILTERS",
    "METRIC_PROVENANCE",
    "adoption_stage",
    "build_feedstock_health_model",
    "build_maintainers_model",
    "build_package_maintainers_model",
    "build_packages_model",
    "ci_red",
    "duckdb_table_from_parquet",
    "has_open_issues",
    "has_open_prs",
    "is_actionable",
    "join_packages_by_maintainer",
    "staleness_age_days",
]
