"""GET-only GitHub REST org listing for fleet inventory (Story 16.1).

Lives in pyforge-warden so django_warden_fabric stays free of raw HTTP imports
(platform ``test_portal_raw_http_to_a_service_is_review_blocking``).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from pyforge.core.errors import PyforgeError

GITHUB_API_HOST = "api.github.com"
_ORG_REPOS_PATH = "/orgs/{organisation}/repos"
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class FleetInventoryApiError(PyforgeError, Exception):
    """GitHub listing failed — never carries a token."""


class HttpMethodRefusedError(FleetInventoryApiError):
    def __init__(self, method: str) -> None:
        super().__init__(f"refused HTTP method {method!r} (GET only)")


@dataclass(frozen=True)
class ListedRepo:
    full_name: str
    default_branch: str
    clone_url: str
    archived: bool


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    match = _LINK_NEXT.search(link_header)
    if match is None:
        return None
    return match.group(1)


def _listed_repo_from_api(entry: dict[str, Any]) -> ListedRepo | None:
    full_name = entry.get("full_name")
    default_branch = entry.get("default_branch")
    clone_url = entry.get("clone_url")
    archived = entry.get("archived")
    if not isinstance(full_name, str) or not full_name:
        return None
    if not isinstance(default_branch, str) or not default_branch:
        default_branch = "main"
    if not isinstance(clone_url, str) or not clone_url:
        return None
    return ListedRepo(
        full_name=full_name,
        default_branch=default_branch,
        clone_url=clone_url,
        archived=bool(archived),
    )


class GitHubRestOrgReposClient:
    """GET-only GitHub REST client for ``/orgs/{org}/repos`` pagination."""

    def __init__(
        self,
        *,
        token: str,
        api_host: str = GITHUB_API_HOST,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._token = token
        self._api_host = api_host
        self._opener = opener or urllib.request.build_opener()

    def list_org_repos(self, organisation: str) -> list[ListedRepo]:
        encoded = urllib.parse.quote(organisation, safe="")
        url: str | None = (
            f"https://{self._api_host}{_ORG_REPOS_PATH.format(organisation=encoded)}?type=all&per_page=100"
        )
        collected: list[ListedRepo] = []
        seen_next: set[str] = set()
        while url:
            if url in seen_next:
                msg = "pagination Link header repeated the same URL"
                raise FleetInventoryApiError(msg)
            seen_next.add(url)
            payload, link = self._get_json(url)
            if not isinstance(payload, list):
                msg = "expected a JSON array from org repos listing"
                raise FleetInventoryApiError(msg)
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                repo = _listed_repo_from_api(entry)
                if repo is not None:
                    collected.append(repo)
            url = _parse_link_next(link)
        return collected

    def _get_json(self, url: str) -> tuple[Any, str | None]:
        request = urllib.request.Request(url, method="GET")  # noqa: S310
        request.add_header("Authorization", f"Bearer {self._token}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "pyforge-warden-fleet-inventory")
        try:
            with self._opener.open(request, timeout=120) as response:
                body = response.read()
                link = response.headers.get("Link")
        except urllib.error.HTTPError as exc:
            msg = f"GitHub API HTTP {exc.code}"
            raise FleetInventoryApiError(msg) from exc
        except urllib.error.URLError as exc:
            msg = f"GitHub API request failed: {exc.reason}"
            raise FleetInventoryApiError(msg) from exc
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            msg = "GitHub API returned invalid JSON"
            raise FleetInventoryApiError(msg) from exc
        return parsed, link

    def request(self, method: str, url: str) -> None:
        """Issue one HTTP call — refuses non-GET before opening a socket."""
        normalized = method.upper()
        if normalized != "GET":
            raise HttpMethodRefusedError(normalized)
        self._get_json(url)
