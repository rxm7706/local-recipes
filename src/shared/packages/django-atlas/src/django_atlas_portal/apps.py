from datetime import date

from django_pyforge.portals import PortalConfig


class AtlasPortalConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_atlas_portal"
    label = "atlas_portal"
    verbose_name = "Atlas portal"
    default = True

    station_name = "atlas"
    mount_token = "/stations/atlas/"  # noqa: S105
    mcp_token = "mcp:atlas"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "atlas"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_atlas_portal.urls"

    def mcp_asgi_app(self):
        from django_atlas_portal.mcp_asgi import build_atlas_mcp_asgi

        return build_atlas_mcp_asgi()
