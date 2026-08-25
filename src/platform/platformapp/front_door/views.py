"""Front door run board — supervisor API only (FR-40, FR-42)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import render
from django.utils import timezone
from django_pyforge.supervisor import SupervisorUnavailableError
from django_pyforge.supervisor import query_board

if TYPE_CHECKING:
    from datetime import datetime

    from django.http import HttpRequest
    from django.http import HttpResponse

TEMPLATE = "front_door/runs.html"


def age_label(last_ok_at: datetime | None, *, now: datetime) -> str:
    if last_ok_at is None:
        return "never"
    seconds = max(0, int((now - last_ok_at).total_seconds()))
    return f"{seconds}s"


def runs_board(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    try:
        snapshot = query_board()
    except SupervisorUnavailableError as exc:
        return render(
            request,
            TEMPLATE,
            {
                "board": "unavailable",
                "age": age_label(exc.last_ok_at, now=now),
                "live": (),
                "timing": (),
            },
        )
    return render(
        request,
        TEMPLATE,
        {
            "board": "current",
            "age": age_label(snapshot.last_ok_at, now=snapshot.queried_at),
            "live": snapshot.live,
            "timing": snapshot.timing,
        },
    )
