"""``pypi_intelligence`` pipeline wiring (Story B2, Task 4 / AC-1).

Nodes bind ``inputs=``/``outputs=`` to catalog dataset names (Story A2). Cross-pipeline
edges resolve by CATALOG NAME (AD-3): ``core_packages_enumerated`` (core→pypi_intelligence,
Phase C). Execution order resolves automatically from declared inputs/outputs — no
``PHASES`` list driver. Phase C produces the intermediate ``pypi_conda_mapping_base``
(an unmanaged MemoryDataset — not in the catalog) that Phase C.5 extends into the
declared ``pypi_conda_mapping`` output, so the two mapping stages chain without two
nodes writing one catalog dataset (AD-3).
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    enrich_pypi_intelligence,
    enumerate_pypi_universe,
    export_pypi_conda_map,
    fetch_pypi_current_versions,
    fetch_pypi_downloads,
    flag_cross_channel,
    map_pypi_conda,
    match_source_urls,
    score_pypi_readiness,
    snapshot_pypi_serials,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=map_pypi_conda,
                inputs=["pypi_parselmouth_mapping_raw", "core_packages_enumerated"],
                outputs="pypi_conda_mapping_base",
                name="map_pypi_conda",
            ),
            node(
                func=match_source_urls,
                inputs=["pypi_conda_mapping_base", "pypi_json_raw"],
                outputs="pypi_conda_mapping",
                name="match_source_urls",
            ),
            node(
                func=enumerate_pypi_universe,
                inputs="pypi_simple_index_raw",
                outputs="pypi_universe",
                name="enumerate_pypi_universe",
            ),
            node(
                func=fetch_pypi_current_versions,
                inputs=["pypi_json_raw", "pypi_universe"],
                outputs="pypi_current_versions",
                name="fetch_pypi_current_versions",
            ),
            node(
                func=snapshot_pypi_serials,
                inputs="pypi_simple_index_raw",
                outputs="pypi_universe_serial_snapshots",
                name="snapshot_pypi_serials",
            ),
            node(
                func=fetch_pypi_downloads,
                inputs="pypi_bigquery_downloads_raw",
                outputs="pypi_downloads_monthly",
                name="fetch_pypi_downloads",
            ),
            node(
                func=flag_cross_channel,
                inputs="pypi_cross_channel_repodata_raw",
                outputs="pypi_cross_channel_flags",
                name="flag_cross_channel",
            ),
            node(
                func=enrich_pypi_intelligence,
                inputs="pypi_json_raw",
                outputs="pypi_intelligence_enriched",
                name="enrich_pypi_intelligence",
            ),
            node(
                func=score_pypi_readiness,
                inputs="pypi_intelligence_enriched",
                outputs="pypi_intelligence_scored",
                name="score_pypi_readiness",
            ),
            # § 3.4 external-refresh asset (Story B5) — the Q6 flat-cache export shim.
            # SINGLE writer of pypi_conda_map_store; reads the migrated Phase C mapping
            # (offline-safe, no remote re-fetch) and preserves g10_spelling + no-clobber.
            node(
                func=export_pypi_conda_map,
                inputs="pypi_conda_mapping",
                outputs="pypi_conda_map_store",
                name="export_pypi_conda_map",
            ),
        ]
    )
