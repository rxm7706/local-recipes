"""``seed_gaps`` pipeline wiring (Story B6, Task 1 / AC-1, AC-4).

The four READ-ONLY gap suggesters as terminal ``derived``-layer report nodes
(§ 5.2 item 6). Each node binds ``inputs=``/``outputs=`` to catalog dataset
NAMES; cross-pipeline edges resolve by name (AD-3): the seed inputs are the A2
``seed_*`` datasets, the ground-truth inputs are core / pypi_intelligence /
vulnerability outputs, and each report is a pre-declared ``derived``-layer
output. Execution order resolves automatically from declared inputs/outputs — no
procedural driver.

Node names are FROZEN (AC-4 asserts the exact 4-node set):
``report_lts_registry_gap`` / ``report_cwe_seed_gap`` / ``report_spdx_schema_gap``
/ ``report_license_map_gap``. ``mapping-gap`` is a WRITER (the ``g10_spelling``
no-clobber writeback) and stays in the PyPI Intelligence pipeline — it is
deliberately NOT a node here (AD-15).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    report_cwe_seed_gap,
    report_license_map_gap,
    report_lts_registry_gap,
    report_spdx_schema_gap,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=report_lts_registry_gap,
                inputs=[
                    "seed_lts_registry",
                    "pypi_endoflife_raw",
                    "core_packages_enumerated",
                    "pypi_conda_mapping",
                ],
                outputs="seed_gaps_lts_registry_report",
                name="report_lts_registry_gap",
            ),
            node(
                func=report_cwe_seed_gap,
                inputs=["seed_cwe_categories", "vulnerability_cwe_categories"],
                outputs="seed_gaps_cwe_report",
                name="report_cwe_seed_gap",
            ),
            node(
                func=report_spdx_schema_gap,
                inputs=[
                    "seed_spdx_schema",
                    "seed_spdx_upstream_list_raw",
                    "core_packages_enumerated",
                ],
                outputs="seed_gaps_spdx_report",
                name="report_spdx_schema_gap",
            ),
            node(
                func=report_license_map_gap,
                inputs=["seed_spdx_schema", "pypi_intelligence_enriched"],
                outputs="seed_gaps_license_map_report",
                name="report_license_map_gap",
            ),
        ]
    )
