"""``vcs_health`` pipeline wiring (Story B1, Task 3 / AC-1).

Nodes bind ``inputs=``/``outputs=`` to catalog dataset names (Story A2). Phase E reads
``core_cf_graph_raw`` — the cross-pipeline shared raw source referenced by catalog
name (AD-3). Execution order resolves automatically; no procedural call order.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    detect_archived_feedstocks,
    enrich_maintainers,
    fetch_live_health,
    track_registry_versions,
    track_upstream_versions,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=enrich_maintainers,
                inputs="core_cf_graph_raw",
                outputs=["vcs_maintainers", "vcs_package_maintainers"],
                name="enrich_maintainers",
            ),
            node(
                func=detect_archived_feedstocks,
                inputs="vcs_github_api_raw",
                outputs="vcs_archived_feedstocks",
                name="detect_archived_feedstocks",
            ),
            node(
                func=track_upstream_versions,
                inputs=[
                    "vcs_github_api_raw",
                    "vcs_gitlab_api_raw",
                    "vcs_codeberg_api_raw",
                ],
                outputs="vcs_upstream_versions",
                name="track_upstream_versions",
            ),
            node(
                func=track_registry_versions,
                inputs=[
                    "vcs_registry_npm_raw",
                    "vcs_registry_cran_raw",
                    "vcs_registry_cpan_raw",
                    "vcs_registry_luarocks_raw",
                    "vcs_registry_crates_raw",
                    "vcs_registry_rubygems_raw",
                    "vcs_registry_maven_raw",
                    "vcs_registry_nuget_raw",
                ],
                outputs="vcs_registry_versions",
                name="track_registry_versions",
            ),
            node(
                func=fetch_live_health,
                inputs="vcs_github_api_raw",
                outputs="vcs_live_health",
                name="fetch_live_health",
            ),
        ]
    )
