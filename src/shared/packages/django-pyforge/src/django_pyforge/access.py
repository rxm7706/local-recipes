"""Station-view enforcement. The switcher is not the gate (canopy AD-15)."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseForbidden

from django_pyforge.roles import roles_from_request


def require_station_role(station_name: str) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Return 403 when this request's token lacks ``station_name``."""

    def decorator(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            if station_name not in roles_from_request(request):
                return HttpResponseForbidden()
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
