"""Refresh the project-item inventory from github.com Projects (Story 16.5)."""

from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand
from pyforge.core.flags import FlagOff, disabled_help, require

from django_warden_fabric.fleet import FLEET_PROJECT_ITEMS_FLAG
from django_warden_fabric.fleet_inventory import FleetInventoryError, load_organisation_from_config
from django_warden_fabric.fleet_project_items import load_project_numbers_from_config
from django_warden_fabric.tasks import run_fleet_project_items


class Command(BaseCommand):
    help = disabled_help(
        "Inventory the items of the operator-designated github.com Projects",
        FLEET_PROJECT_ITEMS_FLAG,
    )

    def handle(self, *args, **options) -> None:
        try:
            require(FLEET_PROJECT_ITEMS_FLAG)
        except FlagOff as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc
        try:
            organisation = load_organisation_from_config()
            # Checked here so a bad config fails before enqueue; the worker reads it again.
            load_project_numbers_from_config()
        except FleetInventoryError as exc:
            self.stderr.write(f"{exc}\n")
            raise SystemExit(1) from exc
        run_id = uuid.uuid4()
        run_fleet_project_items.delay(str(run_id), organisation)
        self.stdout.write(str(run_id))
