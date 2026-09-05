"""Lane 1 console homes + supervisor run board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django_pyforge.non_atomic import non_atomic_view
from django_pyforge.supervisor import SupervisorUnavailableError
from django_pyforge.supervisor import query_board
from wagtail.models import Page

from platformapp.front_door.console_parity import HOMES
from platformapp.front_door.console_parity import directory_rows
from platformapp.front_door.console_parity import require_parity_homes
from platformapp.front_door.detector_jobs import cache_age_label
from platformapp.front_door.models import ConsoleEditorialPage
from platformapp.front_door.models import DetectorVerdict
from platformapp.front_door.runtime_catalog import catalog_entries

if TYPE_CHECKING:
    from datetime import datetime

    from django.http import HttpRequest
    from django.http import HttpResponse

TEMPLATE = "front_door/runs.html"
CATALOG_SURFACES = frozenset(
    {
        "dreams",
        "specs",
        "story_specs",
        "guild",
        "backlog",
        "open_work",
        "archived",
        "program_story_status",
        "in_build_realized_membership",
    },
)


def age_label(last_ok_at: datetime | None, *, now: datetime) -> str:
    if last_ok_at is None:
        return "never"
    seconds = max(0, int((now - last_ok_at).total_seconds()))
    return f"{seconds}s"


@non_atomic_view
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


def console_directory(request: HttpRequest) -> HttpResponse:
    require_parity_homes()
    return render(
        request,
        "front_door/console_directory.html",
        {"rows": directory_rows()},
    )


def console_health(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    rows = list(DetectorVerdict.objects.order_by("detector"))
    oldest = min((row.captured_at for row in rows), default=None)
    return render(
        request,
        "front_door/console_health.html",
        {
            "rows": rows,
            "age": cache_age_label(oldest, now=now),
            "health": "empty" if not rows else "cached",
        },
    )


def console_editorial(request: HttpRequest) -> HttpResponse:
    pages = Page.objects.type(ConsoleEditorialPage).live().specific().order_by("title")
    return render(
        request,
        "front_door/console_editorial.html",
        {"pages": pages},
    )


def console_catalog(request: HttpRequest, surface_id: str) -> HttpResponse:
    if surface_id not in CATALOG_SURFACES:
        raise Http404
    home = HOMES[surface_id]
    return render(
        request,
        "front_door/console_catalog.html",
        {
            "surface_id": surface_id,
            "home": home,
            "entries": catalog_entries(surface_id),
        },
    )
