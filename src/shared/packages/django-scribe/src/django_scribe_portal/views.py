from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django_pyforge.access import require_station_role


@require_GET
@require_station_role("scribe")
def chrome_home(request: HttpRequest) -> HttpResponse:
    return render(request, "scribe_portal/home.html")
