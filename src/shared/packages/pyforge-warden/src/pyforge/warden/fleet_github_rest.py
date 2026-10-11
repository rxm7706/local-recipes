"""GET-only GitHub REST org listing for fleet inventory (Story 16.1).

Lives in pyforge-warden so django_warden_fabric stays free of raw HTTP imports
(platform ``test_portal_raw_http_to_a_service_is_review_blocking``).

The bearer token never leaves ``https://<api_host>``: it rides as an
unredirected header, a redirect off that origin is refused before it is
followed (a redirect on it carries the token again), and a ``Link: rel="next"``
URL off that origin is refused before it is requested.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from http.client import HTTPMessage
from typing import IO, Any

from pyforge.core.errors import PyforgeError

GITHUB_API_HOST = "api.github.com"
_ORG_REPOS_PATH = "/orgs/{organisation}/repos"
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
_HTTPS_DEFAULT_PORT = 443
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


class _ApiHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only within ``https://<api_host>``, carrying the token there."""

    def __init__(self, api_host: str) -> None:
        super().__init__()
        self._api_host = api_host

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not is_api_url(newurl, self._api_host):
            fp.close()
            raise OffApiHostRefusedError("a redirect", newurl, self._api_host)
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        authorization = req.unredirected_hdrs.get("Authorization")
        if new is not None and authorization is not None:
            new.add_unredirected_header("Authorization", authorization)
        return new


class GitHubRestOrgReposClient:
    """GET-only GitHub REST client for ``/orgs/{org}/repos`` pagination.

    ``handlers`` are extra urllib transport handlers (tests pass stubs); the
    client always installs its own redirect policy and refuses another.
    """

    def __init__(
        self,
        *,
        token: str,
        api_host: str = GITHUB_API_HOST,
        handlers: Sequence[urllib.request.BaseHandler] = (),
    ) -> None:
        if any(isinstance(handler, urllib.request.HTTPRedirectHandler) for handler in handlers):
            msg = "the client owns its redirect policy; pass no HTTPRedirectHandler"
            raise ValueError(msg)
        self._token = token
        self._api_host = api_host
        self._opener = urllib.request.build_opener(_ApiHostRedirectHandler(api_host), *handlers)

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
        request = urllib.request.Request(url, method="GET")  # noqa: S310
        request.add_unredirected_header("Authorization", f"Bearer {self._token}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "pyforge-warden-fleet-inventory")
        try:
            with self._opener.open(request, timeout=120) as response:
                body = response.read()
                link = response.headers.get("Link")
        # ``from None``: urllib's own frames (``do_open`` holds the request headers,
        # Authorization included, as a local) must not ride along on the chain into
        # a log renderer that prints frame locals (the platform's ``dict_tracebacks``).
        except urllib.error.HTTPError as exc:
            msg = f"GitHub API HTTP {exc.code}"
            raise FleetInventoryApiError(msg) from None
        except urllib.error.URLError as exc:
            msg = f"GitHub API request failed: {exc.reason}"
            raise FleetInventoryApiError(msg) from None
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
