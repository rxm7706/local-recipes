"""Unit tests for ``pyforge.doctor.prescribe.rank`` (Story 3.2, FR-7) --
covers every row of the story spec's I/O & Edge-Case Matrix."""

from __future__ import annotations

from pyforge.doctor.models import DoctorStatus, Finding, Partition, Source
from pyforge.doctor.prescribe import PartitionedFinding, RankedPrescription, rank


def _pf(
    status=DoctorStatus.FAIL,
    evidence=None,
    source=Source.CVE_WATCHER,
    check="pkg-a",
    partition=Partition.ACTIONABLE,
):
    finding = Finding(
        source=source, check=check, status=status, message="stub", evidence=evidence or {}
    )
    return PartitionedFinding(finding=finding, partition=partition, reason="actionable")


def test_kev_flagged_ranks_above_equal_severity_non_kev():
    kev_finding = _pf(evidence={"kev": True}, check="kev-pkg")
    plain_finding = _pf(evidence={}, check="plain-pkg")
    result = rank([plain_finding, kev_finding])
    assert result[0].finding.check == "kev-pkg"
    assert result[0].rank == 1
    assert result[1].finding.check == "plain-pkg"
    assert result[1].rank == 2


def test_higher_epss_ranks_above_lower_epss_at_equal_severity():
    low = _pf(evidence={"epss": 0.1}, check="low-epss")
    high = _pf(evidence={"epss": 0.62}, check="high-epss")
    result = rank([low, high])
    assert result[0].finding.check == "high-epss"
    assert result[1].finding.check == "low-epss"


def test_kev_beats_epss_when_both_present():
    kev_low_epss = _pf(evidence={"kev": True, "epss": 0.05}, check="kev-pkg")
    non_kev_high_epss = _pf(evidence={"epss": 0.99}, check="high-epss-pkg")
    result = rank([non_kev_high_epss, kev_low_epss])
    assert result[0].finding.check == "kev-pkg"


def test_blast_radius_tiebreak_patch_before_minor_before_major():
    major = _pf(
        evidence={"latest_conda_version": "1.0.0", "upstream_version": "2.0.0"},
        check="major-pkg",
    )
    minor = _pf(
        evidence={"latest_conda_version": "1.0.0", "upstream_version": "1.1.0"},
        check="minor-pkg",
    )
    patch = _pf(
        evidence={"latest_conda_version": "1.0.0", "upstream_version": "1.0.1"},
        check="patch-pkg",
    )
    result = rank([major, minor, patch])
    assert [pf.finding.check for pf in result] == ["patch-pkg", "minor-pkg", "major-pkg"]


def test_severity_dominates_kev_and_epss():
    fail_plain = _pf(status=DoctorStatus.FAIL, evidence={}, check="fail-plain")
    warn_kev = _pf(
        status=DoctorStatus.WARN, evidence={"kev": True, "epss": 0.99}, check="warn-kev"
    )
    result = rank([warn_kev, fail_plain])
    assert result[0].finding.check == "fail-plain"


def test_rank_factors_names_every_signal_never_a_bare_integer():
    finding = _pf(
        evidence={
            "kev": True,
            "epss": 0.62,
            "latest_conda_version": "1.0.0",
            "upstream_version": "1.0.1",
        }
    )
    result = rank([finding])
    factors = result[0].rank_factors
    assert factors == {"kev": True, "epss": 0.62, "blast_radius": "patch"}
    assert isinstance(result[0].rank, int)


def test_missing_epss_reports_none_not_zero():
    finding = _pf(evidence={})
    result = rank([finding])
    assert result[0].rank_factors["epss"] is None


def test_cve_watcher_severity_k_with_positive_now_v_is_kev_without_explicit_flag():
    finding = _pf(
        source=Source.CVE_WATCHER,
        evidence={"severity": "K", "now_v": 3},
        check="kev-by-inference",
    )
    plain = _pf(source=Source.CVE_WATCHER, evidence={}, check="plain")
    result = rank([plain, finding])
    assert result[0].finding.check == "kev-by-inference"
    assert result[0].rank_factors["kev"] is True


def test_severity_k_with_zero_now_v_is_not_kev():
    finding = _pf(evidence={"severity": "K", "now_v": 0})
    result = rank([finding])
    assert result[0].rank_factors["kev"] is False


def test_1_based_rank_and_dense_sequential():
    findings = [_pf(check=f"pkg-{i}") for i in range(4)]
    result = rank(findings)
    assert [pf.rank for pf in result] == [1, 2, 3, 4]


def test_only_actionable_partition_is_ranked():
    actionable = _pf(partition=Partition.ACTIONABLE, check="actionable-pkg")
    blocked = _pf(partition=Partition.BLOCKED, check="blocked-pkg")
    accepted = _pf(partition=Partition.ACCEPTED_RISK, check="accepted-pkg")
    result = rank([actionable, blocked, accepted])
    assert len(result) == 1
    assert result[0].finding.check == "actionable-pkg"


def test_empty_actionable_partition_returns_empty_tuple():
    blocked = _pf(partition=Partition.BLOCKED)
    assert rank([blocked]) == ()


def test_ties_do_not_raise_a_type_error_comparing_findings():
    # Regression guard for the self-review finding recorded in this
    # story's own spec: an earlier draft embedded the Finding itself
    # inside the sorted tuple, which raised TypeError on any tie (frozen
    # dataclasses have no __lt__). Every one of these three ties on every
    # signal.
    findings = [_pf(check=f"identical-{i}") for i in range(3)]
    result = rank(findings)
    assert len(result) == 3


def test_returns_ranked_prescription_dataclass_instances():
    result = rank([_pf()])
    assert isinstance(result[0], RankedPrescription)
