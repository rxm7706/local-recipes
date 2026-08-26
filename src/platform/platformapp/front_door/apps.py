from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

from platformapp.users.provisioning import provision_designated_groups


def _provision_wagtail_admin_group(sender: AppConfig, **kwargs: object) -> None:
    provision_designated_groups()


def _seed_detector_schedule(sender: AppConfig, **kwargs: object) -> None:
    from platformapp.front_door.detector_jobs import (  # noqa: PLC0415
        seed_detector_schedule,
    )

    seed_detector_schedule()


def _seed_lane1_homepage(sender: AppConfig, **kwargs: object) -> None:
    from platformapp.front_door.lane1_seed import seed_lane1_homepage  # noqa: PLC0415

    seed_lane1_homepage()


class FrontDoorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platformapp.front_door"
    label = "front_door"
    verbose_name = _("Front door")

    def ready(self) -> None:
        post_migrate.connect(
            _provision_wagtail_admin_group,
            sender=self,
            dispatch_uid="front_door.provision_wagtail_admin_group",
        )
        post_migrate.connect(
            _seed_detector_schedule,
            sender=self,
            dispatch_uid="front_door.seed_detector_schedule",
        )
        post_migrate.connect(
            _seed_lane1_homepage,
            sender=self,
            dispatch_uid="front_door.seed_lane1_homepage",
        )
