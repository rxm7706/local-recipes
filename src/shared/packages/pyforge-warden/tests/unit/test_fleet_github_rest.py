"""Story 16.1 — GET-only GitHub REST org listing (fixture organisation only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyforge.warden.fleet_github_rest import GitHubRestOrgReposClient
from pyforge.warden.fleet_github_rest import HttpMethodRefusedError

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


def test_http_client_refuses_non_get() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(HttpMethodRefusedError):
            client.request(method, "https://api.github.com/orgs/example-org/repos")
