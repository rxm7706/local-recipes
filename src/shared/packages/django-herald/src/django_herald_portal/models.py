"""Projection of published deck export manifests (CAP-54 D3; no bytes column)."""

from __future__ import annotations

from django.db import models


class DeckExport(models.Model):
    """One row per published export record (sha256 is the object-store key)."""

    slug = models.CharField(max_length=255, db_index=True)
    topic = models.CharField(max_length=255)
    kind = models.CharField(max_length=64)
    export_date = models.DateField()
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, unique=True)
    source_commit = models.CharField(max_length=64)
    published_at = models.DateTimeField()

    class Meta:
        ordering = ("slug", "kind", "-export_date")

    def __str__(self) -> str:
        return f"{self.slug}/{self.kind}@{self.sha256[:8]}"
