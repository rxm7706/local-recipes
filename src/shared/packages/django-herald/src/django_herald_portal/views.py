from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.flags import evaluate_boolean
from django_pyforge.roles import claims_from_request, roles_from_request

from django_herald_portal.deck_viewer import list_published_decks, viewer_context

PORTAL_DECK_SLUG = "pyforge-herald"
DECK_VIEWER_FLAG = "pyforge.herald.deck_viewer"
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


def _deck_viewer_enabled() -> bool:
    return evaluate_boolean(DECK_VIEWER_FLAG, default=False)


@require_GET
@require_station_role("herald")
def chrome_home(request: HttpRequest) -> HttpResponse:
    deck_status = PortalClient().invoke(
        sub=_portal_sub(request),
        roles=list(roles_from_request(request)),
        station="herald",
        argv=list(DECK_STATUS_ARGV),
    )
    return render(
        request,
        "herald_portal/home.html",
        {
            "deck_status": deck_status,
            "deck_viewer_enabled": _deck_viewer_enabled(),
        },
    )


@require_GET
@require_station_role("herald")
def deck_list(request: HttpRequest) -> HttpResponse:
    if not _deck_viewer_enabled():
        raise Http404
    decks = list_published_decks()
    return render(request, "herald_portal/deck_list.html", {"decks": decks})


@require_GET
@require_station_role("herald")
def deck_view(request: HttpRequest, slug: str) -> HttpResponse:
    if not _deck_viewer_enabled():
        raise Http404
    context = viewer_context(slug)
    if context is None:
        raise Http404
    return render(request, "herald_portal/deck_view.html", {"deck": context})
