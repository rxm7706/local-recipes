"""Query-only GitHub GraphQL project-item listing for fleet inventory (Story 16.5).

Lives in pyforge-warden beside ``fleet_github_rest`` for the same reason: the
platform's ``test_portal_raw_http_to_a_service_is_review_blocking`` refuses raw
HTTP imports in ``django_warden_fabric``.

The client sends ``POST https://api.github.com/graphql`` with one ``query``
operation and nothing else:

- ``assert_single_query`` reads the document's own tokens and refuses a
  ``mutation``, a ``subscription``, a ``fragment``-only document or more than one
  operation, before a request is built, so before a socket opens.
- The credential seam is Story 16.1's, reused as it is: the token is held as a
  ``_Credential`` and only the pinned ``_ApiHTTPSHandler`` connection to
  ``https://<api_host>`` ever writes it; no urllib or http.client frame holds it.
- No redirect is followed. A redirected ``POST`` would be re-sent as something
  that is not the reviewed query, so a 3xx is an error like any other HTTP failure.
- Every failure around open and read is typed ``FleetInventoryApiError`` ``from
  None`` after ``traceback.clear_frames``; an error text never carries a token,
  a response body or a GraphQL error message.
"""

from __future__ import annotations

import http.client
import json
import re
import traceback
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import IO, Any

from pyforge.warden.fleet_github_rest import (
    GITHUB_API_HOST,
    FleetInventoryApiError,
    _ApiHTTPSHandler,
    _Credential,
    _transport_failure,
    is_api_url,
)

GRAPHQL_PATH = "/graphql"
PROJECT_ITEMS_PAGE_SIZE = 100
STATUS_FIELD_NAME = "Status"
CONTENT_TYPES = frozenset({"ISSUE", "PULL_REQUEST", "DRAFT_ISSUE", "REDACTED"})
_CONTENT_TYPES_WITH_REPOSITORY = frozenset({"ISSUE", "PULL_REQUEST"})
_OPERATION_KEYWORDS = frozenset({"query", "mutation", "subscription", "fragment"})
_ERROR_TYPE = re.compile(r"[A-Z][A-Z_]{0,63}")
_MAX_ERROR_TYPES = 5

PROJECT_ITEMS_QUERY = """\
query ProjectItems($login: String!, $number: Int!, $after: String) {
  organization(login: $login) {
    projectV2(number: $number) {
      items(first: %(page_size)d, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          type
          updatedAt
          fieldValueByName(name: "%(status)s") {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
          content {
            ... on Issue { title state repository { nameWithOwner } }
            ... on PullRequest { title state repository { nameWithOwner } }
            ... on DraftIssue { title }
          }
        }
      }
    }
  }
}
""" % {"page_size": PROJECT_ITEMS_PAGE_SIZE, "status": STATUS_FIELD_NAME}


class GraphQLOperationRefusedError(FleetInventoryApiError):
    """The document is not exactly one ``query`` operation (refused before any socket)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"refused GraphQL document: {reason} (query only)")


class ProjectEntryError(FleetInventoryApiError):
    """One entry of the config key ``projects`` could not be inventoried."""

    def __init__(self, position: int, total: int, reason: str) -> None:
        self.position = position
        self._parts = (position, total, reason)
        super().__init__(f"config key projects, entry {position} of {total}: {reason}")

    def __reduce__(self) -> tuple[type[ProjectEntryError], tuple[int, int, str]]:
        # Celery stores a task's exception by pickling it: rebuild it from its own parts.
        return type(self), self._parts


@dataclass(frozen=True)
class ListedProjectItem:
    """One project item. A draft has no repository or state; a redacted item has its type only."""

    project_number: int
    id: str
    content_type: str
    title: str | None
    state: str | None
    repository: str | None
    status: str | None
    updated_at: str | None


# --- the query-only guard -------------------------------------------------------------------------

_TOKEN = re.compile(
    r"""
      (?P<space>[\s,\ufeff]+)
    | (?P<comment>\#[^\n\r]*)
    | (?P<block>\"\"\"(?:\\\"\"\"|(?!\"\"\").)*\"\"\")
    | (?P<string>"(?:\\.|[^"\\\n\r])*")
    | (?P<name>[_A-Za-z][_0-9A-Za-z]*)
    | (?P<number>-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)
    | (?P<punct>\.\.\.|[!$&():=@\[\]{|}])
    """,
    re.VERBOSE | re.DOTALL,
)


def assert_single_query(document: object) -> None:
    """Refuse anything that is not exactly one ``query`` operation.

    Reads the document with GraphQL's own lexical grammar (comments, strings and
    block strings included), so a keyword hidden in a string, a comment or a
    variable name (``$mutation``) is neither mistaken for an operation nor able to
    smuggle one in. Any token the lexer does not know is refused.
    """
    if not isinstance(document, str):
        raise GraphQLOperationRefusedError("the document is not text")
    definitions: list[str] = []
    expecting_definition = True
    brace_depth = paren_depth = 0
    position = 0
    while position < len(document):
        match = _TOKEN.match(document, position)
        if match is None:
            raise GraphQLOperationRefusedError("the document has a token GraphQL does not define")
        position = match.end()
        kind, text = match.lastgroup, match.group()
        if kind in ("space", "comment"):
            continue
        if expecting_definition and brace_depth == 0 and paren_depth == 0:
            if text == "{":
                definitions.append("query")
            elif kind == "name" and text in _OPERATION_KEYWORDS:
                definitions.append(text)
            else:
                raise GraphQLOperationRefusedError("the document does not open with an operation")
            expecting_definition = False
        if kind != "punct":
            continue
        if text == "(":
            paren_depth += 1
        elif text == ")":
            paren_depth -= 1
        elif paren_depth == 0 and text == "{":
            brace_depth += 1
        elif paren_depth == 0 and text == "}":
            brace_depth -= 1
            expecting_definition = brace_depth == 0
        if brace_depth < 0 or paren_depth < 0:
            raise GraphQLOperationRefusedError("the document's brackets do not balance")
    if brace_depth or paren_depth:
        raise GraphQLOperationRefusedError("the document's brackets do not balance")
    if len(definitions) != 1:
        raise GraphQLOperationRefusedError(f"{len(definitions)} definitions, expected exactly one operation")
    if definitions[0] != "query":
        raise GraphQLOperationRefusedError(f"a {definitions[0]} operation")


# --- response reading -----------------------------------------------------------------------------


def _graphql_failure(payload: Mapping[str, Any]) -> str | None:
    """A message for an ``errors`` array: its size and simple type codes, never its text."""
    errors = payload.get("errors")
    if not errors:
        return None
    entries = errors if isinstance(errors, list) else [errors]
    codes = sorted(
        {
            entry["type"]
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("type"), str) and _ERROR_TYPE.fullmatch(entry["type"])
        }
    )[:_MAX_ERROR_TYPES]
    suffix = f" ({', '.join(codes)})" if codes else ""
    return f"GitHub GraphQL returned an errors array of {len(entries)}{suffix}"


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _status_value(node: Mapping[str, Any]) -> str | None:
    value = node.get("fieldValueByName")
    return _text_or_none(value.get("name")) if isinstance(value, dict) else None


def _item_from_node(project_number: int, node: object) -> ListedProjectItem | str:
    """The item, or the reason the node cannot be inventoried."""
    if not isinstance(node, dict):
        return "an item is not a JSON object"
    item_id = _text_or_none(node.get("id"))
    if item_id is None:
        return "an item has no id"
    content_type = node.get("type")
    if not isinstance(content_type, str) or content_type not in CONTENT_TYPES:
        return "an item has an unknown content type"
    if content_type == "REDACTED":
        return ListedProjectItem(
            project_number=project_number,
            id=item_id,
            content_type=content_type,
            title=None,
            state=None,
            repository=None,
            status=None,
            updated_at=None,
        )
    content = node.get("content")
    content = content if isinstance(content, dict) else {}
    repository = None
    state = None
    if content_type in _CONTENT_TYPES_WITH_REPOSITORY:
        state = _text_or_none(content.get("state"))
        repo = content.get("repository")
        repository = _text_or_none(repo.get("nameWithOwner")) if isinstance(repo, dict) else None
    return ListedProjectItem(
        project_number=project_number,
        id=item_id,
        content_type=content_type,
        title=_text_or_none(content.get("title")),
        state=state,
        repository=repository,
        status=_status_value(node),
        updated_at=_text_or_none(node.get("updatedAt")),
    )


def _items_connection(payload: Mapping[str, Any]) -> Mapping[str, Any] | str:
    """The ``items`` connection of the queried project, or why there is none."""
    data = payload.get("data")
    organization = data.get("organization") if isinstance(data, dict) else None
    project = organization.get("projectV2") if isinstance(organization, dict) else None
    if not isinstance(project, dict):
        return "the project was not found, or this login cannot read it"
    items = project.get("items")
    if not isinstance(items, dict):
        return "the project returned no items connection"
    return items


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow nothing: a 3xx surfaces as an HTTP error instead of a re-sent request."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> None:
        return None


class GitHubGraphQLProjectItemsClient:
    """Query-only GitHub GraphQL client for the items of organisation Projects (v2)."""

    def __init__(
        self,
        *,
        token: str,
        timeout: float,
        api_host: str = GITHUB_API_HOST,
    ) -> None:
        """``timeout`` is per socket operation and has no default: its one source is the
        caller's (the task's ``FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS``)."""
        try:
            credential = _Credential(token)
        finally:
            # The token never stays a local here, even when the credential refuses it.
            del token
        self._api_host = api_host
        self._timeout = timeout
        self._opener = urllib.request.build_opener(
            _NoRedirectHandler(),
            _ApiHTTPSHandler(credential, api_host),
        )

    def __repr__(self) -> str:
        return f"GitHubGraphQLProjectItemsClient(api_host={self._api_host!r}, token=<redacted>)"

    def execute(self, document: str, variables: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Send one ``query`` as ``POST /graphql``; refuses anything else before a socket opens.

        An ``errors`` array in the reply is a typed error: ``data`` is never
        trusted beside it, and the messages are never echoed.
        """
        assert_single_query(document)
        url = f"https://{self._api_host}{GRAPHQL_PATH}"
        if not is_api_url(url, self._api_host):
            msg = f"refused a request to {self._api_host}: only https://{GITHUB_API_HOST} receives the token"
            raise FleetInventoryApiError(msg)
        body = json.dumps({"query": document, "variables": dict(variables or {})}).encode("utf-8")
        # No Authorization on the Request: the pinned connection adds it (see fleet_github_rest).
        request = urllib.request.Request(url, data=body, method="POST")  # noqa: S310
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", "pyforge-warden-fleet-inventory")
        raw = self._send(request)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            msg = "GitHub GraphQL returned invalid JSON"
            raise FleetInventoryApiError(msg) from exc
        if not isinstance(payload, dict):
            msg = "GitHub GraphQL returned a JSON value that is not an object"
            raise FleetInventoryApiError(msg)
        failure = _graphql_failure(payload)
        if failure is not None:
            raise FleetInventoryApiError(failure)
        return payload

    def _send(self, request: urllib.request.Request) -> bytes:
        # Defence in depth, the same as the REST client: every failure is typed ``from None``
        # with its frames' locals cleared, so no renderer of frame locals reaches request state.
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return response.read()
        except FleetInventoryApiError as exc:
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
            msg = _transport_failure(exc)
            traceback.clear_frames(exc.__traceback__)
            raise FleetInventoryApiError(msg) from None
        except BaseException as exc:
            traceback.clear_frames(exc.__traceback__)
            raise

    def list_project_items(self, organisation: str, project_number: int) -> tuple[ListedProjectItem, ...]:
        """Every item of one project, following ``pageInfo.endCursor`` until ``hasNextPage`` is false."""
        items: dict[str, ListedProjectItem] = {}
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            payload = self.execute(
                PROJECT_ITEMS_QUERY,
                {"login": organisation, "number": project_number, "after": cursor},
            )
            connection = _items_connection(payload)
            if isinstance(connection, str):
                raise FleetInventoryApiError(connection)
            nodes = connection.get("nodes")
            page_info = connection.get("pageInfo")
            if not isinstance(nodes, list) or not isinstance(page_info, dict):
                msg = "the items connection has no nodes or no pageInfo"
                raise FleetInventoryApiError(msg)
            for node in nodes:
                item = _item_from_node(project_number, node)
                if isinstance(item, str):
                    raise FleetInventoryApiError(item)
                items.setdefault(item.id, item)
            if page_info.get("hasNextPage") is not True:
                return tuple(items.values())
            cursor = _text_or_none(page_info.get("endCursor"))
            if cursor is None or cursor in seen_cursors:
                msg = "pageInfo.hasNextPage is true but endCursor is missing or repeated"
                raise FleetInventoryApiError(msg)
            seen_cursors.add(cursor)

    def list_projects_items(self, organisation: str, project_numbers: Sequence[int]) -> tuple[ListedProjectItem, ...]:
        """The items of each designated project, in config order, each project read once.

        Every failure names the config key ``projects`` and the failing entry's
        position (1-based), never the project number or a response.
        """
        collected: list[ListedProjectItem] = []
        read: set[int] = set()
        total = len(project_numbers)
        failure: tuple[int, str] | None = None
        for position, number in enumerate(project_numbers, start=1):
            if number in read:
                continue
            read.add(number)
            try:
                collected.extend(self.list_project_items(organisation, number))
            except FleetInventoryApiError as exc:
                failure = (position, str(exc))
                traceback.clear_frames(exc.__traceback__)
                break
        if failure is not None:
            # Raised outside the loop and the handler, with the earlier projects' items
            # dropped first: this frame is on the traceback, and a renderer of frame
            # locals must not print the operator's item titles.
            del collected
            raise ProjectEntryError(failure[0], total, failure[1])
        return tuple(collected)
