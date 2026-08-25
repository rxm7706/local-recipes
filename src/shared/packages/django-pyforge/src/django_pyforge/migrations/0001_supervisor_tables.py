import uuid

import django.db.models.deletion
from django.core.validators import MinLengthValidator
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RunState",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "pending"),
                            ("running", "running"),
                            ("succeeded", "succeeded"),
                            ("failed", "failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
            ],
            options={
                "db_table": "run_state",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            status__in=(
                                "pending",
                                "running",
                                "succeeded",
                                "failed",
                            ),
                        ),
                        name="run_state_status_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="McpHandle",
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
                (
                    "handle",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        validators=[MinLengthValidator(32)],
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="handles",
                        to="django_pyforge.runstate",
                    ),
                ),
            ],
            options={
                "db_table": "mcp_handles",
            },
        ),
    ]
