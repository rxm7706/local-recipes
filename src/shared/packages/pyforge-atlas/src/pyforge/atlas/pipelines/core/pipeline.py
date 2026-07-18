"""``core`` pipeline wiring (Story B1, Task 3 / AC-1).

Each node binds its ``inputs=``/``outputs=`` to the catalog dataset names declared in
``conf/base/catalog.yml`` (Story A2). Execution order RESOLVES automatically from
those declared names — there is no procedural call order and no ``PHASES`` list driver
(FR-2 / AD-3). ``find_pipelines()`` auto-discovers this module via
``create_pipeline()``.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    attribute_feedstocks,
    build_dependency_graph,
    compute_downloads,
    compute_feedstock_health,
    compute_version_download_history,
    detect_latest_status,
    enumerate_conda_packages,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=enumerate_conda_packages,
                inputs=["core_repodata_raw", "core_channeldata_raw"],
                outputs="core_packages_enumerated",
                name="enumerate_conda_packages",
            ),
            node(
                func=attribute_feedstocks,
                inputs="core_feedstock_outputs_raw",
                outputs="core_feedstock_attribution",
                name="attribute_feedstocks",
            ),
            node(
                func=detect_latest_status,
                inputs=["core_repodata_raw", "core_channeldata_raw"],
                outputs="core_latest_status",
                name="detect_latest_status",
            ),
            node(
                func=compute_downloads,
                inputs=["core_anaconda_downloads_raw", "core_s3_download_stats_raw"],
                outputs=[
                    "core_downloads",
                    "core_downloads_platform_breakdown",
                    "core_downloads_pyver_breakdown",
                    "core_downloads_channel_breakdown",
                ],
                name="compute_downloads",
            ),
            node(
                func=compute_version_download_history,
                inputs="core_anaconda_downloads_raw",
                outputs="core_version_download_history",
                name="compute_version_download_history",
            ),
            node(
                func=build_dependency_graph,
                inputs="core_cf_graph_raw",
                outputs="core_dependencies",
                name="build_dependency_graph",
            ),
            node(
                func=compute_feedstock_health,
                inputs="core_cf_graph_raw",
                outputs="core_feedstock_health",
                name="compute_feedstock_health",
            ),
        ]
    )
