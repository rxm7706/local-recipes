"""FR-level behavioural contract: anything Steward dispatches IS a Duty (AD-7)."""

from __future__ import annotations

import argparse

from pyforge.steward.cli import DUTIES, resolve_duty
from pyforge.steward.interfaces import Duty, DutyResult, NullDuty


def test_nullduty_satisfies_the_protocol_structurally():
    assert isinstance(NullDuty("keys"), Duty)


def test_every_declared_duty_resolves_to_a_conforming_implementation():
    for name in DUTIES:
        impl = resolve_duty(name)
        assert isinstance(impl, Duty), f"{name} does not satisfy the Duty protocol"
        assert impl.name == name


def test_a_duty_returns_a_result_rather_than_exiting():
    """The separation AD-8 depends on: duties return, main() projects."""
    result = NullDuty("keys").run(argparse.Namespace())
    assert isinstance(result, DutyResult)
    assert result.ok is True


def test_dutyresult_is_frozen():
    """A result is evidence — it must not be mutated after the duty returns."""
    import dataclasses
    import pytest

    result = DutyResult(ok=True, summary="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.ok = False        # type: ignore[misc]


def test_an_object_missing_run_is_not_a_duty():
    class NotADuty:
        name = "keys"

    assert not isinstance(NotADuty(), Duty)
