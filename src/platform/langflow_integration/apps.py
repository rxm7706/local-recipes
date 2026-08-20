from django.apps import AppConfig


class LangflowIntegrationConfig(AppConfig):
    """Migration-only app: provisions `langflow_schema` (Story 11.1, AD-5).

    No models -- Django's ORM never creates tables in `langflow_schema`,
    Langflow's own Alembic migrations own everything inside it. This app
    exists solely so its `RunSQL` migration (0001) runs as part of
    `manage.py migrate`, and so `langflow_integration/asgi.py` (which builds
    the actual Langflow ASGI app) has a natural home next to it.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "langflow_integration"
    verbose_name = "Langflow Integration"
