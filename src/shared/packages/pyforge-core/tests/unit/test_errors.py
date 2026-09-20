"""Unit tests for ``pyforge.core.errors`` (Story 14.3, CAP-5).

Covers the intent contract's I/O & Edge-Case Matrix rows for
``PyforgeError``: it is a bare ``Exception`` subclass with no ``__init__``
override, so any subclass's own constructor (including one taking extra
positional/keyword arguments) survives re-parenting unchanged.
"""

from __future__ import annotations

import pytest

from pyforge.core.errors import PyforgeError


def test_pyforge_error_is_an_exception_subclass():
    assert issubclass(PyforgeError, Exception)


def test_pyforge_error_has_no_init_override():
    assert PyforgeError.__init__ is Exception.__init__


def test_pyforge_error_is_catchable_as_exception():
    try:
        raise PyforgeError("boom")
    except Exception as exc:  # noqa: BLE001 -- proving catchability via the base, not narrowing
        assert isinstance(exc, PyforgeError)
    else:
        pytest.fail("PyforgeError was not raised")


def test_a_subclass_with_a_custom_constructor_survives_reparenting():
    class CustomError(PyforgeError):
        def __init__(self, identifier: str, message: str) -> None:
            self.identifier = identifier
            self.message = message
            super().__init__(identifier, message)

    exc = CustomError("x:y", "something failed")
    assert exc.identifier == "x:y"
    assert exc.message == "something failed"
    assert isinstance(exc, PyforgeError)
