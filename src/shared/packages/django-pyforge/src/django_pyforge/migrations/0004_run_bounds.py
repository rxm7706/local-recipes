"""Story 42.2 — run bounds: subject, task id, cancelled, bound indexes.

The constraint is dropped and re-added rather than altered because a
``CheckConstraint`` has no in-place widening in Django's schema editor; the
extraction changeset (``python-agent-platform:20``) mirrors that pair exactly.
"""

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("django_pyforge", "0003_run_state_timing"),
    ]

    operations = [
        migrations.AddField(
            model_name="runstate",
            name="subject",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="runstate",
            name="celery_task_id",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="runstate",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "pending"),
                    ("running", "running"),
                    ("succeeded", "succeeded"),
                    ("failed", "failed"),
                    ("cancelled", "cancelled"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="runstate",
            name="run_state_status_valid",
        ),
        migrations.AddConstraint(
            model_name="runstate",
            constraint=models.CheckConstraint(
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
        ),
        migrations.AddIndex(
            model_name="runstate",
            index=models.Index(
                fields=["subject", "status"],
                name="run_state_subject_status",
            ),
        ),
        migrations.AddIndex(
            model_name="runstate",
            index=models.Index(
                fields=["station", "status"],
                name="run_state_station_status",
            ),
        ),
    ]
