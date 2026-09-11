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
        from django_mason_portal.boot_reconcile import run_mason_boot_reconcile
        from django_mason_portal.diagnose import last_diagnose
        from django_mason_portal.mcp_asgi import ensure_mason_runner  # noqa: PLC0415
        from django_pyforge.assertion.client import LAST_DIAGNOSE_TOOL
        from django_pyforge.assertion.client import register_portal_job

        register_portal_job(self.station_name, LAST_DIAGNOSE_TOOL, last_diagnose)
        ensure_mason_runner()
        from django.db.utils import OperationalError
        from django.db.utils import ProgrammingError

        try:
            run_mason_boot_reconcile()
        except (OperationalError, ProgrammingError):
            # Boot reconcile needs PostgreSQL (collectstatic, early test
            # collection, or a not-yet-ready socket). Production pods start
            # after migrate + DB readiness.
            pass

    def mcp_asgi_app(self):
        from django_mason_portal.mcp_asgi import build_mason_mcp_asgi  # noqa: PLC0415

        return build_mason_mcp_asgi()
