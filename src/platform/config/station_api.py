"""Versioned station API seam — ``/stations/<name>/api/v<N>/`` on FastAPI.

Story 43.2 reserves this namespace on the host ASGI seam. Each station owns a
dedicated FastAPI sub-app with its own OpenAPI document at
``/stations/<name>/api/v<N>/openapi.json``. Routes declare their full path
(``/stations/...``) because the composed dispatcher forwards the scope
unchanged, matching :mod:`config.fastapi_app`'s existing pattern.

Per-station route inventories grow in later stories; warden v1 ships the
contract probe routes here.
"""

from __future__ import annotations

import importlib
import re
from typing import Any

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

_STATION_API_RE = re.compile(
    r"^/stations/(?P<station>[a-z][a-z0-9-]*)/api/v(?P<version>\d+)(?:/|$)",
)

# Every registered route path must match this (fail-loud contract test).
_VERSIONED_ROUTE_RE = re.compile(
    r"^/stations/[a-z][a-z0-9-]*/api/v\d+(?:/|$)",
)

_bearer = HTTPBearer(auto_error=False)

_station_apps: dict[tuple[str, int], FastAPI] = {}


def parse_station_api_path(path: str) -> tuple[str, int] | None:
    match = _STATION_API_RE.match(path)
    if not match:
        return None
    return match.group("station"), int(match.group("version"))


def is_station_api_path(path: str) -> bool:
    return parse_station_api_path(path) is not None


def iter_station_apps() -> list[tuple[str, int, FastAPI]]:
    """Return ``(station, version, app)`` for every registered sub-app."""
    return [
        (station, version, app)
        for (station, version), app in sorted(_station_apps.items())
    ]


def station_application(station: str, version: int) -> FastAPI:
    key = (station, version)
    app = _station_apps.get(key)
    if app is None:
        msg = f"no station API registered for {station!r} v{version}"
        raise KeyError(msg)
    return app


def _verify_station_assertion(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Require a valid RS256 service assertion for mutating station routes."""
    from django_pyforge.assertion.crypto import verify_assertion
    from django_pyforge.assertion.exceptions import AssertionRefusedError
    from django_pyforge.assertion.schema import audience_for

    parsed = parse_station_api_path(request.url.path)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Not Found")
    station, _version = parsed
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="assertion required")
    try:
        return verify_assertion(
            credentials.credentials,
            audience=audience_for(station),
        )
    except AssertionRefusedError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _register_warden_v1(app: FastAPI) -> None:
    prefix = "/stations/warden/api/v1"

    @app.get(f"{prefix}/health")
    async def warden_health() -> dict[str, str]:
        return {"status": "ok", "station": "warden"}

    @app.post(f"{prefix}/compliance/check")
    async def warden_compliance_check(
        payload: dict[str, Any],
        _claims: dict[str, Any] = Depends(_verify_station_assertion),
    ) -> dict[str, Any]:
        recipe_name = payload.get("recipe_name")
        return {
            "status": "accepted",
            "station": "warden",
            "recipe_name": recipe_name,
        }


def _register_herald_v1(app: FastAPI) -> None:
    prefix = "/stations/herald/api/v1"

    @app.get(f"{prefix}/health")
    async def herald_health() -> dict[str, str]:
        return {"status": "ok", "station": "herald"}

    # ``src/platform/`` never imports ``pyforge.*`` — load herald's mount
    # helper by module name (Story 19.1 / pap:AD-2).
    herald_station_api = importlib.import_module("pyforge.herald.station_api")
    herald_station_api.attach_webhook_asgi(app)


def _build_station_app(station: str, version: int) -> FastAPI:
    openapi_url = f"/stations/{station}/api/v{version}/openapi.json"
    app = FastAPI(
        title=f"PyForge {station} API",
        version=f"v{version}",
        openapi_url=openapi_url,
        docs_url=None,
        redoc_url=None,
    )
    if station == "warden" and version == 1:
        _register_warden_v1(app)
    elif station == "herald" and version == 1:
        _register_herald_v1(app)
    return app


def register_station_api(station: str, version: int) -> FastAPI:
    """Register (or return) the FastAPI sub-app for ``station`` at ``version``."""
    key = (station, version)
    if key not in _station_apps:
        _station_apps[key] = _build_station_app(station, version)
    return _station_apps[key]


def assert_routes_are_versioned(app: FastAPI) -> list[str]:
    """Return route paths that violate the ``/api/v<N>/`` prefix contract."""
    violations: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not isinstance(path, str) or path.endswith("/openapi.json"):
            continue
        if not _VERSIONED_ROUTE_RE.match(path):
            violations.append(path)
    return violations


# Seed station APIs at import time (warden v1, herald v1).
register_station_api("warden", 1)
register_station_api("herald", 1)
