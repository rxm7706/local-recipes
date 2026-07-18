"""``derived_artifacts`` pipeline (Story B7 — the § 5.2 item-7 read-surface layer).

Ships the full-universe CycloneDX BOM producer (``build_universe_sbom`` →
``derived_universe_sbom``) under the AD-15 14-day freshness contract. Auto-discovered
by ``find_pipelines()``. (``export-purls`` → ``derived_purl_exports`` is out of B7's
ACs and is owned by a later story; the catalog entry stays declared-but-unproduced.)
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
