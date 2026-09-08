"""``cli.dispatch``'s catching/mapping/stderr rows (Story 1.4, AD-6) -- the
I/O matrix's dispatch scenarios.
"""

from __future__ import annotations

import pytest

from pyforge.herald.cli import TOOL_NAME, dispatch
from pyforge.herald.errors import (
    AuthError,
    ExportConflictError,
    HeraldError,
    PullConflictError,
    SeedConflictError,
    TransportCallError,
    TransportUnreachableError,
    UnconditionalWriteError,
)


def test_dispatch_returns_0_and_writes_nothing_to_stderr_on_success(capsys):
    def operation() -> None:
        return None

    assert dispatch(operation) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "error",
    [
        SeedConflictError("edits exist"),
        PullConflictError("edits exist"),
        ExportConflictError("edits exist"),
    ],
)
def test_dispatch_maps_every_conflict_error_to_3_and_names_it_on_stderr(capsys, error):
    def operation() -> None:
        raise error

    assert dispatch(operation) == 3
    err = capsys.readouterr().err
    assert TOOL_NAME in err
    assert type(error).__name__ in err
    assert "edits exist" in err


@pytest.mark.parametrize(
    "error",
    [
        TransportUnreachableError("no route"),
        AuthError("no credential"),
        TransportCallError("tool failed"),
        UnconditionalWriteError("no etag"),
    ],
)
def test_dispatch_maps_every_transport_error_to_4_and_names_the_concrete_subclass(
    capsys, error
):
    def operation() -> None:
        raise error

    assert dispatch(operation) == 4
    err = capsys.readouterr().err
    assert TOOL_NAME in err
    assert type(error).__name__ in err
    assert str(error) in err


def test_dispatch_maps_an_unmapped_herald_error_to_1(capsys):
    def operation() -> None:
        raise HeraldError("x")

    assert dispatch(operation) == 1
    assert "HeraldError" in capsys.readouterr().err


def test_dispatch_flattens_a_multi_line_message_to_one_stderr_line(capsys):
    """The contract is *one* structured stderr line; a message carrying
    embedded newlines (a future conflict listing, a wrapped OS error) must
    not break line-oriented consumers."""

    def operation() -> None:
        raise HeraldError("line one\nline two")

    assert dispatch(operation) == 1
    err = capsys.readouterr().err
    assert err.endswith("\n")
    assert err.count("\n") == 1
    assert "line one line two" in err


def test_dispatch_flattens_control_characters_out_of_the_stderr_line(capsys):
    """A server-relayed message carrying ANSI escapes or backspaces could
    erase or spoof the structured prefix on a terminal -- every
    non-printable character is flattened to a space alongside newlines."""

    def operation() -> None:
        raise HeraldError("evil \x1b[2K spoof \x08\x08ok")

    assert dispatch(operation) == 1
    err = capsys.readouterr().err
    assert "\x1b" not in err
    assert "\x08" not in err
    assert err.count("\n") == 1
    assert "spoof" in err
