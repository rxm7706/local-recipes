"""Chrome context: switcher lists only stations this request may reach.

Discovery stays unfiltered (URLconf/checks). Reachability is IdP roles on
this request (canopy AD-15). The switcher is not enforcement.
"""

from __future__ import annotations

from django.http import HttpRequest

from django_pyforge.discovery import iter_portal_configs
from django_pyforge.roles import roles_from_request


def chrome(request: HttpRequest) -> dict[str, object]:
    roles = roles_from_request(request)
    return {
        "pyforge_portals": [
            portal for portal in iter_portal_configs() if portal.station_name in roles
        ],
    }
