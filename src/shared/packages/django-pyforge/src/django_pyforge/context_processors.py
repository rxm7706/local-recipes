"""Chrome context: discovered portals for the switcher (roles are S-18.2)."""

from __future__ import annotations

from django.http import HttpRequest

from django_pyforge.discovery import iter_portal_configs


def chrome(request: HttpRequest) -> dict[str, object]:
    _ = request
    return {"pyforge_portals": list(iter_portal_configs())}
