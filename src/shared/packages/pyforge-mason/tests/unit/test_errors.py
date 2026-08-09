"""Story 1.3 — `MasonError` construction, identifier validation, `__str__`.

Story 1.6 extends this file with `CfeImportFloorError` coverage: its
identifier and a message naming every missing module plus the interpreter
path."""

from __future__ import annotations

import pytest

from pyforge.mason.errors import CfeImportFloorError, MasonError


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


@pytest.mark.parametrize("message", ["", "   ", "\n", "\t \n"])
def test_empty_or_whitespace_only_message_raises_value_error(message):
    """An empty or all-whitespace message can't state what failed or what to
    do next (NFR-14) — whitespace-only is the same truncated diagnostic as
    empty, one space bar away."""
    with pytest.raises(ValueError):
        MasonError("cfe:unresolved", message)


def test_non_string_message_raises_value_error():
    """A non-str message (int, list, exception object) must fail with the
    documented ValueError — same asymmetry-closing guard as the non-str
    identifier case above."""
    with pytest.raises(ValueError):
        MasonError("cfe:unresolved", 123)


def test_str_format_is_identifier_colon_space_message():
    exc = MasonError("cfe:unresolved", "run `mason doctor` to see why")
    assert str(exc) == "cfe:unresolved: run `mason doctor` to see why"


def test_mason_error_is_an_exception_subclass():
    assert issubclass(MasonError, Exception)
    with pytest.raises(MasonError):
        raise MasonError("cfe:unresolved", "boom")


# --- Story 1.6: CfeImportFloorError -----------------------------------------

def test_cfe_import_floor_error_identifier():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert exc.identifier == "cfe:import-floor-missing"


def test_cfe_import_floor_error_stores_attributes():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert exc.missing == ("truststore", "ruamel.yaml")
    assert exc.interpreter == "/opt/py"


def test_cfe_import_floor_error_message_names_every_missing_module_and_interpreter():
    exc = CfeImportFloorError(missing=("truststore", "ruamel.yaml"), interpreter="/opt/py")
    assert "truststore" in str(exc)
    assert "ruamel.yaml" in str(exc)
    assert "/opt/py" in str(exc)


def test_cfe_import_floor_error_is_a_mason_error():
    assert issubclass(CfeImportFloorError, MasonError)
    with pytest.raises(MasonError):
        raise CfeImportFloorError(missing=("pyyaml",), interpreter="/opt/py")


def test_cfe_import_floor_error_single_missing_module():
    exc = CfeImportFloorError(missing=("pyyaml",), interpreter="/usr/bin/python3")
    assert "pyyaml" in str(exc)
    assert "/usr/bin/python3" in str(exc)


def test_cfe_import_floor_error_rejects_empty_missing():
    """An import-floor error naming nothing missing is incoherent -- review
    pass (2026-08-09): the constructor now enforces this, matching
    `MasonError`'s own validation rigor rather than only claiming it in
    prose."""
    with pytest.raises(ValueError):
        CfeImportFloorError(missing=(), interpreter="/opt/py")


def test_cfe_import_floor_error_coerces_missing_to_a_tuple():
    """A caller passing a mutable `list` must not silently defeat the
    immutable-shape convention every other dataclass in this story
    follows."""
    exc = CfeImportFloorError(missing=["pyyaml", "requests"], interpreter="/opt/py")
    assert exc.missing == ("pyyaml", "requests")
    assert isinstance(exc.missing, tuple)
