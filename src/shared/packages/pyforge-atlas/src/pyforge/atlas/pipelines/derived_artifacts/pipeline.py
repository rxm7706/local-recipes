"""``derived_artifacts`` pipeline wiring (Story B7, AC-3; Story 23.8; Story 23.3; Story 23.4; Story 23.5).

PURE nodes: ``build_universe_sbom`` (CycloneDX BOM), ``build_inventory_universe``
(workbook-free metrics universe), ``derive_basilisk_vuln_rollup`` + ``assign_inventory_priority``
(Story 23.3 priority hierarchy), ``build_inventory_verified_packages`` +
``build_inventory_aoss_free_queue`` (Story 23.4 deliverable A + AOSS queue),
``build_identity_complete_export`` (Story 23.5 complete export join); the three board projections
``project_behind_upstream``, ``project_live_catalog_coverage`` and ``project_universe_sbom_summary``
(Story 37.4); ``export_purl_artifacts`` (Story 37.8); ``score_alternative_candidates`` (Story 37.7).
``inputs=`` bind to catalog NAMES (AD-3 cross-pipeline edges). Node names FROZEN.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .alternatives import score_alternative_candidates
from .nodes import (
    assign_inventory_priority,
    build_identity_complete_export,
    build_inventory_aoss_free_queue,
    build_inventory_universe,
    build_inventory_verified_packages,
    build_universe_sbom,
    compose_distribution_breakdown,
    derive_basilisk_vuln_rollup,
    project_behind_upstream,
    project_live_catalog_coverage,
    project_universe_sbom_summary,
)
from .purl_exports import export_purl_artifacts


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                # Story 37.3: the distribution-breakdown board's one table
                func=compose_distribution_breakdown,
                inputs=[
                    "core_downloads_platform_breakdown",
                    "core_downloads_pyver_breakdown",
                    "core_downloads_channel_breakdown",
                ],
                outputs="derived_distribution_breakdown",
                name="compose_distribution_breakdown",
            ),
            node(
                func=build_universe_sbom,
                inputs=["core_packages_enumerated", "pypi_conda_mapping", "parameters"],
                outputs="derived_universe_sbom",
                name="build_universe_sbom",
            ),
            node(
                func=build_inventory_universe,
                inputs=[
                    "core_packages_enumerated",
                    "core_anaconda_main_packages",
                    "discovery_anaconda_dist_2026x_raw",
                    "discovery_basilisk_packages_raw",
                    "discovery_aoss_free_python_raw",
                    "discovery_aoss_premium_python_raw",
                    "enterprise_jfrog_names",
                    "enterprise_conda_maintainers",
                    "openteams_project_1_board_raw",
                ],
                outputs="inventory_universe",
                name="build_inventory_universe",
            ),
            node(
                func=derive_basilisk_vuln_rollup,
                inputs=[
                    "vulnerability_basilisk_advisories",
                    "vulnerability_basilisk_details",
                ],
                outputs="vulnerability_basilisk_rollup",
                name="derive_basilisk_vuln_rollup",
            ),
            node(
                func=assign_inventory_priority,
                inputs=[
                    "identity_packages_primary",
                    "enterprise_jfrog_consumption",
                    "enterprise_conda_maintainers",
                    "openteams_project_1_board_raw",
                    "vulnerability_basilisk_rollup",
                    "parameters",
                ],
                outputs="inventory_priority_assignments",
                name="assign_inventory_priority",
            ),
            node(
                func=build_inventory_verified_packages,
                inputs=[
                    "inventory_universe",
                    "core_packages_enumerated",
                    "pypi_universe",
                    "pypi_conda_mapping",
                    "inventory_priority_assignments",
                    "parameters",
                ],
                outputs="inventory_verified_packages",
                name="build_inventory_verified_packages",
            ),
            node(
                func=build_inventory_aoss_free_queue,
                inputs=[
                    "discovery_aoss_free_python_raw",
                    "core_packages_enumerated",
                    "pypi_universe",
                    "pypi_conda_mapping",
                    "enterprise_jfrog_consumption",
                    "enterprise_conda_maintainers",
                    "parameters",
                ],
                outputs="inventory_aoss_free_queue",
                name="build_inventory_aoss_free_queue",
            ),
            node(
                func=build_identity_complete_export,
                inputs=[
                    "identity_packages_primary",
                    "inventory_priority_assignments",
                    "enterprise_jfrog_consumption",
                    "enterprise_conda_maintainers",
                    "inventory_verified_packages",
                    "pypi_cross_channel_flags",
                    "pypi_tier3_channel_flags",
                    "inventory_universe",
                    "parameters",
                ],
                outputs="identity_complete_export",
                name="build_identity_complete_export",
            ),
            # Story 37.4: the projections the behind-upstream, live-catalog-coverage and universe-sbom
            # boards read
            node(
                func=project_behind_upstream,
                inputs=["vcs_upstream_versions", "core_packages_enumerated"],
                outputs="derived_behind_upstream",
                name="project_behind_upstream",
            ),
            node(
                func=project_live_catalog_coverage,
                inputs="identity_complete_export",
                outputs="derived_live_catalog_coverage",
                name="project_live_catalog_coverage",
            ),
            node(
                func=project_universe_sbom_summary,
                inputs="derived_universe_sbom",
                outputs="derived_universe_sbom_summary",
                name="project_universe_sbom_summary",
            ),
            # Story 37.8: legacy export-purls' six artifacts and their manifest
            node(
                func=export_purl_artifacts,
                inputs=[
                    "core_packages_enumerated",
                    "core_latest_status",
                    "pypi_conda_mapping",
                    "pypi_universe",
                    "discovery_recipe_extras_raw",
                    "core_cf_graph_raw",
                    "core_feedstock_attribution",
                ],
                outputs=["derived_purl_artifacts", "derived_purl_export_manifest"],
                name="export_purl_artifacts",
            ),
            # Story 37.7: legacy find-alternative's candidates for every archived package
            node(
                func=score_alternative_candidates,
                inputs=[
                    "core_cf_graph_raw",
                    "core_feedstock_attribution",
                    "semantic_packages",
                    "core_dependencies",
                ],
                outputs="derived_alternative_candidates",
                name="score_alternative_candidates",
            ),
        ]
    )
