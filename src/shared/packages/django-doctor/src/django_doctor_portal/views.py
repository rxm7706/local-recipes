from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django_doctor_portal.pulse import last_fleet_pulse
from django_pyforge.access import require_station_role


@require_GET
@require_station_role("doctor")
def chrome_home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "doctor_portal/home.html",
        {"pulse": last_fleet_pulse(request)},
    )
