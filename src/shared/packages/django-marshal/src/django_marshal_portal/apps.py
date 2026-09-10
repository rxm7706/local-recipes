from datetime import date

from django_pyforge.portals import PortalConfig


class MarshalPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_marshal_portal"
    label = "marshal_portal"
    verbose_name = "Marshal portal"
    default = True

    station_name = "marshal"
    mount_token = "/stations/marshal/"  # noqa: S105
    mcp_token = "mcp:marshal"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "marshal"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_marshal_portal.urls"

    def ready(self) -> None:
        from django_marshal_portal.mcp_asgi import ensure_marshal_runner  # noqa: PLC0415

        ensure_marshal_runner()

    def mcp_asgi_app(self):
        from django_marshal_portal.mcp_asgi import build_marshal_mcp_asgi  # noqa: PLC0415

        return build_marshal_mcp_asgi()
