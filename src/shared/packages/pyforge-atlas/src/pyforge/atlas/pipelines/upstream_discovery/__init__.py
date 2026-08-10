"""``upstream_discovery`` pipeline (Story 13.1, CAP-1 — FR-64).

Ships the GitHub-trending discovery ingest trigger (``refresh_trending_candidates`` ->
``trending_candidates``). Auto-discovered by ``find_pipelines()``. Tier classification
(CAP-2), the read-side operator surface (CAP-3), the fixed-source org-audit track (CAP-4),
and the downstream Mason handoff (CAP-5) are Stories 13.2-13.5 — out of scope here; this
package is named for the epic/SPEC (not just "trending") so those stories can land in it.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
