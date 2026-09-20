"""Unit tests for ``pyforge.marshal.seed.errors`` (Story 7.2) -- covers the
spec's I/O & Edge-Case Matrix: valid construction, blank ``message``/
``remedy`` validation, the closed-hierarchy enumeration (exactly six
leaves, exit-code set exactly ``{1, 2, 3, 4, 5, 10}``, no duplicates), and
pickle/``copy.deepcopy`` round-tripping (review finding: ``remedy``'s
keyword-only constructor breaks ``Exception.__reduce__``'s default
``cls(*self.args)`` reconstruction without ``SeedError.__reduce__``)."""

from __future__ import annotations

import copy
import pickle

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.marshal.seed.errors import (
    ConformanceFailure,
    InternalError,
    NeverWriteViolation,
    PreconditionFailure,
    SeedError,
    StateInvalid,
    UsageError,
)

_ALL_LEAVES = (
    ConformanceFailure,
    UsageError,
    PreconditionFailure,
    NeverWriteViolation,
    StateInvalid,
    InternalError,
)


def _taxonomy_leaves() -> list[type[SeedError]]:
    """``SeedError.__subclasses__()`` filtered to this module's own
    classes. Review finding: ``__subclasses__()`` reflects every subclass
    defined ANYWHERE in the current process -- an unrelated test module
    that stubs a ``SeedError`` subclass would otherwise silently pollute
    the closed-hierarchy count for the rest of the session. Filtering by
    ``__module__`` keeps this check local to what this story actually
    owns."""
    return [cls for cls in SeedError.__subclasses__() if cls.__module__ == SeedError.__module__]


# --- SeedError shape ---------------------------------------------------


def test_seed_error_is_a_pyforge_error_and_an_exception():
    assert issubclass(SeedError, PyforgeError)
    assert issubclass(SeedError, Exception)


def test_seed_error_is_raisable():
    with pytest.raises(SeedError):
        raise SeedError("boom", remedy="fix it")


# --- valid construction: I/O Matrix row 1 -------------------------------


def test_never_write_violation_valid_construction():
    exc = NeverWriteViolation("blocked", remedy="loosen the never-write set")
    assert exc.exit_code == 4
    assert "blocked" in str(exc)


def test_valid_construction_stores_message_and_remedy():
    exc = UsageError("bad flag", remedy="use --help to see valid flags")
    assert exc.message == "bad flag"
    assert exc.remedy == "use --help to see valid flags"


@pytest.mark.parametrize("leaf", _ALL_LEAVES)
def test_every_leaf_constructs_with_a_non_blank_message_and_remedy(leaf):
    exc = leaf("something failed", remedy="do something about it")
    assert isinstance(exc, SeedError)
    assert exc.message == "something failed"
    assert exc.remedy == "do something about it"
    assert "something failed" in str(exc)


# --- blank message: I/O Matrix row 2 ------------------------------------


@pytest.mark.parametrize("message", ["", "   ", "\n", "\t \n"])
def test_blank_message_raises_value_error(message):
    with pytest.raises(ValueError):
        UsageError(message, remedy="fix the flag")


def test_non_string_message_raises_value_error():
    with pytest.raises(ValueError):
        UsageError(None, remedy="fix the flag")  # type: ignore[arg-type]


# --- blank remedy: I/O Matrix row 3 -------------------------------------


@pytest.mark.parametrize("remedy", ["", "   ", "\n", "\t \n"])
def test_blank_remedy_raises_value_error(remedy):
    with pytest.raises(ValueError):
        UsageError("bad flag", remedy=remedy)


def test_non_string_remedy_raises_value_error():
    with pytest.raises(ValueError):
        UsageError("bad flag", remedy=None)  # type: ignore[arg-type]


def test_seed_error_itself_validates_blank_message_and_remedy():
    with pytest.raises(ValueError):
        SeedError("", remedy="fix it")
    with pytest.raises(ValueError):
        SeedError("boom", remedy="")


# --- hierarchy enumeration: I/O Matrix row 4 ----------------------------


def test_hierarchy_has_exactly_six_leaves():
    assert set(_taxonomy_leaves()) == set(_ALL_LEAVES)
    assert len(_taxonomy_leaves()) == 6


def test_hierarchy_exit_code_set_is_exactly_right_with_no_duplicates():
    exit_codes = [leaf.exit_code for leaf in _taxonomy_leaves()]
    assert len(exit_codes) == len(set(exit_codes)), "duplicate exit_code across leaves"
    assert set(exit_codes) == {1, 2, 3, 4, 5, 10}


def test_every_subclass_has_an_int_exit_code():
    for leaf in _taxonomy_leaves():
        # `type(...) is int`, not `isinstance` (review finding): `bool` is
        # an `int` subclass, so `isinstance(True, int)` passes -- an
        # accidental `exit_code = True` would collide with real code `1`
        # and pass an `isinstance` check silently.
        assert type(leaf.exit_code) is int


@pytest.mark.parametrize(
    "leaf,expected_code",
    [
        (ConformanceFailure, 1),
        (UsageError, 2),
        (PreconditionFailure, 3),
        (NeverWriteViolation, 4),
        (StateInvalid, 5),
        (InternalError, 10),
    ],
)
def test_each_leaf_pins_its_documented_exit_code(leaf, expected_code):
    assert leaf.exit_code == expected_code


# --- pickle / deepcopy round-trip: review finding -----------------------
# `Exception.__reduce__`'s default `cls(*self.args)` reconstruction cannot
# satisfy `remedy`'s keyword-only requirement -- reproduced live before
# `SeedError.__reduce__` was added (both `copy.deepcopy` and
# `pickle.loads(pickle.dumps(...))` raised `TypeError`). Parametrized
# across all six leaves: the fix lives once on the shared `SeedError` base,
# but every leaf inherits the same keyword-only signature that broke it.


@pytest.mark.parametrize("leaf", _ALL_LEAVES)
def test_survives_deepcopy(leaf):
    original = leaf("something failed", remedy="do something about it")
    cloned = copy.deepcopy(original)
    assert type(cloned) is leaf
    assert cloned.message == original.message
    assert cloned.remedy == original.remedy
    assert cloned.exit_code == original.exit_code


@pytest.mark.parametrize("leaf", _ALL_LEAVES)
def test_survives_pickle_round_trip(leaf):
    original = leaf("something failed", remedy="do something about it")
    restored = pickle.loads(pickle.dumps(original))
    assert type(restored) is leaf
    assert restored.message == original.message
    assert restored.remedy == original.remedy
    assert restored.exit_code == original.exit_code
