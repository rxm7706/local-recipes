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
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    phase_index = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    report_json = models.TextField(blank=True, default="")
    sbom_json = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.original_name} ({self.status})"


class JobStatus(models.TextChoices):
    """Shared job vocabulary — never a verdict lattice value."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class FleetRepo(models.Model):
    """One inventoried repository (Story 16.1 shape; rows may be fixture-seeded)."""

    organisation = models.CharField(max_length=255, db_index=True)
    full_name = models.CharField(max_length=512)
    default_branch = models.CharField(max_length=255, default="main")
    clone_url = models.CharField(max_length=1024)
    archived = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "full_name"),
                name="warden_fabric_fleetrepo_org_name_uniq",
            ),
        ]
        ordering = ("full_name",)

    def __str__(self) -> str:
        return self.full_name


class FleetRun(models.Model):
    """One fleet scan job — status is job lifecycle only, not a fleet verdict."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
    )
    phase_index = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"fleet-run {self.organisation} ({self.status})"


class FleetRepoScan(models.Model):
    """One repo's ``warden scan`` verdict within a fleet run."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fleet_run = models.ForeignKey(
        FleetRun,
        on_delete=models.CASCADE,
        related_name="repo_scans",
    )
    fleet_repo = models.ForeignKey(
        FleetRepo,
        on_delete=models.CASCADE,
        related_name="scans",
    )
    commit_sha = models.CharField(max_length=64, blank=True, default="")
    report_json = models.TextField(blank=True, default="")
    scan_exit_code = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
    )
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("fleet_run", "fleet_repo"),
                name="warden_fabric_fleetreposcan_run_repo_uniq",
            ),
        ]
        ordering = ("fleet_repo__full_name",)

    def __str__(self) -> str:
        return f"{self.fleet_repo.full_name} ({self.status})"


class FixProposal(models.Model):
    """One operator-gated fleet fix (Story 16.3)."""

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        APPROVED = "approved", "Approved"
        OPENED = "opened", "Opened"
        FAILED = "failed", "Failed"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fleet_repo_scan = models.ForeignKey(
        FleetRepoScan,
        on_delete=models.CASCADE,
        related_name="fix_proposals",
    )
    repo_full_name = models.CharField(max_length=512)
    finding_id = models.CharField(max_length=512)
    action = models.CharField(max_length=32)
    target = models.CharField(max_length=512, blank=True, default="")
    planned_paths_json = models.TextField(blank=True, default="[]")
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.QUEUED,
    )
    pr_url = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    approved_by = models.CharField(max_length=255, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("fleet_repo_scan", "finding_id"),
                name="warden_fabric_fixproposal_scan_finding_uniq",
            ),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.repo_full_name} {self.finding_id} ({self.state})"
