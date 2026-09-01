"""``artifactory_downloads`` pipeline wiring (Story 15.3, CAP-4, Epic 15; + Story
21.5, Tier 2 names-only projection; + Story 23.2, enterprise JFROG consumption rollup).

Six nodes, wired by catalog-name string edges (AD-3):
- ``fetch_artifactory_downloads``: PURE ``params:artifactory -> DataFrame`` fetch node
  (Story 15.1's ``ArtifactoryAqlAdapter``); ``outputs=`` is the ``artifactory_downloads_raw``
  catalog entry.
- ``join_artifactory_identity``: resolves each fetched row against atlas's identity space
  (Story 15.2's ``join_identity``); ``outputs=`` is the ``artifactory_downloads_joined``
  catalog entry.
- ``format_artifactory_purl_export``: formats the joined rows into the ONE NEW
  ``artifactory_downloads.tsv`` partition this story contributes to the
  already-declared-but-unproduced ``derived_purl_exports`` ``PartitionedDataset``
  (``conf/base/catalog.yml``) -- never touching any other partition of that shared
  dataset (``PartitionedDataset.save()`` only writes the keys returned).
- ``project_artifactory_names`` (Story 21.5): projects ``artifactory_downloads_joined``
  down to ``pypi_name``/``conda_name``/``is_internal`` ONLY -- ``outputs=`` is the
  ``enterprise_jfrog_names`` catalog entry (names, not telemetry).
- ``fetch_artifactory_consumption`` (Story 23.2): org telemetry rollup fetch;
  ``outputs=`` is ``artifactory_consumption_raw``.
- ``build_enterprise_jfrog_consumption`` (Story 23.2): outer-join downloads +
  consumption by PEP-503 name; ``outputs=`` is ``enterprise_jfrog_consumption``.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    build_enterprise_jfrog_consumption,
    fetch_artifactory_consumption,
    fetch_artifactory_downloads,
    format_artifactory_purl_export,
    join_artifactory_identity,
    project_artifactory_names,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=fetch_artifactory_downloads,
                inputs="params:artifactory",
                outputs="artifactory_downloads_raw",
                name="fetch_artifactory_downloads",
            ),
            node(
                func=join_artifactory_identity,
                inputs=["artifactory_downloads_raw", "pypi_conda_mapping", "pypi_universe"],
                outputs="artifactory_downloads_joined",
                name="join_artifactory_identity",
            ),
            node(
                func=format_artifactory_purl_export,
                inputs="artifactory_downloads_joined",
                outputs="derived_purl_exports",
                name="format_artifactory_purl_export",
            ),
            node(
                func=project_artifactory_names,
                inputs="artifactory_downloads_joined",
                outputs="enterprise_jfrog_names",
                name="project_artifactory_names",
            ),
            node(
                func=fetch_artifactory_consumption,
                inputs="params:artifactory",
                outputs="artifactory_consumption_raw",
                name="fetch_artifactory_consumption",
            ),
            node(
                func=build_enterprise_jfrog_consumption,
                inputs=["artifactory_downloads_joined", "artifactory_consumption_raw"],
                outputs="enterprise_jfrog_consumption",
                name="build_enterprise_jfrog_consumption",
            ),
        ]
    )
