from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="idp_subject",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                unique=True,
                verbose_name="IdP subject",
            ),
        ),
    ]
