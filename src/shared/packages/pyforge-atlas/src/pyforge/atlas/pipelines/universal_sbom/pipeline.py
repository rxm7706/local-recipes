"""``universal_sbom`` pipeline wiring (Story B7, AC-1/2/3/4/4b + AD-12).

Two PURE nodes over the entry-scoped SBOM datasets. ``inputs=``/``outputs=`` bind to
catalog NAMES; cross-pipeline edges resolve by name (AD-3): ``core_packages_enumerated``
(core), ``pypi_conda_mapping`` + ``pypi_universe`` (pypi_intelligence — the full PyPI
universe is the authoritative ADD-path membership set, VERBATIM legacy universe_lookup),
``derived_universe_sbom`` (derived_artifacts). Execution order resolves automatically
from declared IO — no procedural driver.

Node names are FROZEN (the registry test asserts the exact 2-node set):
``normalize_intake_to_cyclonedx`` / ``match_against_universe``.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import match_against_universe, normalize_intake_to_cyclonedx


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=normalize_intake_to_cyclonedx,
                inputs=["sbom_intake_entry", "sbom_resolution_entry", "parameters"],
                outputs="sbom_normalized_bom_entry",
                name="normalize_intake_to_cyclonedx",
            ),
            node(
                func=match_against_universe,
                inputs=[
                    "sbom_normalized_bom_entry",
                    "core_packages_enumerated",
                    "pypi_conda_mapping",
                    "derived_universe_sbom",
                    "pypi_universe",
                    "parameters",
                ],
                outputs="sbom_match_report_entry",
                name="match_against_universe",
            ),
        ]
    )
