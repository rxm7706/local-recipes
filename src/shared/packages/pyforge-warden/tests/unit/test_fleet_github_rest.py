"""Story 16.1 — GET-only GitHub REST org listing (fixture organisation only).

Every test drives the real client, the real urllib and the real http.client
through a fake socket server: ``HTTPConnection.connect`` and
``HTTPSConnection.connect`` hand the connection a scripted socket instead of
opening one. No socket opens (an autouse guard refuses any connect the fake did
not take), no ``gh`` runs, no host is contacted.

At every connect, send and response read the fake also walks the live call
stack, from the library frame that reached it up to the test, and records any
frame local that holds the token (by ``repr``, or as a urllib ``Request``
header). Every test asserts that record is empty: the token is in no urllib,
http.client or client frame, by construction, not only after a failure.
"""

from __future__ import annotations

import http
import http.client
import io
import json
import logging
import ssl
import sys
import traceback
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from types import FrameType, TracebackType
from typing import Any

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.warden.fleet_github_rest import (
    REQUEST_TIMEOUT_SECONDS,
    FleetInventoryApiError,
    GitHubRestOrgReposClient,
    HttpMethodRefusedError,
    ListedRepo,
    OffApiHostRefusedError,
    RedactedBytes,
    _ApiHTTPSHandler,
    _Credential,
    _listed_repo_from_api,
    _parse_link_next,
    is_api_url,
)

_EXAMPLE_ORG = "example-org"
_SENTINEL = "sentinel-token-must-not-leak-16-1"
_BEARER = f"Bearer {_SENTINEL}"
_API = "https://api.github.com"
_FIRST_PAGE = f"{_API}/orgs/{_EXAMPLE_ORG}/repos?type=all&per_page=100"
_SECOND_PAGE = f"{_API}/orgs/{_EXAMPLE_ORG}/repos?type=all&per_page=100&page=2"
_OFF_HOST = "https://evil.example/collect"
_PARTIAL_BODY = (
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n"
    b'[{"full_name": "example-org/alpha"'
)


class _SoftTimeLimitExceeded(Exception):  # noqa: N818 -- mirrors billiard's name and base (Exception)
    """Stand-in for Celery's ``SoftTimeLimitExceeded`` (an ``Exception``; celery is not in this env)."""


@pytest.fixture(autouse=True)
def _no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """A connection the fake did not take fails loudly instead of connecting."""

    def _refuse(self: object) -> None:
        msg = "a fleet-inventory unit test tried to open a socket"
        raise AssertionError(msg)

    monkeypatch.setattr(http.client.HTTPConnection, "connect", _refuse)
    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _refuse)


# --- the fake socket server -----------------------------------------------------------------------


def _holds_sentinel(value: object) -> bool:
    if isinstance(value, urllib.request.Request) and any(_SENTINEL in str(v) for _, v in value.header_items()):
        return True
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001 -- an object whose repr fails holds nothing we can see
        return False
    return _SENTINEL in text


def _stack_leaks(where: str) -> list[str]:
    """Locals holding the token in the library frames between this fake and the test."""
    frame: FrameType | None = sys._getframe(1)
    while frame is not None and frame.f_code.co_filename == __file__:
        frame = frame.f_back
    leaks: list[str] = []
    while frame is not None and frame.f_code.co_filename != __file__:
        leaks.extend(
            f"{where}: {frame.f_code.co_qualname} local {name!r}"
            for name, value in frame.f_locals.items()
            if _holds_sentinel(value)
        )
        frame = frame.f_back
    return leaks


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None
    timeout: float | None


def _http_response(status: int, *, body: bytes = b"", headers: dict[str, str] | None = None) -> bytes:
    lines = [f"HTTP/1.1 {status} {http.HTTPStatus(status).phrase}"]
    lines.extend(f"{key}: {value}" for key, value in (headers or {}).items())
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


def _json_page(payload: object, *, next_url: str | None = None) -> bytes:
    headers = {"Content-Type": "application/json"}
    if next_url is not None:
        headers["Link"] = f'<{next_url}>; rel="next"'
    return _http_response(200, body=json.dumps(payload).encode(), headers=headers)


class _ScriptedReader(io.BytesIO):
    """Serves ``head``, then raises ``then`` (or reports EOF) once it runs dry."""

    def __init__(self, head: bytes, then: BaseException | None, fake: _FakeGitHub) -> None:
        super().__init__(head)
        self._then = then
        self._fake = fake

    def _dry(self, data: bytes) -> bytes:
        if not data and self._then is not None:
            self._fake.stack_leaks.extend(_stack_leaks("read"))
            raise self._then
        return data

    def readline(self, size: int | None = -1) -> bytes:
        return self._dry(super().readline(size))

    def read(self, size: int | None = -1) -> bytes:
        return self._dry(super().read(size))


_Route = bytes | Callable[["_FakeGitHub"], io.BytesIO]


@dataclass
class _FakeGitHub:
    """Answers by URL from what the client really put on the wire; records each exchange."""

    routes: dict[str, _Route] = field(default_factory=dict)
    connect_error: BaseException | None = None
    send_error: BaseException | None = None
    send_error_call: int = 1
    exchanges: list[_Exchange] = field(default_factory=list)
    stack_leaks: list[str] = field(default_factory=list)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> _FakeGitHub:
        def _connect(connection: http.client.HTTPConnection) -> None:
            self.stack_leaks.extend(_stack_leaks("connect"))
            if self.connect_error is not None:
                raise self.connect_error
            connection.sock = _ServerSocket(self, connection)  # type: ignore[assignment]

        monkeypatch.setattr(http.client.HTTPConnection, "connect", _connect)
        monkeypatch.setattr(http.client.HTTPSConnection, "connect", _connect)
        return self

    def script(self, url: str, head: bytes, then: BaseException | None) -> None:
        self.routes[url] = lambda fake: _ScriptedReader(head, then, fake)

    def client(self, token: str = _SENTINEL) -> GitHubRestOrgReposClient:
        return GitHubRestOrgReposClient(token=token)


class _ServerSocket:
    def __init__(self, fake: _FakeGitHub, connection: http.client.HTTPConnection) -> None:
        self._fake = fake
        self._scheme = "https" if isinstance(connection, http.client.HTTPSConnection) else "http"
        default = 443 if self._scheme == "https" else 80
        self._origin = f"{self._scheme}://{connection.host}" + (
            "" if connection.port == default else f":{connection.port}"
        )
        self._timeout = connection.timeout
        self._sent = bytearray()
        self._calls = 0

    def sendall(self, data: bytes, *args: object) -> None:
        self._calls += 1
        self._fake.stack_leaks.extend(_stack_leaks("send"))
        if self._fake.send_error is not None and self._calls == self._fake.send_error_call:
            raise self._fake.send_error
        self._sent += bytes(data)

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        self._fake.stack_leaks.extend(_stack_leaks("getresponse"))
        head = bytes(self._sent).split(b"\r\n\r\n", 1)[0].decode("latin-1").split("\r\n")
        method, target, _version = head[0].split(" ", 2)
        headers = [line.split(":", 1) for line in head[1:]]
        auth = [value.strip() for name, value in headers if name.strip().lower() == "authorization"]
        url = f"{self._origin}{target}"
        self._fake.exchanges.append(
            _Exchange(method=method, url=url, authorization=auth[0] if auth else None, timeout=self._timeout)
        )
        route = self._fake.routes.get(url, _http_response(404, body=b"{}"))
        return io.BytesIO(route) if isinstance(route, bytes) else route(self._fake)

    def close(self) -> None:
        pass


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeGitHub:
    return _FakeGitHub().install(monkeypatch)


def _serve_two_pages(fake: _FakeGitHub) -> None:
    fake.routes[_FIRST_PAGE] = _json_page([_repo("alpha"), _repo("beta", branch="develop")], next_url=_SECOND_PAGE)
    fake.routes[_SECOND_PAGE] = _json_page([_repo("archived-one", archived=True)])


def _repo(name: str, *, archived: bool = False, branch: str = "main") -> dict[str, object]:
    return {
        "full_name": f"{_EXAMPLE_ORG}/{name}",
        "default_branch": branch,
        "clone_url": f"https://github.com/{_EXAMPLE_ORG}/{name}.git",
        "archived": archived,
    }


# --- AC3 pagination, AC6 GET-only on the real request path (F3) ----------------------------------


def test_pagination_reads_every_page_through_link_next(fake: _FakeGitHub) -> None:
    _serve_two_pages(fake)
    listing = fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [repo.full_name for repo in listing.repos] == [
        f"{_EXAMPLE_ORG}/alpha",
        f"{_EXAMPLE_ORG}/beta",
        f"{_EXAMPLE_ORG}/archived-one",
    ]
    assert listing.skipped == ()
    assert [exchange.url for exchange in fake.exchanges] == [_FIRST_PAGE, _SECOND_PAGE]
    assert listing.repos[2] == ListedRepo(
        full_name=f"{_EXAMPLE_ORG}/archived-one",
        default_branch="main",
        clone_url=f"https://github.com/{_EXAMPLE_ORG}/archived-one.git",
        archived=True,
    )
    assert fake.stack_leaks == []


def test_every_outgoing_request_is_a_get(fake: _FakeGitHub) -> None:
    """The method is read off the bytes the client really sent, not off a fake."""
    _serve_two_pages(fake)
    fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.method for exchange in fake.exchanges] == ["GET", "GET"]


def test_each_request_uses_the_request_timeout(fake: _FakeGitHub) -> None:
    _serve_two_pages(fake)
    fake.client().list_org_repos(_EXAMPLE_ORG)
    assert {exchange.timeout for exchange in fake.exchanges} == {REQUEST_TIMEOUT_SECONDS}


def test_http_client_refuses_non_get_before_a_socket_opens(fake: _FakeGitHub) -> None:
    _serve_two_pages(fake)
    client = fake.client()
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(HttpMethodRefusedError):
            client.request(method, _FIRST_PAGE)
    assert fake.exchanges == []


def test_request_allows_get(fake: _FakeGitHub) -> None:
    _serve_two_pages(fake)
    fake.client().request("get", _FIRST_PAGE)
    assert [(exchange.method, exchange.url) for exchange in fake.exchanges] == [("GET", _FIRST_PAGE)]


# --- F1 / P1: the token goes only to https://api.github.com, and lives in no library frame -------


def test_the_token_reaches_the_wire_but_no_library_frame(fake: _FakeGitHub) -> None:
    """On the wire the API sees the real credential; urllib's Request and every frame never hold it."""
    _serve_two_pages(fake)
    fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.authorization for exchange in fake.exchanges] == [_BEARER, _BEARER]
    assert fake.stack_leaks == []


def test_the_pinned_handler_sends_the_credential_only_to_the_api_origin(fake: _FakeGitHub) -> None:
    """Structural pin, independent of the redirect handler: another origin gets no Authorization."""
    for url in ("https://evil.example/x", "https://api.github.com:8443/x", "https://api.github.com/x"):
        fake.routes[url] = _http_response(200, body=b"[]")
    opener = urllib.request.build_opener(_ApiHTTPSHandler(_Credential(_SENTINEL), "api.github.com"))
    for url in ("https://evil.example/x", "https://api.github.com:8443/x", "https://api.github.com/x"):
        with opener.open(url, timeout=5) as response:
            response.read()
    assert [exchange.authorization for exchange in fake.exchanges] == [None, None, _BEARER]
    assert fake.stack_leaks == []


def test_credential_and_fragments_never_show_the_token() -> None:
    credential = _Credential(_SENTINEL)
    assert _SENTINEL not in repr(credential)
    assert _SENTINEL not in str(credential)
    assert b"".join(credential.fragments) == _BEARER.encode()
    for fragment in credential.fragments:
        assert isinstance(fragment, RedactedBytes)
        assert repr(fragment) == str(fragment) == "<credential bytes redacted>"


@pytest.mark.parametrize(
    "target",
    [
        _OFF_HOST,
        "http://api.github.com/orgs/example-org/repos",
        "https://api.github.com:8443/orgs/example-org/repos",
        "https://user@api.github.com/orgs/example-org/repos",
    ],
    ids=["off-host", "http-downgrade", "other-port", "userinfo"],
)
def test_redirect_off_the_api_origin_is_refused_and_never_followed(fake: _FakeGitHub, target: str) -> None:
    fake.routes[_FIRST_PAGE] = _http_response(302, headers={"Location": target})
    with pytest.raises(OffApiHostRefusedError, match="refused a redirect") as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.url for exchange in fake.exchanges] == [_FIRST_PAGE]
    assert _SENTINEL not in str(caught.value)
    assert _SENTINEL not in repr(caught.value)
    assert fake.stack_leaks == []


def test_redirect_within_the_api_origin_carries_the_token(fake: _FakeGitHub) -> None:
    moved = f"{_API}/organizations/1/repos?type=all&per_page=100"
    fake.routes[_FIRST_PAGE] = _http_response(301, headers={"Location": moved})
    fake.routes[moved] = _json_page([_repo("alpha")])
    listing = fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [repo.full_name for repo in listing.repos] == [f"{_EXAMPLE_ORG}/alpha"]
    assert [exchange.url for exchange in fake.exchanges] == [_FIRST_PAGE, moved]
    assert [exchange.method for exchange in fake.exchanges] == ["GET", "GET"]
    assert [exchange.authorization for exchange in fake.exchanges] == [_BEARER, _BEARER]
    assert fake.stack_leaks == []


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/orgs/example-org/repos?page=2",
        "http://api.github.com/orgs/example-org/repos?page=2",
    ],
    ids=["cross-host", "http"],
)
def test_pagination_link_off_the_api_origin_is_refused(fake: _FakeGitHub, next_url: str) -> None:
    fake.routes[_FIRST_PAGE] = _json_page([_repo("alpha")], next_url=next_url)
    with pytest.raises(OffApiHostRefusedError, match="refused a pagination link"):
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.url for exchange in fake.exchanges] == [_FIRST_PAGE]


def test_request_off_the_api_origin_is_refused_before_a_socket_opens(fake: _FakeGitHub) -> None:
    with pytest.raises(OffApiHostRefusedError, match="refused a request"):
        fake.client().request("GET", _OFF_HOST)
    assert fake.exchanges == []


def test_is_api_url() -> None:
    assert is_api_url(_FIRST_PAGE)
    assert is_api_url("https://API.GITHUB.COM:443/orgs/x/repos")
    assert not is_api_url("http://api.github.com/orgs/x/repos")
    assert not is_api_url("https://api.github.com.evil.example/x")
    assert not is_api_url("https://api.github.com:notaport/x")
    assert not is_api_url("https://user:pw@api.github.com/x")


# --- AC7: no failure path renders the token --------------------------------------------------------


def _shown_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return chain


def _library_frames(tb: TracebackType | None) -> list[FrameType]:
    frames = []
    while tb is not None:
        if tb.tb_frame.f_code.co_filename != __file__:
            frames.append(tb.tb_frame)
        tb = tb.tb_next
    return frames


def _traceback_leaks(exc: BaseException) -> list[str]:
    """Walk every library frame's locals in the raised AND the suppressed tracebacks."""
    leaks: list[str] = []
    seen: set[int] = set()
    pending: list[BaseException] = [exc]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for frame in _library_frames(current.__traceback__):
            leaks.extend(
                f"{type(current).__name__}: {frame.f_code.co_qualname} local {name!r}"
                for name, value in frame.f_locals.items()
                if _holds_sentinel(value)
            )
        pending.extend(link for link in (current.__cause__, current.__context__) if link is not None)
    return leaks


def _assert_sentinel_absent(exc: BaseException, caplog: pytest.LogCaptureFixture) -> None:
    logging.getLogger("tests.fleet_github_rest").exception("listing failed", exc_info=exc)
    for link in _shown_chain(exc):
        assert _SENTINEL not in str(link)
        assert _SENTINEL not in repr(link)
    assert caplog.records
    assert _SENTINEL not in caplog.text
    # The formatted traceback, then every library frame's locals (raised and suppressed). The
    # test's own frames are left out: the fake records what reached the wire, on purpose.
    assert _SENTINEL not in "".join(traceback.TracebackException.from_exception(exc).format())
    assert _traceback_leaks(exc) == []


def _cleared_below_get_json(exc: BaseException) -> bool:
    """Every frame the suppressed error passed through below ``_get_json`` has no locals left."""
    frames = _library_frames(exc.__traceback__)
    names = [frame.f_code.co_name for frame in frames]
    below = frames[names.index("_get_json") + 1 :] if "_get_json" in names else frames
    return bool(below) and all(not frame.f_locals for frame in below)


def test_http_error_path_never_carries_the_token(fake: _FakeGitHub, caplog: pytest.LogCaptureFixture) -> None:
    fake.routes[_FIRST_PAGE] = _http_response(503, body=b'{"message": "unavailable"}')
    with pytest.raises(FleetInventoryApiError, match="HTTP 503") as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    _assert_sentinel_absent(caught.value, caplog)
    assert fake.stack_leaks == []


def test_url_error_path_never_carries_the_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = _FakeGitHub(connect_error=ConnectionRefusedError(111, "Connection refused")).install(monkeypatch)
    with pytest.raises(FleetInventoryApiError, match="request failed") as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__suppress_context__ is True
    assert isinstance(caught.value.__context__, urllib.error.URLError)
    _assert_sentinel_absent(caught.value, caplog)
    assert fake.stack_leaks == []


@pytest.mark.parametrize(
    ("head", "then", "kind"),
    [
        (b"", TimeoutError("timed out"), "TimeoutError: timed out"),
        (b"", ConnectionResetError(104, "Connection reset by peer"), "ConnectionResetError"),
        (b"", None, "RemoteDisconnected"),
        (b"", ssl.SSLEOFError(8, "EOF occurred in violation of protocol"), "SSLEOFError"),
        (_PARTIAL_BODY, None, "IncompleteRead"),
    ],
    ids=["read-timeout", "reset-in-getresponse", "remote-disconnected", "ssl-eof", "incomplete-read"],
)
def test_unwrapped_transport_error_is_typed_and_never_renders_the_token(
    fake: _FakeGitHub,
    caplog: pytest.LogCaptureFixture,
    head: bytes,
    then: BaseException | None,
    kind: str,
) -> None:
    """urllib wraps only ``h.request()``; what ``getresponse()`` and ``read()`` raise is caught here."""
    fake.script(_FIRST_PAGE, head, then)
    with pytest.raises(FleetInventoryApiError, match=f"transport failed: {kind}") as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert caught.value.__context__ is not None
    assert not isinstance(caught.value.__context__, urllib.error.URLError)
    _assert_sentinel_absent(caught.value, caplog)
    assert _cleared_below_get_json(caught.value.__context__)
    assert fake.stack_leaks == []


_PHASES = ("connect", "send", "getresponse")


def _fail_in(fake: _FakeGitHub, phase: str, error: BaseException) -> None:
    if phase == "connect":
        fake.connect_error = error
    elif phase == "send":
        fake.send_error, fake.send_error_call = error, 2  # the call that carries the first credential fragment
    else:
        fake.script(_FIRST_PAGE, b"", error)


@pytest.mark.parametrize("phase", _PHASES)
@pytest.mark.parametrize(
    "error",
    [_SoftTimeLimitExceeded(), RuntimeError("an untyped error inside urllib")],
    ids=["soft-time-limit", "runtime-error"],
)
def test_any_exception_in_urllib_is_typed_and_its_frames_hold_no_token(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    phase: str,
    error: Exception,
) -> None:
    """P1: an error ``_get_json`` once let escape untyped, at connect, send or ``getresponse()``."""
    fake = _FakeGitHub().install(monkeypatch)
    _fail_in(fake, phase, error)
    with pytest.raises(FleetInventoryApiError, match=f"transport failed: {type(error).__name__}") as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__context__ is error
    _assert_sentinel_absent(caught.value, caplog)
    assert _cleared_below_get_json(error)
    assert fake.stack_leaks == []


@pytest.mark.parametrize("phase", _PHASES)
def test_a_base_exception_propagates_with_its_frames_cleared(monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    fake = _FakeGitHub().install(monkeypatch)
    interrupt = KeyboardInterrupt()
    _fail_in(fake, phase, interrupt)
    with pytest.raises(KeyboardInterrupt) as caught:
        fake.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value is interrupt
    assert _cleared_below_get_json(interrupt)
    assert _traceback_leaks(interrupt) == []
    assert fake.stack_leaks == []


def test_a_malformed_token_is_refused_before_any_request(fake: _FakeGitHub, caplog: pytest.LogCaptureFixture) -> None:
    """A token that could inject a header is refused; no frame on the refusal path keeps it."""
    with pytest.raises(FleetInventoryApiError, match="not one printable token") as caught:
        GitHubRestOrgReposClient(token=f"{_SENTINEL}\r\nX-Injected: 1")
    _assert_sentinel_absent(caught.value, caplog)
    assert fake.exchanges == []


def test_invalid_json_is_refused(fake: _FakeGitHub) -> None:
    fake.routes[_FIRST_PAGE] = _http_response(200, body=b"not-json")
    with pytest.raises(FleetInventoryApiError, match="invalid JSON"):
        fake.client().list_org_repos(_EXAMPLE_ORG)


def test_list_org_repos_rejects_non_array_payload(fake: _FakeGitHub) -> None:
    fake.routes[_FIRST_PAGE] = _json_page({"error": "nope"})
    with pytest.raises(FleetInventoryApiError, match="JSON array"):
        fake.client().list_org_repos(_EXAMPLE_ORG)


def test_pagination_rejects_repeated_link_url(fake: _FakeGitHub) -> None:
    fake.routes[_FIRST_PAGE] = _json_page([], next_url=_SECOND_PAGE)
    fake.routes[_SECOND_PAGE] = _json_page([], next_url=_SECOND_PAGE)
    with pytest.raises(FleetInventoryApiError, match="repeated"):
        fake.client().list_org_repos(_EXAMPLE_ORG)


def test_client_repr_redacts_the_token() -> None:
    client = GitHubRestOrgReposClient(token=_SENTINEL)
    assert _SENTINEL not in repr(client)
    assert "redacted" in repr(client)
    assert all(not _holds_sentinel(value) for value in vars(client).values())


# --- M6: an incomplete entry is recorded, never defaulted or dropped silently ----------------------


def test_incomplete_entries_are_recorded_not_defaulted_or_dropped(fake: _FakeGitHub) -> None:
    no_branch = _repo("no-branch")
    del no_branch["default_branch"]
    no_clone = _repo("no-clone")
    no_clone["clone_url"] = ""
    no_archived = _repo("no-archived")
    del no_archived["archived"]
    payload: list[Any] = ["not-a-dict", {"default_branch": "main"}, no_branch, no_clone, no_archived, _repo("good")]
    fake.routes[_FIRST_PAGE] = _json_page(payload)
    listing = fake.client().list_org_repos(_EXAMPLE_ORG)
    assert [repo.full_name for repo in listing.repos] == [f"{_EXAMPLE_ORG}/good"]
    assert [(entry.page, entry.position, entry.full_name, entry.reason) for entry in listing.skipped] == [
        (1, 1, None, "entry is not a JSON object"),
        (1, 2, None, "missing full_name, clone_url"),
        (1, 3, f"{_EXAMPLE_ORG}/no-branch", "missing default_branch"),
        (1, 4, f"{_EXAMPLE_ORG}/no-clone", "missing clone_url"),
        (1, 5, f"{_EXAMPLE_ORG}/no-archived", "archived is not a boolean"),
    ]


def test_listed_repo_from_api_never_defaults_the_branch() -> None:
    entry = {"full_name": "example-org/r", "default_branch": "", "clone_url": "https://c.git", "archived": False}
    assert _listed_repo_from_api(entry) == "missing default_branch"


def test_parse_link_next() -> None:
    assert _parse_link_next(None) is None
    assert _parse_link_next("") is None
    assert _parse_link_next('rel="prev"') is None
    assert _parse_link_next('<https://api.github.com/next>; rel="next"') == "https://api.github.com/next"


def test_fleet_inventory_api_error_is_pyforge_error() -> None:
    assert issubclass(FleetInventoryApiError, PyforgeError)
    assert issubclass(OffApiHostRefusedError, FleetInventoryApiError)
