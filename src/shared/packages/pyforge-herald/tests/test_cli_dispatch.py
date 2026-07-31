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
