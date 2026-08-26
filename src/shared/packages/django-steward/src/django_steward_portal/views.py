from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django_pyforge.access import require_station_role
from django_pyforge.assertion.client import PortalClient


@require_GET
@require_station_role("steward")
def chrome_home(request: HttpRequest) -> HttpResponse:
    environments = PortalClient().provision_list()
    return render(
        request,
        "steward_portal/home.html",
        {
            "environments": [
                {"name": name, "features": list(features)}
                for name, features in sorted(environments.items())
            ],
        },
    )
