# Generated for Story 16.3 — FixProposal queue.

from __future__ import annotations

import uuid

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("warden_fabric", "0002_fleet_run"),
    ]

    operations = [
        migrations.CreateModel(
            name="FixProposal",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("repo_full_name", models.CharField(max_length=512)),
                ("finding_id", models.CharField(max_length=512)),
                ("action", models.CharField(max_length=32)),
                ("target", models.CharField(blank=True, default="", max_length=512)),
                ("planned_paths_json", models.TextField(blank=True, default="[]")),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("approved", "Approved"),
                            ("opened", "Opened"),
                            ("failed", "Failed"),
                            ("dismissed", "Dismissed"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("pr_url", models.TextField(blank=True, default="")),
                ("error", models.TextField(blank=True, default="")),
                ("approved_by", models.CharField(blank=True, default="", max_length=255)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "fleet_repo_scan",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="fix_proposals",
                        to="warden_fabric.fleetreposcan",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="fixproposal",
            constraint=models.UniqueConstraint(
                fields=("fleet_repo_scan", "finding_id"),
                name="warden_fabric_fixproposal_scan_finding_uniq",
            ),
        ),
    ]
