from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django_pyforge.access import require_station_role
from django_pyforge.assertion import PortalClient
from django_pyforge.roles import claims_from_request, roles_from_request
from django_scribe_portal.recall_submit import submit_recall


def _caller_sub(request: HttpRequest) -> str:
    claims = claims_from_request(request)
    if claims:
        sub = claims.get("sub")
        if isinstance(sub, str) and sub.strip():
            return sub
    user = getattr(request, "user", None)
    name = getattr(user, "username", None) or getattr(user, "pk", None)
    if name:
        return str(name)
    return "scribe-operator"


@require_http_methods(["GET", "POST"])
@require_station_role("scribe")
def chrome_home(request: HttpRequest) -> HttpResponse:
    query = ""
    results = None
    if request.method == "POST":
        query = str(request.POST.get("query", ""))
        results = submit_recall(
            PortalClient(),
            query,
            sub=_caller_sub(request),
            roles=sorted(roles_from_request(request)),
        )
    context = {"query": query, "results": results}
    hx_request = request.headers.get("HX-Request")
    if hx_request and request.method == "POST":
        return render(request, "scribe_portal/results.html", context)
    return render(request, "scribe_portal/home.html", context)
