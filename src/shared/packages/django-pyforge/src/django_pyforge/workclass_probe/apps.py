"""Fixture portal AppConfig with work_class 01 (Story 19.2 switcher matrix)."""

from __future__ import annotations

from datetime import date

from django_pyforge.portals import PortalConfig


class InfraProbeConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_pyforge.workclass_probe"
    label = "infra_probe"
    verbose_name = "Infra probe portal"
    default = True

    station_name = "infra-probe"
    mount_token = "/stations/infra-probe/"  # noqa: S105
    mcp_token = "mcp:infra-probe"  # noqa: S105
    chrome_hooks = ("layout",)
    owner_slug = "infra-probe"
    backup = "pyforge-steward"
    work_class = "01"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_pyforge.workclass_probe.urls"
