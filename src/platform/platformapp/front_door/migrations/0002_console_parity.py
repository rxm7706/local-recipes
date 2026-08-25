import django.db.models.deletion
from django.db import migrations
from django.db import models

import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ("front_door", "0001_homepage"),
        ("wagtailcore", "0097_baselogentry_uuid_action_timestamp_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsoleEditorialPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("surface_id", models.CharField(max_length=64)),
                ("body", wagtail.fields.RichTextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="DetectorVerdict",
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
                ("detector", models.CharField(max_length=64, unique=True)),
                ("state", models.CharField(max_length=32)),
                ("findings", models.PositiveIntegerField(default=0)),
                ("verdict", models.TextField(blank=True)),
                (
                    "captured_at",
                    models.DateTimeField(),
                ),
            ],
            options={
                "db_table": "detector_verdict",
            },
        ),
    ]
