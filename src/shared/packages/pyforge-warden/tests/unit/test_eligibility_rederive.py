from datetime import UTC, datetime

from pyforge.warden.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    ProvenanceEntry,
    compute_eligibility_union,
    status_from_eligibility_result,
)
from pyforge.warden.models import Ecosystem
from pyforge.warden.sources import SourceEvidence, resolve_identity

_NOW = datetime(2026, 10, 3, tzinfo=UTC)


def _ev(source, locator):
    return SourceEvidence(
        identity=resolve_identity(Ecosystem.PYPI, "requests", "2.31.0"),
        source_name=source,
        locator=locator,
        raw_name="requests",
    )


def test_override_that_changes_outcome_rederives():
    evidence = (_ev("cyclonedx", "a.json"), _ev("manifest", "/proj"))
    for override, expected in (
        (frozenset({"cyclonedx", "artifactory"}), EligibilityStatus.FLAGGED_FOR_REVIEW),
        (frozenset({"artifactory"}), EligibilityStatus.OBSERVED_IN_USE),
    ):
        (r,) = compute_eligibility_union(evidence, required_authority_sources=override, now=_NOW)
        assert r.status is expected
        assert status_from_eligibility_result(r) is expected


def test_hand_built_result_rederives_from_policy_not_stored_status():
    r = EligibilityResult(
        identity=resolve_identity(Ecosystem.PYPI, "requests", "2.31.0"),
        status=EligibilityStatus.ELIGIBLE_UNION,
        provenance=(ProvenanceEntry(source="cyclonedx", locator="a.json", timestamp=_NOW.isoformat()),),
        effective_required_authority_sources=frozenset({"cyclonedx", "manifest"}),
    )
    assert status_from_eligibility_result(r) is EligibilityStatus.FLAGGED_FOR_REVIEW
