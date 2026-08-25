"""Discover registered station portals from installed AppConfigs."""

from __future__ import annotations

from collections.abc import Iterator

from django.apps import apps

from django_pyforge.portals import PortalConfig


def iter_portal_configs() -> Iterator[PortalConfig]:
    """Yield portal AppConfigs. Discovery is ``apps.get_app_configs()`` only."""
    for config in apps.get_app_configs():
        if isinstance(config, PortalConfig):
            yield config
