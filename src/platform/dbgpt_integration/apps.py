from django.apps import AppConfig


class DbgptIntegrationConfig(AppConfig):
    """Migration-only app: provisions `dbgpt_schema` (Story 11.2, AD-5/AD-17).

    No models -- Django's ORM never creates tables in `dbgpt_schema`. Unlike
    `langflow_integration` (Pattern A, Story 11.1), this app does NOT own an
    `asgi.py`: DB-GPT is configured to Pattern B (AD-17, `dbgpt: B`) -- its
    own sidecar container, built by Story 10.5 (`src/platform/compose/dbgpt/`)
    and reached over Celery/REST (`dbgpt_integration/tasks.py`), never an
    ASGI mount. `config/engine_patterns.py` is the single source of truth for
    that pattern choice; `config/asgi.py` consults it and builds no DB-GPT
    ASGI sub-app.

    DB-GPT's own state, unlike Langflow's, does NOT land in `dbgpt_schema`
    today: verified live (Story 11.2) that `dbgpt_app`'s own metadata-store
    layer (`dbgpt_app/base.py::_initialize_db_storage`,
    `dbgpt_app/_cli.py::_get_migration_config`) hardcodes SQLite/MySQL/
    OceanBase as the only supported `[service.web.database]` backends, and a
    manual `db.create_all()` against a real PostgreSQL engine (DB-GPT's own
    public `dbgpt.storage.metadata.db_manager` API, not a fork) fails with a
    genuine DDL syntax error (`psycopg2.errors.SyntaxError: type modifier is
    not allowed for type "text"`) because DB-GPT's own SQLAlchemy models use
    MySQL-specific `TEXT(length)` column definitions PostgreSQL's grammar
    rejects -- 69 occurrences repo-wide in the installed `dbgpt-sidecar`
    package set, not a one-off. This is a genuine, dual-confirmed upstream
    limitation (AD-9 forbids forking DB-GPT's own model classes to fix it),
    so the sidecar's OWN metadata store stays on Story 10.5's SQLite volume
    -- see `src/platform/compose/compose.yml`'s `dbgpt` service and
    `src/platform/compose/dbgpt/Containerfile` for the full citation. This
    app's `RunSQL` migration (0001) still provisions `dbgpt_schema` for real
    (the schema-isolation half of AD-5 that DOES hold, independent of that
    blocker), so `manage.py migrate` creates it and future work (an upstream
    fix, or a different Pattern-B engine) has it ready.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "dbgpt_integration"
    verbose_name = "DB-GPT Integration"
