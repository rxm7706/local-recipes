from datetime import date

from django_pyforge.portals import PortalConfig


class StewardPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_steward_portal"
    label = "steward_portal"
    verbose_name = "Steward portal"
    default = True

    station_name = "steward"
    mount_token = "/stations/steward/"  # noqa: S105
    mcp_token = "mcp:steward"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "steward"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_steward_portal.urls"
