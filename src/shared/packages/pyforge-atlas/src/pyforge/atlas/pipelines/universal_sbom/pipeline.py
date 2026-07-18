"""``universal_sbom`` pipeline wiring (Story B7, AC-1/2/3/4/4b + AD-12).

Two PURE nodes over the entry-scoped SBOM datasets. ``inputs=``/``outputs=`` bind to
catalog NAMES; cross-pipeline edges resolve by name (AD-3): ``core_packages_enumerated``
(core), ``pypi_conda_mapping`` + ``pypi_universe`` (pypi_intelligence — the full PyPI
universe is the authoritative ADD-path membership set, VERBATIM legacy universe_lookup),
``derived_universe_sbom`` (derived_artifacts). Execution order resolves automatically
from declared IO — no procedural driver.

Node names are FROZEN: the two PURE B7 nodes ``normalize_intake_to_cyclonedx`` /
``match_against_universe``, plus the F4 TERMINAL stage
``run_dependency_hygiene`` (the deptry hygiene node, FR-16) and
``assemble_and_gate`` (the SINGLE-producer four-axis policy gate, AD-12 /
FR-18). The gate node is the terminal quality node: it consumes the hygiene
findings + the six-bucket match report and emits the one schema-validated
``ComplianceReport`` (``sbom_compliance_report_entry``, derived layer).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .gate import assemble_and_gate, run_dependency_hygiene
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
            node(
                func=run_dependency_hygiene,
                inputs=["sbom_intake_entry", "parameters"],
                outputs="sbom_hygiene_entry",
                name="run_dependency_hygiene",
            ),
            node(
                func=assemble_and_gate,
                inputs=["sbom_hygiene_entry", "sbom_match_report_entry", "parameters"],
                outputs="sbom_compliance_report_entry",
                name="assemble_and_gate",
            ),
        ]
    )
