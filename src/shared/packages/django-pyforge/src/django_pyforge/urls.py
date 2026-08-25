"""Mount discovered portals under the host's ``stations/`` prefix.

The host URLconf includes this module once. Station names come from
AppConfig discovery, never from a host-side roster.
"""

from __future__ import annotations

from django.urls import include
from django.urls import path

from django_pyforge.discovery import iter_portal_configs

urlpatterns = [
    path(f"{portal.station_name}/", include(portal.urlconf))
    for portal in iter_portal_configs()
]
