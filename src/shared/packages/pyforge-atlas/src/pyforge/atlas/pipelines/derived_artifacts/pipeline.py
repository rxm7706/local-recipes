"""``derived_artifacts`` pipeline wiring (Story B7, AC-3; Story 23.8; Story 23.3).

PURE nodes: ``build_universe_sbom`` (CycloneDX BOM), ``build_inventory_universe``
(workbook-free metrics universe), ``derive_basilisk_vuln_rollup`` + ``assign_inventory_priority``
(Story 23.3 priority hierarchy). ``inputs=`` bind to catalog NAMES (AD-3 cross-pipeline
edges). Node names FROZEN.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    assign_inventory_priority,
    build_inventory_universe,
    build_universe_sbom,
    derive_basilisk_vuln_rollup,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
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
        ]
    )
