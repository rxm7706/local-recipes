"""PKCE authorization-code login against an OIDC issuer (Story 33.14, CAP-5)."""

from __future__ import annotations

import json
import threading
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyforge.core.client import (
    StationClientError,
    form_urlencode,
    parse_request_path,
    urllib_request,
)
from pyforge.core.errors import PyforgeError

from ..core.pkce import challenge_for, generate_verifier

TokenTransport = Callable[[str, dict[str, str], bytes], bytes]
BrowserOpener = Callable[[str], None]


class PkceLoginError(PyforgeError, Exception):
    """PKCE login failed before a bearer could be obtained.

    Story 52.1, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``Exception`` stays in the MRO."""


class _CallbackResult:
    __slots__ = ("code", "error", "error_description")

    def __init__(
        self,
        *,
        code: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> None:
        self.code = code
        self.error = error
        self.error_description = error_description


class _CallbackHandler(BaseHTTPRequestHandler):
    result: _CallbackResult | None = None
    shutdown_event: threading.Event | None = None

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        del format, args

    def do_GET(self) -> None:  # noqa: N802
        pathname, params = parse_request_path(self.path)
        if pathname != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        type(self).result = _CallbackResult(
            code=_first_param(params, "code"),
            error=_first_param(params, "error"),
            error_description=_first_param(params, "error_description"),
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Login complete. You may close this window.")
        if type(self).shutdown_event is not None:
            type(self).shutdown_event.set()

    def do_POST(self) -> None:  # noqa: N802
        self.send_response(405)
        self.end_headers()


def _first_param(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _normalize_issuer(issuer: str) -> str:
    cleaned = issuer.strip().rstrip("/")
    if not cleaned:
        raise PkceLoginError("issuer is required")
    return cleaned


def build_authorization_url(
    *,
    issuer: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    scope: str = "openid",
) -> str:
    issuer_base = _normalize_issuer(issuer)
    query = form_urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scope,
        }
    )
    return f"{issuer_base}/protocol/openid-connect/auth?{query}"


def _default_transport(url: str, headers: dict[str, str], body: bytes) -> bytes:
    try:
        return urllib_request("POST", url, headers, body)
    except StationClientError as exc:
        raise PkceLoginError("token exchange failed") from exc


def exchange_authorization_code(
    *,
    issuer: str,
    client_id: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
    transport: TokenTransport | None = None,
) -> str:
    issuer_base = _normalize_issuer(issuer)
    token_url = f"{issuer_base}/protocol/openid-connect/token"
    body = form_urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    send = transport or _default_transport
    raw = send(token_url, headers, body)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PkceLoginError("token endpoint returned an invalid response") from exc
    if not isinstance(payload, dict):
        raise PkceLoginError("token endpoint returned an invalid response")
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise PkceLoginError("token endpoint response missing access_token")
    return access_token.strip()


def _bind_loopback_server() -> tuple[HTTPServer, int]:
    last_error: OSError | None = None
    for _ in range(2):
        try:
            server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
            port = server.server_address[1]
            return server, port
        except OSError as exc:
            last_error = exc
    raise PkceLoginError("could not bind loopback callback server") from last_error


def capture_authorization_code(
    *,
    timeout_s: float,
    server: HTTPServer | None = None,
) -> _CallbackResult:
    owns_server = server is None
    if server is None:
        server, _port = _bind_loopback_server()
    shutdown_event = threading.Event()
    _CallbackHandler.shutdown_event = shutdown_event
    _CallbackHandler.result = None
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    if not shutdown_event.wait(timeout=timeout_s):
        server.server_close()
        raise PkceLoginError(f"login timed out after {int(timeout_s)} seconds")
    thread.join(timeout=1.0)
    server.server_close()
    result = _CallbackHandler.result
    if result is None:
        raise PkceLoginError("callback received no authorization response")
    if owns_server:
        del server
    return result


class PkceLogin:
    """Run a PKCE authorization-code flow and return an access token."""

    def __init__(
        self,
        *,
        issuer: str,
        client_id: str = "pyforge-cli",
        timeout_s: float = 120.0,
        scope: str = "openid",
        transport: TokenTransport | None = None,
        open_browser: BrowserOpener | None = None,
    ) -> None:
        self._issuer = issuer
        self._client_id = client_id
        self._timeout_s = timeout_s
        self._scope = scope
        self._transport = transport
        self._open_browser = open_browser or webbrowser.open

    @property
    def authorization_url(self) -> str:
        return self._authorization_url

    def run(self) -> str:
        verifier = generate_verifier()
        challenge = challenge_for(verifier)
        server, port = _bind_loopback_server()
        redirect_uri = f"http://127.0.0.1:{port}/callback"
        self._authorization_url = build_authorization_url(
            issuer=self._issuer,
            client_id=self._client_id,
            redirect_uri=redirect_uri,
            code_challenge=challenge,
            scope=self._scope,
        )
        callback_holder: list[_CallbackResult] = []
        error_holder: list[BaseException] = []

        def wait_for_callback() -> None:
            try:
                callback_holder.append(capture_authorization_code(timeout_s=self._timeout_s, server=server))
            except BaseException as exc:  # pragma: no cover - surfaced below
                error_holder.append(exc)

        waiter = threading.Thread(target=wait_for_callback, daemon=True)
        waiter.start()
        print(self._authorization_url)
        try:
            self._open_browser(self._authorization_url)
        except OSError:
            pass
        waiter.join(timeout=self._timeout_s + 1.0)
        if error_holder:
            raise error_holder[0]
        if not callback_holder:
            raise PkceLoginError(f"login timed out after {int(self._timeout_s)} seconds")
        callback = callback_holder[0]
        if callback.error:
            detail = callback.error_description or callback.error
            raise PkceLoginError(detail or callback.error)
        if not callback.code:
            raise PkceLoginError("authorization response missing code")
        return exchange_authorization_code(
            issuer=self._issuer,
            client_id=self._client_id,
            redirect_uri=redirect_uri,
            code=callback.code,
            code_verifier=verifier,
            transport=self._transport,
        )
