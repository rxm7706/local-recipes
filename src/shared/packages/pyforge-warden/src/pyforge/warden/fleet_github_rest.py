"""GET-only GitHub REST org listing for fleet inventory (Story 16.1).

Lives in pyforge-warden so django_warden_fabric stays free of raw HTTP imports
(platform ``test_portal_raw_http_to_a_service_is_review_blocking``).

The bearer token never leaves ``https://<api_host>``, and no urllib,
http.client or client frame local ever holds it:

- The client keeps it only as a ``_Credential``: redacted ``bytes`` fragments of
  ``Bearer <token>`` whose ``repr``/``str`` never show their content.
- urllib's ``Request`` never carries an Authorization header. ``_ApiHTTPSHandler``
  opens an ``_ApiConnection`` holding the credential only when the request URL is
  ``https://<api_host>`` on the default port. That connection adds an Authorization
  *placeholder*; its socket wrapper swaps the placeholder for the fragments as the
  header bytes leave, so http.client's own frames (``putheader``, ``_send_output``,
  ``send``) and urllib's ``do_open`` only ever see the placeholder.
- A redirect off that origin is refused before it is followed, and a
  ``Link: rel="next"`` URL off it is refused before it is requested. A same-origin
  redirect opens a new pinned connection, so it carries the credential again.
- Defence in depth: every failure around open and read is re-raised as the typed
  ``FleetInventoryApiError`` ``from None`` after ``traceback.clear_frames``, and
  anything that must propagate as-is (a ``BaseException``) has its frames cleared
  first.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import IO, Any

from pyforge.core.errors import PyforgeError

GITHUB_API_HOST = "api.github.com"
_ORG_REPOS_PATH = "/orgs/{organisation}/repos"
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
_HTTPS_DEFAULT_PORT = 443
_AUTHORIZATION_PLACEHOLDER = "Bearer pyforge-warden-credential-placeholder"
_AUTHORIZATION_PLACEHOLDER_BYTES = _AUTHORIZATION_PLACEHOLDER.encode("ascii")
# At most this many bytes per fragment: log renderers that truncate long values
# slice them (a plain-bytes slice would show its content); a short one stays whole.
_FRAGMENT_BYTES = 32
_TOKEN_SHAPE = re.compile(r"[\x21-\x7e]+")
_REQUIRED_TEXT_FIELDS = ("full_name", "default_branch", "clone_url")


class FleetInventoryApiError(PyforgeError, Exception):
    """GitHub listing failed — never carries a token."""


class HttpMethodRefusedError(FleetInventoryApiError):
    def __init__(self, method: str) -> None:
        super().__init__(f"refused HTTP method {method!r} (GET only)")


class OffApiHostRefusedError(FleetInventoryApiError):
    """A request, redirect or pagination link pointed off ``https://<api_host>``."""

    def __init__(self, what: str, url: str, api_host: str) -> None:
        super().__init__(f"refused {what} to {_origin(url)}: only https://{api_host} receives the token")


@dataclass(frozen=True)
class ListedRepo:
    full_name: str
    default_branch: str
    clone_url: str
    archived: bool


@dataclass(frozen=True)
class SkippedRepoEntry:
    """A listing entry that was not inventoried, and why (never silently dropped)."""

    page: int
    position: int
    full_name: str | None
    reason: str


@dataclass(frozen=True)
class OrgReposListing:
    repos: tuple[ListedRepo, ...]
    skipped: tuple[SkippedRepoEntry, ...]


def _origin(url: str) -> str:
    """``scheme://host`` of ``url`` for an error message — no path, query or userinfo."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "an unparseable URL"
    return f"{parts.scheme or '?'}://{parts.hostname or '?'}"


def is_api_url(url: str, api_host: str = GITHUB_API_HOST) -> bool:
    """True only for ``https://<api_host>`` on the default port, with no userinfo."""
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() == api_host.lower()
        and port in (None, _HTTPS_DEFAULT_PORT)
        and parts.username is None
        and parts.password is None
    )


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    match = _LINK_NEXT.search(link_header)
    if match is None:
        return None
    return match.group(1)


def _listed_repo_from_api(entry: object) -> ListedRepo | str:
    """The repo, or the reason the entry cannot be inventoried."""
    if not isinstance(entry, dict):
        return "entry is not a JSON object"
    missing = [name for name in _REQUIRED_TEXT_FIELDS if not isinstance(entry.get(name), str) or not entry.get(name)]
    if missing:
        return f"missing {', '.join(missing)}"
    archived = entry.get("archived")
    if not isinstance(archived, bool):
        return "archived is not a boolean"
    return ListedRepo(
        full_name=entry["full_name"],
        default_branch=entry["default_branch"],
        clone_url=entry["clone_url"],
        archived=archived,
    )


def _transport_failure(exc: BaseException) -> str:
    """A message for a transport error that never echoes request state.

    Only an ``OSError``'s text is kept (a timeout, a reset, an SSL reason); any
    other error gives only its type, since its text is not under this client's
    control (``http.client`` quotes an illegal header value, for one).
    """
    detail = f": {exc}" if isinstance(exc, OSError) else ""
    return f"GitHub API transport failed: {type(exc).__name__}{detail}"


class RedactedBytes(bytes):
    """A credential fragment: ``repr`` and ``str`` never show its content."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<credential bytes redacted>"

    __str__ = __repr__


def _fragments(token: str) -> tuple[RedactedBytes, ...]:
    return tuple(
        RedactedBytes(f"Bearer {token}".encode("ascii")[start : start + _FRAGMENT_BYTES])
        for start in range(0, len(token) + len("Bearer "), _FRAGMENT_BYTES)
    )


class _Credential:
    """The bearer credential, held only as redacted fragments of ``Bearer <token>``."""

    __slots__ = ("_fragments",)

    def __init__(self, token: str) -> None:
        well_formed = _TOKEN_SHAPE.fullmatch(token) is not None
        self._fragments = _fragments(token) if well_formed else ()
        # Drop the token before any raise: a logged traceback renders frame locals.
        del token
        if not well_formed:
            msg = "the GitHub credential is not one printable token (refused before any request)"
            raise FleetInventoryApiError(msg)

    def __repr__(self) -> str:
        return "<credential redacted>"

    __str__ = __repr__

    @property
    def fragments(self) -> tuple[RedactedBytes, ...]:
        return self._fragments


_HEADER_END = b"\r\n\r\n"


class _CredentialSplicingSocket:
    """Swap the Authorization placeholder for the credential's fragments on the way out.

    Only inside the header block, and once per request (a connection carries one
    request: urllib sends ``Connection: close``). From the first CRLF CRLF on, bytes
    pass through untouched, so a body never receives the credential even if it holds
    the placeholder text (``_ApiConnection`` refuses such a body before sending).
    """

    __slots__ = ("_credential", "_head_tail", "_headers_done", "_sock", "_spliced")

    def __init__(self, sock: Any, credential: _Credential) -> None:
        self._sock = sock
        self._credential = credential
        self._head_tail = b""
        self._headers_done = False
        self._spliced = False

    def __repr__(self) -> str:
        return "<credential-splicing socket>"

    def sendall(self, data: Any, *args: Any) -> None:
        if self._headers_done:
            self._sock.sendall(data, *args)
            return
        raw = bytes(data)
        window = self._head_tail + raw
        end = window.find(_HEADER_END)
        if end < 0:
            head, body = raw, b""
            self._head_tail = window[-(len(_HEADER_END) - 1) :]
        else:
            cut = end + len(_HEADER_END) - len(self._head_tail)
            head, body = raw[:cut], raw[cut:]
            self._headers_done = True
        self._send_head(head, *args)
        if body:
            self._sock.sendall(body, *args)

    def _send_head(self, head: bytes, *args: Any) -> None:
        before, marker, after = head.partition(_AUTHORIZATION_PLACEHOLDER_BYTES)
        if not marker or self._spliced:
            self._sock.sendall(head, *args)
            return
        self._spliced = True
        self._sock.sendall(before, *args)
        for fragment in self._credential.fragments:
            self._sock.sendall(fragment, *args)
        self._sock.sendall(after, *args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sock, name)


class _ApiConnection(http.client.HTTPSConnection):
    """HTTPS to the pinned API origin; Authorization exists only as a placeholder here."""

    def __init__(self, host: str, *, credential: _Credential | None, **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        self._credential = credential

    def connect(self) -> None:
        super().connect()
        if self._credential is not None:
            self.sock = _CredentialSplicingSocket(self.sock, self._credential)

    def endheaders(self, message_body: Any = None, *, encode_chunked: bool = False) -> None:
        if self._credential is not None:
            if message_body is not None and (
                not isinstance(message_body, (bytes, bytearray, memoryview))
                or _AUTHORIZATION_PLACEHOLDER_BYTES in bytes(message_body)
            ):
                # Refused before any byte is sent: a body is never spliced, and one that
                # holds the placeholder text (a server-supplied cursor, a configured
                # login) would otherwise sit beside the credential on the wire.
                msg = "refused a request body that carries the credential placeholder (or is not bytes)"
                raise FleetInventoryApiError(msg)
            self.putheader("Authorization", _AUTHORIZATION_PLACEHOLDER)
        super().endheaders(message_body, encode_chunked=encode_chunked)


class _ApiHTTPSHandler(urllib.request.HTTPSHandler):
    """Open HTTPS through ``_ApiConnection``; the credential goes only to the pinned origin."""

    def __init__(self, credential: _Credential, api_host: str) -> None:
        self._ssl_context = ssl.create_default_context()
        super().__init__(context=self._ssl_context)
        self._credential = credential
        self._api_host = api_host

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        credential = self._credential if is_api_url(req.full_url, self._api_host) else None

        def _connection(host: str, /, **kwargs: Any) -> http.client.HTTPConnection:
            return _ApiConnection(host, credential=credential, **kwargs)

        return self.do_open(_connection, req, context=self._ssl_context)


class _ApiHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only within ``https://<api_host>``; refuse any other before following it."""

    def __init__(self, api_host: str) -> None:
        super().__init__()
        self._api_host = api_host

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not is_api_url(newurl, self._api_host):
            fp.close()
            raise OffApiHostRefusedError("a redirect", newurl, self._api_host)
        # No Authorization to carry: a same-origin redirect opens a new pinned connection.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GitHubRestOrgReposClient:
    """GET-only GitHub REST client for ``/orgs/{org}/repos`` pagination."""

    def __init__(
        self,
        *,
        token: str,
        timeout: float,
        api_host: str = GITHUB_API_HOST,
    ) -> None:
        """``timeout`` is per socket operation, and has no default here: its one source is
        the caller's (the inventory task's ``FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS``,
        kept below the task's soft time limit), so the two can never drift apart."""
        try:
            credential = _Credential(token)
        finally:
            # The token never stays a local here, even when the credential refuses it.
            del token
        self._api_host = api_host
        self._timeout = timeout
        self._opener = urllib.request.build_opener(
            _ApiHostRedirectHandler(api_host),
            _ApiHTTPSHandler(credential, api_host),
        )

    def __repr__(self) -> str:
        return f"GitHubRestOrgReposClient(api_host={self._api_host!r}, token=<redacted>)"

    def list_org_repos(self, organisation: str) -> OrgReposListing:
        encoded = urllib.parse.quote(organisation, safe="")
        url: str | None = (
            f"https://{self._api_host}{_ORG_REPOS_PATH.format(organisation=encoded)}?type=all&per_page=100"
        )
        collected: list[ListedRepo] = []
        skipped: list[SkippedRepoEntry] = []
        seen: set[str] = set()
        page = 0
        while url:
            if url in seen:
                msg = "pagination Link header repeated the same URL"
                raise FleetInventoryApiError(msg)
            seen.add(url)
            page += 1
            payload, link = self._get_json(url)
            if not isinstance(payload, list):
                msg = "expected a JSON array from org repos listing"
                raise FleetInventoryApiError(msg)
            for position, entry in enumerate(payload, start=1):
                listed = _listed_repo_from_api(entry)
                if isinstance(listed, ListedRepo):
                    collected.append(listed)
                    continue
                name = entry.get("full_name") if isinstance(entry, dict) else None
                skipped.append(
                    SkippedRepoEntry(
                        page=page,
                        position=position,
                        full_name=name if isinstance(name, str) and name else None,
                        reason=listed,
                    )
                )
            url = _parse_link_next(link)
            if url is not None and not is_api_url(url, self._api_host):
                raise OffApiHostRefusedError("a pagination link", url, self._api_host)
        return OrgReposListing(repos=tuple(collected), skipped=tuple(skipped))

    def _get_json(self, url: str) -> tuple[Any, str | None]:
        if not is_api_url(url, self._api_host):
            raise OffApiHostRefusedError("a request", url, self._api_host)
        # No Authorization on the Request: the pinned connection adds it (module docstring).
        request = urllib.request.Request(url, method="GET")  # noqa: S310
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "pyforge-warden-fleet-inventory")
        # Defence in depth (the token is in no urllib frame to begin with): every failure
        # is typed ``from None`` with its frames' locals cleared, so nothing a renderer
        # that prints frame locals (structlog's ``dict_tracebacks``, Django's DEBUG 500
        # page, django_structlog's Celery ``task_failed``) can reach holds request state.
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                body = response.read()
                link = response.headers.get("Link")
        except FleetInventoryApiError as exc:
            # The client's own refusal (a redirect off the API origin): already typed.
            traceback.clear_frames(exc.__traceback__)
            raise
        except urllib.error.HTTPError as exc:
            msg = f"GitHub API HTTP {exc.code}"
            traceback.clear_frames(exc.__traceback__)
            raise FleetInventoryApiError(msg) from None
        except urllib.error.URLError as exc:
            msg = f"GitHub API request failed: {exc.reason}"
            traceback.clear_frames(exc.__traceback__)
            raise FleetInventoryApiError(msg) from None
        except Exception as exc:
            # urllib wraps only ``h.request()``'s OSError: a read timeout, a reset, an SSL
            # error, ``IncompleteRead``, Celery's ``SoftTimeLimitExceeded`` (an Exception)
            # or any other error from connect, send, ``getresponse()`` or ``read()``.
            msg = _transport_failure(exc)
            traceback.clear_frames(exc.__traceback__)
            raise FleetInventoryApiError(msg) from None
        except BaseException as exc:
            # Must propagate as-is (KeyboardInterrupt, SystemExit): clear its frames first.
            traceback.clear_frames(exc.__traceback__)
            raise
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            msg = "GitHub API returned invalid JSON"
            raise FleetInventoryApiError(msg) from exc
        return parsed, link

    def request(self, method: str, url: str) -> None:
        """Issue one HTTP call — refuses non-GET (and off-host URLs) before opening a socket."""
        normalized = method.upper()
        if normalized != "GET":
            raise HttpMethodRefusedError(normalized)
        self._get_json(url)
