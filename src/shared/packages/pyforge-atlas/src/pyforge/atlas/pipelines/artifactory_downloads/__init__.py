"""``artifactory_downloads`` pipeline (Story 15.3, CAP-4; Epic 15).

Wires Story 15.1's ``ArtifactoryAqlAdapter``/``DownloadRow`` (fetch) and Story 15.2's
``join_identity``/``JoinedDownloadRow`` (identity join) into a 3-node Kedro pipeline: fetch ->
join -> export. The export node contributes exactly one NEW partition
(``artifactory_downloads.tsv``) to the already-declared-but-unproduced ``derived_purl_exports``
``PartitionedDataset`` -- mirrors ``export_purls.py``'s conda->pypi mapped-TSV shape for the
reversed pypi->conda direction. Auto-discovered by ``find_pipelines()``. Default-inert:
``params:artifactory.virtual_repos`` defaults to ``[]``, so the fetch node constructs no
adapter/transport and contacts nothing.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
