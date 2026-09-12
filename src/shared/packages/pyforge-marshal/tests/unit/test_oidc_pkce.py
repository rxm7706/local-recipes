"""Story 33.14 — PKCE adapter unit tests."""

from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from pyforge.marshal.adapters import oidc_pkce as oidc_pkce_mod
from pyforge.marshal.adapters.oidc_pkce import (
    PkceLogin,
    PkceLoginError,
    build_authorization_url,
    capture_authorization_code,
    exchange_authorization_code,
)
from pyforge.marshal.core.pkce import challenge_for, generate_verifier


class RecordingTransport:
    def __init__(self, response: bytes) -> None:
        self.calls: list[tuple[str, dict[str, str], bytes]] = []
        self.response = response

    def __call__(self, url: str, headers: dict[str, str], body: bytes) -> bytes:
        self.calls.append((url, headers, body))
        return self.response


def test_build_authorization_url_shape() -> None:
    verifier = generate_verifier()
    redirect_uri = "http://127.0.0.1:54321/callback"
    url = build_authorization_url(
        issuer="http://127.0.0.1:8080/realms/platform",
        client_id="pyforge-cli",
        redirect_uri=redirect_uri,
        code_challenge=challenge_for(verifier),
    )
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    assert parsed.path.endswith("/protocol/openid-connect/auth")
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["pyforge-cli"]
    assert params["redirect_uri"] == [redirect_uri]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["openid"]


def test_exchange_authorization_code_returns_access_token() -> None:
    transport = RecordingTransport(
        json.dumps({"access_token": "idp-bearer-token", "token_type": "Bearer"}).encode(
            "utf-8"
        )
    )
    token = exchange_authorization_code(
        issuer="http://issuer.test/realms/platform",
        client_id="pyforge-cli",
        redirect_uri="http://127.0.0.1:1/callback",
        code="abc",
        code_verifier="verifier",
        transport=transport,
    )
    assert token == "idp-bearer-token"
    assert transport.calls[0][0].endswith("/protocol/openid-connect/token")
    body = transport.calls[0][2].decode("utf-8")
    assert "grant_type=authorization_code" in body
    assert "code_verifier=verifier" in body


def test_capture_authorization_code_access_denied() -> None:
    server, port = oidc_pkce_mod._bind_loopback_server()

    def hit_callback() -> None:
        with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{port}/callback?error=access_denied",
            timeout=5,
        ):
            pass

    thread = threading.Thread(target=hit_callback, daemon=True)
    thread.start()
    result = capture_authorization_code(timeout_s=5.0, server=server)
    thread.join(timeout=1.0)
    assert result.error == "access_denied"
    assert result.code is None


def test_capture_authorization_code_timeout() -> None:
    server, _port = _bind_test_server()
    with pytest.raises(PkceLoginError, match="timed out"):
        capture_authorization_code(timeout_s=0.2, server=server)


def test_pkce_login_success_with_injected_transport() -> None:
    transport = RecordingTransport(
        json.dumps({"access_token": "mint-me", "token_type": "Bearer"}).encode("utf-8")
    )
    errors: list[Exception] = []
    token_holder: list[str] = []

    def deliver_code(url: str) -> None:
        redirect_uri = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)[
            "redirect_uri"
        ][0]
        with urllib.request.urlopen(  # noqa: S310
            f"{redirect_uri}?code=live-code",
            timeout=5,
        ):
            pass

    def run_login() -> None:
        try:
            token_holder.append(
                PkceLogin(
                    issuer="http://issuer.test/realms/platform",
                    client_id="pyforge-cli",
                    timeout_s=5.0,
                    transport=transport,
                    open_browser=deliver_code,
                ).run()
            )
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    thread = threading.Thread(target=run_login, daemon=True)
    thread.start()
    thread.join(timeout=5.0)
    assert not errors
    assert token_holder == ["mint-me"]


def _bind_test_server() -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    return server, server.server_address[1]
