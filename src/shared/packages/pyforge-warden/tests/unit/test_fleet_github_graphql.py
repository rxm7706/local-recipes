"""Story 16.5 — query-only GitHub GraphQL project-item listing (fixture organisation only).

Every test drives the real client, the real urllib and the real http.client through a
fake socket: ``HTTPConnection.connect`` and ``HTTPSConnection.connect`` hand the connection
a scripted socket instead of opening one, and an autouse guard fails any connect the fake
did not take. No socket opens, no ``gh`` runs, no host is contacted. Every identifier is
fictional (``example-org``, invented project numbers, titles and repositories).
"""

from __future__ import annotations

import http
import http.client
import io
import json
import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

from pyforge.warden.fleet_github_graphql import (
    PROJECT_ITEMS_PAGE_SIZE,
    PROJECT_ITEMS_QUERY,
    GitHubGraphQLProjectItemsClient,
    GraphQLOperationRefusedError,
    ListedProjectItem,
    ProjectEntryError,
    assert_single_query,
)
from pyforge.warden.fleet_github_rest import FleetInventoryApiError

_EXAMPLE_ORG = "example-org"
_REQUEST_TIMEOUT = 7.5  # any value: the test proves the caller's timeout reaches the socket
_SENTINEL = "sentinel-token-must-not-leak-16-5"
_BEARER = f"Bearer {_SENTINEL}"
_GRAPHQL = "https://api.github.com/graphql"
_PROJECT_A = 11  # invented project numbers
_PROJECT_B = 22
_THREE_PAGES = 3


@pytest.fixture(autouse=True)
def _no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(self: object) -> None:
        msg = "a fleet-project-items unit test tried to open a socket"
        raise AssertionError(msg)

    monkeypatch.setattr(http.client.HTTPConnection, "connect", _refuse)
    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _refuse)


# --- the fake GitHub at the socket -------------------------------------------------------------


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None
    content_type: str | None
    timeout: float | None
    body: dict[str, Any] | None


def _http_response(status: int, *, body: bytes = b"", headers: dict[str, str] | None = None) -> bytes:
    lines = [f"HTTP/1.1 {status} {http.HTTPStatus(status).phrase}"]
    lines.extend(f"{key}: {value}" for key, value in (headers or {}).items())
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


def _json_reply(payload: object, status: int = 200) -> bytes:
    return _http_response(status, body=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})


_Answer = Callable[[dict[str, Any]], "bytes | BaseException"]


class _RaisingReader(io.BytesIO):
    """The response stream of a connection that fails while the status line is read."""

    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self._error = error

    def readline(self, size: int | None = -1) -> bytes:
        raise self._error

    def read(self, size: int | None = -1) -> bytes:
        raise self._error


@dataclass
class _FakeGitHub:
    """Answers each POST from its parsed JSON body; records every exchange."""

    answer: _Answer
    exchanges: list[_Exchange] = field(default_factory=list)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> _FakeGitHub:
        def _connect(connection: http.client.HTTPConnection) -> None:
            connection.sock = _ServerSocket(self, connection)  # type: ignore[assignment]

        monkeypatch.setattr(http.client.HTTPConnection, "connect", _connect)
        monkeypatch.setattr(http.client.HTTPSConnection, "connect", _connect)
        return self

    def client(self, token: str = _SENTINEL) -> GitHubGraphQLProjectItemsClient:
        return GitHubGraphQLProjectItemsClient(token=token, timeout=_REQUEST_TIMEOUT)

    @property
    def queries(self) -> list[str]:
        return [e.body["query"] for e in self.exchanges if e.body is not None]


class _ServerSocket:
    def __init__(self, fake: _FakeGitHub, connection: http.client.HTTPConnection) -> None:
        self._fake = fake
        self._origin = f"https://{connection.host}"
        self._timeout = connection.timeout
        self._sent = bytearray()

    def sendall(self, data: bytes, *args: object) -> None:
        self._sent += bytes(data)

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        head, _, raw = bytes(self._sent).partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        method, target, _version = lines[0].split(" ", 2)
        headers = {name.strip().lower(): value.strip() for name, _, value in (line.partition(":") for line in lines[1:])}
        body = json.loads(raw.decode("utf-8")) if raw else None
        self._fake.exchanges.append(
            _Exchange(
                method=method,
                url=f"{self._origin}{target}",
                authorization=headers.get("authorization"),
                content_type=headers.get("content-type"),
                timeout=self._timeout,
                body=body,
            )
        )
        answer = self._fake.answer(body or {})
        return _RaisingReader(answer) if isinstance(answer, BaseException) else io.BytesIO(answer)

    def close(self) -> None:
        pass


def _install(monkeypatch: pytest.MonkeyPatch, answer: _Answer) -> _FakeGitHub:
    return _FakeGitHub(answer=answer).install(monkeypatch)


# --- fixture project data ---------------------------------------------------------------------


def _issue(item_id: str, *, state: str = "OPEN", status: str | None = "Todo") -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "ISSUE",
        "updatedAt": "2026-10-01T10:00:00Z",
        "fieldValueByName": {"name": status} if status else None,
        "content": {"title": f"Issue {item_id}", "state": state, "repository": {"nameWithOwner": f"{_EXAMPLE_ORG}/alpha"}},
    }


def _pull_request(item_id: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "PULL_REQUEST",
        "updatedAt": "2026-10-02T10:00:00Z",
        "fieldValueByName": {"name": "In review"},
        "content": {"title": f"PR {item_id}", "state": "MERGED", "repository": {"nameWithOwner": f"{_EXAMPLE_ORG}/beta"}},
    }


def _draft(item_id: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "DRAFT_ISSUE",
        "updatedAt": "2026-10-03T10:00:00Z",
        "fieldValueByName": {"name": "Backlog"},
        "content": {"title": f"Draft {item_id}"},
    }


def _redacted(item_id: str) -> dict[str, Any]:
    return {"id": item_id, "type": "REDACTED", "updatedAt": "2026-10-04T10:00:00Z", "fieldValueByName": None, "content": None}


def _page(nodes: list[dict[str, Any]], *, next_cursor: str | None = None) -> dict[str, Any]:
    page_info = {"hasNextPage": next_cursor is not None, "endCursor": next_cursor}
    items = {"pageInfo": page_info, "nodes": nodes}
    return {"data": {"organization": {"projectV2": {"items": items}}}}


def _by_project(pages: dict[int, list[dict[str, Any]]]) -> _Answer:
    """Each project's pages in order, keyed by the request's own ``number`` variable."""

    def _answer(body: dict[str, Any]) -> bytes:
        variables = body["variables"]
        project_pages = pages[variables["number"]]
        index = 0 if variables["after"] is None else int(variables["after"].removeprefix("cursor-"))
        return _json_reply(project_pages[index])

    return _answer


# --- the query-only guard -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "document",
    [
        PROJECT_ITEMS_QUERY,
        "{ viewer { login } }",
        "query { viewer { login } }",
        "query Q($mutation: Int = 1, $o: In = {a: [1, 2]}) @live { a(x: $mutation) { b } }  # trailing",
        'query { a(text: "mutation { x } and } braces") { b } }',
        'query { a(text: """block "mutation" { and \\""" escaped""") { b } }',
        "# mutation { x }\nquery { a }",
    ],
    ids=["project-items", "shorthand", "anonymous", "variables-and-directives", "string", "block-string", "comment"],
)
def test_assert_single_query_accepts_one_query(document: str) -> None:
    assert_single_query(document)


@pytest.mark.parametrize(
    ("document", "reason"),
    [
        ("mutation { addProjectV2ItemById(input: {}) { clientMutationId } }", "mutation"),
        ("mutation Named { a }", "mutation"),
        ("subscription { a }", "subscription"),
        ("fragment F on Issue { id }", "fragment"),
        ("query { a } mutation { b }", "2 definitions"),
        ("mutation { a } query { b }", "2 definitions"),
        ("query { a } { b }", "2 definitions"),
        ("query { a } query { b }", "2 definitions"),
        ("", "0 definitions"),
        ("# only a comment", "0 definitions"),
        ("a { b }", "does not open with an operation"),
        ("query { a ", "do not balance"),
        ("query { a } }", "does not open with an operation"),
        ("query (a", "do not balance"),
        ("query a) { b }", "do not balance"),
        ("query { a(x: ?) }", "token GraphQL does not define"),
        ('query { a(x: "unterminated) }', "token GraphQL does not define"),
        (None, "not text"),
        (b"query { a }", "not text"),
    ],
)
def test_assert_single_query_refuses_everything_else(document: object, reason: str) -> None:
    with pytest.raises(GraphQLOperationRefusedError, match=reason) as caught:
        assert_single_query(document)
    assert "query only" in str(caught.value)


@pytest.mark.parametrize("document", ["mutation { a }", "subscription { a }", "query { a } mutation { b }"])
def test_default_client_refuses_a_non_query_before_a_socket_opens(document: str) -> None:
    """The autouse guard fails any connect: a refusal that reached the socket would fail here."""
    client = GitHubGraphQLProjectItemsClient(token=_SENTINEL, timeout=_REQUEST_TIMEOUT)
    with pytest.raises(GraphQLOperationRefusedError):
        client.execute(document)


def test_the_client_refuses_a_non_query_without_any_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(monkeypatch, lambda _body: _json_reply({"data": {}}))
    for document in ("mutation { a }", "subscription { a }"):
        with pytest.raises(GraphQLOperationRefusedError):
            fake.client().execute(document)
    assert fake.exchanges == []


def test_the_shipped_query_is_one_query_with_a_status_lookup() -> None:
    assert_single_query(PROJECT_ITEMS_QUERY)
    assert 'fieldValueByName(name: "Status")' in PROJECT_ITEMS_QUERY
    assert f"first: {PROJECT_ITEMS_PAGE_SIZE}" in PROJECT_ITEMS_QUERY


# --- AC1: two projects, every item type, each item once ----------------------------------------


def test_two_projects_list_each_item_once_with_its_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(
        monkeypatch,
        _by_project(
            {
                _PROJECT_A: [_page([_issue("i-1"), _pull_request("p-1"), _issue("i-1")])],
                _PROJECT_B: [_page([_draft("d-1"), _redacted("r-1"), _issue("i-2", state="CLOSED", status=None)])],
            }
        ),
    )
    items = fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A, _PROJECT_B])
    assert items == (
        ListedProjectItem(_PROJECT_A, "i-1", "ISSUE", "Issue i-1", "OPEN", f"{_EXAMPLE_ORG}/alpha", "Todo", "2026-10-01T10:00:00Z"),
        ListedProjectItem(
            _PROJECT_A, "p-1", "PULL_REQUEST", "PR p-1", "MERGED", f"{_EXAMPLE_ORG}/beta", "In review", "2026-10-02T10:00:00Z"
        ),
        ListedProjectItem(_PROJECT_B, "d-1", "DRAFT_ISSUE", "Draft d-1", None, None, "Backlog", "2026-10-03T10:00:00Z"),
        ListedProjectItem(_PROJECT_B, "r-1", "REDACTED", None, None, None, None, None),
        ListedProjectItem(
            _PROJECT_B, "i-2", "ISSUE", "Issue i-2", "CLOSED", f"{_EXAMPLE_ORG}/alpha", None, "2026-10-01T10:00:00Z"
        ),
    )


def test_a_status_field_that_is_not_single_select_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    node = _issue("i-1")
    node["fieldValueByName"] = {}  # the inline fragment matched nothing
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [_page([node])]}))
    (item,) = fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)
    assert item.status is None


def test_an_issue_with_no_readable_content_keeps_its_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    node = _issue("i-1")
    node["content"] = None
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [_page([node])]}))
    (item,) = fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)
    assert (item.id, item.content_type, item.title, item.state, item.repository) == ("i-1", "ISSUE", None, None, None)


def test_the_same_projects_listed_twice_are_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [_page([_issue("i-1")])]}))
    items = fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A, _PROJECT_A])
    assert [item.id for item in items] == ["i-1"]
    assert len(fake.exchanges) == 1


# --- AC2: pagination ----------------------------------------------------------------------------


def test_every_page_is_read_by_following_the_end_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        _page([_issue("i-1"), _issue("i-2")], next_cursor="cursor-1"),
        _page([_pull_request("p-1")], next_cursor="cursor-2"),
        _page([_draft("d-1")]),
    ]
    fake = _install(monkeypatch, _by_project({_PROJECT_A: pages}))
    items = fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)
    assert [item.id for item in items] == ["i-1", "i-2", "p-1", "d-1"]
    assert [e.body["variables"]["after"] for e in fake.exchanges if e.body] == [None, "cursor-1", "cursor-2"]
    assert len(fake.exchanges) == _THREE_PAGES


def test_an_item_that_moves_between_pages_is_listed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [_page([_issue("i-1")], next_cursor="cursor-1"), _page([_issue("i-1"), _issue("i-2")])]
    fake = _install(monkeypatch, _by_project({_PROJECT_A: pages}))
    assert [item.id for item in fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)] == ["i-1", "i-2"]


@pytest.mark.parametrize("cursor", [None, "", 7], ids=["null", "empty", "not-text"])
def test_has_next_page_without_a_usable_cursor_is_an_error(monkeypatch: pytest.MonkeyPatch, cursor: object) -> None:
    page = _page([_issue("i-1")])
    page["data"]["organization"]["projectV2"]["items"]["pageInfo"] = {"hasNextPage": True, "endCursor": cursor}
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [page]}))
    with pytest.raises(FleetInventoryApiError, match="endCursor"):
        fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)


def test_a_repeated_cursor_cannot_loop_forever(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(monkeypatch, lambda _body: _json_reply(_page([_issue("i-1")], next_cursor="cursor-0")))
    with pytest.raises(FleetInventoryApiError, match="repeated"):
        fake.client().list_project_items(_EXAMPLE_ORG, _PROJECT_A)
    assert len(fake.exchanges) == 2  # noqa: PLR2004 -- the first cursor, then the repeat


# --- AC4: every request is a POST /graphql carrying one query ------------------------------------


def test_every_request_is_a_post_to_graphql_with_one_query(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [_page([_issue("i-1")], next_cursor="cursor-1"), _page([_pull_request("p-1")])]
    fake = _install(monkeypatch, _by_project({_PROJECT_A: pages, _PROJECT_B: pages}))
    fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A, _PROJECT_B])
    assert len(fake.exchanges) == 2 * 2  # noqa: PLR2004 -- two projects, two pages each
    for exchange in fake.exchanges:
        assert (exchange.method, exchange.url) == ("POST", _GRAPHQL)
        assert exchange.content_type == "application/json"
        assert exchange.authorization == _BEARER
        assert exchange.timeout == _REQUEST_TIMEOUT
        assert exchange.body is not None
        assert set(exchange.body) == {"query", "variables"}
        assert exchange.body["variables"]["login"] == _EXAMPLE_ORG
        assert_single_query(exchange.body["query"])
    assert all("mutation" not in query and "subscription" not in query for query in fake.queries)


def test_a_redirect_is_never_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A redirected POST would not be the reviewed query: a 3xx is an error, and nothing is re-sent."""
    fake = _install(
        monkeypatch,
        lambda _body: _http_response(307, headers={"Location": "https://api.github.com/elsewhere"}),
    )
    with pytest.raises(FleetInventoryApiError, match="HTTP 307"):
        fake.client().execute(PROJECT_ITEMS_QUERY, {"login": _EXAMPLE_ORG, "number": 1, "after": None})
    assert len(fake.exchanges) == 1


def test_the_client_repr_hides_the_token() -> None:
    client = GitHubGraphQLProjectItemsClient(token=_SENTINEL, timeout=_REQUEST_TIMEOUT)
    assert _SENTINEL not in repr(client)
    assert "<redacted>" in repr(client)


def test_a_malformed_token_is_refused_before_any_request() -> None:
    with pytest.raises(FleetInventoryApiError, match="not one printable token") as caught:
        GitHubGraphQLProjectItemsClient(token="two words", timeout=_REQUEST_TIMEOUT)
    assert "two words" not in str(caught.value)


# --- AC5: typed errors naming `projects` and the entry's position, no token -----------------------


def _fail_text(caught: pytest.ExceptionInfo[BaseException]) -> str:
    rendered = "".join(traceback.format_exception(caught.value, capture_locals=True))
    return f"{caught.value!s} {caught.value!r} {rendered}"


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            lambda _b: _json_reply(
                {"errors": [{"type": "NOT_FOUND", "message": "Could not resolve to a ProjectV2 secret-name"}], "data": None}
            ),
            "errors array of 1 (NOT_FOUND)",
        ),
        (lambda _b: _json_reply({"data": {"organization": {"projectV2": None}}}), "not found, or this login cannot read it"),
        (lambda _b: _json_reply({"data": {"organization": None}}), "not found, or this login cannot read it"),
        (lambda _b: _json_reply({"data": None}), "not found, or this login cannot read it"),
        (lambda _b: _json_reply({"data": {"organization": {"projectV2": {"items": None}}}}), "no items connection"),
        (lambda _b: _json_reply({"data": {"organization": {"projectV2": {"items": {}}}}}), "no nodes or no pageInfo"),
        (lambda _b: _json_reply({}, status=502), "HTTP 502"),
        (lambda _b: _json_reply({}, status=503), "HTTP 503"),
        (lambda _b: _json_reply({"message": "rate limit"}, status=403), "HTTP 403"),
        (lambda _b: _json_reply({"message": "slow down"}, status=429), "HTTP 429"),
        (lambda _b: _http_response(200, body=b"not json"), "invalid JSON"),
        (lambda _b: _http_response(200, body=b"\xff\xfe"), "invalid JSON"),
        (lambda _b: _json_reply([1, 2]), "not an object"),
    ],
    ids=[
        "errors",
        "project-null",
        "organisation-null",
        "data-null",
        "items-null",
        "items-empty",
        "http-502",
        "http-503",
        "http-403",
        "http-429",
        "invalid-json",
        "invalid-utf8",
        "not-an-object",
    ],
)
def test_a_failing_entry_is_typed_and_named_by_position(
    monkeypatch: pytest.MonkeyPatch, answer: _Answer, expected: str
) -> None:
    ok_page = _page([_issue("i-1")])

    def _answer(body: dict[str, Any]) -> bytes:
        return _json_reply(ok_page) if body["variables"]["number"] == _PROJECT_A else answer(body)

    fake = _install(monkeypatch, _answer)
    with pytest.raises(ProjectEntryError) as caught:
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A, _PROJECT_B])
    message = str(caught.value)
    assert message.startswith("config key projects, entry 2 of 2: ")
    assert expected in message
    assert caught.value.position == 2  # noqa: PLR2004
    assert isinstance(caught.value, FleetInventoryApiError)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    for secret in (_SENTINEL, "secret-name", str(_PROJECT_B)):
        assert secret not in _fail_text(caught)


def test_the_graphql_error_text_is_never_echoed(monkeypatch: pytest.MonkeyPatch) -> None:
    errors = [
        {"type": "NOT_FOUND", "message": "leaky-message-1"},
        {"type": "not an enum", "message": "leaky-message-2"},
        "leaky-message-3",
        {"message": "leaky-message-4"},
    ]
    fake = _install(monkeypatch, lambda _b: _json_reply({"errors": errors}))
    with pytest.raises(ProjectEntryError) as caught:
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])
    assert "errors array of 4 (NOT_FOUND)" in str(caught.value)
    assert "leaky-message" not in _fail_text(caught)


def test_a_single_error_object_is_an_errors_array_too(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _install(monkeypatch, lambda _b: _json_reply({"errors": {"type": "RATE_LIMITED", "message": "x"}}))
    with pytest.raises(ProjectEntryError, match=r"errors array of 1 \(RATE_LIMITED\)"):
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])


@pytest.mark.parametrize(
    ("node", "reason"),
    [
        ("not an object", "an item is not a JSON object"),
        ({"type": "ISSUE"}, "an item has no id"),
        ({"id": "", "type": "ISSUE"}, "an item has no id"),
        ({"id": "x", "type": "EPIC"}, "an item has an unknown content type"),
        ({"id": "x"}, "an item has an unknown content type"),
        ({"id": "x", "type": 5}, "an item has an unknown content type"),
    ],
)
def test_a_malformed_item_fails_the_whole_listing(monkeypatch: pytest.MonkeyPatch, node: object, reason: str) -> None:
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [_page([_issue("i-1"), node])]}))  # type: ignore[list-item]
    with pytest.raises(ProjectEntryError, match=reason):
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])


def test_a_failure_on_a_later_page_discards_the_earlier_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    def _answer(body: dict[str, Any]) -> bytes:
        if body["variables"]["after"] is None:
            return _json_reply(_page([_issue("i-1")], next_cursor="cursor-1"))
        return _json_reply({}, status=502)

    fake = _install(monkeypatch, _answer)
    with pytest.raises(ProjectEntryError, match="entry 1 of 1: GitHub API HTTP 502"):
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])


@pytest.mark.parametrize(
    "error",
    [ConnectionResetError("reset by peer"), TimeoutError("timed out"), RuntimeError("boom")],
    ids=["reset", "timeout", "runtime"],
)
def test_a_transport_failure_is_typed_and_carries_no_token(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def _answer(_body: dict[str, Any]) -> BaseException:
        return error

    fake = _install(monkeypatch, _answer)
    with pytest.raises(ProjectEntryError, match="transport failed") as caught:
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])
    assert _SENTINEL not in _fail_text(caught)


def test_a_connect_failure_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _connect(connection: http.client.HTTPConnection) -> None:
        raise ConnectionRefusedError

    monkeypatch.setattr(http.client.HTTPSConnection, "connect", _connect)
    with pytest.raises(ProjectEntryError, match="request failed") as caught:
        GitHubGraphQLProjectItemsClient(token=_SENTINEL, timeout=_REQUEST_TIMEOUT).list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])
    assert _SENTINEL not in _fail_text(caught)


def test_a_base_exception_propagates_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    def _answer(_body: dict[str, Any]) -> BaseException:
        return KeyboardInterrupt()

    fake = _install(monkeypatch, _answer)
    with pytest.raises(KeyboardInterrupt) as caught:
        fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])
    assert _SENTINEL not in _fail_text(caught)


def test_the_token_reaches_the_wire_and_no_log_or_item(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    fake = _install(monkeypatch, _by_project({_PROJECT_A: [_page([_issue("i-1")])]}))
    items = fake.client().list_projects_items(_EXAMPLE_ORG, [_PROJECT_A])
    assert [e.authorization for e in fake.exchanges] == [_BEARER]
    assert _SENTINEL not in caplog.text
    assert _SENTINEL not in repr(items)
