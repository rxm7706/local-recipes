"""Copy session token roles onto ``request.idp_roles`` when unset (canopy AD-15)."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest
from django.http import HttpResponse

from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_pyforge.roles import role_names


class TokenRolesMiddleware:
    """Populate request-scoped IdP roles from this request's session token."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if getattr(request, "idp_roles", None) is None:
            session = getattr(request, "session", None)
            raw = session.get(IDP_TOKEN_ROLES_SESSION_KEY) if session is not None else None
            request.idp_roles = role_names(raw)
        return self.get_response(request)
