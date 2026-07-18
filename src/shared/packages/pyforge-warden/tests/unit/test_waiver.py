"""Unit tests -- the waiver suppression engine (Story 3.2): schema
validation, exact finding-id matching + expiry-awareness, and the
``--bypass`` stanza shape.

Every ``load_waivers`` test writes a real file to ``tmp_path`` and reads it
back through the real ``yaml.safe_load`` path -- no mocking of the YAML
layer (mirrors ``test_config.py``'s own convention).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import yaml

from pyforge.warden.models import AXIS_HYGIENE, AXIS_INGESTION, AXIS_VULNERABILITY, Status, StatusDriver
from pyforge.warden.waiver import (
    WaiverEntry,
    WaiverParseError,
    WaiverValidationError,
    apply_waivers,
    bypass_blocking,
    emit_bypass_stanza,
    load_waivers,
    warn_blocking,
)

_ACCEPTED = "2026-01-01T00:00:00+00:00"
_EXPIRES = "2026-12-31T00:00:00+00:00"


def _write(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _valid_entry_text(
    entry_id: str = "hygiene:DEP002:requests",
    reason: str = "tracked in JIRA-1",
    authorized_by: str = "alice",
    accepted_at: str = _ACCEPTED,
    expires_at: str = _EXPIRES,
) -> str:
    return (
        "version: 1\n"
        "waivers:\n"
        f"  - id: {entry_id!r}\n"
        f"    reason: {reason!r}\n"
        f"    authorized_by: {authorized_by!r}\n"
        f"    accepted_at: {accepted_at!r}\n"
        f"    expires_at: {expires_at!r}\n"
    )


# --- load_waivers: missing file -----------------------------------------


def test_missing_file_returns_empty_tuple(tmp_path):
    assert load_waivers(tmp_path / ".warden-waivers.yaml") == ()


# --- load_waivers: malformed YAML (WaiverParseError) --------------------


def test_malformed_yaml_raises_waiver_parse_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 1\nwaivers:\n  - id: [unterminated\n")
    with pytest.raises(WaiverParseError):
        load_waivers(path)


# --- load_waivers: version validation -----------------------------------


def test_missing_version_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "waivers: []\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_unknown_version_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 2\nwaivers: []\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_wrong_typed_version_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: '1'\nwaivers: []\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_boolean_version_is_never_coerced_to_int_one(tmp_path):
    """True == 1 in Python -- the literal-int-1 check must reject a bool."""
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: true\nwaivers: []\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_float_version_is_never_coerced_to_int_one(tmp_path):
    """1.0 != 1 is False in Python -- an isinstance/!=-only check would
    silently accept a YAML float here; only `type(version) is not int`
    rejects it."""
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 1.0\nwaivers: []\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_empty_file_is_treated_as_missing_version(tmp_path):
    """An empty (or comment-only) file parses to None via yaml.safe_load --
    handled the same as a missing 'version' key, never guessed."""
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "# just a comment\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_non_mapping_document_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "- not\n- a\n- mapping\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_waivers_key_absent_is_an_empty_stub_file(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 1\n")
    assert load_waivers(path) == ()


def test_waivers_key_not_a_list_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 1\nwaivers: 'not-a-list'\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


# --- load_waivers: per-entry shape/id/reason/timestamp validation -------


def test_non_mapping_entry_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, "version: 1\nwaivers:\n  - just a string\n")
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_missing_required_field_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(
        path,
        "version: 1\nwaivers:\n  - id: 'hygiene:DEP002:requests'\n"
        "    reason: 'x'\n",
    )
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


@pytest.mark.parametrize(
    "entry_id",
    [
        "vuln:*:*",
        "not-a-family-id",
        "hygiene",
        "vuln:GHSA-xxxx:requests",  # missing @<version>
    ],
)
def test_wildcard_or_non_family_id_rejects_the_whole_file(tmp_path, entry_id):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(entry_id=entry_id))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_empty_string_id_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(entry_id=""))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_duplicate_id_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(
        path,
        "version: 1\n"
        "waivers:\n"
        "  - id: 'hygiene:DEP002:requests'\n"
        "    reason: 'a'\n"
        "    authorized_by: 'alice'\n"
        f"    accepted_at: {_ACCEPTED!r}\n"
        f"    expires_at: {_EXPIRES!r}\n"
        "  - id: 'hygiene:DEP002:requests'\n"
        "    reason: 'b'\n"
        "    authorized_by: 'bob'\n"
        f"    accepted_at: {_ACCEPTED!r}\n"
        f"    expires_at: {_EXPIRES!r}\n",
    )
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_empty_reason_is_accepted(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(reason=""))
    (entry,) = load_waivers(path)
    assert entry.reason == ""


def test_reason_at_exactly_1000_chars_is_accepted(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(reason="x" * 1000))
    (entry,) = load_waivers(path)
    assert len(entry.reason) == 1000


def test_reason_over_1000_chars_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(reason="x" * 1001))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_non_string_reason_raises_validation_error(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(
        path,
        "version: 1\n"
        "waivers:\n"
        "  - id: 'hygiene:DEP002:requests'\n"
        "    reason: 5\n"
        "    authorized_by: 'alice'\n"
        f"    accepted_at: {_ACCEPTED!r}\n"
        f"    expires_at: {_EXPIRES!r}\n",
    )
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_empty_authorized_by_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(authorized_by=""))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_authorized_by_at_exactly_200_chars_is_accepted(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(authorized_by="a" * 200))
    (entry,) = load_waivers(path)
    assert len(entry.authorized_by) == 200


def test_authorized_by_over_200_chars_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(authorized_by="a" * 201))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_expires_at_equal_to_accepted_at_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(accepted_at=_ACCEPTED, expires_at=_ACCEPTED))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_expires_at_before_accepted_at_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(accepted_at=_EXPIRES, expires_at=_ACCEPTED))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_naive_timestamp_is_rejected(tmp_path):
    """A timestamp with no UTC offset is unsafe to compare -- fail-closed,
    never guessed (mirrors vuln.is_db_stale's own naive-timestamp rule)."""
    path = tmp_path / ".warden-waivers.yaml"
    _write(
        path,
        _valid_entry_text(accepted_at="2026-01-01T00:00:00", expires_at=_EXPIRES),
    )
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_unparsable_timestamp_is_rejected(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text(accepted_at="not-a-timestamp"))
    with pytest.raises(WaiverValidationError):
        load_waivers(path)


def test_unquoted_timestamp_parsed_as_native_datetime_is_accepted(tmp_path):
    """Review finding: PyYAML's own implicit timestamp resolver turns an
    UNQUOTED ISO-8601-looking scalar (the obvious way to hand-author one)
    into a native ``datetime.datetime``, not a ``str`` -- this must be
    accepted, not rejected with a confusing "got datetime.datetime(...)"
    message, and the resulting ``WaiverEntry`` field must still be a
    ``str`` (re-rendered via ``.isoformat()``)."""
    path = tmp_path / ".warden-waivers.yaml"
    _write(
        path,
        "version: 1\n"
        "waivers:\n"
        "  - id: 'hygiene:DEP002:requests'\n"
        "    reason: 'x'\n"
        "    authorized_by: 'alice'\n"
        "    accepted_at: 2026-01-01T00:00:00+00:00\n"  # unquoted
        "    expires_at: 2026-12-31T00:00:00+00:00\n",  # unquoted
    )
    (entry,) = load_waivers(path)
    assert isinstance(entry.accepted_at, str)
    assert isinstance(entry.expires_at, str)
    assert datetime.fromisoformat(entry.accepted_at) == datetime(
        2026, 1, 1, tzinfo=UTC
    )
    assert datetime.fromisoformat(entry.expires_at) == datetime(
        2026, 12, 31, tzinfo=UTC
    )


# --- load_waivers: the valid round trip ---------------------------------


def test_valid_file_round_trips_into_a_waiver_entry(tmp_path):
    path = tmp_path / ".warden-waivers.yaml"
    _write(path, _valid_entry_text())
    (entry,) = load_waivers(path)
    assert entry == WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="tracked in JIRA-1",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )


# --- apply_waivers: matching + expiry -----------------------------------

_NOW = datetime(2026, 6, 1, tzinfo=UTC)


def _rung(status: Status, finding_id: str | None, axis: str = AXIS_HYGIENE):
    driver = StatusDriver(axis=axis, finding_id=finding_id) if finding_id else None
    return (status, driver)


def test_exact_match_non_expired_bypasses_and_notices():
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="tracked",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    rungs = [_rung(Status.WARN, "hygiene:DEP002:requests")]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == [(Status.BYPASSED, rungs[0][1])]
    assert len(notices) == 1
    assert notices[0].id == "hygiene:DEP002:requests"
    assert notices[0].reason == "tracked"
    assert notices[0].authorized_by == "alice"
    assert notices[0].expires_at == _EXPIRES
    assert expired == []


def test_no_match_leaves_the_rung_untouched():
    waiver = WaiverEntry(
        id="hygiene:DEP002:other",
        reason="x",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    rungs = [_rung(Status.WARN, "hygiene:DEP002:requests")]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == rungs
    assert notices == []
    assert expired == []


def test_expired_match_leaves_the_rung_untouched():
    """Story 3.3: an expired exact-id match still leaves the rung's own
    Status untouched (the already-correct re-block fall-through, unchanged
    from pre-3.3) -- but now ALSO produces a populated expired_notices
    entry, making that fall-through visible for review."""
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at="2020-01-01T00:00:00+00:00",
        expires_at="2020-02-01T00:00:00+00:00",
    )
    rungs = [_rung(Status.WARN, "hygiene:DEP002:requests")]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == rungs
    assert notices == []
    assert len(expired) == 1
    assert expired[0].id == "hygiene:DEP002:requests"
    assert expired[0].reason == "x"
    assert expired[0].authorized_by == "alice"
    assert expired[0].expires_at == "2020-02-01T00:00:00+00:00"


@pytest.mark.parametrize("status", [Status.CLEAN, Status.NOT_APPLICABLE, Status.BYPASSED])
def test_non_blocking_status_is_never_rewritten_even_on_an_id_match(status):
    """Review finding: apply_waivers must actually enforce
    _NON_BLOCKING_STATUSES (not merely by the convention that CLEAN/
    NOT_APPLICABLE/BYPASSED never carry a matching driver in practice) --
    a defense-in-depth guard, mirroring bypass_blocking's own."""
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    rungs = [_rung(status, "hygiene:DEP002:requests")]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == rungs
    assert notices == []
    assert expired == []


def test_expiry_boundary_exactly_now_is_not_expired():
    """Strict-inequality boundary (mirrors vuln.is_db_stale): exactly at
    expires_at is NOT expired."""
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at="2020-01-01T00:00:00+00:00",
        expires_at=_NOW.isoformat(),
    )
    rungs = [_rung(Status.WARN, "hygiene:DEP002:requests")]
    updated, _, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated[0][0] is Status.BYPASSED
    assert expired == []


def test_driverless_rung_is_never_matched():
    rungs = [(Status.CLEAN, None)]
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == rungs
    assert notices == []
    assert expired == []


def test_residual_unwaived_finding_alongside_a_waived_one():
    """Matrix row: two findings, one matched, one not -- only the matched
    rung becomes bypassed; the other's own status stands."""
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.POLICY_VIOLATION, "vuln:GHSA-xxxx:other@1.0.0", axis=AXIS_VULNERABILITY),
    ]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated[0][0] is Status.BYPASSED
    assert updated[1] == rungs[1]
    assert len(notices) == 1
    assert expired == []


def test_two_rungs_sharing_one_waiver_id_produce_one_notice():
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at=_ACCEPTED,
        expires_at=_EXPIRES,
    )
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.WARN, "hygiene:DEP002:requests"),
    ]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert all(status is Status.BYPASSED for status, _ in updated)
    assert len(notices) == 1
    assert expired == []


def test_two_rungs_sharing_one_expired_waiver_id_produce_one_expired_notice():
    waiver = WaiverEntry(
        id="hygiene:DEP002:requests",
        reason="x",
        authorized_by="alice",
        accepted_at="2020-01-01T00:00:00+00:00",
        expires_at="2020-02-01T00:00:00+00:00",
    )
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.WARN, "hygiene:DEP002:requests"),
    ]
    updated, notices, expired = apply_waivers(rungs, (waiver,), now=_NOW)
    assert updated == rungs
    assert notices == []
    assert len(expired) == 1


# --- bypass_blocking -----------------------------------------------------


def test_bypass_blocking_converts_warn_indeterminate_and_policy_violation():
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.INDETERMINATE, "indeterminate:no-version:foo"),
        _rung(Status.POLICY_VIOLATION, "vuln:GHSA-xxxx:pkg@1.0.0", axis=AXIS_VULNERABILITY),
    ]
    updated = bypass_blocking(rungs)
    assert all(status is Status.BYPASSED for status, _ in updated)


@pytest.mark.parametrize("status", [Status.CLEAN, Status.NOT_APPLICABLE, Status.BYPASSED])
def test_bypass_blocking_leaves_non_blocking_statuses_untouched(status):
    rungs = [_rung(status, "hygiene:DEP002:requests")]
    updated = bypass_blocking(rungs)
    assert updated == rungs


def test_bypass_blocking_leaves_error_rungs_untouched():
    """An error:... driver matches none of the three finding-id families --
    --bypass must never silently suppress an operational error."""
    rungs = [_rung(Status.ERROR, "error:config-parse:some-subject", axis=AXIS_INGESTION)]
    updated = bypass_blocking(rungs)
    assert updated == rungs


def test_bypass_blocking_leaves_driverless_rungs_untouched():
    rungs = [(Status.CLEAN, None)]
    assert bypass_blocking(rungs) == rungs


# --- warn_blocking (Story 3.3, --warn-only) ------------------------------


@pytest.mark.parametrize("status", [Status.POLICY_VIOLATION, Status.INDETERMINATE])
def test_warn_blocking_downgrades_policy_violation_and_indeterminate(status):
    driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-xxxx:pkg@1.0.0"
    )
    rungs = [(status, driver)]
    updated, downgraded = warn_blocking(rungs)
    assert updated == [(Status.WARN, driver)]
    assert downgraded == 1


def test_warn_blocking_leaves_error_rungs_untouched():
    """Status.ERROR is NEVER downgraded by --warn-only -- a tool
    malfunction must always surface honestly regardless of adoption mode."""
    rungs = [_rung(Status.ERROR, "error:config-parse:some-subject", axis=AXIS_INGESTION)]
    updated, downgraded = warn_blocking(rungs)
    assert updated == rungs
    assert downgraded == 0


@pytest.mark.parametrize(
    "status", [Status.WARN, Status.BYPASSED, Status.CLEAN, Status.NOT_APPLICABLE]
)
def test_warn_blocking_leaves_already_non_blocking_or_warn_statuses_untouched(status):
    rungs = [_rung(status, "hygiene:DEP002:requests")]
    updated, downgraded = warn_blocking(rungs)
    assert updated == rungs
    assert downgraded == 0


@pytest.mark.parametrize("status", [Status.POLICY_VIOLATION, Status.INDETERMINATE])
def test_warn_blocking_leaves_driverless_rungs_untouched(status):
    """Test-quality note (review-pass-2 finding): this MUST use a status
    that _WARN_ONLY_DOWNGRADE_STATUSES membership alone would otherwise
    downgrade (POLICY_VIOLATION/INDETERMINATE) -- a CLEAN/NOT_APPLICABLE
    driverless rung is already excluded by the status-membership check
    alone and never actually exercises the `driver is not None` guard."""
    rungs = [(status, None)]
    updated, downgraded = warn_blocking(rungs)
    assert updated == rungs
    assert downgraded == 0


def test_warn_blocking_counts_only_the_rungs_it_actually_rewrites():
    """The nudge's exact count depends on this -- a mixed set of rungs
    where only some are downgradable must report only those."""
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.POLICY_VIOLATION, "vuln:GHSA-xxxx:pkg@1.0.0", axis=AXIS_VULNERABILITY),
        _rung(Status.INDETERMINATE, "indeterminate:no-version:foo"),
        _rung(Status.ERROR, "error:config-parse:x", axis=AXIS_INGESTION),
    ]
    updated, downgraded = warn_blocking(rungs)
    assert downgraded == 2
    assert updated[0] == rungs[0]
    assert updated[1][0] is Status.WARN
    assert updated[2][0] is Status.WARN
    assert updated[3] == rungs[3]


def test_warn_blocking_counts_distinct_findings_not_raw_rungs():
    """Edge-case-hunter finding (review pass 3): interfaces.py's
    indeterminate finding-id carries no version segment, so two components
    sharing a name at different versions (inventory.py's documented
    "distinct versions stay distinct" merge policy) landing on the same
    indeterminate reason produce two rungs referencing the SAME one
    Finding (already deduped by id upstream). The downgraded count must
    dedupe by finding_id too, or it overcounts relative to
    report.findings."""
    rungs = [
        _rung(Status.INDETERMINATE, "indeterminate:unmatchable:foo"),
        _rung(Status.INDETERMINATE, "indeterminate:unmatchable:foo"),
    ]
    updated, downgraded = warn_blocking(rungs)
    assert downgraded == 1
    assert all(status is Status.WARN for status, _ in updated)


def test_warn_blocking_preserves_driver_identity_on_a_downgraded_rung():
    driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-xxxx:pkg@1.0.0"
    )
    updated, _ = warn_blocking([(Status.POLICY_VIOLATION, driver)])
    assert updated[0][1] is driver


# --- emit_bypass_stanza --------------------------------------------------


def test_emit_bypass_stanza_shape_and_expiry():
    rungs = [
        _rung(Status.WARN, "hygiene:DEP002:requests"),
        _rung(Status.POLICY_VIOLATION, "vuln:GHSA-xxxx:pkg@1.0.0", axis=AXIS_VULNERABILITY),
        _rung(Status.CLEAN, None),
        _rung(Status.ERROR, "error:config-parse:x", axis=AXIS_INGESTION),
    ]
    accepted_at = datetime(2026, 1, 1, tzinfo=UTC)
    stanza = emit_bypass_stanza(
        rungs,
        reason="ci override",
        authorized_by="alice",
        accepted_at=accepted_at,
        expiry_days=14,
    )
    document = yaml.safe_load(stanza)
    assert document["version"] == 1
    ids = sorted(entry["id"] for entry in document["waivers"])
    assert ids == ["hygiene:DEP002:requests", "vuln:GHSA-xxxx:pkg@1.0.0"]
    for entry in document["waivers"]:
        assert entry["reason"] == "ci override"
        assert entry["authorized_by"] == "alice"
        assert entry["accepted_at"] == accepted_at.isoformat()
        assert entry["expires_at"] == (accepted_at + timedelta(days=14)).isoformat()


def test_emit_bypass_stanza_omits_clean_and_error_and_already_bypassed_rungs():
    rungs = [
        _rung(Status.CLEAN, None),
        _rung(Status.ERROR, "error:config-parse:x", axis=AXIS_INGESTION),
        _rung(Status.BYPASSED, "hygiene:DEP002:already-waived"),
    ]
    stanza = emit_bypass_stanza(
        rungs,
        reason="x",
        authorized_by="alice",
        accepted_at=datetime(2026, 1, 1, tzinfo=UTC),
        expiry_days=14,
    )
    document = yaml.safe_load(stanza)
    assert document["waivers"] == []


def test_emit_bypass_stanza_never_uses_unsafe_yaml_dump(monkeypatch):
    """NFR-S4/D1: this function must call yaml.safe_dump, never yaml.dump."""
    import pyforge.warden.waiver as waiver_module

    def _forbidden(*args, **kwargs):
        raise AssertionError("yaml.dump must never be called (NFR-S4/D1)")

    monkeypatch.setattr(waiver_module.yaml, "dump", _forbidden)
    stanza = emit_bypass_stanza(
        [_rung(Status.WARN, "hygiene:DEP002:requests")],
        reason="x",
        authorized_by="alice",
        accepted_at=datetime(2026, 1, 1, tzinfo=UTC),
        expiry_days=14,
    )
    assert "hygiene:DEP002:requests" in stanza


@pytest.mark.parametrize(
    "reason",
    [
        'reason with "quotes"',
        "key: value-looking colon",
        "-leading dash",
        "?leading question mark",
        "&leading ampersand",
        "line one\nline two",
        "unicode éè中文",
        "",
    ],
)
def test_reason_round_trips_byte_for_byte_through_the_stanza(reason):
    """D1: safe_load(safe_dump(...))["waivers"][i]["reason"] == original,
    exactly, across YAML-hostile content."""
    stanza = emit_bypass_stanza(
        [_rung(Status.WARN, "hygiene:DEP002:requests")],
        reason=reason,
        authorized_by="alice",
        accepted_at=datetime(2026, 1, 1, tzinfo=UTC),
        expiry_days=14,
    )
    document = yaml.safe_load(stanza)
    assert document["waivers"][0]["reason"] == reason
