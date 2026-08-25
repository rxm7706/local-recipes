from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def chrome_home(request: HttpRequest) -> HttpResponse:
    return render(request, "probe_portal/home.html")
