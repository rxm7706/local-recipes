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

    def ready(self) -> None:
        from django_warden_fabric.mcp_asgi import ensure_warden_runner  # noqa: PLC0415

        ensure_warden_runner()

    def mcp_asgi_app(self):
        from django_warden_fabric.mcp_asgi import build_warden_mcp_asgi  # noqa: PLC0415

        return build_warden_mcp_asgi()
