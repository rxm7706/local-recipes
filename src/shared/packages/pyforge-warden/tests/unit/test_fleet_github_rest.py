"""Story 16.1 — GET-only GitHub REST org listing (fixture organisation only).

Every test drives the real client through stub urllib transport handlers: no
socket opens (an autouse guard fails any connect), no ``gh`` runs, no host is
contacted.
"""

from __future__ import annotations

import http.client
import io
import json
import logging
import ssl
import traceback
import urllib.error
import urllib.request
import urllib.response
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import Message

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.warden.fleet_github_rest import (
    FleetInventoryApiError,
    GitHubRestOrgReposClient,
    HttpMethodRefusedError,
    ListedRepo,
    OffApiHostRefusedError,
    _listed_repo_from_api,
    _parse_link_next,
    is_api_url,
)

_EXAMPLE_ORG = "example-org"
_SENTINEL = "sentinel-token-must-not-leak-16-1"
_API = "https://api.github.com"
_FIRST_PAGE = f"{_API}/orgs/{_EXAMPLE_ORG}/repos?type=all&per_page=100"
_SECOND_PAGE = f"{_API}/orgs/{_EXAMPLE_ORG}/repos?type=all&per_page=100&page=2"
_OFF_HOST = "https://evil.example/collect"


@pytest.fixture(autouse=True)
def _no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """A request that slips past the stub transport fails loudly instead of connecting."""

    def _refuse(self: object) -> None:
        msg = "a fleet-inventory unit test tried to open a socket"
        raise AssertionError(msg)

    monkeypatch.setattr(http.client.HTTPConnection, "connect", _refuse)
    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _refuse)


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None
    authorization_redirectable: bool


_Responder = Callable[[urllib.request.Request], urllib.response.addinfourl]


def _repo(name: str, *, archived: bool = False, branch: str = "main") -> dict[str, object]:
    return {
        "full_name": f"{_EXAMPLE_ORG}/{name}",
        "default_branch": branch,
        "clone_url": f"https://github.com/{_EXAMPLE_ORG}/{name}.git",
        "archived": archived,
    }


def _reply(
    req: urllib.request.Request,
    status: int,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> urllib.response.addinfourl:
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    response = urllib.response.addinfourl(io.BytesIO(body), message, req.full_url, status)
    response.msg = "stub"  # urllib's HTTP handlers set .msg on a response; addinfourl lacks it
    return response


def _json(req: urllib.request.Request, payload: object, *, link: str | None = None) -> urllib.response.addinfourl:
    headers = {"Content-Type": "application/json"}
    if link is not None:
        headers["Link"] = link
    return _reply(req, 200, body=json.dumps(payload).encode(), headers=headers)


@dataclass
class _StubTransport:
    """Answers by full URL and records every request the opener really sends."""

    routes: dict[str, _Responder]
    exchanges: list[_Exchange] = field(default_factory=list)

    def respond(self, req: urllib.request.Request) -> urllib.response.addinfourl:
        self.exchanges.append(
            _Exchange(
                method=req.get_method(),
                url=req.full_url,
                authorization=req.get_header("Authorization"),
                authorization_redirectable="Authorization" in req.headers,
            )
        )
        responder = self.routes.get(req.full_url)
        if responder is None:
            return _reply(req, 200, body=b"[]")
        return responder(req)

    def handlers(self) -> list[urllib.request.BaseHandler]:
        return [_StubHTTPS(self), _StubHTTP(self)]

    def client(self, token: str = _SENTINEL) -> GitHubRestOrgReposClient:
        return GitHubRestOrgReposClient(token=token, handlers=self.handlers())


class _StubHTTPS(urllib.request.HTTPSHandler):
    def __init__(self, transport: _StubTransport) -> None:
        super().__init__()
        self._transport = transport

    def https_open(self, req: urllib.request.Request) -> urllib.response.addinfourl:
        return self._transport.respond(req)


class _StubHTTP(urllib.request.HTTPHandler):
    def __init__(self, transport: _StubTransport) -> None:
        super().__init__()
        self._transport = transport

    def http_open(self, req: urllib.request.Request) -> urllib.response.addinfourl:
        return self._transport.respond(req)


def _two_pages() -> _StubTransport:
    return _StubTransport(
        routes={
            _FIRST_PAGE: lambda req: _json(
                req, [_repo("alpha"), _repo("beta", branch="develop")], link=f'<{_SECOND_PAGE}>; rel="next"'
            ),
            _SECOND_PAGE: lambda req: _json(req, [_repo("archived-one", archived=True)]),
        }
    )


# --- AC3 pagination, AC6 GET-only on the real request path (F3) ----------------------------------


def test_pagination_reads_every_page_through_link_next() -> None:
    transport = _two_pages()
    listing = transport.client().list_org_repos(_EXAMPLE_ORG)
    assert [repo.full_name for repo in listing.repos] == [
        f"{_EXAMPLE_ORG}/alpha",
        f"{_EXAMPLE_ORG}/beta",
        f"{_EXAMPLE_ORG}/archived-one",
    ]
    assert listing.skipped == ()
    assert [exchange.url for exchange in transport.exchanges] == [_FIRST_PAGE, _SECOND_PAGE]
    assert listing.repos[2] == ListedRepo(
        full_name=f"{_EXAMPLE_ORG}/archived-one",
        default_branch="main",
        clone_url=f"https://github.com/{_EXAMPLE_ORG}/archived-one.git",
        archived=True,
    )


def test_every_outgoing_request_is_a_get() -> None:
    """The method is read off the request the opener really sends, not off a fake."""
    transport = _two_pages()
    transport.client().list_org_repos(_EXAMPLE_ORG)
    assert len(transport.exchanges) == 2
    assert [exchange.method for exchange in transport.exchanges] == ["GET", "GET"]


def test_http_client_refuses_non_get_before_a_socket_opens() -> None:
    transport = _two_pages()
    client = transport.client()
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(HttpMethodRefusedError):
            client.request(method, _FIRST_PAGE)
    assert transport.exchanges == []


def test_request_allows_get() -> None:
    transport = _two_pages()
    transport.client().request("get", _FIRST_PAGE)
    assert [(exchange.method, exchange.url) for exchange in transport.exchanges] == [("GET", _FIRST_PAGE)]


# --- F1: the token never leaves https://api.github.com ---------------------------------------------


def test_token_rides_as_an_unredirected_header() -> None:
    transport = _two_pages()
    transport.client().list_org_repos(_EXAMPLE_ORG)
    for exchange in transport.exchanges:
        assert exchange.authorization == f"Bearer {_SENTINEL}"
        assert exchange.authorization_redirectable is False


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
def test_redirect_off_the_api_origin_is_refused_and_never_followed(target: str) -> None:
    transport = _StubTransport(routes={_FIRST_PAGE: lambda req: _reply(req, 302, headers={"Location": target})})
    with pytest.raises(OffApiHostRefusedError, match="refused a redirect") as caught:
        transport.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.url for exchange in transport.exchanges] == [_FIRST_PAGE]
    assert _SENTINEL not in str(caught.value)
    assert _SENTINEL not in repr(caught.value)


def test_redirect_within_the_api_origin_keeps_the_token() -> None:
    moved = f"{_API}/organizations/1/repos?type=all&per_page=100"
    transport = _StubTransport(
        routes={
            _FIRST_PAGE: lambda req: _reply(req, 301, headers={"Location": moved}),
            moved: lambda req: _json(req, [_repo("alpha")]),
        }
    )
    listing = transport.client().list_org_repos(_EXAMPLE_ORG)
    assert [repo.full_name for repo in listing.repos] == [f"{_EXAMPLE_ORG}/alpha"]
    assert [exchange.url for exchange in transport.exchanges] == [_FIRST_PAGE, moved]
    assert [exchange.method for exchange in transport.exchanges] == ["GET", "GET"]
    assert transport.exchanges[1].authorization == f"Bearer {_SENTINEL}"
    assert transport.exchanges[1].authorization_redirectable is False


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/orgs/example-org/repos?page=2",
        "http://api.github.com/orgs/example-org/repos?page=2",
    ],
    ids=["cross-host", "http"],
)
def test_pagination_link_off_the_api_origin_is_refused(next_url: str) -> None:
    transport = _StubTransport(
        routes={_FIRST_PAGE: lambda req: _json(req, [_repo("alpha")], link=f'<{next_url}>; rel="next"')}
    )
    with pytest.raises(OffApiHostRefusedError, match="refused a pagination link"):
        transport.client().list_org_repos(_EXAMPLE_ORG)
    assert [exchange.url for exchange in transport.exchanges] == [_FIRST_PAGE]


def test_request_off_the_api_origin_is_refused_before_a_socket_opens() -> None:
    transport = _two_pages()
    with pytest.raises(OffApiHostRefusedError, match="refused a request"):
        transport.client().request("GET", _OFF_HOST)
    assert transport.exchanges == []


def test_client_refuses_a_second_redirect_policy() -> None:
    with pytest.raises(ValueError, match="redirect policy"):
        GitHubRestOrgReposClient(token=_SENTINEL, handlers=[urllib.request.HTTPRedirectHandler()])


def test_is_api_url() -> None:
    assert is_api_url(_FIRST_PAGE)
    assert is_api_url("https://API.GITHUB.COM:443/orgs/x/repos")
    assert not is_api_url("http://api.github.com/orgs/x/repos")
    assert not is_api_url("https://api.github.com.evil.example/x")
    assert not is_api_url("https://api.github.com:notaport/x")
    assert not is_api_url("https://user:pw@api.github.com/x")


# --- F4 (AC7): the sentinel token never reaches the real client's error text ----------------------


def _rendered_with_locals(exc: BaseException) -> str:
    """Each shown frame's locals, as a locals-printing log renderer sees them.

    Frames of this test module are left out: the stub transport records the
    Authorization header on purpose, and that record is not the client's.
    """
    parts: list[str] = []
    rendered: traceback.TracebackException | None = traceback.TracebackException.from_exception(
        exc, capture_locals=True
    )
    while rendered is not None:
        parts.extend(
            f"{frame.filename}:{frame.lineno} {frame.locals!r}"
            for frame in rendered.stack
            if frame.filename != __file__
        )
        parts.append("".join(rendered.format_exception_only()))
        rendered = rendered.__cause__ or (None if rendered.__suppress_context__ else rendered.__context__)
    return "\n".join(parts)


def _assert_sentinel_absent(exc: BaseException, caplog: pytest.LogCaptureFixture) -> None:
    logging.getLogger("tests.fleet_github_rest").exception("listing failed", exc_info=exc)
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    for link in chain:
        assert _SENTINEL not in str(link)
        assert _SENTINEL not in repr(link)
    assert caplog.records
    assert _SENTINEL not in caplog.text
    assert _SENTINEL not in _rendered_with_locals(exc)


def test_http_error_path_never_carries_the_token(caplog: pytest.LogCaptureFixture) -> None:
    transport = _StubTransport(routes={_FIRST_PAGE: lambda req: _reply(req, 503, body=b'{"message": "unavailable"}')})
    with pytest.raises(FleetInventoryApiError, match="HTTP 503") as caught:
        transport.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    _assert_sentinel_absent(caught.value, caplog)


def test_url_error_path_never_carries_the_token(caplog: pytest.LogCaptureFixture) -> None:
    def _reset(req: urllib.request.Request) -> urllib.response.addinfourl:
        raise urllib.error.URLError("connection reset")

    transport = _StubTransport(routes={_FIRST_PAGE: _reset})
    with pytest.raises(FleetInventoryApiError, match="request failed") as caught:
        transport.client().list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    _assert_sentinel_absent(caught.value, caplog)


def test_connection_failure_in_urllib_never_renders_the_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The real ``do_open`` holds the request headers as a local; the chain is cut there."""

    def _refused(self: object) -> None:
        raise ConnectionRefusedError(111, "Connection refused")

    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _refused)
    client = GitHubRestOrgReposClient(token=_SENTINEL)
    with pytest.raises(FleetInventoryApiError, match="request failed") as caught:
        client.list_org_repos(_EXAMPLE_ORG)
    _assert_sentinel_absent(caught.value, caplog)
    # Control: the suppressed urllib error does carry it, so cutting the chain is what keeps it out.
    suppressed = caught.value.__context__
    assert isinstance(suppressed, urllib.error.URLError)
    assert _SENTINEL in _rendered_with_locals(suppressed)


def test_client_repr_redacts_the_token() -> None:
    client = GitHubRestOrgReposClient(token=_SENTINEL)
    assert _SENTINEL not in repr(client)
    assert "redacted" in repr(client)


# --- N1 (iteration 2): transport errors urllib does not wrap -------------------------------------

_PARTIAL_BODY = (
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n"
    b'[{"full_name": "example-org/alpha"'
)


class _ScriptedReader(io.BytesIO):
    """Serves ``head``, then raises ``then`` (or reports EOF) once it runs dry."""

    def __init__(self, head: bytes, then: BaseException | None) -> None:
        super().__init__(head)
        self._then = then

    def _dry(self, data: bytes) -> bytes:
        if not data and self._then is not None:
            raise self._then
        return data

    def readline(self, size: int | None = -1) -> bytes:
        return self._dry(super().readline(size))

    def read(self, size: int | None = -1) -> bytes:
        return self._dry(super().read(size))


class _FakeSocket:
    """Accepts the request bytes and answers from a script; never touches the network."""

    def __init__(self, reader: _ScriptedReader) -> None:
        self._reader = reader

    def sendall(self, data: bytes) -> None:
        del data

    def makefile(self, mode: str, *args: object, **kwargs: object) -> _ScriptedReader:
        return self._reader

    def close(self) -> None:
        pass


def _serve_from_script(monkeypatch: pytest.MonkeyPatch, head: bytes, then: BaseException | None) -> None:
    """Replace the TLS connect with a scripted socket, so the real ``do_open``/``getresponse`` run."""

    def _connect(self: http.client.HTTPConnection) -> None:
        self.sock = _FakeSocket(_ScriptedReader(head, then))

    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _connect)


@pytest.mark.parametrize(
    ("head", "then", "kind", "in_do_open"),
    [
        (b"", TimeoutError("timed out"), "TimeoutError: timed out", True),
        (b"", ConnectionResetError(104, "Connection reset by peer"), "ConnectionResetError", True),
        (b"", None, "RemoteDisconnected", True),
        (b"", ssl.SSLEOFError(8, "EOF occurred in violation of protocol"), "SSLEOFError", True),
        (_PARTIAL_BODY, None, "IncompleteRead", False),
    ],
    ids=["read-timeout", "reset-in-getresponse", "remote-disconnected", "ssl-eof", "incomplete-read"],
)
def test_unwrapped_transport_error_is_typed_and_never_renders_the_token(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    head: bytes,
    then: BaseException | None,
    kind: str,
    in_do_open: bool,
) -> None:
    """urllib wraps only ``h.request()``; what ``getresponse()`` and ``read()`` raise is caught here."""
    _serve_from_script(monkeypatch, head, then)
    client = GitHubRestOrgReposClient(token=_SENTINEL)
    with pytest.raises(FleetInventoryApiError, match=f"transport failed: {kind}") as caught:
        client.list_org_repos(_EXAMPLE_ORG)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    _assert_sentinel_absent(caught.value, caplog)
    suppressed = caught.value.__context__
    assert suppressed is not None
    assert not isinstance(suppressed, urllib.error.URLError)
    if in_do_open:
        # Control: raised inside urllib's do_open, whose ``headers`` local holds the token.
        assert _SENTINEL in _rendered_with_locals(suppressed)


def test_header_value_error_never_echoes_the_token(caplog: pytest.LogCaptureFixture) -> None:
    """``http.client`` refuses an illegal header value by quoting it; the message keeps only the type."""
    client = GitHubRestOrgReposClient(token=f"{_SENTINEL}\nX-Injected: 1")
    with pytest.raises(FleetInventoryApiError, match=r"transport failed: ValueError$") as caught:
        client.list_org_repos(_EXAMPLE_ORG)
    _assert_sentinel_absent(caught.value, caplog)
    # Control: the refused ValueError itself quotes the token.
    assert _SENTINEL in str(caught.value.__context__)


def test_invalid_json_is_refused() -> None:
    transport = _StubTransport(routes={_FIRST_PAGE: lambda req: _reply(req, 200, body=b"not-json")})
    with pytest.raises(FleetInventoryApiError, match="invalid JSON"):
        transport.client().list_org_repos(_EXAMPLE_ORG)


def test_list_org_repos_rejects_non_array_payload() -> None:
    transport = _StubTransport(routes={_FIRST_PAGE: lambda req: _json(req, {"error": "nope"})})
    with pytest.raises(FleetInventoryApiError, match="JSON array"):
        transport.client().list_org_repos(_EXAMPLE_ORG)


def test_pagination_rejects_repeated_link_url() -> None:
    transport = _StubTransport(
        routes={
            _FIRST_PAGE: lambda req: _json(req, [], link=f'<{_SECOND_PAGE}>; rel="next"'),
            _SECOND_PAGE: lambda req: _json(req, [], link=f'<{_SECOND_PAGE}>; rel="next"'),
        }
    )
    with pytest.raises(FleetInventoryApiError, match="repeated"):
        transport.client().list_org_repos(_EXAMPLE_ORG)


# --- M6: an incomplete entry is recorded, never defaulted or dropped silently ----------------------


def test_incomplete_entries_are_recorded_not_defaulted_or_dropped() -> None:
    no_branch = _repo("no-branch")
    del no_branch["default_branch"]
    no_clone = _repo("no-clone")
    no_clone["clone_url"] = ""
    no_archived = _repo("no-archived")
    del no_archived["archived"]
    payload = ["not-a-dict", {"default_branch": "main"}, no_branch, no_clone, no_archived, _repo("good")]
    transport = _StubTransport(routes={_FIRST_PAGE: lambda req: _json(req, payload)})
    listing = transport.client().list_org_repos(_EXAMPLE_ORG)
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
