# Generated for Story 16.2 — FleetRun / FleetRepoScan (+ FleetRepo inventory rows).

from __future__ import annotations

import uuid

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("warden_fabric", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FleetRepo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("organisation", models.CharField(db_index=True, max_length=255)),
                ("full_name", models.CharField(max_length=512)),
                ("default_branch", models.CharField(default="main", max_length=255)),
                ("clone_url", models.CharField(max_length=1024)),
                ("archived", models.BooleanField(default=False)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("full_name",),
            },
        ),
        migrations.CreateModel(
            name="FleetRun",
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
                ("organisation", models.CharField(db_index=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("phase_index", models.PositiveSmallIntegerField(default=0)),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="FleetRepoScan",
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
                ("commit_sha", models.CharField(blank=True, default="", max_length=64)),
                ("report_json", models.TextField(blank=True, default="")),
                ("scan_exit_code", models.IntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "fleet_repo",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="scans",
                        to="warden_fabric.fleetrepo",
                    ),
                ),
                (
                    "fleet_run",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="repo_scans",
                        to="warden_fabric.fleetrun",
                    ),
                ),
            ],
            options={
                "ordering": ("fleet_repo__full_name",),
            },
        ),
        migrations.AddConstraint(
            model_name="fleetrepo",
            constraint=models.UniqueConstraint(
                fields=("organisation", "full_name"),
                name="warden_fabric_fleetrepo_org_name_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="fleetreposcan",
            constraint=models.UniqueConstraint(
                fields=("fleet_run", "fleet_repo"),
                name="warden_fabric_fleetreposcan_run_repo_uniq",
            ),
        ),
    ]
