"""Unit tests for ``core.upstream`` (Story 6.8, FR-58, AD-2) -- pure
``parse_register``/``flagged_for_removal``, no I/O."""

from __future__ import annotations

from pyforge.marshal.core.upstream import (
    ALL_UPSTREAM_STATUSES,
    UPSTREAM_STATUS_LANDED,
    UPSTREAM_STATUS_OPEN,
    UpstreamGapEntry,
    flagged_for_removal,
    parse_register,
)

_GOOD_ENTRY = {
    "id": "idle-strand-detection",
    "gap": "no built-in idle detection",
    "workaround": "core/supervise.py's idle ladder",
    "compensating_fr": "FR-12",
    "upstream_status": "open",
}


def test_parse_register_well_formed_list():
    entries, errors = parse_register({"entries": [_GOOD_ENTRY]})
    assert errors == ()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == "idle-strand-detection"
    assert entry.compensating_fr == "FR-12"
    assert entry.upstream_status == UPSTREAM_STATUS_OPEN
    assert entry.note is None


def test_parse_register_bare_list_without_entries_key():
    entries, errors = parse_register([_GOOD_ENTRY])
    assert errors == ()
    assert len(entries) == 1


def test_parse_register_top_level_not_a_list_or_mapping():
    entries, errors = parse_register("not a register")
    assert entries == ()
    assert len(errors) == 1


def test_parse_register_mapping_without_entries_key():
    entries, errors = parse_register({"foo": "bar"})
    assert entries == ()
    assert len(errors) == 1


def test_parse_register_entry_not_an_object():
    entries, errors = parse_register({"entries": ["not an object"]})
    assert entries == ()
    assert len(errors) == 1
    assert "entry[0]" in errors[0]


def test_parse_register_entry_missing_required_field_is_skipped_and_named():
    incomplete = dict(_GOOD_ENTRY)
    del incomplete["compensating_fr"]
    entries, errors = parse_register({"entries": [incomplete, _GOOD_ENTRY]})
    assert len(entries) == 1
    assert entries[0].id == "idle-strand-detection"
    assert len(errors) == 1
    assert "compensating_fr" in errors[0]


def test_parse_register_entry_blank_required_field_is_skipped():
    blank = dict(_GOOD_ENTRY, gap="")
    entries, errors = parse_register({"entries": [blank]})
    assert entries == ()
    assert len(errors) == 1


def test_parse_register_unrecognized_upstream_status_is_skipped_and_named():
    bogus = dict(_GOOD_ENTRY, upstream_status="in-progress")
    entries, errors = parse_register({"entries": [bogus]})
    assert entries == ()
    assert len(errors) == 1
    assert "in-progress" in errors[0]


def test_parse_register_note_field_optional_and_typed():
    with_note = dict(_GOOD_ENTRY, note="landed 2026-08-01")
    entries, errors = parse_register({"entries": [with_note]})
    assert errors == ()
    assert entries[0].note == "landed 2026-08-01"


def test_parse_register_note_field_wrong_type_is_skipped():
    bad_note = dict(_GOOD_ENTRY, note=42)
    entries, errors = parse_register({"entries": [bad_note]})
    assert entries == ()
    assert len(errors) == 1


def test_flagged_for_removal_empty_when_none_landed():
    entries = (UpstreamGapEntry("a", "gap", "wa", "FR-1", UPSTREAM_STATUS_OPEN),)
    assert flagged_for_removal(entries) == ()


def test_flagged_for_removal_returns_exactly_the_landed_subset_order_preserving():
    open_entry = UpstreamGapEntry("a", "gap", "wa", "FR-1", UPSTREAM_STATUS_OPEN)
    landed_entry_1 = UpstreamGapEntry("b", "gap", "wa", "FR-2", UPSTREAM_STATUS_LANDED)
    landed_entry_2 = UpstreamGapEntry("c", "gap", "wa", "FR-3", UPSTREAM_STATUS_LANDED)
    entries = (open_entry, landed_entry_1, landed_entry_2)
    assert flagged_for_removal(entries) == (landed_entry_1, landed_entry_2)


def test_all_upstream_statuses_is_closed_two_member_set():
    assert ALL_UPSTREAM_STATUSES == {UPSTREAM_STATUS_OPEN, UPSTREAM_STATUS_LANDED}
