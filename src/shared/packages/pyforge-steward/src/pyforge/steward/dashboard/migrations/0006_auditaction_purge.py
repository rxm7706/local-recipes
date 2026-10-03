# Story 84.1 — add AuditAction.PURGE to the closed action vocabulary.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pyforge_steward_dashboard", "0005_corridorload_signer_corridorload_slice_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditentry",
            name="action",
            field=models.CharField(
                choices=[
                    ("load", "Load"),
                    ("filter", "Filter"),
                    ("navigate", "Navigate"),
                    ("export", "Export"),
                    ("audit_read", "Audit read"),
                    ("purge", "Purge"),
                ],
                max_length=16,
            ),
        ),
    ]
