"""Story 91.1: optional /stations/ index (flagged)."""

from __future__ import annotations

import importlib

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django_pyforge.context_processors import is_switcher_tile
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.flags import evaluate_boolean
from django_pyforge.roles import roles_from_request
from wagtail.views import serve as wagtail_serve

from config import optional_components

STATIONS_INDEX_FLAG = "pyforge.steward.stations_index"


def stations_index(request: HttpRequest) -> HttpResponse:
    if not evaluate_boolean(STATIONS_INDEX_FLAG, default=False):
        return wagtail_serve(request, "stations/")

    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])

    roles = roles_from_request(request)
    if not roles:
        return HttpResponseForbidden()

    importlib.import_module("config.station_api")

    rows: list[dict[str, object]] = []
    for portal in sorted(iter_portal_configs(), key=lambda p: p.station_name):
        if not is_switcher_tile(portal, roles):
            continue
        name = portal.station_name
        reason = optional_components.absent_reason(name)
        rows.append(
            {
                "station_name": name,
                "absent": reason is not None,
                "reason": reason or "",
                "mount_path": f"/stations/{name}/",
            },
        )

    return render(request, "stations/index.html", {"rows": rows})
