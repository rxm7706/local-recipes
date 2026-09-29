"""Unit tests for ``pyforge.core.verdict`` (Story 14.3, CAP-3).

Covers the intent contract's I/O & Edge-Case Matrix: ``Lattice.rank``,
``Lattice.exit_codes``, ``Lattice.narrows`` (both a real narrows-True case
and an informational narrows-False case), and ``dispatch_exit_code``'s
matched/unmatched dispatch.
"""

from __future__ import annotations

import pytest

from pyforge.core.verdict import Lattice, dispatch_exit_code


def test_lattice_rank_returns_zero_indexed_position():
    lattice = Lattice(order=("A", "B", "C"), exit_by_member={"A": 2, "B": 1, "C": 0})
    assert lattice.rank("B") == 1
    assert lattice.rank("A") == 0
    assert lattice.rank("C") == 2


def test_lattice_rejects_a_duplicate_order_member():
    """Review-pass patch: a duplicate would silently let the last
    occurrence's rank win, producing an ambiguous rank with no error --
    fail loud instead."""
    with pytest.raises(ValueError, match="duplicate member"):
        Lattice(order=("A", "B", "A"), exit_by_member={"A": 1, "B": 0})


def test_lattice_exit_codes_is_the_frozen_value_domain():
    lattice = Lattice(order=("A", "B", "C"), exit_by_member={"A": 2, "B": 1, "C": 0})
    assert lattice.exit_codes == frozenset({0, 1, 2})


def test_lattice_narrows_true_when_subset():
    doctor = Lattice(order=("FAIL", "WARN", "OK"), exit_by_member={"FAIL": 2, "WARN": 0, "OK": 0})
    warden = Lattice(
        order=("ERROR", "POLICY", "WARN", "CLEAN"),
        exit_by_member={"ERROR": 2, "POLICY": 1, "WARN": 0, "CLEAN": 0},
    )
    assert doctor.exit_codes == frozenset({0, 2})
    assert warden.exit_codes == frozenset({0, 1, 2})
    assert doctor.narrows(warden) is True


def test_lattice_narrows_false_when_not_subset():
    marshal = Lattice(
        order=("ERROR", "GATE_FAILED", "SCOPE", "UNEVAL", "WARN", "CLEAN"),
        exit_by_member={
            "ERROR": 4,
            "GATE_FAILED": 3,
            "SCOPE": 2,
            "UNEVAL": 1,
            "WARN": 0,
            "CLEAN": 0,
        },
    )
    warden = Lattice(
        order=("ERROR", "POLICY", "WARN", "CLEAN"),
        exit_by_member={"ERROR": 2, "POLICY": 1, "WARN": 0, "CLEAN": 0},
    )
    assert marshal.narrows(warden) is False


def test_dispatch_exit_code_matches_most_specific_first():
    class HeraldError(Exception):
        pass

    class TransportError(HeraldError):
        pass

    class SeedConflictError(HeraldError):
        pass

    table = (
        (SeedConflictError, 3),
        (TransportError, 4),
    )
    assert dispatch_exit_code(SeedConflictError("x"), table, default=1) == 3
    assert dispatch_exit_code(TransportError("x"), table, default=1) == 4


def test_dispatch_exit_code_falls_through_to_default_when_unmatched():
    class HeraldError(Exception):
        pass

    class TransportError(HeraldError):
        pass

    table = ((TransportError, 4),)
    assert dispatch_exit_code(HeraldError("x"), table, default=1) == 1
