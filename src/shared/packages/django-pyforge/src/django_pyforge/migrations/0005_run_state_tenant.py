"""Story 42.5 — tenant claim on supervisor runs."""

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("django_pyforge", "0004_run_bounds"),
    ]

    operations = [
        migrations.AddField(
            model_name="runstate",
            name="tenant",
            field=models.CharField(default="", max_length=64),
        ),
    ]
