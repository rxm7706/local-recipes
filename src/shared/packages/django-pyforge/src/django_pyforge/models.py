"""Supervisor store in the Django default schema (canopy AD-6 / AD-12).

``run_state`` and ``mcp_handles`` are tables in ``public`` (SQLite: the
default schema). They are not extra PostgreSQL schemas.
"""

from __future__ import annotations

import uuid

from django.core.validators import MinLengthValidator
from django.db import models


class RunState(models.Model):
    """One supervisor-published run. UUID PK is the run_id MCP get will use."""

    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"
        # Story 42.2: an operator revoked this subject. Terminal, and distinct
        # from FAILED because the run never got to fail -- conflating the two
        # would make "how often does this station break?" unanswerable.
        CANCELLED = "cancelled", "cancelled"

    #: Terminal statuses. A row in one of these is finished and prunable.
    TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")
    #: In-flight statuses. These are what the run bounds count (Story 42.2).
    LIVE_STATUSES = ("pending", "running")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.CharField(max_length=64, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # Story 42.2: the `sub` claim of the assertion that published this run.
    # The run bounds count by this, and `revoke --sub` selects by it, so the
    # subject has to be on the run row and not only on its handle.
    subject = models.CharField(max_length=255, default="")
    # The Celery task id this run was published with. Chosen before the task is
    # sent (never read back from the result), so revoke can name a task that is
    # still only queued.
    celery_task_id = models.CharField(max_length=255, default="")
    result = models.JSONField(null=True, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    heartbeat_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        db_table = "run_state"
        # Named explicitly rather than left to Django's hashed default: these
        # back the two hot bound queries (live runs per subject, per station)
        # and the revoke selection, and a named index is one an operator can
        # recognise in `pg_indexes` and a changeset can reproduce verbatim.
        indexes = [
            models.Index(
                fields=["subject", "status"],
                name="run_state_subject_status",
            ),
            models.Index(
                fields=["station", "status"],
                name="run_state_station_status",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "pending",
                        "running",
                        "succeeded",
                        "failed",
                        "cancelled",
                    ),
                ),
                name="run_state_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return str(self.id)


class McpHandle(models.Model):
    """Opaque TTL'd capability pointing at a supervisor ``run_id``."""

    handle = models.CharField(
        max_length=128,
        unique=True,
        validators=[MinLengthValidator(32)],
    )
    run = models.ForeignKey(
        RunState,
        on_delete=models.CASCADE,
        related_name="handles",
    )
    expires_at = models.DateTimeField()
    subject = models.CharField(max_length=255, default="")

    class Meta:
        db_table = "mcp_handles"

    def __str__(self) -> str:
        return self.handle
