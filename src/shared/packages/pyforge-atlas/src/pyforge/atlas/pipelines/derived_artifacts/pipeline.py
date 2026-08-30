"""``derived_artifacts`` pipeline wiring (Story B7, AC-3; Story 23.8).

Two PURE nodes. ``build_universe_sbom`` produces the full-universe CycloneDX BOM.
``build_inventory_universe`` (Story 23.8) unions 9 already-cataloged Parquet sources
into the workbook-free metrics universe. ``inputs=`` bind to catalog NAMES (AD-3
cross-pipeline edges: ``core`` / ``pypi_intelligence`` / ``upstream_discovery`` /
``artifactory_downloads`` outputs). Node names FROZEN.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import build_inventory_universe, build_universe_sbom


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
        ]
    )
