"""Unit tests — the eligibility union + its provenance trail (Story 7.2).

Covers the full I/O & edge-case matrix from the story spec plus the two
functional ACs (identity object/value preservation, and the per-call
freshly-computed default). Fixtures are hand-built ``SourceEvidence``/
``PackageIdentity`` instances (via ``resolve_identity``, no adapter I/O
needed — this module is pure), mirroring ``test_sources.py``'s own
conventions.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from pyforge.warden.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    ProvenanceEntry,
    compute_eligibility_union,
)
from pyforge.warden.models import Ecosystem
from pyforge.warden.sources import SourceEvidence, resolve_identity

_NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)


def _evidence(*, source_name: str, locator: str, name: str = "requests", version: str = "2.31.0") -> SourceEvidence:
    return SourceEvidence(
        identity=resolve_identity(Ecosystem.PYPI, name, version),
        source_name=source_name,
        locator=locator,
        raw_name=name,
    )


# --- I/O & edge-case matrix ---------------------------------------------------


def test_unanimous_consensus_yields_eligible_union():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json"),
        _evidence(source_name="manifest", locator="/proj"),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 1
    assert results[0].status is EligibilityStatus.ELIGIBLE_UNION
    assert results[0].provenance == (
        ProvenanceEntry(source="cyclonedx", locator="a.json", timestamp=_NOW.isoformat()),
        ProvenanceEntry(source="manifest", locator="/proj", timestamp=_NOW.isoformat()),
    )


def test_partial_consensus_yields_flagged_for_review():
    # Two identities; the full evidence set has two distinct source names
    # ("cyclonedx", "manifest"), but each identity is seen by only one.
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json", name="requests"),
        _evidence(source_name="manifest", locator="/proj", name="packaging"),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 2
    assert all(r.status is EligibilityStatus.FLAGGED_FOR_REVIEW for r in results)


def test_non_required_source_only_yields_observed_in_use():
    evidence = (_evidence(source_name="manifest", locator="/proj"),)

    results = compute_eligibility_union(evidence, required_authority_sources=frozenset({"cyclonedx"}), now=_NOW)

    assert len(results) == 1
    assert results[0].status is EligibilityStatus.OBSERVED_IN_USE


def test_explicit_empty_required_set_yields_observed_in_use_for_everything():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json", name="requests"),
        _evidence(source_name="manifest", locator="/proj", name="requests"),
        _evidence(source_name="manifest", locator="/proj", name="packaging"),
    )

    results = compute_eligibility_union(evidence, required_authority_sources=frozenset(), now=_NOW)

    assert len(results) == 2
    assert all(r.status is EligibilityStatus.OBSERVED_IN_USE for r in results)


def test_duplicate_observation_same_source_and_locator_collapses_to_one_entry():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json"),
        _evidence(source_name="cyclonedx", locator="a.json"),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 1
    assert results[0].provenance == (ProvenanceEntry(source="cyclonedx", locator="a.json", timestamp=_NOW.isoformat()),)


def test_same_source_different_locator_yields_two_entries():
    evidence = (
        _evidence(source_name="manifest", locator="/proj-a"),
        _evidence(source_name="manifest", locator="/proj-b"),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 1
    assert results[0].provenance == (
        ProvenanceEntry(source="manifest", locator="/proj-a", timestamp=_NOW.isoformat()),
        ProvenanceEntry(source="manifest", locator="/proj-b", timestamp=_NOW.isoformat()),
    )


def test_empty_evidence_returns_empty_tuple():
    assert compute_eligibility_union((), now=_NOW) == ()


def test_distinct_versions_yield_independent_results():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json", version="2.31.0"),
        _evidence(source_name="cyclonedx", locator="a.json", version="2.32.0"),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 2
    versions = {r.identity.version for r in results}
    assert versions == {"2.31.0", "2.32.0"}
    for result in results:
        assert result.status is EligibilityStatus.ELIGIBLE_UNION
        assert len(result.provenance) == 1


def test_determinism_same_input_same_now_returns_equal_results():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json", name="requests"),
        _evidence(source_name="manifest", locator="/proj", name="requests"),
        _evidence(source_name="cyclonedx", locator="b.json", name="packaging"),
    )

    first = compute_eligibility_union(evidence, now=_NOW)
    second = compute_eligibility_union(evidence, now=_NOW)

    assert first == second


# --- Acceptance Criteria -------------------------------------------------


def test_ac_identity_is_the_same_object_from_the_input_evidence():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "2.31.0")
    evidence = (
        SourceEvidence(
            identity=identity,
            source_name="cyclonedx",
            locator="a.json",
            raw_name="requests",
        ),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert results[0].identity is identity


def test_ac_each_calls_default_reflects_only_its_own_evidence_set():
    # If the default were cached at module scope from the first call
    # (sources={"cyclonedx"}), the second call's "manifest"-only evidence
    # would compute required_present=frozenset() against that stale
    # default and wrongly classify as OBSERVED_IN_USE instead of
    # ELIGIBLE_UNION.
    first_evidence = (_evidence(source_name="cyclonedx", locator="a.json", name="requests"),)
    second_evidence = (_evidence(source_name="manifest", locator="/proj", name="packaging"),)

    first_results = compute_eligibility_union(first_evidence, now=_NOW)
    second_results = compute_eligibility_union(second_evidence, now=_NOW)

    assert first_results[0].status is EligibilityStatus.ELIGIBLE_UNION
    assert second_results[0].status is EligibilityStatus.ELIGIBLE_UNION


def test_eligibility_result_and_provenance_entry_are_frozen():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "2.31.0")
    entry = ProvenanceEntry(source="cyclonedx", locator="a.json", timestamp=_NOW.isoformat())
    result = EligibilityResult(identity=identity, status=EligibilityStatus.ELIGIBLE_UNION, provenance=(entry,))

    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.source = "other"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = EligibilityStatus.OBSERVED_IN_USE  # type: ignore[misc]


# --- additional coverage (code review) ------------------------------------


def test_results_sort_by_ecosystem_then_name_then_version_with_none_first():
    """Verified real gap: weakening the ``identity.version or ""`` guard in
    the sort key would raise ``TypeError`` comparing ``str`` and
    ``NoneType`` -- no existing test would catch that regression (every
    existing multi-result test either checks membership via ``all()``/a
    ``set``, or only ever uses non-None versions)."""
    evidence = (
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "alpha", "2.0.0"),
            source_name="cyclonedx",
            locator="a.json",
            raw_name="alpha",
        ),
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "alpha", None),
            source_name="cyclonedx",
            locator="a.json",
            raw_name="alpha",
        ),
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "zeta", None),
            source_name="cyclonedx",
            locator="a.json",
            raw_name="zeta",
        ),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert [(r.identity.canonical_name, r.identity.version) for r in results] == [
        ("alpha", None),
        ("alpha", "2.0.0"),
        ("zeta", None),
    ]


def test_partial_consensus_generalizes_to_three_plus_required_sources():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json"),
        _evidence(source_name="manifest", locator="/proj"),
    )

    results = compute_eligibility_union(
        evidence,
        required_authority_sources=frozenset({"cyclonedx", "manifest", "artifactory"}),
        now=_NOW,
    )

    assert len(results) == 1
    assert results[0].status is EligibilityStatus.FLAGGED_FOR_REVIEW


def test_cross_ecosystem_evidence_groups_and_sorts_independently():
    evidence = (
        SourceEvidence(
            identity=resolve_identity(Ecosystem.CONDA, "requests", "2.31.0"),
            source_name="cyclonedx",
            locator="a.json",
            raw_name="requests",
        ),
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "requests", "2.31.0"),
            source_name="cyclonedx",
            locator="a.json",
            raw_name="requests",
        ),
    )

    results = compute_eligibility_union(evidence, now=_NOW)

    assert len(results) == 2
    assert [r.identity.ecosystem for r in results] == [Ecosystem.CONDA, Ecosystem.PYPI]


def test_different_now_values_change_only_timestamps():
    evidence = (
        _evidence(source_name="cyclonedx", locator="a.json", name="requests"),
        _evidence(source_name="manifest", locator="/proj", name="requests"),
    )
    later = datetime(2026, 8, 23, 0, 0, 0, tzinfo=UTC)

    first = compute_eligibility_union(evidence, now=_NOW)
    second = compute_eligibility_union(evidence, now=later)

    assert len(first) == len(second) == 1
    assert first[0].identity == second[0].identity
    assert first[0].status == second[0].status
    assert [(p.source, p.locator) for p in first[0].provenance] == [(p.source, p.locator) for p in second[0].provenance]
    assert all(p.timestamp == _NOW.isoformat() for p in first[0].provenance)
    assert all(p.timestamp == later.isoformat() for p in second[0].provenance)
    assert first != second  # timestamps differ -- full-tuple equality fails
