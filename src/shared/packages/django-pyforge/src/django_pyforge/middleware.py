"""Populate request-scoped IdP roles from this request's token (canopy AD-15)."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest
from django.http import HttpResponse

from django_pyforge.roles import claims_from_request
from django_pyforge.roles import roles_from_claims


class TokenRolesMiddleware:
    """Populate ``request.idp_roles`` from current IdP token claims."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        claims = claims_from_request(request)
        if claims is not None:
            request.idp_token_claims = claims
            request.idp_roles = roles_from_claims(claims)
        elif getattr(request, "idp_roles", None) is None:
            request.idp_roles = []
        return self.get_response(request)
