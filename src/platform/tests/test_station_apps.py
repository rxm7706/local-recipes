"""Story 127.1: the host installs the station apps its portal packages declare.

Steward's corridor duties (load, passport, quarantine, glass) keep their
records in ``pyforge.steward.dashboard``'s models. The ``django-steward``
portal declares that app for the host, so its tables migrate into the
platform's database and Liquibase carries their production DDL.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.db.migrations.loader import MigrationLoader

from config.settings import base
from db import sqlmigrate_extraction

if TYPE_CHECKING:
    import pytest

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
STEWARD_STATION_APPS = (
    REPO_ROOT
    / "src/shared/packages/django-steward/src/django_steward_portal/station_apps.py"
)
CORRIDOR_LABEL = "pyforge_steward_dashboard"
CORRIDOR_MIGRATIONS = 8  # 0001_initial .. 0008_quarantineshelfrow


def test_the_corridor_app_is_installed_after_the_steward_portal() -> None:
    installed = list(settings.INSTALLED_APPS)
    assert "pyforge.steward.dashboard" in installed
    assert installed.index("pyforge.steward.dashboard") > installed.index(
        "django_steward_portal"
    )
    assert apps.get_app_config(CORRIDOR_LABEL).name == "pyforge.steward.dashboard"


def test_the_corridor_models_belong_to_the_installed_app() -> None:
    models = {
        model.__name__ for model in apps.get_app_config(CORRIDOR_LABEL).get_models()
    }
    assert {
        "AuditEntry",
        "WorkPassport",
        "CorridorLoad",
        "QuarantineShelfRow",
    } <= models


def test_the_corridor_migrations_are_in_the_host_migration_plan() -> None:
    loader = MigrationLoader(None, ignore_no_migrations=True)
    names = sorted(
        name for label, name in loader.disk_migrations if label == CORRIDOR_LABEL
    )
    assert names[0] == "0001_initial"
    assert len(names) == CORRIDOR_MIGRATIONS


def test_every_corridor_migration_maps_to_a_steward_changeset() -> None:
    migration_map = sqlmigrate_extraction.load_map()
    index = sqlmigrate_extraction.parse_changeset_index()
    loader = MigrationLoader(None, ignore_no_migrations=True)
    for label, name in loader.disk_migrations:
        if label != CORRIDOR_LABEL:
            continue
        found = migration_map.lookup(f"{label}.{name}")
        assert found is not None, f"{label}.{name} has no sqlmigrate-map.yaml entry"
        distribution, seq = found
        assert distribution == "pyforge-steward"
        assert f"{distribution}:{seq}" in index


def test_a_station_app_migration_counts_as_first_party() -> None:
    migration = REPO_ROOT / (
        "src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/migrations/0001_initial.py"
    )
    assert sqlmigrate_extraction.is_first_party_migration_module(str(migration))


def test_a_portal_without_a_station_apps_module_declares_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        base, "_STATION_PORTAL_PACKAGES", (("django-doctor", "django_doctor_portal"),)
    )
    assert base.declared_station_apps() == []


def test_a_missing_portal_declares_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        base, "_STATION_PORTAL_PACKAGES", (("django-nowhere", "django_nowhere_portal"),)
    )
    assert base.declared_station_apps() == []


def test_the_steward_portal_declares_the_corridor_app_by_name_only() -> None:
    tree = ast.parse(STEWARD_STATION_APPS.read_text(encoding="utf-8"))
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert all(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        for node in imports
    )
    assert base.declared_station_apps() == ["pyforge.steward.dashboard"]
