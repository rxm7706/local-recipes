"""Unit tests for ``pyforge.doctor.sources`` (Story 6.2) -- covers every row
of the spec's I/O & Edge-Case Matrix: ``SourceRegistration`` construction
(well-formed, missing subject, missing owner, invalid scope) and the
registry <-> ``Source`` coherence test, mirroring ``checks/registry.py``'s
own ``test_every_cataloged_category_is_dispatchable_by_gather_one``
tripwire -- a ``Source`` with no registry entry, or a registry entry with no
matching ``Source``, must fail loudly rather than pass silently.
"""

from __future__ import annotations

import pytest

from pyforge.doctor.models import Source
from pyforge.doctor.sources import REGISTRY, SourceRegistration, list_sources

# --- SourceRegistration construction ------------------------------------------


def test_well_formed_registration_constructs():
    registration = SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    )
    assert registration.source is Source.MARSHAL_DURABILITY
    assert registration.scope == "repo"
    assert registration.subject_station == "marshal"
    assert registration.owning_station == "doctor"


def test_non_source_value_raises_value_error():
    with pytest.raises(ValueError, match="source"):
        SourceRegistration(
            source="marshal-durability",  # a plain str, not a Source member
            scope="repo",
            subject_station="marshal",
            owning_station="doctor",
        )


def test_empty_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="",
            owning_station="doctor",
        )


def test_whitespace_only_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="   ",
            owning_station="doctor",
        )


def test_whitespace_only_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station="\t",
        )


def test_none_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station=None,
            owning_station="doctor",
        )


def test_empty_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station="",
        )


def test_none_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station=None,
        )


def test_invalid_scope_raises_value_error():
    with pytest.raises(ValueError, match="scope"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="hostile",
            subject_station="marshal",
            owning_station="doctor",
        )


# --- REGISTRY <-> Source coherence --------------------------------------------


def test_every_source_member_has_exactly_one_registry_entry():
    # Two-directional set-equality: a Source with no REGISTRY entry, or a
    # REGISTRY entry with no matching Source, fails this test -- never a
    # silent one-directional subset pass (Epic 6's own stated discipline).
    source_values = {member.value for member in Source}
    registry_values = [registration.source.value for registration in REGISTRY]

    assert set(registry_values) == source_values
    assert len(registry_values) == len(set(registry_values)), (
        "REGISTRY must carry exactly one entry per Source member, no duplicates"
    )


def test_every_registry_entry_has_valid_subject_owner_and_scope():
    for registration in REGISTRY:
        assert registration.subject_station
        assert registration.owning_station
        assert registration.scope in {"repo", "runtime"}


def test_list_sources_returns_the_registry():
    assert list_sources() == REGISTRY


# --- to_json_dict --------------------------------------------------------------


def test_to_json_dict_matches_the_four_declared_fields():
    registration = SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    )
    assert registration.to_json_dict() == {
        "source": "marshal-durability",
        "scope": "repo",
        "subject_station": "marshal",
        "owning_station": "doctor",
    }
