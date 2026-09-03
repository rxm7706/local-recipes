"""Story 43.2 — versioned station API seam (FastAPI sub-apps + host dispatch)."""

from __future__ import annotations

import asyncio
from http import HTTPStatus

import pytest
from django.test import override_settings
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.roles import prefixed_station
from django_pyforge.station_client import API_VERSION_HEADER
from django_pyforge.station_client import StationHttpClient
from httpx import ASGITransport
from httpx import AsyncClient

from config.station_api import assert_routes_are_versioned
from config.station_api import iter_station_apps
from config.station_api import register_station_api
from config.station_api import station_application


def _get_station(path: str, *, headers: dict[str, str] | None = None):
    async def _call():
        app = station_application("warden", 1)
        transport = ASGITransport(app=app)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.get(path, headers=headers or {})

    return asyncio.run(_call())


def _post_station(path: str, *, headers: dict[str, str] | None = None, json_body: dict | None = None):
    async def _call():
        app = station_application("warden", 1)
        transport = ASGITransport(app=app)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.post(path, headers=headers or {}, json=json_body or {})

    return asyncio.run(_call())


def test_warden_openapi_lists_versioned_routes():
    response = _get_station("/stations/warden/api/v1/openapi.json")

    assert response.status_code == HTTPStatus.OK
    document = response.json()
    paths = document.get("paths", {})
    assert "/stations/warden/api/v1/health" in paths
    assert "/stations/warden/api/v1/compliance/check" in paths
    for path in paths:
        assert path.startswith("/stations/warden/api/v1/")


def test_every_registered_station_route_has_a_version_prefix():
    violations: list[str] = []
    for _station, _version, app in iter_station_apps():
        violations.extend(assert_routes_are_versioned(app))
    assert not violations, f"unversioned station routes: {violations}"


def test_adding_an_unversioned_route_fails_the_contract():
    probe = register_station_api("contract-probe", 99)

    @probe.get("/stations/contract-probe/bad-route")
    async def bad_route() -> dict[str, str]:
        return {"bad": "route"}

    try:
        assert "/stations/contract-probe/bad-route" in assert_routes_are_versioned(probe)
    finally:
        from config.station_api import _station_apps

        _station_apps.pop(("contract-probe", 99), None)


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_station_client_carries_version_header_and_assertion():
    token = PortalClient().emit(
        "cli-user",
        [prefixed_station("warden")],
        "warden",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    captured: dict[str, object] = {}

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["body"] = body
        return b'{"status":"accepted","station":"warden","recipe_name":"numpy"}'

    StationHttpClient(PortalClient()).post(
        "/compliance/check",
        payload={"recipe_name": "numpy"},
        station="warden",
        sub="cli-user",
        roles=[prefixed_station("warden")],
        base_url="http://testserver",
        private_pem=GOLDEN_PRIVATE_PEM,
        transport=transport,
    )

    assert captured["url"] == "http://testserver/stations/warden/api/v1/compliance/check"
    headers = captured["headers"]
    assert headers[API_VERSION_HEADER] == "1"
    assert headers["Authorization"] == f"Bearer {token}"


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_warden_compliance_check_requires_assertion():
    response = _post_station(
        "/stations/warden/api/v1/compliance/check",
        json_body={"recipe_name": "numpy"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_warden_compliance_check_accepts_signed_assertion():
    token = PortalClient().emit(
        "portal-user",
        [prefixed_station("warden")],
        "warden",
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    response = _post_station(
        "/stations/warden/api/v1/compliance/check",
        headers={
            API_VERSION_HEADER: "1",
            "Authorization": f"Bearer {token}",
        },
        json_body={"recipe_name": "numpy"},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["recipe_name"] == "numpy"
