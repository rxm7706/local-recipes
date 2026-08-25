from datetime import date

from django_pyforge.portals import PortalConfig


class DoctorPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_doctor_portal"
    label = "doctor_portal"
    verbose_name = "Doctor portal"
    default = True

    station_name = "doctor"
    mount_token = "/stations/doctor/"  # noqa: S105
    mcp_token = "mcp:doctor"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "doctor"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_doctor_portal.urls"

    def mcp_asgi_app(self):
        from django_pyforge.mcp_http import asgi_for_station  # noqa: PLC0415

        return asgi_for_station(self.station_name)
