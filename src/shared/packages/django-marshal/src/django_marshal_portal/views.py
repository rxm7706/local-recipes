from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient


@require_GET
@require_station_role("marshal")
def chrome_home(request: HttpRequest) -> HttpResponse:
    homes = PortalClient().list_loop_homes()
    return render(request, "marshal_portal/home.html", {"loop_homes": homes})
