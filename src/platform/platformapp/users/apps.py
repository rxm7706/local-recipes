import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "platformapp.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import platformapp.users.signals  # noqa: F401, PLC0415

        # CAP-3 / steward 16.2: stage-2 refusal contract (DEBUG / local-settings
        # escape). Deployed-only; sentinel set even when local so wiring is
        # observable under CI.
        from config.startup import run_stage_two  # noqa: PLC0415

        run_stage_two()

        from config.station_port import wire_station_port  # noqa: PLC0415

        wire_station_port()
