from datetime import date

from django_pyforge.portals import PortalConfig


class HeraldPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_herald_portal"
    label = "herald_portal"
    verbose_name = "Herald portal"
    default = True

    station_name = "herald"
    mount_token = "/stations/herald/"  # noqa: S105
    mcp_token = "mcp:herald"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "herald"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_herald_portal.urls"

    def mcp_asgi_app(self):
        from django_pyforge.mcp_http import asgi_for_station  # noqa: PLC0415

        return asgi_for_station(self.station_name)
