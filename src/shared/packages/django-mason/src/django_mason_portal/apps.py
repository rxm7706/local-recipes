from datetime import date

from django_pyforge.portals import PortalConfig


class MasonPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_mason_portal"
    label = "mason_portal"
    verbose_name = "Mason portal"
    default = True

    station_name = "mason"
    mount_token = "/stations/mason/"  # noqa: S105
    mcp_token = "mcp:mason"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "mason"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_mason_portal.urls"

    def ready(self) -> None:
        from django_mason_portal.diagnose import last_diagnose
        from django_pyforge.assertion.client import LAST_DIAGNOSE_TOOL
        from django_pyforge.assertion.client import register_portal_job

        register_portal_job(self.station_name, LAST_DIAGNOSE_TOOL, last_diagnose)

    def mcp_asgi_app(self):
        from django_pyforge.mcp_http import asgi_for_station  # noqa: PLC0415

        return asgi_for_station(self.station_name)
