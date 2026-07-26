"""Meta test -- AD-39 envelope consistency (Story 1.1).

Constructs a valid ``Envelope`` for every lattice member and asserts the
``status_for`` partitioning holds (``{clean, warn} -> ok``, everything else
-> ``error``); asserts both AD-39 invalid-construction scenarios from the
spec's I/O & Edge-Case Matrix raise ``ValueError``. A meta-test (not just a
unit test) because AD-39 is an architecture invariant every future
command's envelope must keep holding, not just this story's own
construction paths.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import findings
from pyforge.marshal.core.model import (
    Envelope,
    Finding,
    Severity,
    Status,
    Verdict,
    build_envelope,
    status_for,
)

_CODE = "MRS-TST-001"


@pytest.fixture(autouse=True)
def _registered_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({_CODE}))


@pytest.mark.parametrize("member", list(Verdict))
def test_every_lattice_member_produces_a_status_consistent_envelope(member):
    expected_status = status_for(member)
    severity = Severity.WARN if expected_status is Status.OK else Severity.ERROR
    finding = Finding(code=_CODE, severity=severity, message="m")
    envelope = build_envelope(command="x", verdict=member, data={}, findings=(finding,))
    assert envelope.status is expected_status
    assert envelope.verdict is member


def test_status_for_partition_is_exactly_two_valued():
    ok_verdicts = {member for member in Verdict if status_for(member) is Status.OK}
    error_verdicts = {member for member in Verdict if status_for(member) is Status.ERROR}
    assert ok_verdicts == {Verdict.CLEAN, Verdict.WARN}
    assert error_verdicts == set(Verdict) - ok_verdicts


def test_mismatched_status_and_verdict_raises():
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.ERROR,
            data={},
            data_version=1,
            findings=(),
        )


def test_ok_status_with_error_severity_finding_raises():
    error_finding = Finding(code=_CODE, severity=Severity.ERROR, message="m")
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.CLEAN,
            data={},
            data_version=1,
            findings=(error_finding,),
        )
