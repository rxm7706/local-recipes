"""Start a fleet scan run (Story 16.2)."""

from __future__ import annotations

import sys

from django.core.management.base import BaseCommand
from pyforge.core.flags import FlagOff
from pyforge.core.flags import disabled_help
from pyforge.core.flags import require

from django_warden_fabric.fleet import FLEET_SCAN_FLAG
from django_warden_fabric.models import FleetRun
from django_warden_fabric.models import JobStatus
from django_warden_fabric.tasks import run_fleet_run


class Command(BaseCommand):
    help = disabled_help(
        "Run warden scan across every inventoried repo in an organisation",
        FLEET_SCAN_FLAG,
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "organisation",
            help="GHE organisation slug whose FleetRepo rows to scan",
        )

    def handle(self, *args, **options) -> None:
        try:
            require(FLEET_SCAN_FLAG)
        except FlagOff as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc
        organisation: str = options["organisation"]
        run = FleetRun.objects.create(
            organisation=organisation,
            status=JobStatus.PENDING,
        )
        run_fleet_run.delay(str(run.pk))
        self.stdout.write(str(run.pk))
