"""Chrome context: switcher lists only stations this request may reach.

Discovery stays unfiltered (URLconf/checks). Reachability is IdP roles on
this request (canopy AD-15). Work class 01/02 registrations are not tiled.
The switcher is not enforcement.
"""

from __future__ import annotations

from django.http import HttpRequest

from django_pyforge.discovery import iter_portal_configs
from django_pyforge.roles import roles_from_request
from django_pyforge.sidecars import mybmad_sidecar

_SWITCHER_HIDDEN_WORK_CLASSES = frozenset({"01", "02"})


def is_switcher_tile(portal: object, roles: frozenset[str]) -> bool:
    """True when chrome may list this registration as a first-class station."""
    name = getattr(portal, "station_name", None)
    work_class = getattr(portal, "work_class", None)
    return name in roles and work_class not in _SWITCHER_HIDDEN_WORK_CLASSES


def chrome(request: HttpRequest) -> dict[str, object]:
    roles = roles_from_request(request)
    return {
        "pyforge_portals": [
            portal
            for portal in iter_portal_configs()
            if is_switcher_tile(portal, roles)
        ],
        # Same OIDC session as station tiles. Not a portal; process stays sidecar.
        "pyforge_sidecars": [mybmad_sidecar()] if roles else [],
    }
