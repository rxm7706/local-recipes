"""``query_plane_cache`` wiring (Story 34.2, FR-47)."""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import extract_estate_to_cache


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=extract_estate_to_cache,
                inputs="query_plane_estate_source",
                outputs="query_plane_estate",
                name="extract_estate_to_cache",
            ),
        ]
    )
