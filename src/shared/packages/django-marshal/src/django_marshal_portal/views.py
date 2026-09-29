from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django_marshal_portal.mcp_asgi import WATCH_TOOL
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient


@require_GET
@require_station_role("marshal")
def chrome_home(request: HttpRequest) -> HttpResponse:
    homes = PortalClient().list_loop_homes()
    return render(request, "marshal_portal/home.html", {"loop_homes": homes})


@require_GET
@require_station_role("marshal")
def watch_report(request: HttpRequest) -> HttpResponse:
    """Render ``marshal watch`` for a selected project/run/fleet (Story 44.4)."""
    project = (request.GET.get("project") or "").strip() or None
    run = (request.GET.get("run") or "").strip() or None
    fleet = request.GET.get("fleet") in {"1", "true", "on", "yes"}
    roles = list(getattr(request, "idp_roles", []) or [])
    sub = getattr(request, "idp_sub", None) or "marshal-portal"
    report = PortalClient().call(
        "marshal",
        WATCH_TOOL,
        {"project": project, "run": run, "fleet": fleet},
        sub=str(sub),
        roles=roles,
    )
    return render(
        request,
        "marshal_portal/watch.html",
        {
            "report": report,
            "project": project,
            "run": run,
            "fleet": fleet,
        },
    )
