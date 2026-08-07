"""Unit tests for ``pyforge.doctor.prescribe.partition`` (Story 3.1, FR-6) --
covers every row of the story spec's I/O & Edge-Case Matrix."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Partition, Source
from pyforge.doctor.prescribe import PartitionedFinding, partition


def _finding(status, evidence=None, source=Source.CVE_WATCHER, check="pkg-a"):
    return Finding(
        source=source,
        check=check,
        status=status,
        message="stub",
        evidence=evidence or {},
    )


def test_every_finding_lands_in_exactly_one_partition_total_matches_count():
    findings = [
        _finding(DoctorStatus.WARN),
        _finding(DoctorStatus.FAIL, evidence={"fix_available": False}, check="pkg-b"),
        _finding(DoctorStatus.OK, check="pkg-c"),
    ]
    result = partition(findings)
    assert len(result) == len(findings)
    partitions = {pf.partition for pf in result}
    assert partitions <= {Partition.ACTIONABLE, Partition.BLOCKED, Partition.ACCEPTED_RISK}


def test_unfixed_cve_lands_in_blocked_with_a_human_readable_reason():
    findings = [_finding(DoctorStatus.FAIL, evidence={"fix_available": False})]
    result = partition(findings)
    assert len(result) == 1
    assert result[0].partition is Partition.BLOCKED
    assert result[0].reason  # never empty
    assert "no fix" in result[0].reason.lower()


def test_blocked_reason_uses_evidence_block_reason_when_present():
    findings = [
        _finding(
            DoctorStatus.FAIL,
            evidence={"fix_available": False, "block_reason": "upstream frozen"},
        )
    ]
    result = partition(findings)
    assert result[0].reason == "upstream frozen"


def test_fixable_finding_is_actionable():
    findings = [_finding(DoctorStatus.WARN)]
    result = partition(findings)
    assert result[0].partition is Partition.ACTIONABLE


def test_waived_finding_is_accepted_risk():
    findings = [
        _finding(
            DoctorStatus.FAIL,
            evidence={"waived": True, "waived_reason": "approved by security"},
        )
    ]
    result = partition(findings)
    assert result[0].partition is Partition.ACCEPTED_RISK
    assert result[0].reason == "approved by security"


def test_waived_wins_over_fix_available_false():
    findings = [
        _finding(
            DoctorStatus.FAIL,
            evidence={"waived": True, "fix_available": False},
        )
    ]
    result = partition(findings)
    assert result[0].partition is Partition.ACCEPTED_RISK


def test_ok_finding_lands_in_actionable_with_a_no_action_reason():
    findings = [_finding(DoctorStatus.OK)]
    result = partition(findings)
    assert result[0].partition is Partition.ACTIONABLE
    assert "no remediation needed" in result[0].reason


def test_none_yet_waived_in_a_realistic_mix_produces_zero_accepted_risk():
    # Story 3.1 AC1's own fixture wording: "some with a known fix, one
    # unfixed CVE, none yet waived" -- no current producer ever sets
    # evidence["waived"], so a realistic mix (no waived flag anywhere)
    # never populates ACCEPTED_RISK.
    findings = [
        _finding(DoctorStatus.WARN, check="fixable-a"),
        _finding(DoctorStatus.WARN, check="fixable-b"),
        _finding(
            DoctorStatus.FAIL, evidence={"fix_available": False}, check="unfixed-cve"
        ),
    ]
    result = partition(findings)
    assert sum(1 for pf in result if pf.partition is Partition.ACCEPTED_RISK) == 0
    assert sum(1 for pf in result if pf.partition is Partition.BLOCKED) == 1
    assert sum(1 for pf in result if pf.partition is Partition.ACTIONABLE) == 2


def test_empty_input_returns_empty_tuple():
    assert partition([]) == ()


def test_preserves_input_order():
    findings = [_finding(DoctorStatus.WARN, check=f"pkg-{i}") for i in range(5)]
    result = partition(findings)
    assert [pf.finding.check for pf in result] == [f"pkg-{i}" for i in range(5)]


def test_returns_partitioned_finding_dataclass_instances():
    result = partition([_finding(DoctorStatus.WARN)])
    assert isinstance(result[0], PartitionedFinding)
    assert result[0].finding.check == "pkg-a"
