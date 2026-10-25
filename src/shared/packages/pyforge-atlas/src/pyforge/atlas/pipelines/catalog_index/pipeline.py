"""``catalog_index`` pipeline wiring (Story 37.10, CAP-69): one node over the read-only catalog index."""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import report_catalog_index_health


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=report_catalog_index_health,
                inputs=["catalog_index_raw", "params:catalog_index_health"],
                outputs="catalog_index_health",
                name="report_catalog_index_health",
            ),
        ]
    )
