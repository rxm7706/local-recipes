"""``seed_gaps`` pipeline (Story B6 — the four READ-ONLY seed-freshness suggesters).

Auto-discovered by ``find_pipelines()`` (B1/B2 pattern — ``pipeline_registry.py`` is not
edited).
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
