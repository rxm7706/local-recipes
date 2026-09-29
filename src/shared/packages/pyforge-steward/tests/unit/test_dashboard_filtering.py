"""Story 9.2 — `RoleFilteredRows`, `filter_by_role` (CAP-2), `search` (AD-6)."""

from __future__ import annotations

import pytest

from pyforge.steward.dashboard.declarations import AccessDeclaration
from pyforge.steward.dashboard.filtering import RoleFilteredRows, filter_by_role, search


def test_role_filtered_rows_accepts_a_tuple_of_mappings():
    frame = RoleFilteredRows(rows=({"region": "east"}, {"region": "west"}))
    assert frame.rows == ({"region": "east"}, {"region": "west"})


def test_role_filtered_rows_accepts_an_empty_tuple():
    assert RoleFilteredRows(rows=()).rows == ()


def test_role_filtered_rows_rejects_a_list():
    """A bare list can keep changing out from under a caller holding this
    value -- the immutability a frozen dataclass otherwise promises.
    """
    with pytest.raises(TypeError, match="rows"):
        RoleFilteredRows(rows=[{"region": "east"}])


def test_role_filtered_rows_rejects_a_non_mapping_row():
    with pytest.raises(TypeError, match=r"rows\[1\]"):
        RoleFilteredRows(rows=({"region": "east"}, "not-a-mapping"))


def test_filter_by_role_returns_only_rows_matching_the_role():
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [
        {"region": "east", "value": 1},
        {"region": "west", "value": 2},
        {"region": "east", "value": 3},
    ]

    result = filter_by_role(master, declaration, "east")

    assert isinstance(result, RoleFilteredRows)
    assert result.rows == ({"region": "east", "value": 1}, {"region": "east", "value": 3})


def test_filter_by_role_with_no_identity_fails_closed_to_zero_rows():
    """CAP-1's degrade: `role=None` never raises, and never returns every
    row -- only an empty `RoleFilteredRows`.
    """
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": "east"}, {"region": "west"}]

    result = filter_by_role(master, declaration, None)

    assert result == RoleFilteredRows(rows=())


def test_filter_by_role_rejects_an_undeclared_role():
    """Unlike `role=None`, a role that is PRESENT but outside the declared
    vocabulary is a configuration defect and must raise loudly, never
    silently degrade like the no-identity case.
    """
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": "east"}]

    with pytest.raises(ValueError, match="superadmin"):
        filter_by_role(master, declaration, "superadmin")


def test_filter_by_role_raises_for_a_row_missing_the_access_column():
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": "east"}, {"other_column": "west"}]

    with pytest.raises(KeyError) as excinfo:
        filter_by_role(master, declaration, "east")

    message = str(excinfo.value)
    assert "region" in message
    assert "1" in message, "the offending row's index must be named"


def test_filter_by_role_never_mutates_the_master_dataset():
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": "east"}, {"region": "west"}]
    snapshot = [dict(row) for row in master]

    filter_by_role(master, declaration, "east")

    assert master == snapshot, "filter_by_role must never mutate the master dataset it was given"


def test_filter_by_role_deep_copies_rows_so_a_nested_value_is_not_shared():
    """A shallow `dict(row)` copy would still share a nested mutable value
    (e.g. a list or dict field) with `master` -- mutating it through the
    returned frame must not reach back into the master dataset.
    """
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": "east", "tags": ["a", "b"]}]

    result = filter_by_role(master, declaration, "east")
    result.rows[0]["tags"].append("mutated")

    assert master[0]["tags"] == ["a", "b"], "a nested value must not be shared with master"


def test_filter_by_role_rejects_a_non_sequence_master():
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))

    with pytest.raises(TypeError, match="master"):
        filter_by_role(None, declaration, "east")


def test_filter_by_role_uses_exact_equality_with_no_normalization():
    """Inherited Story 9.1 deferral to Story 9.3: no `.strip()` or
    case-folding is applied to the role comparison -- a padded or
    differently-cased value in the master data simply does not match.
    """
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [{"region": " east"}, {"region": "East"}, {"region": "east"}]

    result = filter_by_role(master, declaration, "east")

    assert result.rows == ({"region": "east"},)


def test_search_returns_only_rows_matching_the_predicate():
    frame = RoleFilteredRows(rows=({"region": "east", "value": 1}, {"region": "east", "value": 2}))

    result = search(frame, lambda row: row["value"] > 1)

    assert result == ({"region": "east", "value": 2},)


def test_search_rejects_the_raw_master_object_by_type():
    """AD-6's "enforced by signature," proven by execution: the exact shape
    `get_master_dataset()` would hand back -- a plain list of row mappings,
    never filtered by role -- must be refused by `search()` itself, not by
    caller discipline.
    """
    unfiltered_master = [{"region": "east"}, {"region": "west"}]

    calls: list[object] = []
    with pytest.raises(TypeError, match="RoleFilteredRows"):
        search(unfiltered_master, lambda row: calls.append(row) or True)

    assert calls == [], "no row may be inspected before the type check runs"


def test_search_rejects_a_dict_and_a_none():
    calls: list[object] = []

    for not_a_frame in ({"region": "east"}, None, "east", ()):
        with pytest.raises(TypeError, match="RoleFilteredRows"):
            search(not_a_frame, lambda row: calls.append(row) or True)

    assert calls == []


def test_search_on_an_empty_frame_returns_an_empty_tuple():
    assert search(RoleFilteredRows(rows=()), lambda row: True) == ()


def test_search_rejects_a_non_callable_predicate():
    frame = RoleFilteredRows(rows=({"region": "east"},))

    with pytest.raises(TypeError, match="predicate"):
        search(frame, "not-callable")
