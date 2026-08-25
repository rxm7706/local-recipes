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
