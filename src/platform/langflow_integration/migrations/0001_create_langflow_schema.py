from django.db import migrations


class Migration(migrations.Migration):
    """Provisions `langflow_schema` -- AD-5 schema isolation, real not conventional.

    `CREATE SCHEMA IF NOT EXISTS` makes this idempotent (I/O & Edge-Case Matrix:
    "Migration is idempotent"), so re-running `manage.py migrate` against an
    already-provisioned database is a no-op. This is a `RunSQL` migration, not a
    model migration: Django's ORM never creates tables inside `langflow_schema`
    -- everything inside it belongs to Langflow's own Alembic migrations, which
    run at ASGI lifespan startup against `LANGFLOW_DATABASE_URL`
    (`config/settings/base.py`), never against `manage.py migrate`.
    """

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS langflow_schema;",
            reverse_sql="DROP SCHEMA IF EXISTS langflow_schema CASCADE;",
        ),
    ]
