"""Unit tests for pyforge.core.client (Story 43.2)."""

from __future__ import annotations

import json

import pytest

from pyforge.core.client import API_VERSION_HEADER, PyForgeStationClient

pytestmark = pytest.mark.unit


def test_build_url_prefixes_station_api_root() -> None:
    client = PyForgeStationClient(station="warden", version=1, base_url="http://host")
    assert client.build_url("/compliance/check") == ("http://host/stations/warden/api/v1/compliance/check")


def test_build_headers_carry_version_and_assertion() -> None:
    client = PyForgeStationClient(
        station="warden",
        version=2,
        assertion="signed-token",
    )
    headers = client.build_headers()
    assert headers[API_VERSION_HEADER] == "2"
    assert headers["Authorization"] == "Bearer signed-token"


def test_post_uses_injected_transport() -> None:
    seen: dict[str, object] = {}

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        seen["method"] = method
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = body
        return b'{"ok": true}'

    client = PyForgeStationClient(
        station="warden",
        version=1,
        base_url="http://host",
        assertion="tok",
        transport=transport,
    )
    raw = client.post("/health", payload={"x": 1})
    assert json.loads(raw.decode("utf-8")) == {"ok": True}
    assert seen["method"] == "POST"
    assert seen["url"] == "http://host/stations/warden/api/v1/health"
    assert seen["headers"][API_VERSION_HEADER] == "1"
