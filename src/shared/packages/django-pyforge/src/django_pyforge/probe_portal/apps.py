"""Fixture portal AppConfig (Story 18.1 proof only)."""

from __future__ import annotations

from datetime import date

from django_pyforge.portals import PortalConfig


class ChromeProbeConfig(PortalConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_pyforge.probe_portal"
    label = "chrome_probe"
    verbose_name = "Chrome probe portal"
    default = True

    station_name = "chrome-probe"
    mount_token = "/stations/chrome-probe/"
    mcp_token = "mcp:chrome-probe"
    chrome_hooks = ("layout",)
    owner_slug = "chrome-probe"
    backup = "pyforge-steward"
    work_class = "03"
    promotion_date = date(2026, 8, 24)
    urlconf = "django_pyforge.probe_portal.urls"
