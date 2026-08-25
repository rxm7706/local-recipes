"""AppConfig for the chrome package (canopy AD-1 / AD-3)."""

from __future__ import annotations

from django.apps import AppConfig


class DjangoPyforgeConfig(AppConfig):
    """The chrome package itself is not a station portal."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_pyforge"
    label = "django_pyforge"
    verbose_name = "PyForge chrome"
    default = True

    def ready(self) -> None:
        from django_pyforge import checks as _checks  # noqa: PLC0415

        _ = _checks
        try:
            from django_pyforge.flags import configure_from_env  # noqa: PLC0415
        except ImportError:
            return
        configure_from_env()
