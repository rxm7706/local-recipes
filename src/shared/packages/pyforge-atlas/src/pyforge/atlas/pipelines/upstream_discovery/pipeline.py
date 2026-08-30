"""``upstream_discovery`` pipeline wiring (Story 13.1 CAP-1 + Story 13.2 CAP-2 +
Story 13.4 CAP-4 + Story 21.4 Tier 1 catalog sources + Story 21.5 Tier 2 catalog
sources + Story 21.6 CAP-3 identity join).

Fourteen nodes — the original four, Story 21.4's three Tier-1 external-refresh
triggers, Story 21.5's two Tier-2 additions (``refresh_about_maintainers`` +
``join_enterprise_conda_maintainers``), and Story 21.6's five CAP-3 identity-join
additions (three external-refresh triggers + two pure join/shape nodes):
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
- ``refresh_purl_associator_mappings`` / ``refresh_openteams_board`` /
  ``refresh_staged_recipes_prs``: PURE triggers (Story 21.6, CAP-3); each is the
  SINGLE writer of its named catalog entry (``purl_associator_mappings_raw`` /
  ``openteams_project_1_board_raw`` / ``discovery_staged_recipes_prs_raw``).
- ``build_identity_packages_primary``: joins the three new raw sources +
  ``discovery_local_recipes_raw`` + ``core_feedstock_attribution`` + the
  CDO-ENT-JFROG/CDO-ENT-CONDA universe (``enterprise_jfrog_names`` /
  ``enterprise_conda_maintainers``, Story 21.5) + ``pypi_universe`` /
  ``core_packages_enumerated`` (verification signals), reproducing the legacy
  identity join, and writes ``identity_packages_primary`` (Story 21.6, CAP-3).
- ``build_identity_export_parquet``: reshapes ``identity_packages_primary`` to the
  full ``GIST_SCHEMA`` column order (ranking/JFROG columns null) and writes
  ``identity_export_parquet`` (Story 21.6, CAP-3).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    build_identity_export_parquet,
    build_identity_packages_primary,
    classify_trending_candidates,
    join_enterprise_conda_maintainers,
    load_org_audit_candidates,
    refresh_about_maintainers,
    refresh_anaconda_dist_2026x,
    refresh_aoss_premium_python,
    refresh_basilisk_packages,
    refresh_openteams_board,
    refresh_purl_associator_mappings,
    refresh_staged_recipes_prs,
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
            # Story 21.6 — CAP-3 identity join (Phase D): 3 new external-refresh
            # triggers (single writers) + 2 pure join/shape nodes.
            node(
                func=refresh_purl_associator_mappings,
                inputs="params:ttls",
                outputs="purl_associator_mappings_raw",
                name="refresh_purl_associator_mappings",
            ),
            node(
                func=refresh_openteams_board,
                inputs="params:ttls",
                outputs="openteams_project_1_board_raw",
                name="refresh_openteams_board",
            ),
            node(
                func=refresh_staged_recipes_prs,
                inputs="params:ttls",
                outputs="discovery_staged_recipes_prs_raw",
                name="refresh_staged_recipes_prs",
            ),
            node(
                func=build_identity_packages_primary,
                inputs=[
                    "purl_associator_mappings_raw",
                    "openteams_project_1_board_raw",
                    "discovery_staged_recipes_prs_raw",
                    "discovery_local_recipes_raw",
                    "core_feedstock_attribution",
                    "enterprise_jfrog_names",
                    "enterprise_conda_maintainers",
                    "pypi_universe",
                    "core_packages_enumerated",
                ],
                outputs="identity_packages_primary",
                name="build_identity_packages_primary",
            ),
            node(
                func=build_identity_export_parquet,
                inputs="identity_packages_primary",
                outputs="identity_export_parquet",
                name="build_identity_export_parquet",
            ),
        ]
    )
