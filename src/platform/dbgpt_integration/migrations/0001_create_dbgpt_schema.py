from django.db import migrations


class Migration(migrations.Migration):
    """Provisions `dbgpt_schema` -- AD-5 schema isolation, real not conventional.

    `CREATE SCHEMA IF NOT EXISTS` makes this idempotent, mirroring
    `langflow_integration`'s `0001_create_langflow_schema` (Story 11.1). This
    is a `RunSQL` migration, not a model migration: Django's ORM never
    creates tables inside `dbgpt_schema`.

    Unlike Langflow's own Alembic migrations (which DO run against
    `langflow_schema`, at ASGI lifespan startup), nothing populates
    `dbgpt_schema` today -- DB-GPT's own metadata-store layer only supports
    SQLite/MySQL/OceanBase, a genuine, verified upstream limitation (see
    `dbgpt_integration/apps.py`'s docstring for the full citation). Landing
    the schema now costs nothing and is needed regardless: it is real,
    independent groundwork for whenever that upstream limitation is fixed
    (or a future Pattern-B engine that doesn't share it lands here).
    """

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS dbgpt_schema;",
            reverse_sql="DROP SCHEMA IF EXISTS dbgpt_schema CASCADE;",
        ),
    ]
