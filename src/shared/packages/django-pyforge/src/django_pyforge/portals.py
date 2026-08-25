"""Registration protocol a station portal implements (canopy AD-1).

SLA body is not a chrome field — do not add ``sla_body`` here.
"""

from __future__ import annotations

from datetime import date

from django.apps import AppConfig


class PortalConfig(AppConfig):
    """Portal AppConfig base. Not itself an installed app (default=False)."""

    default = False
    station_name: str
    mount_token: str
    mcp_token: str
    chrome_hooks: tuple[str, ...] = ()
    owner_slug: str
    backup: str
    work_class: str
    promotion_date: date
    urlconf: str

    def mcp_asgi_app(self):  # noqa: PLR6301 -- optional hook; default is no MCP face
        """Return a Streamable HTTP ASGI app, or ``None`` until the station registers one."""
        return None
