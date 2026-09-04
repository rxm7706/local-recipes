"""Story 43.3 — co-located portals never loopback HTTP to the host."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.roles import prefixed_station
from django_pyforge.station_client import API_VERSION_HEADER
from django_pyforge.station_client import StationHttpClient
from django_pyforge.station_port import is_station_remote

# Stub Langflow before config.asgi imports it (platform-ci-test has no langflow).
_langflow_asgi_app = MagicMock()
_langflow_pkg = MagicMock()
_langflow_pkg.main.create_app.return_value = _langflow_asgi_app
sys.modules.setdefault("langflow", _langflow_pkg)
sys.modules.setdefault("langflow.main", _langflow_pkg.main)


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_default_profile_uses_in_process_port_without_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STATION_REMOTE", raising=False)
    assert is_station_remote() is False

    captured: dict[str, object] = {}

    def fake_invoke(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["body"] = body
        return json.dumps(
            {"status": "accepted", "station": "warden", "recipe_name": "numpy"},
        ).encode("utf-8")

    from django_pyforge.station_port import replace_in_process_handler

    previous = replace_in_process_handler(fake_invoke)

    def _forbid_http(*args: object, **kwargs: object) -> None:
        raise AssertionError("urllib HTTP must not run in the default in-process profile")

    monkeypatch.setattr(
        "pyforge.core.client.urllib.request.urlopen",
        _forbid_http,
    )

    try:
        StationHttpClient(PortalClient()).post(
            "/compliance/check",
            payload={"recipe_name": "numpy"},
            station="warden",
            sub="portal-user",
            roles=[prefixed_station("warden")],
            base_url="http://127.0.0.1:8000",
            private_pem=GOLDEN_PRIVATE_PEM,
        )
    finally:
        if previous is not None:
            replace_in_process_handler(previous)

    assert captured["method"] == "POST"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers[API_VERSION_HEADER] == "1"
    assert headers["Authorization"].startswith("Bearer ")


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_wired_asgi_invoker_reaches_station_api_without_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STATION_REMOTE", raising=False)
    from django_pyforge.station_port import replace_in_process_handler

    from config.station_port import asgi_invoke

    previous = replace_in_process_handler(asgi_invoke)
    try:
        body = StationHttpClient(PortalClient()).post(
            "/compliance/check",
            payload={"recipe_name": "numpy"},
            station="warden",
            sub="portal-user",
            roles=[prefixed_station("warden")],
            base_url="http://127.0.0.1:8000",
            private_pem=GOLDEN_PRIVATE_PEM,
        )
    finally:
        if previous is not None:
            replace_in_process_handler(previous)

    payload = json.loads(body.decode("utf-8"))
    assert payload["station"] == "warden"
    assert payload["recipe_name"] == "numpy"


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_station_remote_uses_http_transport_with_assertion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STATION_REMOTE", "1")
    assert is_station_remote() is True

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
        sub="portal-user",
        roles=[prefixed_station("warden")],
        base_url="http://testserver",
        private_pem=GOLDEN_PRIVATE_PEM,
        transport=transport,
    )

    assert captured["url"] == "http://testserver/stations/warden/api/v1/compliance/check"
    headers = captured["headers"]
    assert headers[API_VERSION_HEADER] == "1"
    assert headers["Authorization"].startswith("Bearer ")


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_station_remote_default_transport_is_http_not_in_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STATION_REMOTE", "1")
    from django_pyforge.station_port import default_transport

    assert default_transport() is None
