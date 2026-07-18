"""``universal_sbom`` pipeline (Story B7 — § 4.10 intake → CycloneDX → six-bucket match).

Auto-discovered by ``find_pipelines()`` (B1/B2 pattern — ``pipeline_registry.py`` is
not edited).
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
