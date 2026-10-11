"""Story 16.1 — GET-only GitHub REST org listing (fixture organisation only)."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.warden.fleet_github_rest import (
    FleetInventoryApiError,
    GitHubRestOrgReposClient,
    HttpMethodRefusedError,
    _listed_repo_from_api,
    _parse_link_next,
)

_EXAMPLE_ORG = "example-org"
_PAGINATED_REPO_COUNT = 2


def test_pagination_reads_link_next() -> None:
    page_one = [
        {
            "full_name": f"{_EXAMPLE_ORG}/page-one",
            "default_branch": "main",
            "clone_url": "https://example.com/one.git",
            "archived": False,
        },
    ]
    page_two = [
        {
            "full_name": f"{_EXAMPLE_ORG}/page-two",
            "default_branch": "main",
            "clone_url": "https://example.com/two.git",
            "archived": False,
        },
    ]
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    link = '<https://api.github.com/orgs/example-org/repos?page=2>; rel="next"'
    with patch.object(
        client,
        "_get_json",
        side_effect=[
            (page_one, link),
            (page_two, None),
        ],
    ):
        repos = client.list_org_repos(_EXAMPLE_ORG)
    assert len(repos) == _PAGINATED_REPO_COUNT


def test_pagination_rejects_repeated_link_url() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    url = "https://api.github.com/orgs/example-org/repos?page=2"
    link = f'<{url}>; rel="next"'
    payload: list[dict[str, str]] = []
    with patch.object(client, "_get_json", return_value=(payload, link)):
        with pytest.raises(FleetInventoryApiError, match="repeated"):
            client.list_org_repos(_EXAMPLE_ORG)


def test_list_org_repos_rejects_non_array_payload() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    with patch.object(client, "_get_json", return_value=({"error": "nope"}, None)):
        with pytest.raises(FleetInventoryApiError, match="JSON array"):
            client.list_org_repos(_EXAMPLE_ORG)


def test_list_org_repos_skips_invalid_entries() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    payload = [
        "not-a-dict",
        {"full_name": "", "default_branch": "main", "clone_url": "https://x.git"},
        {"full_name": f"{_EXAMPLE_ORG}/bad", "clone_url": ""},
        {
            "full_name": f"{_EXAMPLE_ORG}/good",
            "default_branch": "main",
            "clone_url": "https://example.com/good.git",
            "archived": False,
        },
    ]
    with patch.object(client, "_get_json", return_value=(payload, None)):
        repos = client.list_org_repos(_EXAMPLE_ORG)
    assert len(repos) == 1
    assert repos[0].full_name == f"{_EXAMPLE_ORG}/good"


def test_http_client_refuses_non_get() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(HttpMethodRefusedError):
            client.request(method, "https://api.github.com/orgs/example-org/repos")


def test_request_allows_get() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    with patch.object(client, "_get_json", return_value=([], None)) as get_json:
        client.request("get", "https://api.github.com/orgs/example-org/repos")
    get_json.assert_called_once()


def test_parse_link_next() -> None:
    assert _parse_link_next(None) is None
    assert _parse_link_next("") is None
    assert _parse_link_next('rel="prev"') is None
    assert _parse_link_next('<https://api.github.com/next>; rel="next"') == "https://api.github.com/next"


def test_listed_repo_from_api_defaults_branch_and_filters() -> None:
    assert _listed_repo_from_api({}) is None
    assert _listed_repo_from_api({"full_name": "org/r", "clone_url": ""}) is None
    repo = _listed_repo_from_api({"full_name": "org/r", "default_branch": "", "clone_url": "https://c.git"})
    assert repo is not None
    assert repo.default_branch == "main"


def test_get_json_http_error() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    opener = MagicMock()
    opener.open.side_effect = urllib.error.HTTPError(
        url="https://api.github.com",
        code=503,
        msg="Unavailable",
        hdrs=None,
        fp=None,
    )
    client = GitHubRestOrgReposClient(token="fixture-token", opener=opener)  # noqa: S106
    with pytest.raises(FleetInventoryApiError, match="HTTP 503"):
        client._get_json("https://api.github.com/orgs/x/repos")


def test_get_json_url_error() -> None:
    opener = MagicMock()
    opener.open.side_effect = urllib.error.URLError("connection reset")
    client = GitHubRestOrgReposClient(token="fixture-token", opener=opener)  # noqa: S106
    with pytest.raises(FleetInventoryApiError, match="request failed"):
        client._get_json("https://api.github.com/orgs/x/repos")


def test_get_json_invalid_json() -> None:
    response = MagicMock()
    response.read.return_value = b"not-json"
    response.headers.get.return_value = None
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    opener = MagicMock()
    opener.open.return_value = response
    client = GitHubRestOrgReposClient(token="fixture-token", opener=opener)  # noqa: S106
    with pytest.raises(FleetInventoryApiError, match="invalid JSON"):
        client._get_json("https://api.github.com/orgs/x/repos")


def test_get_json_success() -> None:
    body = json.dumps([{"full_name": "a/b"}]).encode()
    response = MagicMock()
    response.read.return_value = body
    response.headers.get.return_value = 'rel="next"'
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    opener = MagicMock()
    opener.open.return_value = response
    client = GitHubRestOrgReposClient(token="fixture-token", opener=opener)  # noqa: S106
    parsed, link = client._get_json("https://api.github.com/orgs/x/repos")
    assert parsed == [{"full_name": "a/b"}]
    assert link == 'rel="next"'


def test_fleet_inventory_api_error_is_pyforge_error() -> None:
    assert issubclass(FleetInventoryApiError, PyforgeError)
