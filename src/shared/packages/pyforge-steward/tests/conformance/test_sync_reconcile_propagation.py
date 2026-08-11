"""`reconcile` — Epic 8, Story 8.1. One test per I/O & Edge-Case Matrix row,
against the AD-5(amended)/AD-10 per-field baseline-value mechanism (never a
timestamp — see `sync.py`'s own module docstring and this story's Design
Notes). Every test drives `reconcile` through a fake `transport` returning
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
    _parse_baseline,
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
    github_baseline_field_id="gh_baseline",
    jira_base_url="https://example.atlassian.net",
    jira_project_key="PROJ",
    jira_link_field_id="jira_link",
    jira_baseline_field_id="jira_baseline",
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
        jira_issue_key: str = "PROJ-1",
        jira_fields: dict[str, object] | None = None,
        jira_transitions: list[dict[str, object]] | None = None,
    ) -> None:
        self.github_item_id = github_item_id
        self.github_fields: dict[str, str] = dict(github_fields or {})
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
            payload = {"fields": dict(self.jira_fields)}
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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress"}


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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress"}


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
            "gh_baseline": '{"status": "In Progress"}',  # matches current -- unchanged
        },
        jira_fields={
            "status": {"name": "In Progress"},
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "In Progress"}',  # matches current -- unchanged
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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress"}


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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "In Progress"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "In Progress"}


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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": None}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": None}


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
    assert json.loads(transport.github_fields["gh_baseline"]) == {"status": "Blocked"}
    assert json.loads(transport.jira_fields["jira_baseline"]) == {"status": "Blocked"}


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
    transition_index = next(
        i for i, c in enumerate(writes) if c["url"].endswith("/transitions")
    )
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

    result = reconcile(
        github_item_id="ITEM_1", jira_issue_key="PROJ-1", config=CONFIG, transport=transport
    )

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
        transition_jira_issue(
            "PROJ-1", "In Progress", config=CONFIG, credential=credential, transport=transport
        )


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
    `implementation-readiness-report-20260810.md:15`). Reuses
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
