from datetime import date

from django_pyforge.portals import PortalConfig


class WardenFabricConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_warden_fabric"
    label = "warden_fabric"
    verbose_name = "Warden fabric portal"
    default = True

    station_name = "warden"
    mount_token = "/stations/warden/"  # noqa: S105
    mcp_token = "mcp:warden"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "warden"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 22)
    urlconf = "django_warden_fabric.portal_urls"
