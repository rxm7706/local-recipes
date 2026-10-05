"""Unit tests for the default ``GitHubForgeClient`` (Story 6.9 client, Story 14.1 coverage).

The client is the only place the package opens a socket, so its integration
test drives a loopback server. These tests drive the same code through a
scripted ``urllib.request.urlopen``: request shape, the dedup lookup, the
five-call open sequence with its malformed-payload fallbacks, the 422
branch-exists skip, and the egress marker that brackets every call.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from urllib.error import HTTPError

import pytest

from pyforge.warden import actuator
from pyforge.warden.actuator import (
    ForgeResponseError,
    GitHubForgeClient,
    RemediationProposal,
    _branch_name,
    _BranchExistsError,
    run_actuator,
)
from pyforge.warden.models import Finding, Severity, SeverityTier

_REPO = "owner/name"
_PROPOSAL = RemediationProposal(
    finding_id="vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0",
    action="upgrade",
    subject="pdos-vuln-fixture",
    title="warden: upgrade pdos-vuln-fixture to resolve PDOS-FIXTURE-0001",
    body="body",
)


class _Response:
    def __init__(self, body: object) -> None:
        self._raw = b"" if body is None else json.dumps(body).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._raw


class _Transport:
    """A scripted ``urlopen``: replies are consumed in order; an ``Exception``
    reply is raised. Records each request and the egress marker it saw."""

    def __init__(self, *replies: object) -> None:
        self._replies = list(replies)
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[object] = []
        self.egress_seen: list[bool] = []

    def __call__(self, request: urllib.request.Request, timeout: object = None) -> _Response:
        self.requests.append(request)
        self.timeouts.append(timeout)
        self.egress_seen.append(actuator._EGRESS_ACTIVE.get())
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return _Response(reply)

    def payload(self, index: int) -> Any:
        data = self.requests[index].data
        assert isinstance(data, bytes)
        return json.loads(data)


def _install(monkeypatch: pytest.MonkeyPatch, *replies: object) -> _Transport:
    transport = _Transport(*replies)
    monkeypatch.setattr(urllib.request, "urlopen", transport)
    return transport


def _client(**kwargs: Any) -> GitHubForgeClient:
    return GitHubForgeClient("tok", _REPO, "https://api.example", **kwargs)


def _http_error(code: int) -> HTTPError:
    return HTTPError("https://api.example/x", code, "status", None, None)  # type: ignore[arg-type]


_BASE_BRANCH = {"commit": {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}}


def _open_replies(*, pull: object = None, ref: object = None) -> tuple[object, ...]:
    return (
        {"default_branch": "trunk"},
        _BASE_BRANCH,
        {"sha": "new-sha"},
        {} if ref is None else ref,
        {"html_url": "https://forge.example/pull/9"} if pull is None else pull,
    )


def test_from_env_builds_a_client_that_calls_the_resolved_api(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(monkeypatch, [])
    client = GitHubForgeClient.from_env(
        {"GITHUB_TOKEN": "tok", "GITHUB_REPOSITORY": _REPO, "GITHUB_API_URL": "https://ghe.example/api/"}
    )
    assert client.existing_open_pr(_PROPOSAL.finding_id) is None
    (request,) = transport.requests
    assert request.full_url.startswith("https://ghe.example/api/repos/owner/name/pulls?")
    assert request.get_method() == "GET"
    assert request.get_header("Authorization") == "Bearer tok"
    assert not request.has_header("Content-type")
    assert request.data is None


def test_a_timeout_is_passed_to_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(monkeypatch, [])
    _client(timeout=7).existing_open_pr(_PROPOSAL.finding_id)
    assert transport.timeouts == [7]


def test_existing_open_pr_queries_the_open_head_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(monkeypatch, [{"html_url": "https://forge.example/pull/3"}])
    assert _client().existing_open_pr(_PROPOSAL.finding_id) == "https://forge.example/pull/3"
    url = transport.requests[0].full_url
    assert "state=open" in url
    assert f"head=owner%3A{_branch_name(_PROPOSAL.finding_id).replace('/', '%2F')}" in url


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ([{"url": "https://api.example/pulls/4"}], "https://api.example/pulls/4"),
        ([{"number": 5}], ""),
        (["not-a-dict"], ""),
        ([], None),
        ({"message": "not a list"}, None),
        (None, None),
    ],
)
def test_existing_open_pr_reads_every_response_shape(
    monkeypatch: pytest.MonkeyPatch, reply: object, expected: str | None
) -> None:
    _install(monkeypatch, reply)
    assert _client().existing_open_pr(_PROPOSAL.finding_id) == expected


def test_open_pull_request_runs_the_five_call_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(monkeypatch, *_open_replies())
    assert _client().open_pull_request(_PROPOSAL) == "https://forge.example/pull/9"

    assert [(r.get_method(), r.full_url.removeprefix("https://api.example")) for r in transport.requests] == [
        ("GET", "/repos/owner/name"),
        ("GET", "/repos/owner/name/branches/trunk"),
        ("POST", "/repos/owner/name/git/commits"),
        ("POST", "/repos/owner/name/git/refs"),
        ("POST", "/repos/owner/name/pulls"),
    ]
    branch = _branch_name(_PROPOSAL.finding_id)
    assert transport.payload(2) == {"message": _PROPOSAL.title, "tree": "tree-sha", "parents": ["base-sha"]}
    assert transport.payload(3) == {"ref": f"refs/heads/{branch}", "sha": "new-sha"}
    assert transport.payload(4) == {"title": _PROPOSAL.title, "head": branch, "base": "trunk", "body": "body"}
    assert transport.requests[2].get_header("Content-type") == "application/json"


def test_open_pull_request_falls_back_to_main_and_no_parent_on_malformed_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _install(monkeypatch, ["not-a-repo-dict"], [], {"sha": "new-sha"}, {}, {"html_url": "u"})
    assert _client().open_pull_request(_PROPOSAL) == "u"
    assert transport.requests[1].full_url.endswith("/branches/main")
    assert transport.payload(2) == {"message": _PROPOSAL.title, "tree": None, "parents": []}
    assert transport.payload(4)["base"] == "main"


def test_open_pull_request_tolerates_a_commit_with_no_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(
        monkeypatch,
        {},
        {"commit": {"sha": "base-sha", "commit": "not-a-dict"}},
        ["not-a-commit-dict"],
        {},
        {"url": "https://api.example/pulls/12"},
    )
    assert _client().open_pull_request(_PROPOSAL) == "https://api.example/pulls/12"
    assert transport.payload(2) == {"message": _PROPOSAL.title, "tree": None, "parents": ["base-sha"]}
    assert transport.payload(3)["sha"] is None


def test_a_422_on_the_ref_is_a_branch_exists_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = list(_open_replies())
    replies[3] = _http_error(422)
    _install(monkeypatch, *replies)
    with pytest.raises(_BranchExistsError):
        _client().open_pull_request(_PROPOSAL)


def test_any_other_ref_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = list(_open_replies())
    replies[3] = _http_error(500)
    _install(monkeypatch, *replies)
    with pytest.raises(HTTPError) as caught:
        _client().open_pull_request(_PROPOSAL)
    assert caught.value.code == 500


@pytest.mark.parametrize("pull", [{}, {"number": 9}, ["not-a-dict"]])
def test_a_pull_response_with_no_url_is_a_loud_failure(monkeypatch: pytest.MonkeyPatch, pull: object) -> None:
    _install(monkeypatch, *_open_replies(pull=pull))
    with pytest.raises(ForgeResponseError):
        _client().open_pull_request(_PROPOSAL)


def test_egress_is_marked_only_for_the_duration_of_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _install(monkeypatch, [], _http_error(500))
    client = _client()
    client.existing_open_pr(_PROPOSAL.finding_id)
    with pytest.raises(HTTPError):
        client.existing_open_pr(_PROPOSAL.finding_id)
    assert transport.egress_seen == [True, True]
    assert actuator._EGRESS_ACTIVE.get() is False


def test_run_actuator_records_a_branch_exists_as_skipped_not_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    finding = Finding(
        id=_PROPOSAL.finding_id,
        axis="vulnerability",
        message="pdos-vuln-fixture: PDOS-FIXTURE-0001 (severity critical)",
        subject="pdos-vuln-fixture",
        severity=Severity(tier=SeverityTier.CRITICAL, raw="CVSS:3.1/…"),
    )
    replies = list(_open_replies())
    replies[3] = _http_error(422)
    _install(monkeypatch, [], *replies)
    actuation = run_actuator([finding], dry_run=False, client=_client(), fix_target_resolution_enabled=False)
    (outcome,) = actuation.outcomes
    assert outcome.status == "skipped"
    assert "already exists" in (outcome.detail or "")
    assert outcome.pr_url is None
