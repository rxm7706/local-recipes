from datetime import date

from django_pyforge.portals import PortalConfig


class ScribePortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_scribe_portal"
    label = "scribe_portal"
    verbose_name = "Scribe portal"
    default = True

    station_name = "scribe"
    mount_token = "/stations/scribe/"  # noqa: S105
    mcp_token = "mcp:scribe"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "scribe"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_scribe_portal.urls"
