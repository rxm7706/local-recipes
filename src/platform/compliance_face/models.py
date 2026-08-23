"""Models for async compliance jobs (keys-not-blobs)."""

from __future__ import annotations

import uuid

from django.db import models


class ComplianceJob(models.Model):
    """One uploaded-manifest analysis job.

    ``storage_key`` points at the blob on disk / object storage. The Celery
    message carries ONLY this key (+ job id) — never the manifest bytes.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=512)
    original_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    phase_index = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    report_json = models.TextField(blank=True, default="")
    sbom_json = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
