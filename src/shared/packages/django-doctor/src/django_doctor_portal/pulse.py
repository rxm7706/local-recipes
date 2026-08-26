"""Last ``doctor monitor --fleet`` summary for the doctor portal.

Reach is ``PortalClient.emit`` only. This module must not import ``pyforge.*``
and must not open HTTP to a service.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest

from django_doctor_portal.pulse_document import present_pulse
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import audience_for
from django_pyforge.roles import claims_from_request
from django_pyforge.roles import roles_from_request

STATION = "doctor"
CACHE_KEY = "django_doctor_portal:last_fleet_pulse"
SURFACE_PATH_SETTING = "DOCTOR_FLEET_SURFACE_PATH"


def _operator_sub(request: HttpRequest) -> str:
    claims = claims_from_request(request)
    if claims is not None:
        sub = claims.get(CLAIM_SUB)
        if isinstance(sub, str) and sub.strip():
            return sub.strip()
    user = getattr(request, "user", None)
    username = getattr(user, "get_username", None)
    if callable(username):
        name = username()
        if isinstance(name, str) and name.strip():
            return name.strip()
    return "doctor-operator"


def _read_surface_document() -> dict[str, Any] | None:
    cached = cache.get(CACHE_KEY)
    if isinstance(cached, dict) and isinstance(cached.get("summary"), dict):
        return cached
    raw_path = getattr(settings, SURFACE_PATH_SETTING, "") or ""
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def last_fleet_pulse(request: HttpRequest) -> dict[str, Any]:
    """Return the last fleet-pulse document after a PortalClient emit."""
    roles = list(roles_from_request(request))
    try:
        token = PortalClient().emit(_operator_sub(request), roles, STATION)
        verify_assertion(token, audience=audience_for(STATION))
    except AssertionRefusedError:
        return present_pulse(None)
    return present_pulse(_read_surface_document())
