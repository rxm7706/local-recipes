"""``pyforge.atlas.artifactory`` -- Story 15.1 (Epic 15, CAP-1): a standalone,
network-injectable adapter for an Artifactory instance's own AQL (Artifactory Query
Language) API -- the org-specific download telemetry a public PyPI/conda-forge crawl
structurally cannot see.

Package marker only (mirrors ``factory/``'s / ``trending_candidates/``'s sibling shape as a
new top-level package beside ``pipelines/``, ``nl/``, ``rag/``). Mock-only: no live
Artifactory instance is named, selected, or contacted here. NOT a Kedro pipeline subpackage
-- it exposes no ``create_pipeline()``, so it is never touched by
``find_pipelines(raise_errors=True)``. Story 15.3 (CAP-4) owns wiring a pipeline that imports
``ArtifactoryAqlAdapter`` from this package; Story 15.2 (CAP-2/CAP-3) owns the identity join
and the internal/private flag.
"""

from __future__ import annotations

from .aql_adapter import (
    AqlRequest,
    AqlResponse,
    ArtifactoryAqlAdapter,
    ArtifactoryAqlError,
    ArtifactoryConfig,
    DownloadRow,
)

__all__ = [
    "AqlRequest",
    "AqlResponse",
    "ArtifactoryAqlAdapter",
    "ArtifactoryAqlError",
    "ArtifactoryConfig",
    "DownloadRow",
]
