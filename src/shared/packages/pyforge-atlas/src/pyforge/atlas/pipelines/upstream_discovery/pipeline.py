"""``upstream_discovery`` pipeline wiring (Story 13.1 CAP-1 + Story 13.2 CAP-2 +
Story 13.4 CAP-4).

Four nodes:
- ``refresh_trending_candidates``: PURE trigger, ``inputs=`` binds to ``params:ttls``
  (the daily discovery cadence); ``outputs=`` is the ``trending_candidates`` catalog
  entry (``TrendingSnapshotDataset``), the SINGLE writer (AD-3/AD-10).
- ``classify_trending_candidates``: joins ``trending_candidates`` against
  ``pypi_universe`` / ``pypi_conda_mapping`` / ``pypi_intelligence_enriched`` and
  writes ``trending_candidates_classified`` (Story 13.2, FR-65 / CAP-2).
- ``load_org_audit_candidates``: PURE ``params:org_audit_candidates -> DataFrame``
  loader; ``outputs=`` is the ``org_audit_candidates`` catalog entry (Story 13.4,
  FR-67 / CAP-4).
- ``classify_org_audit_candidates``: the SAME ``classify_trending_candidates``
  function, bound via Kedro's positional ``inputs=[...]`` to ``org_audit_candidates``
  instead of ``trending_candidates`` — zero duplicated classification logic, writes
  ``org_audit_candidates_classified`` (Story 13.4, FR-67 / CAP-4).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    classify_trending_candidates,
    load_org_audit_candidates,
    refresh_trending_candidates,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=refresh_trending_candidates,
                inputs="params:ttls",
                outputs="trending_candidates",
                name="refresh_trending_candidates",
            ),
            node(
                func=classify_trending_candidates,
                inputs=[
                    "trending_candidates",
                    "pypi_universe",
                    "pypi_conda_mapping",
                    "pypi_intelligence_enriched",
                ],
                outputs="trending_candidates_classified",
                name="classify_trending_candidates",
            ),
            node(
                func=load_org_audit_candidates,
                inputs="params:org_audit_candidates",
                outputs="org_audit_candidates",
                name="load_org_audit_candidates",
            ),
            node(
                func=classify_trending_candidates,
                inputs=[
                    "org_audit_candidates",
                    "pypi_universe",
                    "pypi_conda_mapping",
                    "pypi_intelligence_enriched",
                ],
                outputs="org_audit_candidates_classified",
                name="classify_org_audit_candidates",
            ),
        ]
    )
