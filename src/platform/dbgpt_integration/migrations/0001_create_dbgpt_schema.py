from django.db import migrations


class Migration(migrations.Migration):
    """Provisions `dbgpt_schema` -- AD-5 schema isolation, real not conventional.

    `CREATE SCHEMA IF NOT EXISTS` makes this idempotent, mirroring
    `langflow_integration`'s `0001_create_langflow_schema` (Story 11.1). This
    is a `RunSQL` migration, not a model migration: Django's ORM never
    creates tables inside `dbgpt_schema` -- everything inside it belongs to
    DB-GPT's own Alembic migrations, which (per this app's design) would run
    at ASGI lifespan startup against `DBGPT_DATABASE_URL`
    (`config/settings/base.py`), never against `manage.py migrate`.

    This migration is real, independent groundwork: it does not depend on
    DB-GPT's FastAPI app being importable at all, unlike the ASGI mount
    itself (see this story's Design Notes -- CAP-3's mount is BLOCKED,
    `db-gpt not pluggable as ASGI mount`, a verified upstream `fastapi`
    version conflict between `dbgpt-client` and `langflow-base`). Landing the
    schema now costs nothing and is needed regardless of whether CAP-3 is
    eventually delivered via a fixed Pattern A or a dated sidecar deviation.
    """

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS dbgpt_schema;",
            reverse_sql="DROP SCHEMA IF EXISTS dbgpt_schema CASCADE;",
        ),
    ]
