"""Estate-wide eligibility union over ingested evidence (Story 7.2).

Story 7.1 gave Warden a way to ingest ``sources.SourceEvidence`` from
heterogeneous evidence sources (an external CycloneDX document, the
existing per-project manifest scan) and a standalone identity API
(``sources.PackageIdentity``/``resolve_identity``). This module answers the
estate-wide question those adapters exist for: given evidence from several
sources about the SAME package identity, is it eligible for use, with a
provenance trail proving the answer.

``compute_eligibility_union`` is a pure function over already-``ingest()``-ed
evidence -- it never calls ``.fetch()``/``.ingest()`` itself, mirrors
``models.py``'s "pure data" precedent, and performs no filesystem/network/
subprocess I/O of its own. ``now`` is caller-injected (mirrors ``feeds.py``'s
own ``now: datetime``-injected-for-testability convention) so every
timestamp this module produces is fully deterministic under test.

``EligibilityStatus``/``ProvenanceEntry``/``EligibilityResult`` are NEW,
standalone types -- deliberately never added to ``models.py``'s frozen
``Status`` enum or ``ComplianceReport`` shape (epic Technical Decision: the
two vocabularies answer different questions -- estate-wide "may this exist"
vs. project-scoped "did the scan pass" -- and must not be merged).

Consensus policy design decision (recorded): the default
``required_authority_sources`` (used when a caller passes ``None``) is
computed ONCE from the distinct ``source_name``s present across the FULL
input evidence tuple -- never re-derived per identity. A per-identity
default would mean "the sources that saw THIS package" always equals "the
sources required for THIS package," making ``ELIGIBLE_UNION`` trivially
true for every single-source identity and ``FLAGGED_FOR_REVIEW``
unreachable -- silently defeating the whole point of a consensus policy.
Computing it once from the full evidence set gives a stable meaning: "by
default, every source consulted in this run must agree."

This module is pure data + computation: no I/O, no subprocess, no network,
no filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .sources import PackageIdentity, SourceEvidence


class EligibilityStatus(StrEnum):
    """The 3-way estate-wide eligibility classification (closed set).

    ``ELIGIBLE_UNION`` -- every required-authority source observed the
    identity (unanimous consensus). ``FLAGGED_FOR_REVIEW`` -- SOME but not
    all required-authority sources observed it (partial consensus).
    ``OBSERVED_IN_USE`` -- no required-authority source observed it at all
    (evidence exists, but none of it carries authority under the active
    policy).
    """

    ELIGIBLE_UNION = "eligible-union"
    FLAGGED_FOR_REVIEW = "flagged-for-review"
    OBSERVED_IN_USE = "observed-in-use"


@dataclass(frozen=True)
class ProvenanceEntry:
    """One deduplicated ``(source, locator)`` observation contributing to an
    ``EligibilityResult``.

    Deliberately omits the Dream's ``metadata`` field: the tracked Tier-2
    spec (``_bmad-output/projects/pyforge-warden/planning-artifacts/specs/
    spec-package-inventory-eligibility/SPEC.md``, CAP-2 -- the durable
    source of record) and ``epic-7-context.md`` (its Tier-3, regeneratable
    compilation -- the sibling Dream is pattern-reference only, not a
    requirements source) both state only "every result must carry
    ``ProvenanceEntry`` trails (source + timestamp)"; adding an unrequested,
    untested ``metadata`` field would be speculative surface Simplicity
    First forbids. ``locator`` is kept (present for free on every
    ``SourceEvidence``) because "reproducible from provenance alone"
    requires knowing WHERE each contributing observation came from, not
    just which source type observed it.

    ``timestamp`` records WHEN THIS UNION COMPUTATION RAN (``now`` at the
    ``compute_eligibility_union`` call site), NOT when a source originally
    observed the package -- ``SourceEvidence`` (Story 7.1's shipped shape)
    carries no per-observation timestamp of its own, so this is the best
    available signal, not a limitation of this story's own logic.
    """

    source: str
    locator: str
    timestamp: str


@dataclass(frozen=True)
class EligibilityResult:
    """One identity's eligibility classification + its provenance trail."""

    identity: PackageIdentity
    status: EligibilityStatus
    provenance: tuple[ProvenanceEntry, ...]


def compute_eligibility_union(
    evidence: tuple[SourceEvidence, ...],
    *,
    required_authority_sources: frozenset[str] | None = None,
    now: datetime,
) -> tuple[EligibilityResult, ...]:
    """Group ``evidence`` by ``PackageIdentity`` and classify each identity
    against ``required_authority_sources``.

    ``required_authority_sources=None`` (the default) means "every source
    name present in the full ``evidence`` tuple, computed once" -- see the
    module docstring's consensus-policy design decision. An identity's
    status is ``ELIGIBLE_UNION`` when ``required_authority_sources`` is
    non-empty and every required source observed it; ``FLAGGED_FOR_REVIEW``
    when some (not all) required sources observed it; ``OBSERVED_IN_USE``
    otherwise (including whenever ``required_authority_sources`` is
    explicitly empty).

    Each result's ``provenance`` is one ``ProvenanceEntry`` per distinct
    ``(source_name, locator)`` pair observed for that identity, deduplicated
    and sorted by ``(source, locator)``. Results are returned sorted by
    ``(identity.ecosystem, identity.canonical_name, identity.version or "")``.

    ``required_authority_sources`` is a pure in-process value -- this story
    deliberately ships no CLI flag or TOML config key to set it (``cli.py``/
    ``config.py`` are untouched); wiring a config-driven surface for it is a
    later story's job.
    """
    # Normalize to a tuple up front: `evidence` is walked twice below (once
    # for the default computation, once for grouping), so a one-shot
    # iterable/generator would silently look empty on the second pass.
    evidence = tuple(evidence)
    if required_authority_sources is None:
        required_authority_sources = frozenset(ev.source_name for ev in evidence)

    groups: dict[PackageIdentity, list[SourceEvidence]] = {}
    for ev in evidence:
        groups.setdefault(ev.identity, []).append(ev)

    results: list[EligibilityResult] = []
    for identity, group in groups.items():
        observed = frozenset(ev.source_name for ev in group)
        required_present = observed & required_authority_sources
        if required_authority_sources and required_present == required_authority_sources:
            status = EligibilityStatus.ELIGIBLE_UNION
        elif required_present:
            status = EligibilityStatus.FLAGGED_FOR_REVIEW
        else:
            status = EligibilityStatus.OBSERVED_IN_USE

        seen: set[tuple[str, str]] = set()
        provenance: list[ProvenanceEntry] = []
        for ev in group:
            key = (ev.source_name, ev.locator)
            if key in seen:
                continue
            seen.add(key)
            provenance.append(
                ProvenanceEntry(
                    source=ev.source_name,
                    locator=ev.locator,
                    timestamp=now.isoformat(),
                )
            )
        provenance.sort(key=lambda p: (p.source, p.locator))

        results.append(EligibilityResult(identity=identity, status=status, provenance=tuple(provenance)))

    results.sort(
        key=lambda r: (
            r.identity.ecosystem,
            r.identity.canonical_name,
            r.identity.version or "",
        )
    )
    return tuple(results)
