from http import HTTPStatus

from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods

from django_pyforge.access import require_station_role
from django_pyforge.form_errors import PydanticFormErrorBridge
from django_pyforge.forms import VersionForm

# FastAPI RequestValidationError shape for loc ["body", "version"].
REJECTED_422 = {
    "detail": [
        {
            "type": "value_error",
            "loc": ["body", "version"],
            "msg": "version is not a valid PEP 440 string",
        }
    ]
}


@require_GET
@require_station_role("chrome-probe")
def chrome_home(request: HttpRequest) -> HttpResponse:
    return render(request, "probe_portal/home.html")


@require_http_methods(["GET", "POST"])
@require_station_role("chrome-probe")
def chrome_form(request: HttpRequest) -> HttpResponse:
    """Originating HTMX surface: a rejected API 422 renders inline field errors."""
    if request.method == "POST":
        form = VersionForm(request.POST)
        PydanticFormErrorBridge().apply(form, REJECTED_422)
        status = HTTPStatus.UNPROCESSABLE_ENTITY
    else:
        form = VersionForm()
        status = HTTPStatus.OK
    hx_request = request.headers.get("HX-Request")
    template = "django_pyforge/htmx_form.html" if hx_request else "probe_portal/form.html"
    return render(request, template, {"form": form}, status=status)
