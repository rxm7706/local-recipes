from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("django_pyforge", "0001_supervisor_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="runstate",
            name="result",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mcphandle",
            name="subject",
            field=models.CharField(default="", max_length=255),
        ),
    ]
