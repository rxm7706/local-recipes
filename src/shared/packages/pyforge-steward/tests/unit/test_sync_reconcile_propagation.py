"""`reconcile` — Epic 8, Story 8.1. One test per I/O & Edge-Case Matrix row,
against the AD-5(amended)/AD-10 per-field baseline-value mechanism (never a
timestamp — see `sync.py`'s own module docstring and this story's Design
Notes). Every test drives `reconcile` through a fake `transport` returning
canned GraphQL/REST JSON, entirely in-memory — no live network call.
"""

from __future__ import annotations

import json
import urllib.request
from urllib.parse import unquote

import pytest

from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import (
    SyncAPIError,
    SyncConfig,
    SyncMultipleAssigneesError,
    TransportResponse,
    _parse_baseline,
    _parse_content,
    get_jira_issue,
    github_graphql_request,
    list_linked_github_items,
    reconcile,
    reconcile_schedule_batch,
    transition_jira_issue,
    update_github_assignees,
)

_GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

CONFIG = SyncConfig(
    github_project_id="PVT_1",
    github_status_field_id="gh_status",
    github_link_field_id="gh_link",
    github_baseline_field_id="gh_baseline",
    jira_base_url="https://example.atlassian.net",
    jira_project_key="PROJ",
    jira_link_field_id="jira_link",
    jira_baseline_field_id="jira_baseline",
    # Identity mapping covering this file's entire fixture vocabulary (every
    # `push_to_github`-decision test in this file, including the `--schedule`
    # batch tests) -- Story 8.6. Every existing test's Jira status values
    # already match their GitHub counterparts 1:1, so translation is a no-op
    # here; the dedicated translation/unmapped tests below use their own
    # differently-shaped `status_mapping`.
    status_mapping={"To Do": "To Do", "In Progress": "In Progress", "Blocked": "Blocked"},
)

CONFIG_JIRA_WINS = SyncConfig(**{**CONFIG.__dict__, "field_overrides": {"status": "jira"}})

# Story 8.7: github login -> jira accountId, covering this file's assignee
# fixture vocabulary. "ghost"/"acc_ghost" are deliberately absent -- the
# dedicated unmapped-assignee tests below rely on that.
CONFIG_USER_MAPPING = SyncConfig(
    **{**CONFIG.__dict__, "user_mapping": {"octocat": "acc_octocat", "hubot": "acc_hubot"}}
)

# An IDENTITY user_mapping (github login string == jira accountId string) --
# isolates the assignee convergence-check test from translation noise, the
# same technique CONFIG's own identity status_mapping already uses for the
# symmetric status convergence tests.
CONFIG_USER_MAPPING_IDENTITY = SyncConfig(
    **{**CONFIG.__dict__, "user_mapping": {"octocat": "octocat", "hubot": "hubot"}}
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
        github_content: dict[str, object] | None = None,
        github_content_unreadable: bool = False,
        jira_issue_key: str = "PROJ-1",
        jira_fields: dict[str, object] | None = None,
        jira_transitions: list[dict[str, object]] | None = None,
    ) -> None:
        self.github_item_id = github_item_id
        self.github_fields: dict[str, str] = dict(github_fields or {})
        # Story 8.7: the `content` fragment (assignees/repository/number) --
        # `None` (the default, every pre-8.7 fixture) reads as "no content"
        # KEY ABSENT, matching a DraftIssue exactly (both parse to
        # assignee=None, content_ref=None, assignee_unknown=False).
        self.github_content = github_content
        # RESOLVED 2026-08-15 (escalation, finding 3): distinct from the
        # above -- an explicit `content: null` (a partial-response
        # signature, e.g. a permission gap), which reads as UNKNOWN, never
        # a confident "no assignee".
        self.github_content_unreadable = github_content_unreadable
        self.jira_issue_key = jira_issue_key
        self.jira_fields: dict[str, object] = dict(jira_fields or {})
        self.jira_transitions = jira_transitions or []
        self.calls: list[dict[str, object]] = []

    def __call__(self, request: urllib.request.Request) -> TransportResponse:
        method = request.get_method()
        url = request.full_url
        body = json.loads(request.data) if request.data else None
        self.calls.append({"method": method, "url": url, "body": body})

        if url == _GITHUB_GRAPHQL_URL:
            return self._github(body)
        if url.startswith("https://api.github.com/repos/"):
            return self._github_rest_assignees(method, url, body)
        return self._jira(method, url, body)

    # -- GitHub GraphQL ------------------------------------------------

    def _github(self, body: dict[str, object]) -> TransportResponse:
        variables = body["variables"]
        if "fieldId" in variables:
            self.github_fields[variables["fieldId"]] = variables["value"]["text"]
            payload = {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": variables["itemId"]}}}}
            return TransportResponse(status=200, body=json.dumps(payload).encode())

        node = {
            "id": self.github_item_id,
            "fieldValues": {
                "nodes": [{"text": value, "field": {"id": field_id}} for field_id, value in self.github_fields.items()]
            },
        }
        if self.github_content_unreadable:
            node["content"] = None
        elif self.github_content is not None:
            node["content"] = self.github_content
        payload = {"data": {"node": node}}
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    # -- GitHub REST v3 (Story 8.7: assignee writes only) -----------------

    def _github_rest_assignees(self, method: str, url: str, body: dict[str, object] | None) -> TransportResponse:
        """Distinct from `_jira` (Story 8.7: both are non-GraphQL HTTP
        calls, routed by URL host/path in `__call__` above, never
        conflated). Records the call (already done in `__call__`) and
        reports success.

        The write is APPLIED to `github_content["assignees"]["nodes"]`
        (review pass 2): asserting only on the requests issued cannot
        distinguish "assigned the right person" from "POSTed then DELETEd
        the same login and left the item unassigned" -- the two are the
        same request list. Tests that care about the resulting state read
        `_github_assignees(transport)`; tests that care about the calls are
        unaffected, since applying the write changes no recorded call."""
        if method not in ("POST", "DELETE"):
            raise AssertionError(f"FakeTransport: unexpected github REST call {method} {url}")
        if self.github_content is not None:
            logins = [node["login"] for node in ((self.github_content.get("assignees") or {}).get("nodes") or [])]
            for login in (body or {}).get("assignees", []):
                if method == "POST" and login not in logins:
                    logins.append(login)
                elif method == "DELETE" and login in logins:
                    logins.remove(login)
            self.github_content["assignees"] = {"nodes": [{"login": login} for login in logins]}
        return TransportResponse(status=200, body=b"{}")

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
            payload = {"fields": dict(self.jira_fields)}
            return TransportResponse(status=200, body=json.dumps(payload).encode())
        if method == "PUT":
            self.jira_fields.update(body["fields"])
            return TransportResponse(status=204, body=b"")
        raise AssertionError(f"FakeTransport: unexpected jira call {method} {url}")

    # -- Test helpers ------------------------------------------------------

    def write_calls(self) -> list[dict[str, object]]:
        """Every call that mutated state: a GitHub field write (has
        `fieldId` in its GraphQL variables), a GitHub REST assignee
        POST/DELETE, a Jira transition POST, or a Jira PUT."""
        writes = []
        for call in self.calls:
            if call["url"] == _GITHUB_GRAPHQL_URL:
                if "fieldId" in call["body"]["variables"]:
                    writes.append(call)
            elif call["url"].startswith("https://api.github.com/repos/"):
                writes.append(call)
            elif call["method"] in ("POST", "PUT"):
                writes.append(call)
        return writes


def _jira_status(transport: FakeTransport) -> str | None:
    return (transport.jira_fields.get("status") or {}).get("name")


def _status_push_calls(transport: FakeTransport) -> list[dict[str, object]]:
    """Calls that push the TRACKED value itself -- as opposed to a baseline
    refresh: a GitHub field write to the status field, or a Jira transition
    POST."""
    pushes = []
    for call in transport.calls:
        if call["url"] == _GITHUB_GRAPHQL_URL:
            variables = (call["body"] or {}).get("variables", {})
            if variables.get("fieldId") == CONFIG.github_status_field_id:
                pushes.append(call)
        elif call["url"].endswith("/transitions") and call["method"] == "POST":
            pushes.append(call)
    return pushes


def _baseline_write_calls(transport: FakeTransport) -> list[dict[str, object]]:
    """Calls that refresh a baseline field: a GitHub field write to the
    baseline field, or a Jira PUT (baseline writes go through
    `update_jira_issue_fields`, distinct from a transition POST)."""
    writes = []
    for call in transport.calls:
        if call["url"] == _GITHUB_GRAPHQL_URL:
            variables = (call["body"] or {}).get("variables", {})
            if variables.get("fieldId") == CONFIG.github_baseline_field_id:
                writes.append(call)
        elif call["method"] == "PUT":
            writes.append(call)
    return writes


# ── Row: GH changed, Jira didn't -> Jira updated to match, both baselines refreshed ──


def test_github_changed_jira_did_not_pushes_to_jira_and_refreshes_both_baselines():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # matches current -- jira unchanged
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress", "assignee": None}


# ── Row: Jira changed, GH didn't -> GH item field updated, both baselines refreshed ──


def test_jira_changed_github_did_not_pushes_to_github_and_refreshes_both_baselines():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',  # matches current -- gh unchanged
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"
    assert transport.github_fields["gh_status"] == "In Progress"
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress", "assignee": None}


# ── Row (Story 8.6, AD-6/CAP-5): a mapped Jira status translates before writing to GitHub ──

CONFIG_STATUS_TRANSLATION = SyncConfig(**{**CONFIG.__dict__, "status_mapping": {"Closed": "Done"}})


def test_mapped_jira_status_translates_before_writing_to_github():
    """A Jira status name that differs from its GitHub counterpart must be
    translated through `status_mapping` before the GitHub write -- GitHub's
    status field receives the MAPPED value, GitHub's baseline records that
    mapped value, and Jira's baseline records the original (untranslated)
    value, since Jira's own value never changed."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',  # matches current -- gh unchanged
        },
        jira_fields={
            "status": {"name": "Closed"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG_STATUS_TRANSLATION, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"
    assert transport.github_fields["gh_status"] == "Done"
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "Done", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "Closed", "assignee": None}
    # `result.details["baseline"]` must mirror the actually-written (translated)
    # GH value, never the raw pre-translation `target_value` -- a caller reading
    # the returned details, not the transport, must see the same truth.
    assert result.details["baseline"] == {"status": "Done"}


def test_unmapped_jira_status_pushed_to_github_is_a_named_failure_not_a_passthrough():
    """AD-6: an unmapped status value crossing into GitHub is a hard, named
    failure, never passed through as a phantom GitHub state. No GitHub
    write happens, and neither baseline is written (mirrors
    `test_no_matching_jira_transition_is_a_named_failure_not_a_guess`'s
    assertion shape for the symmetric push_to_jira direction)."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',  # matches current -- gh unchanged
        },
        jira_fields={
            "status": {"name": "Triage"},  # not in CONFIG_STATUS_TRANSLATION.status_mapping
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
    )

    result = reconcile(jira_issue_key="PROJ-1", config=CONFIG_STATUS_TRANSLATION, transport=transport)

    assert result.ok is False
    assert "unmapped: jira status 'Triage' has no status_mapping entry for github" in result.summary
    assert transport.write_calls() == []
    assert transport.github_fields["gh_baseline"] == '{"status": "To Do"}'
    assert transport.jira_fields["jira_baseline"] == '{"status": "To Do"}'


# ── Row: both changed since their own baseline (real conflict) -> GitHub wins per AD-4 ──


def _conflict_transport() -> FakeTransport:
    return FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "Blocked"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
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


# ── Row: neither changed (loop candidate / redelivery / echo) -> no-op, no writes ──


def test_neither_changed_is_a_no_op_with_zero_writes():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            # this pair has already synced once post-upgrade -- both fields
            # present in the baseline, matching current -- unchanged
            "gh_baseline": '{"status": "In Progress", "assignee": null}',
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress", "assignee": null}',  # matches current -- unchanged
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert transport.write_calls() == []  # true no-op: baseline is never touched either


# ── Row: --dry-run -> same decision computed and reported, zero write calls ──


def test_dry_run_computes_the_same_decision_and_makes_no_write_calls():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, dry_run=True, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"  # same decision a real run would make
    assert transport.write_calls() == []  # zero writes, including to either baseline field
    assert _jira_status(transport) == "To Do"  # untouched


# ── Row: link unresolvable -> ok=False naming the unlinked item, no write attempted ──


def test_unresolvable_github_link_fails_named_and_makes_no_write():
    transport = FakeTransport(
        github_fields={
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',
            # no "gh_link" entry at all -> link field reads as unset
        },
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
            "jira_baseline": '{"status": "To Do"}',
            # no "jira_link" entry -> link field reads as unset
        },
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
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # unchanged
        },
        jira_transitions=[{"id": "21", "to": {"name": "To Do"}}],  # no match for "Nonexistent Status"
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "Nonexistent Status" in result.summary
    assert _jira_status(transport) == "To Do"  # never guessed a different transition
    # the baseline refresh must never run after a failed value push
    assert transport.github_fields["gh_baseline"] == '{"status": "To Do"}'
    assert transport.jira_fields["jira_baseline"] == '{"status": "To Do"}'


# ── Row: first link (no baseline yet) ───────────────────────────────────────


def test_first_link_no_baseline_and_differing_values_ad4_decides_and_writes_both_baselines():
    """AD-10 rule 1: an absent baseline key is a first link, not a loop
    candidate -- never collapsed with 'both changed relative to a real
    baseline'. Both sides already hold differing values, so AD-4's default
    authority (GitHub wins) decides, and both sides' baseline fields are
    written for the first time afterward."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            # no "gh_baseline" entry at all -> never synced
        },
        jira_fields={
            "status": {"name": "Blocked"},
            "jira_link": "ITEM_1",
            # no "jira_baseline" entry at all -> never synced
        },
        jira_transitions=[{"id": "31", "to": {"name": "In Progress"}}],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress", "assignee": None}


def test_first_link_no_baseline_and_matching_values_is_a_no_op_but_still_writes_both_baselines():
    """Same first-link scenario, but both sides already agree -- no push
    needed, yet both baseline fields must still be written for the first
    time (AD-10 rule 1's 'baselines written afterward'), or every future
    reconcile of this newly-linked pair would see it as 'changed' forever."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
        },
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert _status_push_calls(transport) == []
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress", "assignee": None}


# ── Row: field cleared on one side (explicit null CURRENT value, not the baseline) ──


def test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github():
    """The 'field cleared' row: Jira's baseline recorded a real prior value,
    but Jira's CURRENT status is now the explicit null sentinel (the key is
    present in the baseline map -- it's the CURRENT read that's absent).
    This must be treated as a genuine change and propagated -- never
    confused with 'never synced' (which is the baseline KEY's absence, not
    the current value's).

    Exercises the GH-unchanged / Jira-cleared-pushed-to-GitHub direction via
    `update_project_item_field`, which accepts any value (including a
    clear) -- chosen over the inverse direction because
    `transition_jira_issue`'s transition lookup has no sensible way to
    'transition to null'."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "In Progress"}',  # matches current -- unchanged
        },
        jira_fields={
            # no "status" key at all -> reads as None (cleared)
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress"}',  # was "In Progress"; now cleared
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_github"
    assert result.details["target_value"] is None
    assert transport.github_fields["gh_status"] is None
    assert not any(c["url"].endswith("/transitions") for c in transport.calls)
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": None, "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": None, "assignee": None}


# ── Row: baseline exceeds the vendor field-size ceiling -> named failure, not a sidecar ──


def test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push():
    """AD-2/AD-10's escape hatch to Mode B: a serialized baseline map that
    would not fit the configured field's size ceiling must never silently
    fall back to a sidecar store. Jira's ceiling (255 chars) is the
    tighter of the two, so it is the one this test drives over -- and by
    the time it fires, the cross-system VALUE push (the Jira transition)
    has already completed, per reconcile's own documented, accepted
    non-atomicity (same risk class as `keys.rotate_identity`'s
    partial-completion state -- mirrors this file's own
    `test_no_matching_jira_transition_is_a_named_failure_not_a_guess` proof
    shape for a different failure mode)."""
    long_status = "X" * 300  # comfortably over Jira's 255-char ceiling, under GitHub's 1024
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": long_status,
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # unchanged
        },
        jira_transitions=[{"id": "99", "to": {"name": long_status}}],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "baseline" in result.summary
    assert "Mode B" in result.summary
    # The value push already completed -- accepted non-atomicity.
    assert _jira_status(transport) == long_status
    # Neither baseline field was actually written (the failure fires while
    # computing the serialized maps, before either write is attempted).
    assert transport.github_fields["gh_baseline"] == '{"status": "To Do"}'
    assert transport.jira_fields["jira_baseline"] == '{"status": "To Do"}'


# ── Row: both changed to the SAME value -> converged already, no push, baselines still refreshed ──


def test_both_diverged_to_the_same_value_is_a_no_op_but_still_refreshes_baselines():
    """The scenario this check protects under the new mechanism: an
    established pair (both baselines present and non-empty) where BOTH
    sides changed relative to their own baseline (gh_changed=True AND
    jira_changed=True -- an AD-4 'conflict' by the loop-guard's own
    definition), but gh.status already equals jira.status -- both
    independently converged to the SAME new value from their respective
    stale baselines. No push is needed (the destination already holds the
    value AD-4's authority pick would have pushed), but both baselines are
    still stale relative to their OWN prior value and must be refreshed, or
    every future reconcile of this pair would see it as 'changed' forever."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "Blocked",
            "gh_baseline": '{"status": "In Progress"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "Blocked"},  # already matches gh's value
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
        # No transitions registered: if reconcile attempted a live push, the
        # "no transition matches" failure would fire and this test would
        # fail loudly instead of silently passing on the wrong branch.
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert _status_push_calls(transport) == []  # no push write to either side's tracked field
    assert len(_baseline_write_calls(transport)) == 2  # both baselines still refreshed
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "Blocked", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "Blocked", "assignee": None}


def test_both_diverged_to_the_same_value_short_circuits_even_with_jira_wins_override():
    """Same scenario as above, but with `field_overrides={"status": "jira"}`
    -- proves the convergence check fires regardless of which side AD-4
    would have picked as authority, since the two current values already
    agree."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "Blocked",
            "gh_baseline": '{"status": "In Progress"}',
        },
        jira_fields={
            "status": {"name": "Blocked"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
        },
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_JIRA_WINS, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert _status_push_calls(transport) == []
    assert len(_baseline_write_calls(transport)) == 2


# ── Baseline written strictly after the tracked-value write, never before ──


def test_baseline_written_after_the_tracked_value_write_not_before():
    """The two baseline writes must be the LAST calls FakeTransport records
    -- proof `reconcile` refreshes the baseline only after the cross-system
    value write has already completed, never before or interleaved."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert result.ok is True

    writes = transport.write_calls()
    # The tracked-value write (the Jira transition POST) happens before
    # either baseline write (one GitHub GraphQL mutation, one Jira PUT).
    transition_index = next(i for i, c in enumerate(writes) if c["url"].endswith("/transitions"))
    baseline_indices = [i for i in range(len(writes)) if i != transition_index]
    assert baseline_indices, "expected two baseline writes after the tracked-value write"
    assert all(i > transition_index for i in baseline_indices)


# ── AC: given a valid SyncConfig missing a link on entry (both ids empty) ──


def test_neither_identifier_given_fails_named_without_any_call():
    transport = FakeTransport()

    result = reconcile(config=CONFIG, transport=transport)

    assert result.ok is False
    assert transport.calls == []


def test_empty_string_identifier_is_treated_like_not_given():
    transport = FakeTransport()

    result = reconcile(github_item_id="", jira_issue_key="", config=CONFIG, transport=transport)

    assert result.ok is False


def test_both_identifiers_given_and_reciprocal_reconciles_normally():
    """The "both identifiers given" branch of `_read_both_sides` (as
    opposed to resolving one via the other's link field) was otherwise
    untouched by this diff's fixture rewrite -- exercise it directly under
    the new baseline mechanism, not just the two single-identifier paths
    every other test in this file drives."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # unchanged
        },
        jira_transitions=[{"id": "31", "to": {"name": "In Progress"}}],
    )

    result = reconcile(github_item_id="ITEM_1", jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"


# ── Review pass 1 findings: reciprocal-link and configured-project validation ──


def test_mismatched_reciprocal_link_is_rejected():
    """Github item ITEM_1 links to PROJ-1, but PROJ-1's own link field points
    somewhere else -- not a real pair, must not silently reconcile."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_999",  # does not point back at ITEM_1
            "jira_baseline": '{"status": "To Do"}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "not a reciprocal pair" in result.summary
    assert transport.write_calls() == []


def test_jira_issue_outside_configured_project_is_rejected():
    """CONFIG.jira_project_key is 'PROJ'; an issue key from another project
    must be rejected before any state is read from it."""
    transport = FakeTransport()

    result = reconcile(jira_issue_key="OTHER-1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "does not belong to configured project" in result.summary
    assert transport.calls == []


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
        payload = {"fields": {"status": "not-a-mapping"}}
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
        transition_jira_issue("PROJ-1", "In Progress", config=CONFIG, credential=credential, transport=transport)


def test_parse_baseline_treats_none_and_empty_string_as_never_synced():
    assert _parse_baseline(None, side="github item", identifier="ITEM_1") == {}
    assert _parse_baseline("", side="github item", identifier="ITEM_1") == {}


def test_parse_baseline_rejects_a_falsy_non_string_value_instead_of_treating_it_as_never_synced():
    """A baseline field genuinely misconfigured to point at a non-text field
    (e.g. a Jira Number/Checkbox field returning `0`/`false`) must surface a
    named, loud failure -- never silently collapse to '{}' the same way an
    actually-never-synced field does, which would hide a real config
    mismatch behind indistinguishable "first link" behavior."""
    with pytest.raises(SyncAPIError, match="malformed baseline field"):
        _parse_baseline(0, side="jira issue", identifier="PROJ-1")
    with pytest.raises(SyncAPIError, match="malformed baseline field"):
        _parse_baseline(False, side="jira issue", identifier="PROJ-1")


# ── Epic 8 Story 8.7: assignee and identity-link propagation ───────────────
#
# Assignee follows status's exact per-field baseline/AD-4 decision shape,
# translated through `user_mapping` (push_to_jira) or its computed inverse
# (push_to_github). Every fixture below sets both sides' baselines to an
# explicit `"assignee": null` UNLESS the test is specifically about a
# pre-8.7 pair's missing "assignee" key (the adoption/accepted-limitation
# tests) -- an explicit null means "already observed, currently unassigned",
# isolating each test to the ONE thing it's about.


def _github_assignee_rest_calls(transport: FakeTransport) -> list[dict[str, object]]:
    return [call for call in transport.calls if call["url"].endswith("/assignees")]


def _github_assignees(transport: FakeTransport) -> list[str]:
    """GitHub's RESULTING assignee logins, after the fake applied every
    REST write (review pass 2) -- the end state, as opposed to the requests
    that produced it."""
    content = transport.github_content or {}
    return [node["login"] for node in ((content.get("assignees") or {}).get("nodes") or [])]


def test_assignee_changed_on_github_only_translates_and_pushes_to_jira():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"  # status untouched -- isolates the assertion
    assert result.details["assignee"] == {
        "decision": "push_to_jira",
        "target_value": "octocat",
        # written_value mirrors the actually-persisted (translated) value --
        # never the raw pre-translation login.
        "written_value": "acc_octocat",
    }
    assert transport.jira_fields["assignee"] == {"accountId": "acc_octocat"}
    assert _github_assignee_rest_calls(transport) == []  # GH's own value was the source, never written
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": "octocat"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": "acc_octocat"}


def test_assignee_changed_on_jira_only_translates_and_pushes_to_github():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": []},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["assignee"] == {
        "decision": "push_to_github",
        "target_value": "acc_octocat",
        # written_value mirrors the actually-persisted (translated) value --
        # never the raw pre-translation accountId.
        "written_value": "octocat",
    }
    rest_calls = _github_assignee_rest_calls(transport)
    assert len(rest_calls) == 1
    assert rest_calls[0]["url"] == "https://api.github.com/repos/acme/widgets/issues/42/assignees"
    assert rest_calls[0]["method"] == "POST"
    assert rest_calls[0]["body"] == {"assignees": ["octocat"]}
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": "octocat"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": "acc_octocat"}


def test_unmapped_github_login_pushed_to_jira_is_a_named_failure_not_a_passthrough():
    """AD-6/CAP-5's mirror for assignee: an unmapped value crossing into
    Jira is a hard, named failure, never a phantom passthrough. No write
    happens to either side (mirrors
    `test_unmapped_jira_status_pushed_to_github_is_a_named_failure_not_a_passthrough`'s
    assertion shape for the symmetric field)."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "unknown_user"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    assert "unmapped: github login 'unknown_user' has no user_mapping entry for jira" in result.summary
    assert transport.write_calls() == []
    assert transport.github_fields["gh_baseline"] == '{"status": "To Do", "assignee": null}'
    assert transport.jira_fields["jira_baseline"] == '{"status": "To Do", "assignee": null}'


def test_unmapped_jira_account_id_pushed_to_github_is_a_named_failure_not_a_passthrough():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": []},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_unknown"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    assert "unmapped: jira accountId 'acc_unknown' has no user_mapping entry for github" in result.summary
    assert transport.write_calls() == []


def test_assignee_explicitly_cleared_on_github_bypasses_translation_and_clears_jira():
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": "octocat"}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": []},  # cleared
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": "acc_octocat"}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["assignee"] == {
        "decision": "push_to_jira",
        "target_value": None,
        "written_value": None,
    }
    assert transport.jira_fields["assignee"] is None
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": None}


def test_assignee_explicitly_cleared_on_jira_bypasses_translation_and_removes_only_the_tracked_github_login():
    """The GitHub-side mirror: only the PREVIOUSLY-tracked login is removed
    (Boundaries & Constraints, 'never touch an assignee this module didn't
    itself add') -- never a blind wipe of whatever GitHub currently shows."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": "octocat"}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            # no "assignee" key -> reads as None (cleared)
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": "acc_octocat"}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["assignee"] == {
        "decision": "push_to_github",
        "target_value": None,
        "written_value": None,
    }
    rest_calls = _github_assignee_rest_calls(transport)
    assert len(rest_calls) == 1
    assert rest_calls[0]["method"] == "DELETE"
    assert rest_calls[0]["body"] == {"assignees": ["octocat"]}
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": None}


def test_assignee_push_to_a_draft_issue_content_is_a_named_failure_never_a_guess():
    """`content_ref is None` (a DraftIssue, or absent content) has no
    owner/repo/number to target -- raises SyncAPIError naming the item,
    never guesses. No write attempted to any side."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={},  # DraftIssue (or absent) -- no owner/repo/number
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    assert "cannot write assignee" in result.summary
    assert "draft issue" in result.summary
    assert "ITEM_1" in result.summary
    assert transport.write_calls() == []


def test_pre_8_7_pair_assignees_already_agree_is_a_true_no_op_with_zero_writes():
    """Design Notes' accepted-limitation row: an established pair (baseline
    has 'status' only, no 'assignee' key) whose GitHub/Jira assignees
    already happen to agree (both None here, no content configured) must
    not spuriously backfill -- the missing key is silently adopted, without
    comparison, and the call remains a true, zero-write no-op."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "In Progress"}',  # no "assignee" key -- pre-8.7
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress"}',  # no "assignee" key -- pre-8.7
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"
    assert result.details["assignee"]["decision"] == "no_op"
    assert transport.write_calls() == []


def test_pre_8_7_pair_assignees_already_disagree_is_resolved_via_ad4():
    """RESOLVED 2026-08-15 (escalation, finding 1, decision (b)): a
    pre-existing real-world assignee mismatch (GitHub says 'octocat', Jira
    says hubot's accountId) observed for the first time on an established
    pair's post-upgrade reconcile is now a real first-sync AD-4 decision
    for the assignee field alone -- GitHub wins by default -- exactly one
    write, never the prior design's silent, un-compared, permanently-inert
    adoption."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "In Progress"}',  # no "assignee" key -- pre-8.7
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "assignee": {"accountId": "acc_hubot"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress"}',  # no "assignee" key -- pre-8.7
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"  # status itself did not change
    assert result.details["assignee"]["decision"] == "push_to_jira"  # GitHub wins by default
    assert result.details["assignee"]["written_value"] == "acc_octocat"
    assert len(transport.write_calls()) > 0


def test_identity_link_missing_on_jira_side_is_self_healed_without_touching_baseline():
    """The literal AF-5 gap: GitHub's link field already names the Jira
    issue, but Jira's OWN link field was never written back. Previously a
    hard `SyncUnlinkedError`; now a silent, unconditional repair -- no
    human action, and never routed through the baseline (Boundaries &
    Constraints)."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            # no "jira_link" entry at all -> reads as unset
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert result.details["link_repairs"] == ["jira"]
    assert transport.jira_fields["jira_link"] == "ITEM_1"
    # never baselined -- status/assignee both stayed converged, so no
    # baseline write was triggered by the link repair alone.
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": None}


# ── Story 8.7 retro: adversarial-review-confirmed fixes ────────────────────


def test_assignee_both_diverged_to_the_same_translated_value_is_a_no_op_but_still_refreshes_baselines():
    """Assignee's own analog of `test_both_diverged_to_the_same_value_is_a_
    no_op_but_still_refreshes_baselines` for status: an established pair
    where BOTH sides' assignee changed relative to their own stale
    baseline, but the two sides' CURRENT values already agree once
    translated (an identity user_mapping isolates this from translation
    noise, mirroring CONFIG's own identity status_mapping) -- no push is
    needed, but both baselines are still stale relative to their OWN prior
    value and must be refreshed."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": "hubot"}',  # stale -- gh_assignee_changed
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "octocat"},  # already matches gh's NEW value (identity-mapped)
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": "hubot"}',  # stale -- jira_assignee_changed
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING_IDENTITY, transport=transport)

    assert result.ok is True
    assert result.details["decision"] == "no_op"  # status untouched -- isolates the assertion
    assert result.details["assignee"]["decision"] == "no_op"
    assert _github_assignee_rest_calls(transport) == []  # no push write to either side's assignee field
    assert len(_baseline_write_calls(transport)) == 2  # both baselines still refreshed
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "To Do", "assignee": "octocat"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "To Do", "assignee": "octocat"}


def test_update_github_assignees_non_2xx_response_is_a_named_failure():
    """A non-2xx/3xx response from GitHub's REST assignees endpoint must
    raise SyncAPIError, surfaced by `reconcile` as a named ok=False
    failure -- never swallowed or treated as success."""
    inner = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": []},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    def failing_transport(request: urllib.request.Request) -> TransportResponse:
        if request.full_url.endswith("/assignees"):
            return TransportResponse(status=422, body=b'{"message": "Validation Failed"}')
        return inner(request)

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=failing_transport)

    assert result.ok is False
    assert "add assignee" in result.summary
    assert "422" in result.summary


def test_status_push_commits_and_baselines_even_when_assignee_fails_in_the_same_call():
    """Fix (review-confirmed): a LATER field's write failure must not
    strand an EARLIER field's already-successful write's baseline forever.
    Status changes and successfully pushes to Jira; assignee's own login
    ('unknown_user') has no `user_mapping` entry and fails. Status's push
    already committed live and its baseline gets recorded despite the
    later failure; the overall result is still ok=False, naming the
    unmapped-assignee failure."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do", "assignee": null}',  # stale status -- gh_changed
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "unknown_user"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',  # unchanged
        },
        jira_transitions=[{"id": "31", "to": {"name": "In Progress"}}],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    assert "unmapped: github login 'unknown_user' has no user_mapping entry for jira" in result.summary
    # status's push already committed live...
    assert _jira_status(transport) == "In Progress"
    # ...and its baseline got recorded despite the later assignee failure
    assert json.loads(transport.github_fields["gh_baseline"])["status"] == "In Progress"
    assert json.loads(transport.jira_fields["jira_baseline"])["status"] == "In Progress"
    # assignee's own baseline stays untouched -- the failed field is never
    # falsely marked converged, so it's correctly retried next time
    assert json.loads(transport.github_fields["gh_baseline"])["assignee"] is None
    assert json.loads(transport.jira_fields["jira_baseline"])["assignee"] is None


def test_assignee_established_side_is_not_silently_overwritten_by_a_wholly_empty_baseline_side():
    """Fix (review-confirmed, AD-10 rule 1 read at the PAIR level): GitHub's
    baseline is non-empty (an established pair predating this story) but
    has no "assignee" key yet; Jira's baseline is WHOLLY empty (`{}` --
    reachable via the accepted partial-baseline-write-failure precedent,
    e.g. a first reconcile where GH's baseline write succeeded but Jira's
    failed). Before the fix, GH's side (non-empty) would silently ADOPT its
    own current value with no comparison while Jira's side (wholly empty)
    underwent a genuine but essentially-arbitrary AD-4 decision -- and the
    resulting "jira changed, gh unchanged" outcome would silently overwrite
    GH's real, established assignee with Jira's unrelated current value.
    After the fix, a wholly-empty baseline on EITHER side makes this a
    genuine AD-4 conflict decision for BOTH sides -- GitHub's established
    value wins by default authority instead of being clobbered."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "In Progress"}',  # non-empty, established; no "assignee" key
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},  # GH's real, established assignee
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "assignee": {"accountId": "acc_hubot"},  # jira's own unrelated current value
            "jira_link": "ITEM_1",
            # no "jira_baseline" entry at all -> {} (wholly empty)
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    # A genuine, consistent AD-4 decision for BOTH sides -- GitHub's
    # ESTABLISHED assignee wins by default authority rather than being
    # silently overwritten by Jira's essentially-arbitrary current value.
    assert result.details["assignee"]["decision"] == "push_to_jira"
    assert transport.jira_fields["assignee"] == {"accountId": "acc_octocat"}
    assert json.loads(transport.github_fields["gh_baseline"])["assignee"] == "octocat"
    assert json.loads(transport.jira_fields["jira_baseline"])["assignee"] == "acc_octocat"


def test_update_github_assignees_adds_before_removing_when_swapping():
    """Fix (review-confirmed): ADD happens before REMOVE -- proven by
    inspecting `transport.calls`' ordering directly, not just the end
    state, when reconcile swaps GitHub's assignee from one tracked login to
    another."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": "octocat"}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},  # current live assignee
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_hubot"},  # jira changed to a different, mapped user
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": "acc_octocat"}',  # stale -- jira_assignee_changed
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    rest_calls = _github_assignee_rest_calls(transport)
    assert [c["method"] for c in rest_calls] == ["POST", "DELETE"]
    assert rest_calls[0]["body"] == {"assignees": ["hubot"]}
    assert rest_calls[1]["body"] == {"assignees": ["octocat"]}
    assert _github_assignees(transport) == ["hubot"]  # exactly one, the new one


# ── Review pass 2 findings ─────────────────────────────────────────────────


def test_assignee_already_converged_under_a_real_mapping_is_a_no_op_not_a_self_cancelling_write():
    """The convergence check must compare in the DESTINATION's vocabulary.

    Jira's assignee moved off its own stale baseline, but the person it now
    names is -- once translated -- ALREADY GitHub's live assignee. Comparing
    the untranslated values (a Jira accountId against a GitHub login) can
    never match under a real `user_mapping`, so the check never fired and a
    push_to_github was issued with `add` and `remove` naming the SAME login:
    POST octocat, DELETE octocat, item left with NO assignee, which the next
    reconcile then propagates to Jira as a genuine unassignment. The whole
    point is proven on the END STATE, not the request list."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": "octocat"}',  # unchanged
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            # The same human, in Jira's spelling -- diverged from jira's own
            # stale baseline, but already converged with GitHub.
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": "acc_hubot"}',  # stale
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["assignee"]["decision"] == "no_op"
    assert _github_assignee_rest_calls(transport) == []  # no churn at all
    assert _github_assignees(transport) == ["octocat"]  # NOT unassigned
    # Both baselines still refresh -- both were stale against their own
    # prior value, exactly like status's convergent-same-value case.
    assert json.loads(transport.github_fields["gh_baseline"])["assignee"] == "octocat"
    assert json.loads(transport.jira_fields["jira_baseline"])["assignee"] == "acc_octocat"


def test_update_github_assignees_never_deletes_the_login_it_just_added():
    """Belt-and-braces guard at the only place that can cause the loss:
    even called directly with `add == remove`, the DELETE is not issued, so
    the item cannot end up unassigned."""
    calls: list[tuple[str, object]] = []

    def transport(request):
        calls.append((request.method, json.loads(request.data) if request.data else None))
        return TransportResponse(status=201, body=b"{}")

    update_github_assignees(
        "acme",
        "widgets",
        42,
        add="octocat",
        remove="octocat",
        credential=HostScopedCredential(hosts=("api.github.com",)),
        transport=transport,
    )

    assert calls == [("POST", {"assignees": ["octocat"]})]


def test_one_sided_link_mismatch_is_rejected_even_when_the_other_side_is_empty():
    """A GitHub item already linked to a DIFFERENT Jira issue, paired
    against a Jira issue whose own link field is empty. The empty side is
    not evidence of a pair -- the non-empty side actively contradicts it.
    Story 8.7 relaxed the reciprocity check for the empty-side repair, and
    must not have relaxed it for this: repairing here would destroy a real
    link to PROJ-99 and cross-propagate between two items that were never
    a pair."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-99",  # already linked -- to something else
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "",  # empty
            "jira_baseline": '{"status": "To Do"}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", jira_issue_key="PROJ-1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "not a reciprocal pair" in result.summary
    assert transport.write_calls() == []
    assert transport.github_fields["gh_link"] == "PROJ-99"  # untouched


def test_link_repair_is_not_reported_as_done_when_an_earlier_field_write_failed():
    """Link repairs are sequenced last, so an earlier field's SyncError
    skips them entirely. `details["link_repairs"]` reports what was
    PERSISTED, never what was merely computed as needed -- otherwise a
    caller reads "the link was repaired" about a link that is still
    broken."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "ghost"}]},  # deliberately unmapped
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": None,
            "jira_link": "",  # the AF-5 gap -- a repair IS needed
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    assert "unmapped" in result.summary
    assert result.details["link_repairs"] == []  # computed ["jira"], performed none
    assert transport.jira_fields["jira_link"] == ""  # and it really did not happen


def test_baseline_refresh_failure_still_returns_the_full_details_shape():
    """The one return path that omitted `details` entirely, defaulting to
    `{}` and breaking the "read any key unconditionally" guarantee on
    exactly the path where a caller most needs to know what DID get
    written.

    Reuses the established over-the-ceiling technique (a status value past
    Jira's 255-char baseline-field ceiling) rather than a new fixture knob.
    """
    long_status = "X" * 300
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": long_status,
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
        },
        jira_transitions=[{"id": "99", "to": {"name": long_status}}],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "failed refreshing baseline" in result.summary
    assert result.details["decision"] == "push_to_jira"  # never a KeyError
    assert result.details["assignee"]["decision"] == "no_op"
    assert result.details["link_repairs"] == []


def test_real_conflict_honors_field_overrides_assignee_jira_wins():
    """`_VALID_OVERRIDE_FIELDS` gained "assignee", and this is the branch
    that override actually selects -- both sides' assignee diverged from
    their own baseline, and the override sends Jira's value to GitHub
    instead of AD-4's GitHub-wins default."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',  # stale -- gh_assignee_changed
        },
        github_content={
            "number": 42,
            "assignees": {"nodes": [{"login": "octocat"}]},
            "repository": {"owner": {"login": "acme"}, "name": "widgets"},
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": {"accountId": "acc_hubot"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do", "assignee": null}',  # stale -- jira_assignee_changed
        },
    )
    config = SyncConfig(**{**CONFIG_USER_MAPPING.__dict__, "field_overrides": {"assignee": "jira"}})

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is True
    assert result.details["assignee"]["decision"] == "push_to_github"
    assert result.details["assignee"]["written_value"] == "hubot"
    assert _github_assignees(transport) == ["hubot"]  # jira's value won, exactly one assignee


def test_dry_run_reports_a_pending_link_repair_and_writes_nothing():
    """--dry-run predates the link-repair step, which is the one write in
    this module NOT gated on a "changed" flag -- assert directly that it
    stays behind the dry-run early return."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do", "assignee": null}',
        },
        jira_fields={
            "status": {"name": "To Do"},
            "assignee": None,
            "jira_link": "",  # repair needed
            "jira_baseline": '{"status": "To Do", "assignee": null}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, dry_run=True, transport=transport)

    assert result.ok is True
    assert result.details["link_repairs"] == ["jira"]  # reported as pending
    assert transport.write_calls() == []
    assert transport.jira_fields["jira_link"] == ""  # and not actually written


def test_malformed_content_shapes_never_raw_crash_and_unreadable_assignees_are_unknown():
    """`content` is externally sourced. A partial or proxied response whose
    `repository`/`assignees` came back as a list or a string must read as a
    type-safe result, never a raw `AttributeError` escaping this module's
    named-error contract (which would, under `--schedule`, abort the whole
    batch instead of one item). RESOLVED 2026-08-15 (escalation, finding
    3): a malformed `assignees` sub-shape specifically is UNKNOWN, not a
    confident "no assignee" -- distinct from a well-formed, genuinely-empty
    one."""
    for content in (
        {"number": 42, "assignees": [], "repository": "acme/widgets"},
        {"number": 42, "assignees": {"nodes": ["octocat"]}, "repository": {"owner": []}},
    ):
        assignee, content_ref, unknown = _parse_content({"content": content})
        assert content_ref is None or isinstance(content_ref[2], int)
        assert assignee is None
        assert unknown is True

    # A malformed `number`/`repository` alone (not `assignees`) does not
    # make a well-formed assignee reading unknown -- content_ref simply
    # fails independently.
    assignee, content_ref, unknown = _parse_content(
        {"content": {"number": "42", "assignees": {"nodes": [{"login": "octocat"}]}, "repository": {}}}
    )
    assert content_ref is None
    assert assignee == "octocat"
    assert unknown is False


def test_unreadable_content_is_unknown_not_a_confident_unassignment():
    """RESOLVED 2026-08-15 (escalation, finding 3): `content` present but
    explicit `None` (a partial-response signature, e.g. a permission gap on
    a Projects-only token) is DISTINCT from `content` absent entirely (a
    genuine `DraftIssue`, every pre-8.7 fixture) -- the former is UNKNOWN,
    the latter a confident "no assignee". Reproduces the live data-loss
    path: a converged pair whose GitHub read comes back unreadable must
    never clear Jira's real assignee."""
    assignee, content_ref, unknown = _parse_content({"content": None})
    assert assignee is None
    assert content_ref is None
    assert unknown is True

    assignee, content_ref, unknown = _parse_content({})
    assert assignee is None
    assert content_ref is None
    assert unknown is False


def test_reconcile_downgrades_to_no_op_when_github_assignee_is_unknown():
    """End-to-end (escalation, finding 3): a converged pair whose GitHub
    assignee read comes back UNREADABLE (explicit `content: null`, e.g. a
    permission gap) must never clear Jira's real assignee -- the assignee
    decision downgrades to `no_op`, neither baseline is touched, and the
    round is re-attempted on the next reconcile rather than "converging"
    on data loss."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "In Progress", "assignee": "octocat"}',
        },
        github_content_unreadable=True,
        jira_fields={
            "status": {"name": "In Progress"},
            "assignee": {"accountId": "acc_octocat"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress", "assignee": "acc_octocat"}',
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is True
    assert result.details["assignee"]["decision"] == "no_op"
    assert result.details["assignee"]["written_value"] is None
    assert transport.write_calls() == []
    # Jira's real assignee must survive untouched.
    assert transport.jira_fields["assignee"]["accountId"] == "acc_octocat"


def test_github_item_with_a_co_assignee_is_refused_named():
    """RESOLVED 2026-08-15 (escalation, finding 4, decision (a)): a GitHub
    item carrying more than one assignee is refused named
    (`SyncMultipleAssigneesError`) rather than silently tracking only the
    first, which could leave the item with two assignees or silently
    revert a human's later Jira reassignment."""
    with pytest.raises(SyncMultipleAssigneesError) as exc_info:
        _parse_content(
            {
                "content": {
                    "number": 42,
                    "assignees": {"nodes": [{"login": "octocat"}, {"login": "hubot"}]},
                    "repository": {"owner": {"login": "acme"}, "name": "widgets"},
                }
            }
        )
    assert "octocat" in str(exc_info.value) or "hubot" in str(exc_info.value)


# ── Epic 8 Story 8.2: the zero-loop guarantee, proven by N round trips ──────
#
# CAP-2 claims propagation "holds by construction" (AD-5 amended/AD-10), but
# until now no test ever called `reconcile()` more than once against the
# same stateful transport. These tests seed exactly one human-made change,
# then call `reconcile()` repeatedly against the SAME `FakeTransport`
# instance and assert every later call is a true no-op with zero new WRITES
# (the first call propagates for the two one-sided tests; for the
# convergent-same-value test, round 1 is itself already a no-op -- nothing
# to propagate, since both sides already agree). `reconcile()` re-reads both
# sides on every call by design (AD-9: "a webhook or schedule tick is only
# ever a wake-up, never a value source"), so `transport.calls` (raw reads+writes)
# necessarily grows every round even in a genuinely no-op round; the
# property being proven is zero new writes, so every assertion below
# snapshots `len(transport.write_calls())`, never raw `len(transport.calls)`.


def test_zero_loop_github_initiated_n_round_trips():
    """GH status differs from its baseline; Jira matches its own baseline.
    Round 1 propagates GH's change to Jira and refreshes both baselines;
    rounds 2-5 must each independently be a true no-op with zero new
    writes."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # matches current -- jira unchanged
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "push_to_jira"
    assert _jira_status(transport) == "In Progress"
    writes_after_first = len(transport.write_calls())

    for round_number in range(2, 6):  # rounds 2-5
        result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
        assert result.ok is True, f"round {round_number}"
        assert result.details["decision"] == "no_op", f"round {round_number}"
        assert len(transport.write_calls()) == writes_after_first, f"round {round_number}"


def test_zero_loop_jira_initiated_n_round_trips():
    """Same shape as the GitHub-initiated round trip, mirrored: Jira status
    differs from its baseline, GH matches its own baseline. Round 1
    propagates Jira's change to GitHub and refreshes both baselines; rounds
    2-5 must each independently be a true no-op with zero new writes."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',  # matches current -- gh unchanged
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
    )

    first = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "push_to_github"
    assert transport.github_fields["gh_status"] == "In Progress"
    writes_after_first = len(transport.write_calls())

    for round_number in range(2, 6):  # rounds 2-5
        result = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)
        assert result.ok is True, f"round {round_number}"
        assert result.details["decision"] == "no_op", f"round {round_number}"
        assert len(transport.write_calls()) == writes_after_first, f"round {round_number}"


def test_zero_loop_convergent_same_value_n_round_trips():
    """Both sides differ from their own baseline but already agree with each
    other. Round 1 makes zero API writes to either tracked field (already
    converged) but still refreshes both stale baselines; rounds 2-5 must
    each independently be a true no-op with zero new writes."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "Blocked",
            "gh_baseline": '{"status": "In Progress"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "Blocked"},  # already matches gh's value
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
        jira_transitions=[],
    )

    first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "no_op"
    assert _status_push_calls(transport) == []  # zero writes to either tracked field
    assert len(_baseline_write_calls(transport)) == 2  # both stale baselines still refreshed
    writes_after_first = len(transport.write_calls())

    for round_number in range(2, 6):  # rounds 2-5
        result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
        assert result.ok is True, f"round {round_number}"
        assert result.details["decision"] == "no_op", f"round {round_number}"
        assert len(transport.write_calls()) == writes_after_first, f"round {round_number}"


def test_zero_loop_survives_a_baseline_refresh_failure():
    """Covers the non-atomic baseline-refresh failure path (`sync.py:869-880`),
    required by the audit's dispatch note (`epics.md:664-665`,
    `implementation-readiness-report-2026-08-10.md:15`). Reuses
    `test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push`'s
    fixture shape -- a status value over Jira's 255-char baseline-field
    ceiling (`_JIRA_BASELINE_FIELD_CEILING`) -- driven through 3
    `reconcile()` ticks against the SAME transport.

    Tick 1 already fails (`ok is False`, "Mode B" in summary): the value
    push (the Jira transition) already succeeded before the baseline
    refresh fired and failed, so there is no successful round 1 to snapshot
    writes after -- snapshot `len(transport.write_calls())` AFTER tick 1
    instead. Ticks 2-3 must each independently assert `ok is False` again
    (the convergence check downgrades the would-be push to `no_op` on these
    ticks, since both sides already hold the pushed value from tick 1, but
    the baseline refresh is retried and fails again for the same reason)
    and `len(transport.write_calls())` unchanged from its value after tick
    1 -- proving this persistent-failure steady state never re-propagates
    the pushed value, even though it never self-heals without
    operator/Mode-B intervention."""
    long_status = "X" * 300  # comfortably over Jira's 255-char ceiling, under GitHub's 1024
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": long_status,
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # unchanged
        },
        jira_transitions=[{"id": "99", "to": {"name": long_status}}],
    )

    first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert first.ok is False
    assert "Mode B" in first.summary
    assert _jira_status(transport) == long_status  # the value push already completed
    writes_after_first = len(transport.write_calls())

    for tick_number in range(2, 4):  # ticks 2-3
        result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
        assert result.ok is False, f"tick {tick_number}"
        assert len(transport.write_calls()) == writes_after_first, f"tick {tick_number}"


# ── Epic 8 Story 8.3: idempotent redelivery, proven byte-identical (CAP-3) ──
#
# CAP-3 claims re-processing the same update twice leaves both systems
# byte-identical to a single delivery (AD-9: "redelivery must be a no-op ...
# out-of-order arrival must not regress state"). 8.2 proved the zero-loop
# property via N round trips through the SAME identifier, checked by write
# COUNT only; this story adds proofs 8.2 never attempted: (1) full end-state
# dict-equality across a duplicate delivery, not merely a write-count check,
# and (2) entry-point symmetry -- a redelivery arriving via the OPPOSITE
# identifier from the one that made the first call is still a true no-op.
# A third test covers AD-9 rule 2 directly (stale-value convergence, distinct
# from entry-point symmetry -- see the re-issued intent contract): a genuine
# intervening state change between two real convergences, followed by a late/
# out-of-order redelivery nominally "about" the now-superseded first value,
# must converge on the CURRENT value, never regress toward the stale one.
# `dry_run` stays False throughout (Boundaries & Constraints); `reconcile()`'s
# internals are never mocked -- observed only through `DutyResult` and the
# transport's own state/call log, matching this file's existing idiom.


def test_idempotent_redelivery_same_identifier_is_byte_identical():
    """CAP-3's literal claim: redelivering the identical GH-initiated change
    via the SAME identifier that made the first call must leave both sides'
    full field state byte-identical -- not just a write-count check -- to
    the state captured immediately after the first delivery."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # matches current -- jira unchanged
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "21", "to": {"name": "To Do"}},
        ],
    )

    first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "push_to_jira"
    github_snapshot = dict(transport.github_fields)
    jira_snapshot = dict(transport.jira_fields)
    writes_after_first = len(transport.write_calls())

    second = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)  # redelivery

    assert second.ok is True
    assert second.details["decision"] == "no_op"
    assert second.details["target_value"] is None
    assert second.details["baseline"] is None
    assert len(transport.write_calls()) == writes_after_first
    assert transport.github_fields == github_snapshot
    assert transport.jira_fields == jira_snapshot


def test_idempotent_redelivery_via_the_opposite_identifier_does_not_regress():
    """Entry-point symmetry (NOT AD-9 rule 2 -- re-issued 2026-08-11): a
    Jira-initiated change propagates to GitHub via `jira_issue_key`, then the
    same already-converged pair is redelivered via `github_item_id`, the
    OPPOSITE identifier from the one that made the first call. Genuinely new
    ground relative to 8.2, whose round trips always reused the same
    identifier across every round -- proves idempotency holds regardless of
    which side's channel redelivers the notification."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',  # matches current -- gh unchanged
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',  # stale -- jira_changed
        },
    )

    first = reconcile(jira_issue_key="PROJ-1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "push_to_github"
    github_snapshot = dict(transport.github_fields)
    jira_snapshot = dict(transport.jira_fields)
    writes_after_first = len(transport.write_calls())

    second = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)  # opposite identifier

    assert second.ok is True
    assert second.details["decision"] == "no_op"
    assert second.details["target_value"] is None
    assert second.details["baseline"] is None
    assert len(transport.write_calls()) == writes_after_first
    assert transport.github_fields == github_snapshot
    assert transport.jira_fields == jira_snapshot


def test_late_delivery_about_a_superseded_value_does_not_regress_state_ad9_rule2():
    """AD-9 rule 2: "a late delivery about a superseded value converges to
    the current one rather than overwriting it." `reconcile()` takes no
    delivered-value parameter -- it always re-reads current state against
    each side's own baseline (AD-5: never a timestamp, never the payload) --
    so a late delivery "about" a superseded value can only be represented by
    a GENUINE INTERVENING STATE CHANGE between two real convergences: GH
    moves once (propagates, baselines refresh to the first new value), then
    GH moves AGAIN to a second value (propagates again, baselines refresh to
    the second), then a redelivery call -- nominally "about" the now-
    superseded first value -- must land on the CURRENT (second) value, never
    regress toward the first."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "In Progress",
            "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
        },
        jira_fields={
            "status": {"name": "To Do"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
        },
        jira_transitions=[
            {"id": "31", "to": {"name": "In Progress"}},
            {"id": "41", "to": {"name": "Blocked"}},
        ],
    )

    # Delivery 1 (in-order): propagates "In Progress"; both baselines
    # refresh to it. This is the value a late, out-of-order notification
    # will (stalely) describe.
    first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert first.ok is True
    assert first.details["decision"] == "push_to_jira"

    # Genuine intervening state change: GH moves AGAIN, to "Blocked" -- a
    # second, later real event the earlier notification knows nothing about.
    transport.github_fields["gh_status"] = "Blocked"
    second = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert second.ok is True
    assert second.details["decision"] == "push_to_jira"
    github_snapshot = dict(transport.github_fields)
    jira_snapshot = dict(transport.jira_fields)
    writes_after_second = len(transport.write_calls())

    # The late/out-of-order delivery: nominally "about" the now-superseded
    # "In Progress" value, but reconcile() never consumes a delivered
    # value -- it must converge on the CURRENT value ("Blocked"), never
    # regress to it.
    late = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert late.ok is True
    assert late.details["decision"] == "no_op"
    assert late.details["target_value"] is None
    assert late.details["baseline"] is None
    assert len(transport.write_calls()) == writes_after_second
    assert transport.github_fields == github_snapshot
    assert transport.jira_fields == jira_snapshot


# ── Epic 8 Story 8.4: trigger=schedule candidate enumeration + batch dispatch ──
#
# `list_linked_github_items`/`reconcile_schedule_batch` are new -- `reconcile()`
# itself is reused verbatim (Boundaries & Constraints), so the bulk of this
# section proves the NEW listing/dispatch machinery, not the reconcile
# decision logic already proven above. `list_linked_github_items` is called
# once per batch, then `reconcile()` is called once per discovered candidate
# -- both against the SAME transport instance -- so, unlike `FakeTransport`
# above (which only ever models ONE linked pair), the fake below must model
# MULTIPLE independent GitHub-item/Jira-issue pairs.


def _issue_key_from_url(url: str) -> str:
    """`.../rest/api/3/issue/<key>[?fields=...]` or
    `.../rest/api/3/issue/<key>/transitions` -- pulls `<key>` back out,
    reversing `sync.py`'s own `quote(issue_key, safe='')` escaping."""
    after = url.split("/issue/", 1)[1]
    after = after.split("?", 1)[0]
    after = after.split("/transitions", 1)[0]
    return unquote(after)


class ScheduleFakeTransport:
    """A dedicated fake for Story 8.4's batch dispatcher -- serves BOTH the
    new bulk-listing query (`_LIST_PROJECT_ITEMS_QUERY`, routed on
    `"projectId"` present / `"itemId"` absent in `variables`, distinct from
    `FakeTransport`'s single-item query/mutation routing above) AND every
    single-pair call `reconcile()` itself makes per dispatched candidate.

    `items`: `{github_item_id: {"fields": {field_id: text, ...}, "updated_at": ...}}`.
    `jira_issues`: `{jira_issue_key: {"fields": {...}, "transitions": [...]}}`
    -- an issue key absent from this mapping answers every GET/transitions
    call for it with HTTP 404, simulating a stale/mismatched link (the I/O
    Matrix's own example of a candidate that fails mid-batch).
    `page_size` is deliberately small by default so a multi-item fixture
    exercises real pagination (Design Notes' pagination-loop shape) without
    a large fixture.
    """

    def __init__(
        self,
        *,
        items: dict[str, dict[str, object]] | None = None,
        jira_issues: dict[str, dict[str, object]] | None = None,
        page_size: int = 2,
    ) -> None:
        self.items: dict[str, dict[str, object]] = {
            item_id: {
                "fields": dict(entry.get("fields") or {}),
                "updated_at": entry.get("updated_at"),
                # Story 8.7: an optional `content` fragment, same shape as
                # `FakeTransport.github_content` -- `None` (the default,
                # every pre-8.7 fixture) reads as "no content".
                "content": entry.get("content"),
            }
            for item_id, entry in (items or {}).items()
        }
        self.jira_issues: dict[str, dict[str, object]] = {
            key: {
                "fields": dict(entry.get("fields") or {}),
                "transitions": list(entry.get("transitions") or []),
            }
            for key, entry in (jira_issues or {}).items()
        }
        self.page_size = page_size
        self.calls: list[dict[str, object]] = []

    def __call__(self, request: urllib.request.Request) -> TransportResponse:
        method = request.get_method()
        url = request.full_url
        body = json.loads(request.data) if request.data else None
        self.calls.append({"method": method, "url": url, "body": body})

        if url == _GITHUB_GRAPHQL_URL:
            return self._github(body)
        if url.startswith("https://api.github.com/repos/"):
            return self._github_rest_assignees(method, url, body)
        return self._jira(method, url, body)

    # -- GitHub GraphQL ------------------------------------------------

    def _github(self, body: dict[str, object]) -> TransportResponse:
        variables = body["variables"]
        if "fieldId" in variables:
            item_id = variables["itemId"]
            self.items.setdefault(item_id, {"fields": {}, "updated_at": None, "content": None})
            self.items[item_id]["fields"][variables["fieldId"]] = variables["value"]["text"]
            payload = {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": item_id}}}}
            return TransportResponse(status=200, body=json.dumps(payload).encode())

        if "itemId" in variables:
            item_id = variables["itemId"]
            entry = self.items.get(item_id, {"fields": {}, "content": None})
            node = self._node(item_id, entry)
            payload = {"data": {"node": node}}
            return TransportResponse(status=200, body=json.dumps(payload).encode())

        # The bulk-listing query: "projectId" present, "itemId" absent.
        return self._list_page(variables.get("after"))

    def _node(self, item_id: str, entry: dict[str, object]) -> dict[str, object]:
        node = {
            "id": item_id,
            "updatedAt": entry.get("updated_at"),
            "fieldValues": {
                "nodes": [{"text": value, "field": {"id": field_id}} for field_id, value in entry["fields"].items()]
            },
        }
        if entry.get("content") is not None:
            node["content"] = entry["content"]
        return node

    # -- GitHub REST v3 (Story 8.7: assignee writes only) -----------------

    def _github_rest_assignees(self, method: str, url: str, body: dict[str, object] | None) -> TransportResponse:
        if method not in ("POST", "DELETE"):
            raise AssertionError(f"ScheduleFakeTransport: unexpected github REST call {method} {url}")
        return TransportResponse(status=200, body=b"{}")

    def _list_page(self, after: str | None) -> TransportResponse:
        ids = list(self.items.keys())
        start = 0 if after is None else ids.index(after) + 1
        page_ids = ids[start : start + self.page_size]
        has_next = (start + self.page_size) < len(ids)
        end_cursor = page_ids[-1] if page_ids else None
        nodes = [self._node(item_id, self.items[item_id]) for item_id in page_ids]
        payload = {
            "data": {
                "node": {
                    "items": {
                        "nodes": nodes,
                        "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
                    }
                }
            }
        }
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    # -- Jira REST v3 ----------------------------------------------------

    def _jira(self, method: str, url: str, body: dict[str, object] | None) -> TransportResponse:
        issue_key = _issue_key_from_url(url)
        issue = self.jira_issues.get(issue_key)
        if issue is None:
            # No such issue -- a stale/mismatched link, the I/O Matrix's own
            # example of a candidate that fails mid-batch.
            return TransportResponse(status=404, body=b'{"errorMessages": ["Issue Does Not Exist"]}')

        if url.endswith("/transitions"):
            if method == "GET":
                payload = {"transitions": issue["transitions"]}
                return TransportResponse(status=200, body=json.dumps(payload).encode())
            transition_id = body["transition"]["id"]
            matched = next(t for t in issue["transitions"] if t["id"] == transition_id)
            issue["fields"]["status"] = {"name": matched["to"]["name"]}
            return TransportResponse(status=204, body=b"")
        if method == "GET":
            payload = {"fields": dict(issue["fields"])}
            return TransportResponse(status=200, body=json.dumps(payload).encode())
        if method == "PUT":
            issue["fields"].update(body["fields"])
            return TransportResponse(status=204, body=b"")
        raise AssertionError(f"ScheduleFakeTransport: unexpected jira call {method} {url}")


_GH_CREDENTIAL = HostScopedCredential(hosts=("api.github.com",))


# ── Row: paginated board (> one page) -- lister follows the cursor to exhaustion ──


def test_list_linked_github_items_follows_pagination_across_multiple_pages():
    transport = ScheduleFakeTransport(
        items={
            f"ITEM_{i}": {"fields": {"gh_link": f"PROJ-{i}", "gh_status": "To Do"}}
            for i in range(1, 6)  # 5 items, page_size=2 below -> forces 3 pages
        },
        page_size=2,
    )

    candidates = list_linked_github_items(config=CONFIG, credential=_GH_CREDENTIAL, transport=transport)

    assert {c["github_item_id"] for c in candidates} == {f"ITEM_{i}" for i in range(1, 6)}
    # every listing call carries "after" in its variables (even when None on
    # the first page) -- distinct from a single-item/mutation call, neither
    # of which ever sets it.
    listing_calls = [c for c in transport.calls if "after" in (c["body"] or {}).get("variables", {})]
    assert len(listing_calls) == 3  # 2 + 2 + 1 items per page


# ── Row: candidacy is gated on nothing -- every enumerated item is a candidate ──


def test_list_linked_github_items_never_filters_on_link_or_baseline():
    """Story 8.5 (CAP-4 "fail loud, fail alone"): candidacy is never gated on
    any field value -- not the link field, not the baseline. Every
    deduplicated node the bulk listing returns becomes a candidate,
    regardless of whether it is linked. AD-10 rule 1 (an absent baseline is
    a first link, not a loop candidate) still holds, but is now just one
    instance of the broader "never gate on field values" rule -- the
    baseline is never even read during enumeration (Boundaries &
    Constraints)."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_link": "PROJ-1"}},  # linked, no baseline -- still a candidate (unchanged)
            "ITEM_2": {"fields": {"gh_status": "To Do"}},  # no link -- NOW also a candidate (changed)
            "ITEM_3": {"fields": {"gh_link": "PROJ-3", "gh_baseline": '{"status": "Blocked"}'}},
        },
        page_size=10,
    )

    candidates = list_linked_github_items(config=CONFIG, credential=_GH_CREDENTIAL, transport=transport)

    assert {c["github_item_id"] for c in candidates} == {"ITEM_1", "ITEM_2", "ITEM_3"}


def test_list_linked_github_items_malformed_response_is_a_named_failure():
    def transport(request: urllib.request.Request) -> TransportResponse:
        return TransportResponse(status=200, body=json.dumps({"data": {"node": None}}).encode())

    with pytest.raises(SyncAPIError, match="malformed response"):
        list_linked_github_items(config=CONFIG, credential=_GH_CREDENTIAL, transport=transport)


# ── Row: batch entirely unlinked items -> ok=False, every entry named "unlinked:" ──


def test_schedule_batch_with_all_unlinked_items_fails_every_entry_by_name():
    """Story 8.5 (CAP-4 "fail loud, fail alone"): an item with no link field
    value is still a candidate and is still dispatched through `reconcile()`
    -- it is `reconcile()`'s own `SyncUnlinkedError` (via `_read_both_sides`)
    that names the failure, not `list_linked_github_items` silently dropping
    it. An all-unlinked-item batch therefore still enumerates every item,
    dispatches every one, and fails every one by name -- never a silent
    "0 candidates" no-op."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_status": "To Do"}},  # no gh_link -> still a candidate, now fails
            "ITEM_2": {"fields": {}},
        },
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is False
    candidates = {c["github_item_id"]: c for c in result.details["candidates"]}
    assert len(candidates) == 2
    assert candidates["ITEM_1"]["ok"] is False
    assert "unlinked: github item ITEM_1 has no linked jira issue" in candidates["ITEM_1"]["summary"]
    assert candidates["ITEM_2"]["ok"] is False
    assert "unlinked: github item ITEM_2 has no linked jira issue" in candidates["ITEM_2"]["summary"]
    assert "2 candidates" in result.summary
    assert "2 failed" in result.summary
    # reconcile() raises SyncUnlinkedError before ever attempting a Jira
    # call -- only the GitHub listing + per-item reads ran.
    assert all(call["url"] == _GITHUB_GRAPHQL_URL for call in transport.calls)


# ── Row: multiple candidates, all converge cleanly -> ok=True, 3 entries ───


def test_schedule_batch_with_multiple_candidates_all_converge_cleanly():
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {
                "fields": {"gh_link": "PROJ-1", "gh_status": "To Do", "gh_baseline": '{"status": "To Do"}'},
                "updated_at": "2026-08-13T00:00:00Z",
            },
            "ITEM_2": {
                "fields": {
                    "gh_link": "PROJ-2",
                    "gh_status": "In Progress",
                    "gh_baseline": '{"status": "In Progress"}',
                }
            },
            "ITEM_3": {"fields": {"gh_link": "PROJ-3", "gh_status": "Blocked", "gh_baseline": '{"status": "Blocked"}'}},
        },
        jira_issues={
            "PROJ-1": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1", "jira_baseline": '{"status": "To Do"}'}
            },
            "PROJ-2": {
                "fields": {
                    "status": {"name": "In Progress"},
                    "jira_link": "ITEM_2",
                    "jira_baseline": '{"status": "In Progress"}',
                }
            },
            "PROJ-3": {
                "fields": {
                    "status": {"name": "Blocked"},
                    "jira_link": "ITEM_3",
                    "jira_baseline": '{"status": "Blocked"}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is True
    candidates = result.details["candidates"]
    assert len(candidates) == 3
    assert all(c["ok"] for c in candidates)
    assert {c["github_item_id"] for c in candidates} == {"ITEM_1", "ITEM_2", "ITEM_3"}
    assert "3 candidates" in result.summary
    assert "3 ok" in result.summary
    assert "0 failed" in result.summary
    # `updated_at` is fetched during enumeration and must be surfaced per
    # candidate for observability (Boundaries & Constraints), never silently
    # dropped between the lister and the aggregate result.
    by_id = {c["github_item_id"]: c for c in candidates}
    assert by_id["ITEM_1"]["updated_at"] == "2026-08-13T00:00:00Z"


def test_schedule_batch_dry_run_threads_through_every_candidate_with_no_writes():
    """The existing `--dry-run` flag applies uniformly to every candidate in
    the batch (Boundaries & Constraints) -- proven here with a real,
    non-empty, multi-candidate board, not just the CLI's zero-candidate
    smoke test."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {
                "fields": {"gh_link": "PROJ-1", "gh_status": "In Progress", "gh_baseline": '{"status": "To Do"}'}
            },
            "ITEM_2": {"fields": {"gh_link": "PROJ-2", "gh_status": "Blocked", "gh_baseline": '{"status": "To Do"}'}},
        },
        jira_issues={
            "PROJ-1": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1", "jira_baseline": '{"status": "To Do"}'}
            },
            "PROJ-2": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_2", "jira_baseline": '{"status": "To Do"}'}
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, dry_run=True, transport=transport)

    assert result.ok is True
    candidates = result.details["candidates"]
    assert len(candidates) == 2
    assert all(c["ok"] for c in candidates)
    # dry_run: both candidates had a real divergence to report, but zero
    # write calls (mutations) reached the transport for either.
    write_calls = [
        call
        for call in transport.calls
        if call["url"] == _GITHUB_GRAPHQL_URL and "fieldId" in (call["body"] or {}).get("variables", {})
    ] + [call for call in transport.calls if call["method"] in ("PUT", "POST") and "/issue/" in call["url"]]
    assert write_calls == []


# ── Row: one candidate fails mid-batch -> others still reconcile, ok=False overall ──


def test_schedule_batch_one_candidate_failing_does_not_abort_the_others():
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_link": "PROJ-1", "gh_status": "To Do", "gh_baseline": '{"status": "To Do"}'}},
            "ITEM_2": {"fields": {"gh_link": "PROJ-2", "gh_status": "In Progress"}},
            "ITEM_3": {"fields": {"gh_link": "PROJ-3", "gh_status": "Blocked", "gh_baseline": '{"status": "Blocked"}'}},
        },
        jira_issues={
            "PROJ-1": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1", "jira_baseline": '{"status": "To Do"}'}
            },
            # PROJ-2 intentionally absent -- a stale/mismatched link (the
            # I/O Matrix's own example), so ITEM_2's reconcile() fails.
            "PROJ-3": {
                "fields": {
                    "status": {"name": "Blocked"},
                    "jira_link": "ITEM_3",
                    "jira_baseline": '{"status": "Blocked"}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is False
    candidates = {c["github_item_id"]: c for c in result.details["candidates"]}
    assert len(candidates) == 3
    assert candidates["ITEM_1"]["ok"] is True
    assert candidates["ITEM_2"]["ok"] is False
    assert candidates["ITEM_3"]["ok"] is True
    assert "1 failed" in result.summary
    assert "3 candidates" in result.summary


# ── Row (Story 8.6): one unmapped status among linked items fails only that entry ──


def test_schedule_batch_with_one_unmapped_status_among_linked_items_fails_only_that_entry():
    """AD-6/CAP-5's batch-composition guarantee: 3 board items, PROJ-2's
    Jira status ("Triage") has no `status_mapping` entry in `CONFIG`.
    ITEM_1/ITEM_3 converge cleanly; ITEM_2's entry is `ok=False` with the
    named, greppable `SyncUnmappedStatusError` summary -- mirrors Story
    8.5's own unlinked-item batch-isolation test for the symmetric failure
    mode (`test_schedule_batch_with_one_unlinked_item_among_linked_items_
    fails_only_that_entry`)."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_link": "PROJ-1", "gh_status": "To Do", "gh_baseline": '{"status": "To Do"}'}},
            "ITEM_2": {
                "fields": {
                    "gh_link": "PROJ-2",
                    "gh_status": "In Progress",
                    "gh_baseline": '{"status": "In Progress"}',  # matches current -- gh unchanged
                }
            },
            "ITEM_3": {"fields": {"gh_link": "PROJ-3", "gh_status": "Blocked", "gh_baseline": '{"status": "Blocked"}'}},
        },
        jira_issues={
            "PROJ-1": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1", "jira_baseline": '{"status": "To Do"}'}
            },
            "PROJ-2": {
                # no jira_baseline -- jira_changed (first sync); gh
                # unchanged above, so this is a clean push_to_github
                # decision, exercising the new unmapped-status path.
                "fields": {"status": {"name": "Triage"}, "jira_link": "ITEM_2"}
            },
            "PROJ-3": {
                "fields": {
                    "status": {"name": "Blocked"},
                    "jira_link": "ITEM_3",
                    "jira_baseline": '{"status": "Blocked"}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is False
    candidates = {c["github_item_id"]: c for c in result.details["candidates"]}
    assert len(candidates) == 3
    assert candidates["ITEM_1"]["ok"] is True
    assert candidates["ITEM_3"]["ok"] is True
    assert candidates["ITEM_2"]["ok"] is False
    assert "unmapped: jira status 'Triage' has no status_mapping entry for github" in candidates["ITEM_2"]["summary"]
    assert "1 failed" in result.summary
    assert "3 candidates" in result.summary


# ── Row: mixed batch -- one unlinked item among otherwise-linked items ─────
# (Story 8.5's own frozen I/O Matrix scenario, CAP-4 "fail loud, fail alone")


def test_schedule_batch_with_one_unlinked_item_among_linked_items_fails_only_that_entry():
    """The frozen AC's literal scenario: 3 board items, ITEM_2 has no link
    field value, ITEM_1/ITEM_3 are linked and converge cleanly. Every linked
    item's own entry is `ok=True`; the unlinked item's entry is `ok=False`
    with the named, greppable `"unlinked: github item <id> has no linked
    jira issue"` summary; the aggregate `DutyResult.ok` is `False`."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_link": "PROJ-1", "gh_status": "To Do", "gh_baseline": '{"status": "To Do"}'}},
            "ITEM_2": {"fields": {"gh_status": "In Progress"}},  # no gh_link -- unlinked
            "ITEM_3": {"fields": {"gh_link": "PROJ-3", "gh_status": "Blocked", "gh_baseline": '{"status": "Blocked"}'}},
        },
        jira_issues={
            "PROJ-1": {
                "fields": {"status": {"name": "To Do"}, "jira_link": "ITEM_1", "jira_baseline": '{"status": "To Do"}'}
            },
            "PROJ-3": {
                "fields": {
                    "status": {"name": "Blocked"},
                    "jira_link": "ITEM_3",
                    "jira_baseline": '{"status": "Blocked"}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is False
    candidates = {c["github_item_id"]: c for c in result.details["candidates"]}
    assert len(candidates) == 3
    assert candidates["ITEM_1"]["ok"] is True
    assert candidates["ITEM_3"]["ok"] is True
    assert candidates["ITEM_2"]["ok"] is False
    assert "unlinked: github item ITEM_2 has no linked jira issue" in candidates["ITEM_2"]["summary"]
    assert "1 failed" in result.summary
    assert "3 candidates" in result.summary


# ── Row: bulk listing itself fails -> ok=False before any candidate dispatched ──


def test_schedule_batch_listing_failure_is_named_and_dispatches_no_candidates():
    def failing_transport(request: urllib.request.Request) -> TransportResponse:
        # malformed: no "items" key under data.node at all
        return TransportResponse(status=200, body=json.dumps({"data": {"node": None}}).encode())

    result = reconcile_schedule_batch(config=CONFIG, transport=failing_transport)

    assert result.ok is False
    assert "enumerating candidates" in result.summary
    assert result.details == {}  # never even entered the per-candidate dispatch loop


# ── Story 8.7: assignee/link-repair composition with --schedule ────────────


def test_schedule_batch_with_one_unmapped_assignee_among_linked_items_fails_only_that_entry():
    """Mirrors `test_schedule_batch_with_one_unmapped_status_among_linked_
    items_fails_only_that_entry`'s batch-isolation shape for the symmetric
    assignee failure mode: 3 board items, ITEM_2's GitHub assignee ('ghost')
    has no `user_mapping` entry in `CONFIG_USER_MAPPING`. ITEM_1/ITEM_3
    converge cleanly; ITEM_2's entry is `ok=False` with the named,
    greppable `SyncUnmappedUserError` summary."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {
                "fields": {
                    "gh_link": "PROJ-1",
                    "gh_status": "To Do",
                    "gh_baseline": '{"status": "To Do", "assignee": null}',
                },
            },
            "ITEM_2": {
                "fields": {
                    "gh_link": "PROJ-2",
                    "gh_status": "To Do",
                    "gh_baseline": '{"status": "To Do", "assignee": null}',
                },
                "content": {
                    "number": 7,
                    "assignees": {"nodes": [{"login": "ghost"}]},
                    "repository": {"owner": {"login": "acme"}, "name": "widgets"},
                },
            },
            "ITEM_3": {
                "fields": {
                    "gh_link": "PROJ-3",
                    "gh_status": "Blocked",
                    "gh_baseline": '{"status": "Blocked", "assignee": null}',
                },
            },
        },
        jira_issues={
            "PROJ-1": {
                "fields": {
                    "status": {"name": "To Do"},
                    "jira_link": "ITEM_1",
                    "jira_baseline": '{"status": "To Do", "assignee": null}',
                }
            },
            "PROJ-2": {
                "fields": {
                    "status": {"name": "To Do"},
                    "jira_link": "ITEM_2",
                    "jira_baseline": '{"status": "To Do", "assignee": null}',
                }
            },
            "PROJ-3": {
                "fields": {
                    "status": {"name": "Blocked"},
                    "jira_link": "ITEM_3",
                    "jira_baseline": '{"status": "Blocked", "assignee": null}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG_USER_MAPPING, transport=transport)

    assert result.ok is False
    candidates = {c["github_item_id"]: c for c in result.details["candidates"]}
    assert len(candidates) == 3
    assert candidates["ITEM_1"]["ok"] is True
    assert candidates["ITEM_3"]["ok"] is True
    assert candidates["ITEM_2"]["ok"] is False
    assert "unmapped: github login 'ghost' has no user_mapping entry for jira" in candidates["ITEM_2"]["summary"]
    assert "1 failed" in result.summary
    assert "3 candidates" in result.summary


def test_schedule_batch_composes_with_identity_link_self_heal():
    """A `--schedule` candidate whose Jira counterpart's own link field was
    never written back is still discovered (candidacy is gated only on
    GitHub's own link field, unchanged -- Boundaries & Constraints) and
    self-healed by the per-candidate `reconcile()` call, exactly like the
    single-pair case."""
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {
                "fields": {
                    "gh_link": "PROJ-1",
                    "gh_status": "To Do",
                    "gh_baseline": '{"status": "To Do", "assignee": null}',
                },
            },
        },
        jira_issues={
            "PROJ-1": {
                "fields": {
                    "status": {"name": "To Do"},
                    # no "jira_link" -- resolved via GH's own link, self-healed
                    "jira_baseline": '{"status": "To Do", "assignee": null}',
                }
            },
        },
        page_size=10,
    )

    result = reconcile_schedule_batch(config=CONFIG, transport=transport)

    assert result.ok is True
    candidates = result.details["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["ok"] is True
    assert transport.jira_issues["PROJ-1"]["fields"]["jira_link"] == "ITEM_1"
