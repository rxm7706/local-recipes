from django.apps import AppConfig


class DbgptIntegrationConfig(AppConfig):
    """Migration-only app: provisions `dbgpt_schema` (Story 11.2, AD-5).

    No models -- Django's ORM never creates tables in `dbgpt_schema`,
    DB-GPT's own Alembic migrations own everything inside it (see this
    story's Design Notes for why that Alembic bootstrap could not actually
    be driven in this environment -- CAP-3 is BLOCKED, not delivered). This
    app exists solely so its `RunSQL` migration (0001) runs as part of
    `manage.py migrate`, mirroring `langflow_integration.apps.
    LangflowIntegrationConfig` (Story 11.1) -- the schema-isolation
    scaffolding that is real and independent of the blocked ASGI mount.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "dbgpt_integration"
    verbose_name = "DB-GPT Integration"
