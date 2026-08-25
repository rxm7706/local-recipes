"""Refuse trusted identity headers unless a valid RS256 assertion is present."""

from __future__ import annotations

from typing import TYPE_CHECKING

import jwt
from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from jwt.exceptions import PyJWTError

from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import AUDIENCE_PREFIX

if TYPE_CHECKING:
    from collections.abc import Callable

IDENTITY_HEADERS = (
    "HTTP_X_FORWARDED_USER",
    "HTTP_X_REMOTE_USER",
    "HTTP_REMOTE_USER",
)


def _has_identity_header(request: HttpRequest) -> bool:
    return any(request.META.get(name) for name in IDENTITY_HEADERS)


def _bearer(request: HttpRequest) -> str | None:
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        return token or None
    return None


def _assertion_is_valid(token: str) -> bool:
    public_pem = getattr(settings, "PYFORGE_ASSERTION_PUBLIC_KEY", "")
    if not public_pem:
        return False
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
        )
        aud = unverified.get("aud")
        if not isinstance(aud, str) or not aud.startswith(AUDIENCE_PREFIX) or aud == AUDIENCE_PREFIX:
            return False
        verify_assertion(token, audience=aud, public_pem=public_pem)
    except (AssertionRefusedError, PyJWTError, TypeError, ValueError):
        return False
    return True


class AssertionMiddleware:
    """Identity headers are not an identity path (FR-15)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if _has_identity_header(request):
            token = _bearer(request)
            if token is None or not _assertion_is_valid(token):
                return JsonResponse({"error": "assertion required"}, status=401)
        return self.get_response(request)
