"""Host mint: CLI authenticates with an IdP bearer; the host signs RS256."""

from __future__ import annotations

import json

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from jwt.exceptions import PyJWTError

from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.identity import identity_from_idp_bearer


@csrf_exempt
@require_POST
def mint(request: HttpRequest) -> HttpResponse:
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth.startswith("Bearer "):
        return JsonResponse({"error": "missing bearer"}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        station = payload["station"]
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError, TypeError):
        return JsonResponse({"error": "invalid body"}, status=400)
    if not isinstance(station, str) or not station:
        return JsonResponse({"error": "invalid station"}, status=400)
    try:
        sub, roles = identity_from_idp_bearer(auth.removeprefix("Bearer ").strip())
        token = mint_assertion(sub=sub, roles=roles, station=station)
    except (AssertionRefusedError, PyJWTError, ValueError):
        return JsonResponse({"error": "refused"}, status=401)
    return JsonResponse({"assertion": token})
