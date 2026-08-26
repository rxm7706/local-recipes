from __future__ import annotations

from typing import Any

from django.db.models import F
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient
from django_pyforge.models import RunState
from django_pyforge.roles import claims_from_request
from django_pyforge.roles import roles_from_request
from django_pyforge.supervisor import ATLAS_STATION

_DEFAULT_SUB = "atlas-portal"


def _subject(request: HttpRequest) -> str:
    claims = claims_from_request(request)
    if claims is not None:
        sub = claims.get("sub")
        if isinstance(sub, str) and sub.strip():
            return sub
    return _DEFAULT_SUB


def _idle_inventory_row() -> dict[str, Any]:
    return {
        "run_id": "",
        "station": ATLAS_STATION,
        "status": "idle",
        "started_at": None,
        "heartbeat_at": None,
        "completed_at": None,
        "duration_ms": None,
    }


def _public_row(row: RunState) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "station": row.station,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "heartbeat_at": row.heartbeat_at.isoformat() if row.heartbeat_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "duration_ms": row.duration_ms,
    }


def load_atlas_inventory_row() -> dict[str, Any]:
    row = (
        RunState.objects.filter(station=ATLAS_STATION)
        .order_by(F("started_at").desc(nulls_last=True), "-id")
        .first()
    )
    if row is None:
        return _idle_inventory_row()
    return _public_row(row)


@require_GET
@require_station_role("atlas")
def chrome_home(request: HttpRequest) -> HttpResponse:
    PortalClient().emit(
        _subject(request),
        list(roles_from_request(request)),
        ATLAS_STATION,
    )
    return render(
        request,
        "atlas_portal/home.html",
        {"inventory_row": load_atlas_inventory_row()},
    )
