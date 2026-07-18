"""``derived_artifacts`` pipeline wiring (Story B7, AC-3).

One PURE node producing the full-universe CycloneDX BOM. ``inputs=`` bind to catalog
NAMES (AD-3 cross-pipeline edges): ``core_packages_enumerated`` (core) +
``pypi_conda_mapping`` (pypi_intelligence). Node name FROZEN.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import build_universe_sbom


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=build_universe_sbom,
                inputs=["core_packages_enumerated", "pypi_conda_mapping", "parameters"],
                outputs="derived_universe_sbom",
                name="build_universe_sbom",
            ),
        ]
    )
