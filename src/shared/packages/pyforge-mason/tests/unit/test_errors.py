"""Story 1.3 — `MasonError` construction, identifier validation, `__str__`.

Story 1.6 extends this file with `CfeImportFloorError` coverage: its
identifier and a message naming every missing module plus the interpreter
path. Story 1.7 extends it again with `CfeUnresolvedError` coverage: its
fixed identifier and message naming all four `resolve.py` step names plus
how to satisfy the first three. Story 2.1 extends it again with
`CfeTimeoutError` coverage: its identifier and a message naming both the
timed-out script's key and the timeout value. Story 3.1 extends it again
with `EngineAbsentError` coverage: its identifier, stored attributes, and a
message naming both the absent engine and its provisioning hint, matching
`CfeImportFloorError`'s existing test shape."""

from __future__ import annotations

import copy
import pickle

import pytest

from pyforge.mason.errors import (
    CfeImportFloorError, CfeTimeoutError, CfeUnresolvedError,
    EngineAbsentError, MasonError,
)


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


# --- Story 1.7: CfeUnresolvedError -------------------------------------------

def test_cfe_unresolved_error_identifier():
    exc = CfeUnresolvedError()
    assert exc.identifier == "cfe:unresolved"


def test_cfe_unresolved_error_message_names_all_four_step_names():
    exc = CfeUnresolvedError()
    for step_name in ("flag", "environment", "cwd-walk", "not-found"):
        assert step_name in str(exc)


def test_cfe_unresolved_error_message_names_how_to_satisfy_the_first_three():
    exc = CfeUnresolvedError()
    message = str(exc)
    assert "--cfe-root" in message
    assert "MASON_CFE_ROOT" in message
    assert ".claude/scripts/conda-forge-expert" in message


def test_cfe_unresolved_error_is_a_mason_error():
    assert issubclass(CfeUnresolvedError, MasonError)
    with pytest.raises(MasonError):
        raise CfeUnresolvedError()


def test_cfe_unresolved_error_takes_no_constructor_arguments():
    with pytest.raises(TypeError):
        CfeUnresolvedError("cfe:unresolved")  # type: ignore[call-arg]


def test_cfe_unresolved_error_str_format_is_identifier_colon_space_message():
    exc = CfeUnresolvedError()
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_cfe_unresolved_error_survives_deepcopy():
    """Review pass (2026-08-09): `Exception.__reduce__` reconstructs via
    `cls(*self.args)`, but `MasonError.__init__` sets `self.args` to a
    two-item tuple while this class's constructor takes zero arguments --
    without the `__reduce__` override, this would raise `TypeError` instead
    of round-tripping."""
    original = CfeUnresolvedError()
    clone = copy.deepcopy(original)
    assert isinstance(clone, CfeUnresolvedError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_cfe_unresolved_error_survives_pickle_round_trip():
    original = CfeUnresolvedError()
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, CfeUnresolvedError)
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 2.1: CfeTimeoutError -----------------------------------------------

def test_cfe_timeout_error_identifier():
    exc = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    assert exc.identifier == "cfe:timeout"


def test_cfe_timeout_error_stores_attributes():
    exc = CfeTimeoutError(script="submit_pr", timeout=300.0)
    assert exc.script == "submit_pr"
    assert exc.timeout == 300.0


def test_cfe_timeout_error_message_names_the_script_key_and_timeout_value():
    exc = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    message = str(exc)
    assert "validate_recipe" in message
    assert "120.0" in message


def test_cfe_timeout_error_is_a_mason_error():
    assert issubclass(CfeTimeoutError, MasonError)
    with pytest.raises(MasonError):
        raise CfeTimeoutError(script="submit_pr", timeout=300.0)


def test_cfe_timeout_error_str_format_is_identifier_colon_space_message():
    exc = CfeTimeoutError(script="validate_recipe", timeout=45.5)
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_cfe_timeout_error_survives_deepcopy():
    """Review pass (2026-08-11): unlike `CfeUnresolvedError` (whose
    zero-argument constructor immediately mismatches `self.args`'s two
    items and raises `TypeError` without a `__reduce__` override), this
    class's constructor also takes two arguments -- so without the override
    below, `cls(*self.args)` would NOT raise, but would silently reconstruct
    with `script == "cfe:timeout"` (the identifier) and `timeout` bound to
    the built message string (not a number), corrupting the clone instead
    of failing loudly."""
    original = CfeTimeoutError(script="validate_recipe", timeout=120.0)
    clone = copy.deepcopy(original)
    assert isinstance(clone, CfeTimeoutError)
    assert clone.script == original.script
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_cfe_timeout_error_survives_pickle_round_trip():
    original = CfeTimeoutError(script="submit_pr", timeout=300.0)
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, CfeTimeoutError)
    assert clone.script == original.script
    assert clone.timeout == original.timeout
    assert clone.identifier == original.identifier
    assert clone.message == original.message


# --- Story 3.1: EngineAbsentError --------------------------------------------

def test_engine_absent_error_identifier():
    exc = EngineAbsentError(name="conda-lock", conda_package="conda-lock")
    assert exc.identifier == "engine:absent"


def test_engine_absent_error_stores_attributes():
    exc = EngineAbsentError(name="build", conda_package="python-build")
    assert exc.name == "build"
    assert exc.conda_package == "python-build"


def test_engine_absent_error_message_names_the_engine_and_its_conda_package():
    exc = EngineAbsentError(name="build", conda_package="python-build")
    message = str(exc)
    assert "build" in message
    assert "python-build" in message


def test_engine_absent_error_is_a_mason_error():
    assert issubclass(EngineAbsentError, MasonError)
    with pytest.raises(MasonError):
        raise EngineAbsentError(name="pixi", conda_package="pixi")


def test_engine_absent_error_str_format_is_identifier_colon_space_message():
    exc = EngineAbsentError(name="twine", conda_package="twine")
    assert str(exc) == f"{exc.identifier}: {exc.message}"


def test_engine_absent_error_rejects_empty_name():
    with pytest.raises(ValueError):
        EngineAbsentError(name="", conda_package="pixi")


def test_engine_absent_error_rejects_empty_conda_package():
    with pytest.raises(ValueError):
        EngineAbsentError(name="pixi", conda_package="")


def test_engine_absent_error_rejects_whitespace_only_name():
    with pytest.raises(ValueError):
        EngineAbsentError(name="   ", conda_package="pixi")


def test_engine_absent_error_survives_deepcopy():
    """Review pass (2026-08-13): mirrors `CfeTimeoutError`'s own deepcopy
    guard -- without the `__reduce__` override, `cls(*self.args)` would
    reconstruct with `name == "engine:absent"` (the identifier) and
    `conda_package` bound to the built message string, corrupting the
    clone's `.args`/`repr()` instead of failing loudly."""
    original = EngineAbsentError(name="pixi", conda_package="pixi")
    clone = copy.deepcopy(original)
    assert isinstance(clone, EngineAbsentError)
    assert clone.name == original.name
    assert clone.conda_package == original.conda_package
    assert clone.identifier == original.identifier
    assert clone.message == original.message


def test_engine_absent_error_survives_pickle_round_trip():
    original = EngineAbsentError(name="build", conda_package="python-build")
    clone = pickle.loads(pickle.dumps(original))
    assert isinstance(clone, EngineAbsentError)
    assert clone.name == original.name
    assert clone.conda_package == original.conda_package
    assert clone.identifier == original.identifier
    assert clone.message == original.message
