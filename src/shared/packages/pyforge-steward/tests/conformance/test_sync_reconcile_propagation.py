"""`reconcile` — Epic 8, Story 8.1. One test per I/O & Edge-Case Matrix row,
plus the two algorithm corrections recorded in the story's Design Notes
(value-equality short-circuit; sync-point captured strictly after the
write). Every test drives `reconcile` through a fake `transport` returning
canned GraphQL/REST JSON, entirely in-memory — no live network call.
"""

from __future__ import annotations

import json
import urllib.request

import pytest
from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import (
    SyncAPIError,
    SyncConfig,
    TransportResponse,
    get_jira_issue,
    github_graphql_request,
    reconcile,
    transition_jira_issue,
)

_GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

CONFIG = SyncConfig(
    github_project_id="PVT_1",
    github_status_field_id="gh_status",
    github_link_field_id="gh_link",
    github_sync_point_field_id="gh_syncpoint",
    jira_base_url="https://example.atlassian.net",
    jira_project_key="PROJ",
    jira_link_field_id="jira_link",
    jira_sync_point_field_id="jira_syncpoint",
)

CONFIG_JIRA_WINS = SyncConfig(
    **{**CONFIG.__dict__, "field_overrides": {"status": "jira"}}
)


class FakeTransport:
    """Routes GitHub GraphQL POSTs and Jira REST calls against small,
    in-memory `github_fields`/`jira_fields` state, entirely without a live
    network call. Records every call so tests can assert exactly which
    writes did (or, for --dry-run/no-op, did not) happen.
    """

    def __init__(
        self,
        *,
        github_item_id: str = "ITEM_1",
        github_fields: dict[str, str] | None = None,
        github_updated_at: str,
        jira_issue_key: str = "PROJ-1",
        jira_fields: dict[str, object] | None = None,
        jira_updated_at: str,
        jira_transitions: list[dict[str, object]] | None = None,
    ) -> None:
        self.github_item_id = github_item_id
        self.github_fields: dict[str, str] = dict(github_fields or {})
        self.github_updated_at = github_updated_at
        self.jira_issue_key = jira_issue_key
        self.jira_fields: dict[str, object] = dict(jira_fields or {})
        self.jira_updated_at = jira_updated_at
        self.jira_transitions = jira_transitions or []
        self.calls: list[dict[str, object]] = []

    def __call__(self, request: urllib.request.Request) -> TransportResponse:
        method = request.get_method()
        url = request.full_url
        body = json.loads(request.data) if request.data else None
        self.calls.append({"method": method, "url": url, "body": body})

        if url == _GITHUB_GRAPHQL_URL:
            return self._github(body)
        return self._jira(method, url, body)

    # -- GitHub GraphQL ------------------------------------------------

    def _github(self, body: dict[str, object]) -> TransportResponse:
        variables = body["variables"]
        if "fieldId" in variables:
            self.github_fields[variables["fieldId"]] = variables["value"]["text"]
            payload = {
                "data": {
                    "updateProjectV2ItemFieldValue": {
                        "projectV2Item": {"id": variables["itemId"]}
                    }
                }
            }
            return TransportResponse(status=200, body=json.dumps(payload).encode())

        node = {
            "id": self.github_item_id,
            "updatedAt": self.github_updated_at,
            "fieldValues": {
                "nodes": [
                    {"text": value, "field": {"id": field_id}}
                    for field_id, value in self.github_fields.items()
                ]
            },
        }
        payload = {"data": {"node": node}}
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    # -- Jira REST v3 ----------------------------------------------------

    def _jira(self, method: str, url: str, body: dict[str, object] | None) -> TransportResponse:
        if url.endswith("/transitions"):
            if method == "GET":
                payload = {"transitions": self.jira_transitions}
                return TransportResponse(status=200, body=json.dumps(payload).encode())
            transition_id = body["transition"]["id"]
            matched = next(t for t in self.jira_transitions if t["id"] == transition_id)
            self.jira_fields["status"] = {"name": matched["to"]["name"]}
            return TransportResponse(status=204, body=b"")
        if method == "GET":
            payload = {"fields": {**self.jira_fields, "updated": self.jira_updated_at}}
            return TransportResponse(status=200, body=json.dumps(payload).encode())
        if method == "PUT":
            self.jira_fields.update(body["fields"])
            return TransportResponse(status=204, body=b"")
        raise AssertionError(f"FakeTransport: unexpected jira call {method} {url}")

    # -- Test helpers ------------------------------------------------------

    def write_calls(self) -> list[dict[str, object]]:
        """Every call that mutated state: a GitHub field write (has
        `fieldId` in its GraphQL variables), a Jira transition POST, or a
        Jira PUT."""
        writes = []
        for call in self.calls:
            if call["url"] == _GITHUB_GRAPHQL_URL:
                if "fieldId" in call["body"]["variables"]:
                    writes.append(call)
            elif call["method"] in ("POST", "PUT"):
                writes.append(call)
        return writes


def _jira_status(transport: FakeTransport) -> str | None:
    return (transport.jira_fields.get("status") or {}).get("name")


# ── Row: GH changed, Jira didn't -> Jira updated to match, both sync-points refreshed ──


def test_github_changed_jira_did_not_pushes_to_jira_and_refreshes_both_sync_points():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",  # newer than gh_syncpoint -> not stale
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",  # <= jira_syncpoint -> stale
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"
    assert transport.github_fields["gh_syncpoint"] != "2026-08-01T00:00:00+00:00"
    assert transport.jira_fields["jira_syncpoint"] != "2026-08-05T00:00:00+00:00"
    assert transport.github_fields["gh_syncpoint"] == transport.jira_fields["jira_syncpoint"]


# ── Row: Jira changed, GH didn't -> GH item field updated, both sync-points refreshed ──


def test_jira_changed_github_did_not_pushes_to_github_and_refreshes_both_sync_points():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        github_updated_at="2026-08-01T00:00:00Z",  # <= gh_syncpoint -> stale
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        jira_updated_at="2026-08-05T00:00:00Z",  # newer than jira_syncpoint -> not stale
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"
    assert transport.github_fields["gh_status"] == "In Progress"
    assert transport.github_fields["gh_syncpoint"] != "2026-08-05T00:00:00+00:00"
    assert transport.jira_fields["jira_syncpoint"] != "2026-08-01T00:00:00+00:00"
    assert transport.github_fields["gh_syncpoint"] == transport.jira_fields["jira_syncpoint"]


# ── Row: both changed since last sync (real conflict) -> GitHub wins per AD-4 ──


def _conflict_transport() -> FakeTransport:
    return FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",  # newer than gh_syncpoint -> not stale
        jira_fields={
            "status": {"name": "Blocked"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        jira_updated_at="2026-08-05T00:00:00Z",  # newer than jira_syncpoint -> not stale
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "41", "to": {"name": "Blocked"}},
        ],
    )


def test_real_conflict_github_wins_by_default_per_ad4():
    transport = _conflict_transport()

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"
    assert transport.github_fields["gh_status"] == "In Progress"  # github's own value untouched


def test_real_conflict_honors_field_overrides_jira_wins():
    transport = _conflict_transport()

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_JIRA_WINS, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"
    assert transport.github_fields["gh_status"] == "Blocked"
    assert _jira_status(transport) == "Blocked"  # jira's own value untouched


# ── Row: neither changed (loop candidate / redelivery) -> no-op, no writes ──


def test_neither_changed_is_a_no_op_with_zero_writes():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        github_updated_at="2026-08-01T00:00:00Z",  # <= gh_syncpoint -> stale
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",  # <= jira_syncpoint -> stale
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert transport.write_calls() == []


# ── Row: --dry-run -> same decision computed and reported, zero write calls ──


def test_dry_run_computes_the_same_decision_and_makes_no_write_calls():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, dry_run=True, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"  # same decision a real run would make
    assert transport.write_calls() == []
    assert _jira_status(transport) == "To Do"  # untouched


# ── Row: link unresolvable -> ok=False naming the unlinked item, no write attempted ──


def test_unresolvable_github_link_fails_named_and_makes_no_write():
    transport = FakeTransport(
        github_fields={
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
            # no "gh_link" entry at all -> link field reads as unset
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_updated_at="2026-08-05T00:00:00Z",
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary
    assert "ITEM_1" in result.summary
    assert transport.write_calls() == []


def test_unresolvable_jira_link_fails_named_and_makes_no_write():
    transport = FakeTransport(
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_syncpoint": "2026-08-01T00:00:00+00:00",
            # no "jira_link" entry -> link field reads as unset
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_updated_at="2026-08-05T00:00:00Z",
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary
    assert "PROJ-1" in result.summary
    assert transport.write_calls() == []


# ── Row: target API rejects the pushed value -> named, logged failure ──


def test_no_matching_jira_transition_is_a_named_failure_not_a_guess():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "Nonexistent Status",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",
        jira_transitions=[{"id": "21", "to": {"name": "To Do"}}],  # no match for "Nonexistent Status"
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "Nonexistent Status" in result.summary
    assert _jira_status(transport) == "To Do"  # never guessed a different transition
    # the sync-point refresh must never run after a failed value push
    assert transport.github_fields["gh_syncpoint"] == "2026-08-01T00:00:00+00:00"


# ── Design Notes correction (1): value-equality short-circuit ──


def test_value_already_matches_destination_is_a_no_op_despite_staleness_saying_push():
    """An unrelated field edit legitimately makes gh_stale False (AD-5 is
    item-level, not field-level) without the TRACKED value having changed --
    reconcile must recognize the destination already holds the target value
    and make no write, rather than attempting a live push/transition for a
    value that's already there."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",  # already matches jira's status below
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",  # not stale (some unrelated field changed)
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",  # stale -> would compute push_to_jira
        # No transitions registered: if reconcile attempted a live push, the
        # "no transition matches" failure below would fire and this test
        # would fail loudly instead of silently passing on the wrong branch.
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert transport.write_calls() == []


def test_value_already_matches_short_circuits_even_a_real_conflict():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "Blocked",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",  # not stale
        jira_fields={
            "status": {"name": "Blocked"},  # already matches gh's value
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        jira_updated_at="2026-08-05T00:00:00Z",  # not stale -> real conflict by staleness alone
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert transport.write_calls() == []


# ── Design Notes correction (2): sync-point captured strictly after the write ──


def test_sync_point_written_is_not_older_than_the_tracked_value_write():
    """The two sync-point writes must be the LAST calls FakeTransport
    records -- proof `reconcile` captures/writes the new sync point only
    after the cross-system value write has already completed, never before
    or once up front."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert result.ok is True

    writes = transport.write_calls()
    # The tracked-value write (the Jira transition POST) happens before
    # either sync-point write (one GitHub GraphQL mutation, one Jira PUT).
    transition_index = next(
        i for i, c in enumerate(writes) if c["url"].endswith("/transitions")
    )
    sync_point_indices = [i for i in range(len(writes)) if i != transition_index]
    assert sync_point_indices, "expected two sync-point writes after the tracked-value write"
    assert all(i > transition_index for i in sync_point_indices)


# ── AC: given a valid SyncConfig missing a link on entry (both ids empty) ──


def test_neither_identifier_given_fails_named_without_any_call():
    transport = FakeTransport(github_updated_at="2026-08-05T00:00:00Z", jira_updated_at="2026-08-05T00:00:00Z")

    result = reconcile(config=CONFIG, transport=transport)

    assert result.ok is False
    assert transport.calls == []


def test_empty_string_identifier_is_treated_like_not_given():
    transport = FakeTransport(github_updated_at="2026-08-05T00:00:00Z", jira_updated_at="2026-08-05T00:00:00Z")

    result = reconcile(github_item_id="", jira_issue_key="", config=CONFIG, transport=transport)

    assert result.ok is False


# ── Review pass 1 findings: reciprocal-link and configured-project validation ──


def test_mismatched_reciprocal_link_is_rejected():
    """Github item ITEM_1 links to PROJ-1, but PROJ-1's own link field points
    somewhere else -- not a real pair, must not silently reconcile."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_syncpoint": "2026-08-01T00:00:00+00:00",
        },
        github_updated_at="2026-08-05T00:00:00Z",
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_999",  # does not point back at ITEM_1
            "jira_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        jira_updated_at="2026-08-01T00:00:00Z",
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "not a reciprocal pair" in result.summary
    assert transport.write_calls() == []


def test_jira_issue_outside_configured_project_is_rejected():
    """CONFIG.jira_project_key is 'PROJ'; an issue key from another project
    must be rejected before any state is read from it."""
    transport = FakeTransport(
        github_updated_at="2026-08-05T00:00:00Z",
        jira_updated_at="2026-08-05T00:00:00Z",
    )

    result = reconcile(jira_issue_key="OTHER-1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "does not belong to configured project" in result.summary
    assert transport.calls == []


def test_jira_timestamp_without_colon_in_offset_is_parsed():
    """Jira Cloud's real wire format is commonly '+0000' with no colon,
    distinct from every other fixture's 'Z'/'+00:00' style."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_syncpoint": "2026-08-05T00:00:00+00:00",
        },
        github_updated_at="2026-08-01T00:00:00Z",  # stale
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_syncpoint": "2026-08-01T00:00:00+0000",
        },
        jira_updated_at="2026-08-05T12:00:00.000+0000",  # not stale, no colon in offset
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"


def test_github_graphql_non_dict_response_is_a_named_failure():
    """A 2xx response whose body is valid JSON but not an object (e.g. a
    bare list) must raise SyncAPIError, not an unhandled AttributeError
    from `payload.get(...)`."""

    def transport(request):
        return TransportResponse(status=200, body=b"[1, 2, 3]")

    credential = HostScopedCredential(hosts=("api.github.com",))
    with pytest.raises(SyncAPIError, match="unexpected response shape"):
        github_graphql_request("query{x}", {}, credential=credential, transport=transport)


def test_jira_status_field_not_a_mapping_reads_as_unknown_status():
    """A malformed 'status' value (present but not an object) must read as
    an unknown status, never raise an unhandled AttributeError."""

    def transport(request):
        payload = {"fields": {"status": "not-a-mapping", "updated": "2026-08-05T00:00:00Z"}}
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    credential = HostScopedCredential(hosts=("example.atlassian.net",))
    state = get_jira_issue("PROJ-1", config=CONFIG, credential=credential, transport=transport)

    assert state.status is None


def test_jira_transitions_not_a_list_is_a_named_failure():
    """A malformed 'transitions' value (present but not a list) must raise
    SyncAPIError, never an unhandled AttributeError mid-iteration."""

    def transport(request):
        if request.full_url.endswith("/transitions") and request.get_method() == "GET":
            return TransportResponse(status=200, body=json.dumps({"transitions": "not-a-list"}).encode())
        raise AssertionError("unexpected call")

    credential = HostScopedCredential(hosts=("example.atlassian.net",))
    with pytest.raises(SyncAPIError, match="not a list"):
        transition_jira_issue(
            "PROJ-1", "In Progress", config=CONFIG, credential=credential, transport=transport
        )
