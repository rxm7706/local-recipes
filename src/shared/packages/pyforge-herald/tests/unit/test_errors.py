"""``errors.exit_code_for``'s fixed map (Story 1.4, AD-6).

One test per mapped family plus the unmapped fallback -- the I/O matrix's
dispatch rows exercise the same map through ``cli.dispatch``
(``test_cli_dispatch.py``); this file asserts the projection in isolation.
"""

from __future__ import annotations

import pytest

from pyforge.herald.errors import (
    AuthError,
    EvidenceLinkError,
    ExportConflictError,
    HeraldError,
    InvalidDateRangeError,
    OperatorAuthorizationError,
    PullConflictError,
    SeedConflictError,
    TransportCallError,
    TransportError,
    TransportUnreachableError,
    UnconditionalWriteError,
    exit_code_for,
)


@pytest.mark.parametrize(
    "error",
    [
        SeedConflictError("edits exist"),
        PullConflictError("edits exist"),
        ExportConflictError("edits exist"),
    ],
)
def test_conflict_errors_map_to_3(error: HeraldError):
    assert exit_code_for(error) == 3


@pytest.mark.parametrize(
    "error",
    [
        TransportError("generic transport failure"),
        AuthError("no credential"),
        TransportUnreachableError("no route"),
        TransportCallError("tool failed"),
        UnconditionalWriteError("no etag"),
    ],
)
def test_transport_errors_and_every_subclass_map_to_4(error: HeraldError):
    assert exit_code_for(error) == 4


def test_a_bare_herald_error_falls_back_to_1():
    assert exit_code_for(HeraldError("unmapped")) == 1


def test_a_future_unmapped_subclass_also_falls_back_to_1():
    class SomeFutureHeraldError(HeraldError):
        pass

    assert exit_code_for(SomeFutureHeraldError("x")) == 1


@pytest.mark.parametrize(
    "error",
    [
        OperatorAuthorizationError("unauthorized: operator role required"),
        InvalidDateRangeError("Invalid date format"),
        EvidenceLinkError("Evidence link broken: https://example.invalid"),
    ],
)
def test_epic_6_error_types_fall_back_to_1(error: HeraldError):
    """Story 6.3/6.2/6.4's new error types are deliberately unmapped --
    each AC calls for exit code 1, which is exactly what the safety-net
    fallback already gives them without a new map entry."""
    assert exit_code_for(error) == 1


@pytest.mark.parametrize(
    "conflict_error",
    [SeedConflictError, PullConflictError, ExportConflictError],
)
def test_conflict_errors_are_not_transport_errors(conflict_error: type[HeraldError]):
    """The module docstring calls this distinction load-bearing: a conflict
    is bridge-core's own interpretation, never a transport failure. Pinned
    here so a future edit can't accidentally re-parent one under
    ``TransportError`` (which would silently change its exit code from 3 to
    4 via ``exit_code_for``'s most-specific-first ``isinstance`` scan)."""
    assert not issubclass(conflict_error, TransportError)
    assert issubclass(conflict_error, HeraldError)
