"""GraphQL queries and pagination for Projects V2 ingest.

Query shapes follow `pyforge.steward.sync` (`_LIST_PROJECT_ITEMS_QUERY`,
`_GET_PROJECT_ITEM_QUERY` field-value fragments). This module is ingest-only —
no reconcile writes, no Jira calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import TransportFn, github_graphql_request

# GitHub primary rate limit: 5,000 points/hr for authenticated GraphQL.
DEFAULT_POINTS_BUDGET = 5000
DEFAULT_PAGE_SIZE = 100

_LIST_PROJECT_SNAPSHOT_QUERY = """
query($projectId: ID!, $after: String, $pageSize: Int!) {
  rateLimit {
    cost
    remaining
    resetAt
  }
  node(id: $projectId) {
    ... on ProjectV2 {
      id
      title
      fields(first: 100) {
        nodes {
          ... on ProjectV2FieldCommon {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options {
              id
              name
            }
          }
        }
      }
      items(first: $pageSize, after: $after) {
        nodes {
          id
          updatedAt
          fieldValues(first: 50) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { id name } }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { id name } }
              }
            }
          }
          content {
            ... on Issue {
              number
              title
              repository { owner { login } name }
            }
            ... on PullRequest {
              number
              title
              repository { owner { login } name }
            }
            ... on DraftIssue {
              title
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class RateLimitSnapshot:
    cost: int | None
    remaining: int | None
    reset_at: str | None


@dataclass(frozen=True)
class ProjectSnapshotPage:
    project_id: str
    project_title: str | None
    fields: list[dict[str, object]]
    items: list[dict[str, object]]
    rate_limit: RateLimitSnapshot
    has_next_page: bool
    end_cursor: str | None


def _parse_rate_limit(payload: dict[str, object]) -> RateLimitSnapshot:
    raw = payload.get("rateLimit") or {}
    if not isinstance(raw, dict):
        return RateLimitSnapshot(None, None, None)
    cost = raw.get("cost")
    remaining = raw.get("remaining")
    reset_at = raw.get("resetAt")
    return RateLimitSnapshot(
        cost if isinstance(cost, int) else None,
        remaining if isinstance(remaining, int) else None,
        reset_at if isinstance(reset_at, str) else None,
    )


def fetch_project_snapshot_page(
    project_id: str,
    *,
    credential: HostScopedCredential,
    transport: TransportFn,
    after: str | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ProjectSnapshotPage:
    """Fetch one paginated Projects V2 snapshot page."""
    if page_size < 1 or page_size > DEFAULT_PAGE_SIZE:
        raise ValueError(f"page_size must be 1..{DEFAULT_PAGE_SIZE}, got {page_size}")

    variables: dict[str, object] = {
        "projectId": project_id,
        "pageSize": page_size,
    }
    if after is not None:
        variables["after"] = after

    payload = github_graphql_request(
        _LIST_PROJECT_SNAPSHOT_QUERY,
        variables,
        credential=credential,
        transport=transport,
    )
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("GitHub GraphQL response missing data object")

    rate_limit = _parse_rate_limit(data)
    node = data.get("node") or {}
    if not isinstance(node, dict):
        raise ValueError(f"project node {project_id!r} not found or not accessible")

    fields_conn = node.get("fields") or {}
    items_conn = node.get("items") or {}
    field_nodes = fields_conn.get("nodes") if isinstance(fields_conn, dict) else []
    item_nodes = items_conn.get("nodes") if isinstance(items_conn, dict) else []
    page_info = items_conn.get("pageInfo") if isinstance(items_conn, dict) else {}

    return ProjectSnapshotPage(
        project_id=str(node.get("id") or project_id),
        project_title=node.get("title") if isinstance(node.get("title"), str) else None,
        fields=[entry for entry in (field_nodes or []) if isinstance(entry, dict)],
        items=[entry for entry in (item_nodes or []) if isinstance(entry, dict)],
        rate_limit=rate_limit,
        has_next_page=bool((page_info or {}).get("hasNextPage")),
        end_cursor=(page_info or {}).get("endCursor")
        if isinstance((page_info or {}).get("endCursor"), str)
        else None,
    )


def iter_project_snapshot_pages(
    project_id: str,
    *,
    credential: HostScopedCredential,
    transport: TransportFn,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    min_remaining_points: int = 100,
    on_page: Callable[[ProjectSnapshotPage, int], None] | None = None,
) -> Iterator[ProjectSnapshotPage]:
    """Paginate project items, stopping on budget exhaustion or `max_pages`."""
    cursor: str | None = None
    pages = 0
    while True:
        page = fetch_project_snapshot_page(
            project_id,
            credential=credential,
            transport=transport,
            after=cursor,
            page_size=page_size,
        )
        pages += 1
        if on_page is not None:
            on_page(page, pages)

        yield page

        if page.rate_limit.remaining is not None and page.rate_limit.remaining < min_remaining_points:
            break
        if not page.has_next_page:
            break
        if max_pages is not None and pages >= max_pages:
            break
        cursor = page.end_cursor
