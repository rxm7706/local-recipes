# Generated for Story 16.7 — the fleet run counts its failed and skipped repos.

from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("warden_fabric", "0003_fix_proposal"),
    ]

    operations = [
        migrations.AddField(
            model_name="fleetrun",
            name="failed_repo_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fleetrun",
            name="skipped_repo_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
