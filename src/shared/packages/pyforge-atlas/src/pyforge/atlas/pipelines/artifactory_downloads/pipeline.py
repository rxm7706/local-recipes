"""``artifactory_downloads`` pipeline wiring (Story 15.3, CAP-4; Epic 15).

Three nodes, wired by catalog-name string edges (AD-3):
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
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node

from .nodes import (
    fetch_artifactory_downloads,
    format_artifactory_purl_export,
    join_artifactory_identity,
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
        ]
    )
