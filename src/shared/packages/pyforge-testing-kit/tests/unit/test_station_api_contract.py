"""Golden contract test: portal and CLI paths share one station API header set."""

from __future__ import annotations

import json

import pytest
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.roles import prefixed_station
from django_pyforge.station_client import StationHttpClient
from pyforge.core.client import API_VERSION_HEADER, PyForgeStationClient

_SUB = "contract-user"
_ROLES = [prefixed_station("warden")]
_STATION = "warden"
_PATH = "/compliance/check"
_PAYLOAD = {"recipe_name": "numpy"}


def _capture_transport(store: list[dict[str, object]]):
    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        store.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
            }
        )
        return json.dumps({"status": "accepted", "station": "warden", "recipe_name": "numpy"}).encode("utf-8")

    return transport


@pytest.mark.unit
def test_cli_client_and_portal_wrapper_emit_identical_headers() -> None:
    from django_pyforge.assertion.client import PortalClient

    portal_token = PortalClient().emit(
        _SUB,
        _ROLES,
        _STATION,
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    cli_capture: list[dict[str, object]] = []
    cli_client = PyForgeStationClient(
        station=_STATION,
        version=1,
        base_url="http://testserver",
        assertion=portal_token,
        transport=_capture_transport(cli_capture),
    )
    cli_client.post(_PATH, payload=_PAYLOAD)

    portal_capture: list[dict[str, object]] = []
    StationHttpClient(PortalClient()).post(
        _PATH,
        payload=_PAYLOAD,
        station=_STATION,
        sub=_SUB,
        roles=_ROLES,
        base_url="http://testserver",
        private_pem=GOLDEN_PRIVATE_PEM,
        transport=_capture_transport(portal_capture),
    )

    assert len(cli_capture) == 1
    assert len(portal_capture) == 1
    cli_headers = cli_capture[0]["headers"]
    portal_headers = portal_capture[0]["headers"]
    assert cli_headers[API_VERSION_HEADER] == "1"
    assert portal_headers[API_VERSION_HEADER] == "1"
    assert cli_headers["Authorization"].startswith("Bearer ")
    assert portal_headers["Authorization"].startswith("Bearer ")
    assert cli_capture[0]["url"] == portal_capture[0]["url"]
    assert cli_capture[0]["url"] == "http://testserver/stations/warden/api/v1/compliance/check"
