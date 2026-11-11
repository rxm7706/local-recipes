"""Golden contract test: portal and CLI paths share one station API header set.

Live-tree (Story 118.1, spec-pyforge-testing-charter:CAP-7): the portal side is the host package
``django_pyforge``, which runs in the live-tree half with django-pyforge on ``PYTHONPATH``. Django is configured
by a module-scoped fixture and every ``django`` / ``django_pyforge`` import sits inside a fixture or test body, so
collecting this module is import-safe on a root without the host.
"""

from __future__ import annotations

import json

import pytest
from pyforge.core.client import API_VERSION_HEADER, PyForgeStationClient

pytestmark = pytest.mark.live_tree

_SUB = "contract-user"
_STATION = "warden"
_PATH = "/compliance/check"
_PAYLOAD = {"recipe_name": "numpy"}


@pytest.fixture(scope="module")
def golden_private_pem() -> str:
    """Configure Django once for this module (the kit's conftest did it for the whole session until Story 118.1)."""
    import django
    from django.conf import settings
    from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM, GOLDEN_PUBLIC_PEM

    if not settings.configured:
        settings.configure(
            SECRET_KEY="testing-kit-contract-test",
            USE_TZ=True,
            INSTALLED_APPS=[],
            PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
            PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
        )
        django.setup()
    return GOLDEN_PRIVATE_PEM


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
def test_cli_client_and_portal_wrapper_emit_identical_headers(golden_private_pem: str) -> None:
    from django_pyforge.assertion.client import PortalClient
    from django_pyforge.roles import prefixed_station
    from django_pyforge.station_client import StationHttpClient

    roles = [prefixed_station("warden")]
    portal_token = PortalClient().emit(
        _SUB,
        roles,
        _STATION,
        private_pem=golden_private_pem,
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
        roles=roles,
        base_url="http://testserver",
        private_pem=golden_private_pem,
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
