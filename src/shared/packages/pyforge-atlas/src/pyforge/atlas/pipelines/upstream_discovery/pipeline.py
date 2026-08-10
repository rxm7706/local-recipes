"""``upstream_discovery`` pipeline wiring (Story 13.1, CAP-1).

One PURE trigger node: ``inputs=`` binds to ``params:ttls`` (the daily discovery
cadence); ``outputs=`` is the ``trending_candidates`` catalog entry
(``TrendingSnapshotDataset``), the SINGLE writer (AD-3/AD-10).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import refresh_trending_candidates


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=refresh_trending_candidates,
                inputs="params:ttls",
                outputs="trending_candidates",
                name="refresh_trending_candidates",
            ),
        ]
    )
