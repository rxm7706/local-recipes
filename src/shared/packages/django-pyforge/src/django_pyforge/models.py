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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        db_table = "run_state"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("pending", "running", "succeeded", "failed"),
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

    class Meta:
        db_table = "mcp_handles"

    def __str__(self) -> str:
        return self.handle
