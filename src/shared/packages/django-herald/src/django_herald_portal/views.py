from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.roles import claims_from_request, roles_from_request

PORTAL_DECK_SLUG = "pyforge-herald"
DECK_STATUS_ARGV = ("deck", "status", PORTAL_DECK_SLUG)


def _portal_sub(request: HttpRequest) -> str:
    claims = claims_from_request(request) or {}
    sub = claims.get(CLAIM_SUB)
    if isinstance(sub, str) and sub.strip():
        return sub.strip()
    user = getattr(request, "user", None)
    username = getattr(user, "username", "") if user is not None else ""
    if isinstance(username, str) and username.strip():
        return username.strip()
    return "operator"


@require_GET
@require_station_role("herald")
def chrome_home(request: HttpRequest) -> HttpResponse:
    deck_status = PortalClient().invoke(
        sub=_portal_sub(request),
        roles=list(roles_from_request(request)),
        station="herald",
        argv=list(DECK_STATUS_ARGV),
    )
    return render(request, "herald_portal/home.html", {"deck_status": deck_status})
