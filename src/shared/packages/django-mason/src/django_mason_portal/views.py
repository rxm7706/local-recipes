from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.roles import claims_from_request
from django_pyforge.roles import roles_from_request


def _operator_sub(request: HttpRequest) -> str:
    claims = claims_from_request(request) or {}
    raw = claims.get(CLAIM_SUB)
    if isinstance(raw, str) and raw.strip():
        return raw
    return "operator"


@require_GET
@require_station_role("mason")
def chrome_home(request: HttpRequest) -> HttpResponse:
    diagnosis = PortalClient().last_diagnose(
        _operator_sub(request),
        list(roles_from_request(request)),
        "mason",
    )
    return render(request, "mason_portal/home.html", {"diagnosis": diagnosis})
