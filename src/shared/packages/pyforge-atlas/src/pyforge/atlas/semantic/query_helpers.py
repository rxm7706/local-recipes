"""BSL query helpers — dimension projection with installed boring_semantic_layer.

``SemanticModel.query(dimensions=[...])`` without ``measures`` is a no-op group_by in
current BSL: ``SemanticGroupByOp.to_ibis()`` returns the raw source table and computed
dimensions (``adoption_stage``, ``ci_red``, …) never materialize. Supplying any declared
count measure forces the aggregate path, which evaluates dimension expressions. When the
caller did not request measures, the injected count column is dropped before return.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd

_ROW_COUNT_FALLBACKS: tuple[str, ...] = (
    "package_count",
    "feedstock_count",
    "maintainer_count",
    "sku_count",
    "actionable_count",
    "ci_red_count",
    "open_prs_count",
    "open_issues_count",
)


def bsl_query(
    model: Any,
    *,
    dimensions: Sequence[str] | None = None,
    measures: Sequence[str] | None = None,
    filters: list | None = None,
    order_by: Sequence[tuple[str, str]] | None = None,
    limit: int | None = None,
    drop_injected_count: bool = True,
) -> pd.DataFrame:
    """Run a BSL ``query`` and return a pandas frame with computed dimensions projected."""
    dims = list(dimensions or [])
    meas = list(measures or [])
    injected: str | None = None

    if dims and not meas:
        available = model.get_measures()
        for name in _ROW_COUNT_FALLBACKS:
            if name in available:
                injected = name
                meas = [name]
                break
        if not meas and available:
            injected = next(iter(available))
            meas = [injected]

    result = model.query(
        dimensions=dims or None,
        measures=meas or None,
        filters=filters,
        order_by=order_by,
        limit=limit,
    ).execute()

    if drop_injected_count and injected and injected in result.columns and not measures:
        result = result.drop(columns=[injected])
    return result
