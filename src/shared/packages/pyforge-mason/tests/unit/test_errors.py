"""Story 1.3 — `MasonError` construction, identifier validation, `__str__`."""

from __future__ import annotations

import pytest

from pyforge.mason.errors import MasonError


def test_valid_identifier_constructs_and_stores_attributes():
    exc = MasonError("cfe:unresolved", "the CFE root could not be found")
    assert exc.identifier == "cfe:unresolved"
    assert exc.message == "the CFE root could not be found"


@pytest.mark.parametrize("identifier", [
    "cfe:unresolved",
    "ship:credential-missing",
    "engine:absent",
    "a:b",
    "multi-part-name:multi-part-message",
])
def test_valid_identifiers_from_the_architecture_spine(identifier):
    MasonError(identifier, "message")  # must not raise


@pytest.mark.parametrize("identifier", [
    "Bad Id",
    "NoColon",
    "cfe:",
    ":unresolved",
    "cfe:Unresolved",
    "CFE:unresolved",
    "cfe :unresolved",
    "cfe: unresolved",
    "cfe:un_resolved",
    "cfe--bad:unresolved",
    "cfe:unresolved:extra",
    "",
    "cfe:unresolved\n",  # a trailing newline must not slip past `$`-style anchoring
])
def test_invalid_identifiers_raise_value_error(identifier):
    with pytest.raises(ValueError):
        MasonError(identifier, "msg")


def test_non_string_identifier_raises_value_error_not_type_error():
    """A non-str identifier must fail with the documented ValueError, not an
    incidental TypeError from the regex engine rejecting a non-str input."""
    with pytest.raises(ValueError):
        MasonError(None, "msg")


def test_empty_message_raises_value_error():
    """An empty message can't state what failed or what to do next (NFR-14)."""
    with pytest.raises(ValueError):
        MasonError("cfe:unresolved", "")


def test_str_format_is_identifier_colon_space_message():
    exc = MasonError("cfe:unresolved", "run `mason doctor` to see why")
    assert str(exc) == "cfe:unresolved: run `mason doctor` to see why"


def test_mason_error_is_an_exception_subclass():
    assert issubclass(MasonError, Exception)
    with pytest.raises(MasonError):
        raise MasonError("cfe:unresolved", "boom")
