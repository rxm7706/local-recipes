"""Host mint: CLI authenticates with an IdP bearer; the host signs RS256."""

from __future__ import annotations

import json
import logging

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from jwt.exceptions import PyJWTError

from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.exceptions import StationNotInRolesError
from django_pyforge.roles import station_granted
from django_pyforge.assertion.exceptions import VerifierNotConfiguredError
from django_pyforge.assertion.identity import verify_idp_bearer

logger = logging.getLogger(__name__)


def _refusal_reason(exc: BaseException) -> str:
    name = type(exc).__name__
    message = str(exc).strip()
    if message:
        return f"{name}: {message}"
    return name


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
    bearer = auth.removeprefix("Bearer ").strip()
    try:
        sub, roles = verify_idp_bearer(bearer)
    except VerifierNotConfiguredError as exc:
        logger.warning(
            "assertion.mint_refused",
            extra={"reason": _refusal_reason(exc), "event": "assertion.mint_refused"},
        )
        return JsonResponse({"error": "verifier not configured"}, status=503)
    except (AssertionRefusedError, PyJWTError, ValueError) as exc:
        logger.warning(
            "assertion.mint_refused",
            extra={"reason": _refusal_reason(exc), "event": "assertion.mint_refused"},
        )
        return JsonResponse({"error": "refused"}, status=401)
    if not station_granted(station, roles):
        refusal = StationNotInRolesError("station is not in verified roles")
        logger.warning(
            "assertion.mint_refused",
            extra={"reason": _refusal_reason(refusal), "event": "assertion.mint_refused"},
        )
        return JsonResponse({"error": "forbidden"}, status=403)
    try:
        token = mint_assertion(sub=sub, roles=roles, station=station)
    except (AssertionRefusedError, PyJWTError, ValueError) as exc:
        logger.warning(
            "assertion.mint_refused",
            extra={"reason": _refusal_reason(exc), "event": "assertion.mint_refused"},
        )
        return JsonResponse({"error": "refused"}, status=401)
    return JsonResponse({"assertion": token})
