"""HTTP adapter tests for model-list refresh (Story 84.1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyforge.marshal.adapters.model_list_http import http_get_for_model_list
from pyforge.marshal.ports.model_list_fetch import HttpGetResult


def test_http_get_rejects_non_https():
    result = http_get_for_model_list("http://example.com/v1/models", {}, timeout_s=1.0)
    assert result.status_code == 0
    assert b"invalid url scheme" in result.body


def test_http_get_success():
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"data":[]}'
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_response

    with patch("pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection", return_value=mock_conn):
        result = http_get_for_model_list(
            "https://api.anthropic.com/v1/models",
            {"x-api-key": "sekret"},
            timeout_s=5.0,
        )
    assert result.status_code == 200
    assert result.body == b'{"data":[]}'
    mock_conn.request.assert_called_once()
    call_args = mock_conn.request.call_args
    path = call_args[0][1]
    assert path.startswith("/v1/models")


@pytest.mark.parametrize(
    "target",
    ["https://api.anthropic.com:8443/v1/models", "https://elsewhere.invalid/v1/models", "http://127.0.0.1:9/v1/models"],
    ids=["same-host-other-port", "other-host", "https-to-http"],
)
@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_http_get_redirect_not_followed(monkeypatch, status, target):
    """Story 84.2: a 3xx names a target; the target gets no connection and no key."""
    connections: list[tuple[str, int]] = []
    sent: list[tuple[tuple[str, int], dict[str, str]]] = []

    class _Response:
        def __init__(self, code: int, location: str | None) -> None:
            self.status = code
            self._location = location

        def read(self) -> bytes:
            return b""

        def getheader(self, name: str, default: str | None = None) -> str | None:
            return self._location if name.lower() == "location" else default

    class _Conn:
        def __init__(self, host, port=None, **_kwargs):
            self._endpoint = (host, port)
            connections.append(self._endpoint)

        def request(self, method, url, body=None, headers=None):
            del method, url, body
            sent.append((self._endpoint, dict(headers or {})))

        def getresponse(self):
            if self._endpoint == ("api.anthropic.com", 443):
                return _Response(status, target)
            return _Response(200, None)

        def close(self):
            return None

    monkeypatch.setattr("pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection", _Conn)
    monkeypatch.setattr("pyforge.marshal.adapters.model_list_http.http.client.HTTPConnection", _Conn, raising=False)
    result = http_get_for_model_list(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": "SENTINEL-NOT-A-REAL-KEY"},
        timeout_s=5.0,
    )
    assert result == HttpGetResult(status_code=0, body=b"redirect not followed")
    assert connections == [("api.anthropic.com", 443)]
    assert sent == [(("api.anthropic.com", 443), {"x-api-key": "SENTINEL-NOT-A-REAL-KEY"})]


def test_http_get_timeout():
    mock_conn = MagicMock()
    mock_conn.request.side_effect = TimeoutError()

    with patch("pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection", return_value=mock_conn):
        result = http_get_for_model_list("https://example.com/v1/models", {}, timeout_s=1.0)
    assert result.status_code == 0
    assert result.body == b"timeout"
