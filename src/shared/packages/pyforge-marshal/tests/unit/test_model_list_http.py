"""HTTP adapter tests for model-list refresh (Story 84.1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pyforge.marshal.adapters.model_list_http import http_get_for_model_list


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


def test_http_get_redirect_not_followed():
    mock_response = MagicMock()
    mock_response.status = 302
    mock_response.read.return_value = b""
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value = mock_response

    with patch("pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection", return_value=mock_conn):
        result = http_get_for_model_list(
            "https://api.anthropic.com/v1/models",
            {"x-api-key": "sekret"},
            timeout_s=5.0,
        )
    assert result.status_code == 0
    assert result.body == b"redirect not followed"


def test_http_get_timeout():
    mock_conn = MagicMock()
    mock_conn.request.side_effect = TimeoutError()

    with patch("pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection", return_value=mock_conn):
        result = http_get_for_model_list("https://example.com/v1/models", {}, timeout_s=1.0)
    assert result.status_code == 0
    assert result.body == b"timeout"
