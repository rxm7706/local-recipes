"""``upstream_discovery`` pipeline wiring (Story 13.1 CAP-1 + Story 13.2 CAP-2 +
Story 13.4 CAP-4 + Story 21.4 Tier 1 catalog sources + Story 21.5 Tier 2 catalog
sources).

Nine nodes — the original four, Story 21.4's three Tier-1 external-refresh triggers,
and Story 21.5's two Tier-2 additions (``refresh_about_maintainers`` +
``join_enterprise_conda_maintainers``):
- ``refresh_trending_candidates``: PURE trigger, ``inputs=`` binds to ``params:ttls``
  (the daily discovery cadence); ``outputs=`` is the ``trending_candidates`` catalog
  entry (``TrendingSnapshotDataset``), the SINGLE writer (AD-3/AD-10).
- ``classify_trending_candidates``: joins ``trending_candidates`` against
  ``pypi_universe`` / ``pypi_conda_mapping`` / ``pypi_intelligence_enriched`` and
  writes ``trending_candidates_classified`` (Story 13.2, FR-65 / CAP-2).
- ``load_org_audit_candidates``: PURE ``(params:org_audit_candidates,
  discovery_curated_groups_seed) -> DataFrame`` loader (Story 21.5 added the second
  input); ``outputs=`` is the ``org_audit_candidates`` catalog entry (Story 13.4,
  FR-67 / CAP-4).
- ``classify_org_audit_candidates``: the SAME ``classify_trending_candidates``
  function, bound via Kedro's positional ``inputs=[...]`` to ``org_audit_candidates``
  instead of ``trending_candidates`` — zero duplicated classification logic, writes
  ``org_audit_candidates_classified`` (Story 13.4, FR-67 / CAP-4).
- ``refresh_about_maintainers``: PURE trigger (Story 21.5, Tier 2); ``outputs=`` is
  the ``discovery_about_maintainers_raw`` catalog entry (``AboutMaintainersDataset``),
  the SINGLE writer.
- ``join_enterprise_conda_maintainers``: joins ``discovery_about_maintainers_raw``
  against ``core_feedstock_attribution`` and writes ``enterprise_conda_maintainers``
  (Story 21.5, the CDO-ENT-CONDA enterprise-consumption universe).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    classify_trending_candidates,
    join_enterprise_conda_maintainers,
    load_org_audit_candidates,
    refresh_about_maintainers,
    refresh_anaconda_dist_2026x,
    refresh_aoss_premium_python,
    refresh_basilisk_packages,
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
                inputs=["params:org_audit_candidates", "discovery_curated_groups_seed"],
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
            # Story 21.4 — Tier 1 external-refresh triggers (single writers).
            node(
                func=refresh_anaconda_dist_2026x,
                inputs="params:ttls",
                outputs="discovery_anaconda_dist_2026x_raw",
                name="refresh_anaconda_dist_2026x",
            ),
            node(
                func=refresh_basilisk_packages,
                inputs="params:ttls",
                outputs="discovery_basilisk_packages_raw",
                name="refresh_basilisk_packages",
            ),
            node(
                func=refresh_aoss_premium_python,
                inputs="params:ttls",
                outputs="discovery_aoss_premium_python_raw",
                name="refresh_aoss_premium_python",
            ),
            # Story 21.5 — Tier 2 catalog sources (CDO-ENT-CONDA).
            node(
                func=refresh_about_maintainers,
                inputs="params:ttls",
                outputs="discovery_about_maintainers_raw",
                name="refresh_about_maintainers",
            ),
            node(
                func=join_enterprise_conda_maintainers,
                inputs=["discovery_about_maintainers_raw", "core_feedstock_attribution"],
                outputs="enterprise_conda_maintainers",
                name="join_enterprise_conda_maintainers",
            ),
        ]
    )
