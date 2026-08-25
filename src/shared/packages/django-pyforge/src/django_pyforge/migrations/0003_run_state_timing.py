from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("django_pyforge", "0002_run_result_and_handle_subject"),
    ]

    operations = [
        migrations.AddField(
            model_name="runstate",
            name="station",
            field=models.CharField(default="", max_length=64),
        ),
        migrations.AddField(
            model_name="runstate",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runstate",
            name="heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runstate",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runstate",
            name="duration_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
