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
    from pyforge.core.client import parse_request_path

    verifier = generate_verifier()
    redirect_uri = "http://127.0.0.1:54321/callback"
    url = build_authorization_url(
        issuer="http://127.0.0.1:8080/realms/platform",
        client_id="pyforge-cli",
        redirect_uri=redirect_uri,
        code_challenge=challenge_for(verifier),
    )
    path, params = parse_request_path(url.removeprefix("http://127.0.0.1:8080"))
    assert path == "/realms/platform/protocol/openid-connect/auth"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["pyforge-cli"]
    assert params["redirect_uri"] == [redirect_uri]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["openid"]


def test_exchange_authorization_code_returns_access_token() -> None:
    transport = RecordingTransport(
        json.dumps({"access_token": "idp-bearer-token", "token_type": "Bearer"}).encode("utf-8")
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
    transport = RecordingTransport(json.dumps({"access_token": "mint-me", "token_type": "Bearer"}).encode("utf-8"))
    errors: list[Exception] = []
    token_holder: list[str] = []

    def deliver_code(url: str) -> None:
        redirect_uri = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["redirect_uri"][0]
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


# --- Story 52.1, SPEC-pyforge-core CAP-5: the re-parent widening guard ----


def test_pkce_login_error_is_a_pyforge_error_and_an_exception() -> None:
    """``PkceLoginError`` gained ``PyforgeError`` as an additional base and
    kept its original ``Exception`` base -- so ``login.py``'s exact-class
    ``except PkceLoginError`` and any ``except Exception`` site behave
    identically, and ``except PyforgeError`` newly catches it too."""
    from pyforge.core.errors import PyforgeError

    assert issubclass(PkceLoginError, PyforgeError)
    assert issubclass(PkceLoginError, Exception)
    for catch in (PkceLoginError, Exception, PyforgeError):
        try:
            raise PkceLoginError("no bearer")
        except catch:
            pass


# --- Coverage of the remaining branches (Story 52.1 coverage gate) --------
# Every I/O here is a loopback socket on an ephemeral port, an injected
# transport, or a monkeypatched module attribute -- never a real issuer.


def _hit(url: str) -> int:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
        return response.status


def _serve_one(server: HTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    return thread


def test_callback_handler_404s_any_other_path() -> None:
    server, port = oidc_pkce_mod._bind_loopback_server()
    oidc_pkce_mod._CallbackHandler.result = None
    oidc_pkce_mod._CallbackHandler.shutdown_event = None
    thread = _serve_one(server)
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _hit(f"http://127.0.0.1:{port}/not-the-callback")
    thread.join(timeout=2.0)
    server.server_close()
    assert excinfo.value.code == 404
    assert oidc_pkce_mod._CallbackHandler.result is None


def test_callback_handler_rejects_post_with_405() -> None:
    server, port = oidc_pkce_mod._bind_loopback_server()
    thread = _serve_one(server)
    request = urllib.request.Request(f"http://127.0.0.1:{port}/callback", data=b"code=x", method="POST")
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        with urllib.request.urlopen(request, timeout=5):  # noqa: S310
            pass
    thread.join(timeout=2.0)
    server.server_close()
    assert excinfo.value.code == 405


def test_callback_without_shutdown_event_still_records_result() -> None:
    """The handler's ``shutdown_event is not None`` guard: a bare handler
    (no event wired) still records the result and answers 200."""
    server, port = oidc_pkce_mod._bind_loopback_server()
    oidc_pkce_mod._CallbackHandler.result = None
    oidc_pkce_mod._CallbackHandler.shutdown_event = None
    thread = _serve_one(server)
    assert _hit(f"http://127.0.0.1:{port}/callback?code=%20raw%20") == 200
    thread.join(timeout=2.0)
    server.server_close()
    result = oidc_pkce_mod._CallbackHandler.result
    assert result is not None
    assert result.code == "raw"  # `_first_param` strips whitespace


def test_first_param_treats_blank_values_as_absent() -> None:
    assert oidc_pkce_mod._first_param({"code": ["  "]}, "code") is None
    assert oidc_pkce_mod._first_param({"code": []}, "code") is None
    assert oidc_pkce_mod._first_param({}, "code") is None
    assert oidc_pkce_mod._first_param({"code": [" abc "]}, "code") == "abc"


def test_blank_issuer_is_rejected() -> None:
    with pytest.raises(PkceLoginError, match="issuer is required"):
        build_authorization_url(issuer="  / ", client_id="c", redirect_uri="r", code_challenge="x")


def test_default_transport_wraps_station_client_error(monkeypatch) -> None:
    from pyforge.core.client import StationClientError

    def _boom(method, url, headers, body):
        raise StationClientError("502 upstream")

    monkeypatch.setattr(oidc_pkce_mod, "urllib_request", _boom)
    with pytest.raises(PkceLoginError, match="token exchange failed") as excinfo:
        oidc_pkce_mod._default_transport("http://issuer.test/token", {}, b"")
    assert isinstance(excinfo.value.__cause__, StationClientError)


def test_default_transport_returns_the_raw_body(monkeypatch) -> None:
    seen: list[tuple[str, str, dict[str, str], bytes]] = []

    def _ok(method, url, headers, body):
        seen.append((method, url, headers, body))
        return b'{"access_token": "t"}'

    monkeypatch.setattr(oidc_pkce_mod, "urllib_request", _ok)
    assert oidc_pkce_mod._default_transport("http://x/token", {"H": "v"}, b"b") == (b'{"access_token": "t"}')
    assert seen == [("POST", "http://x/token", {"H": "v"}, b"b")]


def _exchange(transport: RecordingTransport) -> str:
    return exchange_authorization_code(
        issuer="http://issuer.test/realms/platform",
        client_id="pyforge-cli",
        redirect_uri="http://127.0.0.1:1/callback",
        code="abc",
        code_verifier="verifier",
        transport=transport,
    )


@pytest.mark.parametrize(
    "raw",
    [b"not json", b"\xff\xfe", b"[1, 2]", b'"a string"'],
    ids=["malformed-json", "undecodable", "json-list", "json-scalar"],
)
def test_exchange_rejects_an_invalid_token_response(raw: bytes) -> None:
    with pytest.raises(PkceLoginError, match="invalid response"):
        _exchange(RecordingTransport(raw))


@pytest.mark.parametrize(
    "payload",
    [{}, {"access_token": ""}, {"access_token": "   "}, {"access_token": 42}],
    ids=["absent", "empty", "blank", "non-string"],
)
def test_exchange_rejects_a_missing_access_token(payload: dict) -> None:
    with pytest.raises(PkceLoginError, match="missing access_token"):
        _exchange(RecordingTransport(json.dumps(payload).encode("utf-8")))


def test_exchange_strips_the_access_token() -> None:
    raw = json.dumps({"access_token": "  padded  "}).encode("utf-8")
    assert _exchange(RecordingTransport(raw)) == "padded"


def test_bind_loopback_server_gives_up_after_two_os_errors(monkeypatch) -> None:
    attempts: list[int] = []

    def _refuse(address, handler):
        attempts.append(1)
        raise OSError(98, "address in use")

    monkeypatch.setattr(oidc_pkce_mod, "HTTPServer", _refuse)
    with pytest.raises(PkceLoginError, match="could not bind") as excinfo:
        oidc_pkce_mod._bind_loopback_server()
    assert len(attempts) == 2
    assert isinstance(excinfo.value.__cause__, OSError)


def test_bind_loopback_server_retries_once(monkeypatch) -> None:
    real_server_cls = HTTPServer
    attempts: list[int] = []

    def _flaky(address, handler):
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError(98, "address in use")
        return real_server_cls(address, handler)

    monkeypatch.setattr(oidc_pkce_mod, "HTTPServer", _flaky)
    server, port = oidc_pkce_mod._bind_loopback_server()
    server.server_close()
    assert len(attempts) == 2
    assert port > 0


def test_capture_authorization_code_binds_its_own_server_when_none_given(
    monkeypatch,
) -> None:
    """``server=None`` takes the ``owns_server`` path: the function binds
    (via ``_bind_loopback_server``, stubbed here so the test learns the
    port), serves the one callback, and releases the server it owns."""
    server, port = oidc_pkce_mod._bind_loopback_server()
    monkeypatch.setattr(oidc_pkce_mod, "_bind_loopback_server", lambda: (server, port))
    thread = threading.Thread(target=lambda: _hit(f"http://127.0.0.1:{port}/callback?code=owned"), daemon=True)
    thread.start()
    result = capture_authorization_code(timeout_s=5.0)
    thread.join(timeout=2.0)
    assert result.code == "owned"
    assert result.error is None


def test_capture_authorization_code_with_no_recorded_result(monkeypatch) -> None:
    """The ``result is None`` guard after the event fires: a handler that
    signalled shutdown without recording a result is reported as an error,
    not returned as ``None``."""
    import types

    server, _port = _bind_test_server()

    class _EventThatFiresEmpty:
        def wait(self, timeout: float) -> bool:
            oidc_pkce_mod._CallbackHandler.result = None
            return True

    # Shim only the module's OWN `threading` reference (a real `Thread`, a
    # fake `Event`) -- patching `threading.Event` globally would break
    # `threading.Thread`'s internal `_started` event.
    monkeypatch.setattr(
        oidc_pkce_mod,
        "threading",
        types.SimpleNamespace(Event=_EventThatFiresEmpty, Thread=threading.Thread),
    )
    with pytest.raises(PkceLoginError, match="no authorization response"):
        capture_authorization_code(timeout_s=1.0, server=server)


def _run_login_with(open_browser, *, timeout_s: float = 5.0) -> tuple[PkceLogin, BaseException | None]:
    login = PkceLogin(
        issuer="http://issuer.test/realms/platform",
        client_id="pyforge-cli",
        timeout_s=timeout_s,
        transport=RecordingTransport(b'{"access_token": "unused"}'),
        open_browser=open_browser,
    )
    errors: list[BaseException] = []

    def _go() -> None:
        try:
            login.run()
        except BaseException as exc:  # noqa: BLE001 -- surfaced to the assertion
            errors.append(exc)

    thread = threading.Thread(target=_go, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s + 3.0)
    return login, (errors[0] if errors else None)


def _redirect_uri_of(url: str) -> str:
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["redirect_uri"][0]


def test_pkce_login_surfaces_the_idp_error_description() -> None:
    def deliver_error(url: str) -> None:
        _hit(f"{_redirect_uri_of(url)}?error=access_denied&error_description=User%20declined")

    login, error = _run_login_with(deliver_error)
    assert isinstance(error, PkceLoginError)
    assert str(error) == "User declined"
    # The property is populated before the browser is opened.
    assert login.authorization_url.startswith("http://issuer.test/realms/platform/protocol/openid-connect/auth?")


def test_pkce_login_falls_back_to_the_bare_error_code() -> None:
    def deliver_error(url: str) -> None:
        _hit(f"{_redirect_uri_of(url)}?error=server_error")

    _login, error = _run_login_with(deliver_error)
    assert isinstance(error, PkceLoginError)
    assert str(error) == "server_error"


def test_pkce_login_rejects_a_callback_with_neither_code_nor_error() -> None:
    def deliver_nothing(url: str) -> None:
        _hit(f"{_redirect_uri_of(url)}")

    _login, error = _run_login_with(deliver_nothing)
    assert isinstance(error, PkceLoginError)
    assert "missing code" in str(error)


def test_pkce_login_swallows_a_browser_launch_failure_then_times_out() -> None:
    """``open_browser`` raising ``OSError`` is tolerated (the URL was
    already printed for the operator to open by hand); with nobody hitting
    the callback the waiter's own timeout is what surfaces."""

    def no_browser(url: str) -> None:
        raise OSError("no display")

    _login, error = _run_login_with(no_browser, timeout_s=0.3)
    assert isinstance(error, PkceLoginError)
    assert "timed out" in str(error)


def test_pkce_login_defaults_to_webbrowser_open(monkeypatch) -> None:
    opened: list[str] = []

    def _fake_open(url: str) -> bool:
        opened.append(url)
        _hit(f"{_redirect_uri_of(url)}?error=x")
        return True

    monkeypatch.setattr(oidc_pkce_mod.webbrowser, "open", _fake_open)
    login = PkceLogin(issuer="http://issuer.test/realms/platform", timeout_s=5.0)
    with pytest.raises(PkceLoginError, match="^x$"):
        login.run()
    assert opened == [login.authorization_url]
