"""Refresh fleet repo inventory from github.com (Story 16.1)."""

from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand
from pyforge.core.flags import FlagOff, disabled_help, require

from django_warden_fabric.fleet import FLEET_INVENTORY_FLAG
from django_warden_fabric.fleet_inventory import FleetInventoryError, load_organisation_from_config
from django_warden_fabric.tasks import run_fleet_inventory


class Command(BaseCommand):
    help = disabled_help(
        "Inventory every repo in the operator-designated github.com organisation",
        FLEET_INVENTORY_FLAG,
    )

    def handle(self, *args, **options) -> None:
        try:
            require(FLEET_INVENTORY_FLAG)
        except FlagOff as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc
        try:
            organisation = load_organisation_from_config()
        except FleetInventoryError as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(1) from exc
        run_id = uuid.uuid4()
        run_fleet_inventory.delay(str(run_id), organisation)
        self.stdout.write(str(run_id))
