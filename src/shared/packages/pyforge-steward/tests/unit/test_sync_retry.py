"""Story 83.2 (DW-FU-8-1-3): one bounded retry around `sync.py`'s transport seam.

No GitHub/Jira call used to retry: `_default_transport` returns any HTTP status and
every caller raised `SyncAPIError` on the first `status >= 400`, a 429 or a
secondary-rate-limit 403 included. `_send` now wraps the seam at each call site, so a
fake injected straight into `github_graphql_request` / the Jira functions goes through
it too: a 429, a rate-limited 403 and a 502/503/504 are retried a fixed number of
times (4 attempts in total), sleeping `Retry-After` (capped) when given and
exponential backoff otherwise, through the injectable `sync._sleep`. Every other
status is returned on the first answer; after the last attempt the response goes to
the caller, which fails as before.
"""

from __future__ import annotations

import email.message
import io
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

import pytest

from pyforge.steward import sync
from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import (
    JiraIssueState,
    SyncAPIError,
    SyncConfig,
    TransportResponse,
    get_jira_issue,
    github_graphql_request,
    transition_jira_issue,
    update_github_assignees,
    update_jira_issue_fields,
)

CONFIG = SyncConfig(
    github_project_id="PVT_1",
    github_status_field_id="gh_status",
    github_link_field_id="gh_link",
    github_baseline_field_id="gh_baseline",
    jira_base_url="https://example.atlassian.net",
    jira_project_key="PROJ",
    jira_link_field_id="jira_link",
    jira_baseline_field_id="jira_baseline",
)

_GH = HostScopedCredential(hosts=("api.github.com",))
_JIRA = HostScopedCredential(hosts=("example.atlassian.net",))

_OK_GRAPHQL = TransportResponse(status=200, body=json.dumps({"data": {"ok": True}}).encode())
_OK_JIRA_ISSUE = TransportResponse(
    status=200,
    body=json.dumps({"fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1"}}).encode(),
)


def _limited(status: int = 429, **headers: str) -> TransportResponse:
    return TransportResponse(status=status, body=b"slow down", headers=headers)


class Scripted:
    """A transport answering from a script, one response per call; the last one
    repeats once the script is spent, so "429 on every attempt" is a one-item
    script. Records every request."""

    def __init__(self, *responses: TransportResponse) -> None:
        self.responses = list(responses)
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request) -> TransportResponse:
        self.requests.append(request)
        index = min(len(self.requests), len(self.responses)) - 1
        return self.responses[index]

    @property
    def calls(self) -> int:
        return len(self.requests)


@pytest.fixture
def slept(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace the injectable sleep: records each wait, never waits."""
    seen: list[float] = []
    monkeypatch.setattr(sync, "_sleep", seen.append)
    return seen


def _graphql(transport: Scripted) -> dict[str, object]:
    return github_graphql_request("query{x}", {}, credential=_GH, transport=transport)


def _jira_issue(transport: Scripted) -> JiraIssueState:
    return get_jira_issue("PROJ-1", config=CONFIG, credential=_JIRA, transport=transport)


# ── The headline rows ───────────────────────────────────────────────────────


def test_429_with_retry_after_then_200_returns_the_payload_and_sleeps_that_long(slept):
    transport = Scripted(_limited(429, **{"Retry-After": "2"}), _OK_GRAPHQL)

    payload = _graphql(transport)

    assert payload == {"data": {"ok": True}}
    assert transport.calls == 2
    assert slept == [2.0]


@pytest.mark.parametrize("call", [_graphql, _jira_issue], ids=["github", "jira"])
def test_429_on_every_attempt_raises_after_the_bounded_attempts(slept, call):
    transport = Scripted(_limited(429))

    with pytest.raises(SyncAPIError, match="HTTP 429"):
        call(transport)

    assert transport.calls == 4  # 1 call + 3 retries, never further
    assert slept == [1.0, 2.0, 4.0]  # backoff when no Retry-After is given


@pytest.mark.parametrize("status", [400, 401, 404, 422])
@pytest.mark.parametrize("call", [_graphql, _jira_issue], ids=["github", "jira"])
def test_a_4xx_other_than_429_and_the_rate_limited_403_is_not_retried(slept, call, status):
    transport = Scripted(TransportResponse(status=status, body=b"nope"))

    with pytest.raises(SyncAPIError, match=f"HTTP {status}"):
        call(transport)

    assert transport.calls == 1
    assert slept == []


# ── Which responses are retried ─────────────────────────────────────────────


def test_a_plain_permission_403_is_not_retried(slept):
    transport = Scripted(TransportResponse(status=403, body=b"forbidden"))

    with pytest.raises(SyncAPIError, match="HTTP 403"):
        _graphql(transport)

    assert transport.calls == 1
    assert slept == []


def test_a_403_that_is_not_a_rate_limit_stays_a_403_with_headers_present(slept):
    transport = Scripted(_limited(403, **{"x-ratelimit-remaining": "42"}))

    with pytest.raises(SyncAPIError, match="HTTP 403"):
        _graphql(transport)

    assert transport.calls == 1


@pytest.mark.parametrize(
    "headers",
    [
        {"Retry-After": "3"},
        {"retry-after": "3"},
        {"x-ratelimit-remaining": "0"},
        {"X-RateLimit-Remaining": "0"},
    ],
    ids=["retry-after", "retry-after-lower", "ratelimit-remaining", "ratelimit-remaining-mixed-case"],
)
def test_a_rate_limited_403_is_retried(slept, headers):
    transport = Scripted(_limited(403, **headers), _OK_GRAPHQL)

    assert _graphql(transport) == {"data": {"ok": True}}

    assert transport.calls == 2
    assert len(slept) == 1


@pytest.mark.parametrize("status", [502, 503, 504])
def test_a_gateway_error_is_retried_then_succeeds(slept, status):
    transport = Scripted(TransportResponse(status=status, body=b"bad gateway"), _OK_JIRA_ISSUE)

    state = _jira_issue(transport)

    assert state.status == "To Do"
    assert transport.calls == 2
    assert slept == [1.0]


def test_a_500_is_not_retried(slept):
    transport = Scripted(TransportResponse(status=500, body=b"boom"))

    with pytest.raises(SyncAPIError, match="HTTP 500"):
        _graphql(transport)

    assert transport.calls == 1
    assert slept == []


def test_a_success_is_never_slept_for(slept):
    transport = Scripted(_OK_GRAPHQL)

    _graphql(transport)

    assert transport.calls == 1
    assert slept == []


# ── How long it waits ───────────────────────────────────────────────────────


def test_backoff_without_retry_after_doubles_each_attempt(slept):
    transport = Scripted(_limited(503), _limited(503), _limited(503), _OK_GRAPHQL)

    assert _graphql(transport) == {"data": {"ok": True}}

    assert slept == [1.0, 2.0, 4.0]
    assert transport.calls == 4


def test_retry_after_is_honoured_each_time_it_is_given(slept):
    transport = Scripted(
        _limited(429, **{"Retry-After": "5"}),
        _limited(429, **{"Retry-After": "0"}),
        _limited(429),
        _OK_GRAPHQL,
    )

    _graphql(transport)

    assert slept == [5.0, 0.0, 4.0]  # the third answer has none: backoff for attempt 3


def test_retry_after_is_capped(slept):
    transport = Scripted(_limited(429, **{"Retry-After": "3600"}), _OK_GRAPHQL)

    _graphql(transport)

    assert slept == [60.0]


@pytest.mark.parametrize(
    "value",
    ["Wed, 21 Oct 2026 07:28:00 GMT", "soon", "", "nan", "inf", "-inf", "-5"],
)
def test_an_unusable_retry_after_falls_back_to_the_backoff(slept, value):
    transport = Scripted(_limited(429, **{"Retry-After": value}), _OK_GRAPHQL)

    _graphql(transport)

    assert slept == [1.0]


# ── Every call site goes through the retry ──────────────────────────────────


def _assignees_add(transport: Scripted) -> None:
    update_github_assignees("acme", "widgets", 7, add="octocat", remove=None, credential=_GH, transport=transport)


def _assignees_remove(transport: Scripted) -> None:
    update_github_assignees("acme", "widgets", 7, add=None, remove="octocat", credential=_GH, transport=transport)


def _jira_put(transport: Scripted) -> None:
    update_jira_issue_fields("PROJ-1", {"jira_baseline": "{}"}, config=CONFIG, credential=_JIRA, transport=transport)


def _jira_transition(transport: Scripted) -> None:
    transition_jira_issue("PROJ-1", "In Progress", config=CONFIG, credential=_JIRA, transport=transport)


_TRANSITIONS = TransportResponse(
    status=200,
    body=json.dumps({"transitions": [{"id": "31", "to": {"name": "In Progress"}}]}).encode(),
)
_NO_CONTENT = TransportResponse(status=204, body=b"")


@pytest.mark.parametrize(
    ("call", "script"),
    [
        pytest.param(_graphql, [_limited(), _OK_GRAPHQL], id="github-graphql"),
        pytest.param(_assignees_add, [_limited(), _NO_CONTENT], id="github-assignee-add"),
        pytest.param(_assignees_remove, [_limited(), _NO_CONTENT], id="github-assignee-remove"),
        pytest.param(_jira_issue, [_limited(), _OK_JIRA_ISSUE], id="jira-issue-get"),
        pytest.param(_jira_put, [_limited(), _NO_CONTENT], id="jira-fields-put"),
        pytest.param(_jira_transition, [_limited(), _TRANSITIONS, _NO_CONTENT], id="jira-transitions-get"),
        pytest.param(_jira_transition, [_TRANSITIONS, _limited(), _NO_CONTENT], id="jira-transition-post"),
    ],
)
def test_every_transport_call_site_retries_a_rate_limit(slept, call, script):
    transport = Scripted(*script)

    call(transport)  # raises SyncAPIError if any call site bypasses `_send`

    assert transport.calls == len(script)
    assert slept == [1.0]


@pytest.mark.parametrize(
    "call",
    [_assignees_add, _assignees_remove, _jira_put],
    ids=["github-assignee-add", "github-assignee-remove", "jira-fields-put"],
)
def test_a_write_that_is_rate_limited_on_every_attempt_fails_after_four_calls(slept, call):
    transport = Scripted(_limited())

    with pytest.raises(SyncAPIError, match="HTTP 429"):
        call(transport)

    assert transport.calls == 4
    assert slept == [1.0, 2.0, 4.0]


# ── The seam itself: `TransportResponse.headers` and `_default_transport` ───


def test_transport_response_headers_default_to_empty_so_existing_fakes_keep_working():
    response = TransportResponse(status=200, body=b"{}")

    assert response.headers == {}
    assert response == TransportResponse(200, b"{}")
    assert hash(response) == hash(TransportResponse(200, b"{}"))  # a frozen value stays hashable


class _FakeResponse:
    def __init__(self, status: int, body: bytes, headers: Mapping[str, str]) -> None:
        self.status = status
        self._body = body
        message = email.message.Message()
        for name, value in headers.items():
            message[name] = value
        self.headers = message

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status


class _FakeBridge:
    def __init__(self, open_url: Callable[..., object]) -> None:
        self.open_url = open_url


def _request() -> urllib.request.Request:
    return urllib.request.Request("https://api.github.com/graphql", method="POST")


def test_default_transport_carries_the_response_headers(monkeypatch):
    monkeypatch.setattr(
        sync,
        "http_bridge",
        lambda: _FakeBridge(lambda request, timeout: _FakeResponse(200, b"{}", {"X-RateLimit-Remaining": "7"})),
    )

    response = sync._default_transport(_request())

    assert response.status == 200
    assert response.headers == {"X-RateLimit-Remaining": "7"}


def test_default_transport_carries_the_headers_of_an_http_error_status(monkeypatch):
    headers = email.message.Message()
    headers["Retry-After"] = "2"

    def open_url(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", headers, io.BytesIO(b"slow"))

    monkeypatch.setattr(sync, "http_bridge", lambda: _FakeBridge(open_url))

    response = sync._default_transport(_request())

    assert (response.status, response.body) == (429, b"slow")
    assert response.headers == {"Retry-After": "2"}
    # ... and the wrapped transport turns that into the sleep the headline row expects.
    assert sync._retry_delay(response, 1) == 2.0


def test_default_transport_tolerates_an_http_error_with_no_headers(monkeypatch):
    def open_url(request, timeout):
        # `HTTPError.headers` really can be None; typeshed declares it non-optional.
        raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "http_bridge", lambda: _FakeBridge(open_url))

    response = sync._default_transport(_request())

    assert response.status == 503
    assert response.headers == {}
