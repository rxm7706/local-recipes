"""``semantic_packages`` pipeline wiring (Story 20.3, CAP-6).

DOWNSTREAM ONLY of the sealed `core` + `vcs_health` pipelines' own catalog outputs --
bound here by their existing catalog dataset names (execution order resolves from those
names, AD-3; no procedural call order). Mirrors `pipelines/query_plane_cache/`'s shape
exactly (Story 34.2, FR-47): a 3-line ``Pipeline([node(...)])``.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import compose_semantic_packages


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=compose_semantic_packages,
                inputs=[
                    "core_packages_enumerated",
                    "core_latest_status",
                    "core_feedstock_attribution",
                    "vcs_archived_feedstocks",
                    "core_downloads",
                ],
                outputs="semantic_packages",
                name="compose_semantic_packages",
            ),
        ]
    )
