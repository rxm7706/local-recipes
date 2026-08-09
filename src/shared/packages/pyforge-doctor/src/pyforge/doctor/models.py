"""Canonical enums + report/finding types — the frozen contract (Story 1.1).

Doctor's own closed taxonomy (architecture spine AD-3): structurally mirrors
``pyforge.warden``'s ``StrEnum`` + frozen-dataclass ``__post_init__``
coercion idiom, but THIS MODULE never imports from ``pyforge.warden`` — its
``Finding``/``Source``/``DoctorStatus`` taxonomy is deliberately independent.
Importing warden's ``ErrorKind`` would silently stretch a vocabulary scoped
to *scan-engine operational failure* over Doctor's broader domain
(engine-missing / feedstock-stale / credential-hygiene), making it a shared,
driftable vocabulary neither package fully owns. The rule is scoped, not an
absolute package-wide ban: ``doctor.sources.warden`` (Story 1.2, AD-1) is
the one sanctioned exception, importing only
``pyforge.warden.engines.run_doctor_checks`` as a library call and
normalizing its output into this module's own ``Finding`` shape — it never
imports ``ErrorKind`` or any other warden vocabulary into this taxonomy.

``DoctorReport`` is the one JSON envelope per invocation (Consistency
Conventions): ``{schema_version, verb, generated_at, findings,
prescriptions}`` — ``prescriptions`` present (a list, possibly empty) only
when ``verb == "diagnose"``; for ``check``/``monitor`` it stays ``None`` in
the Python model AND is omitted (never ``null``) from the serialized JSON.

This module is pure data: no I/O, no subprocess, no network, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# The three verbs the CLI will dispatch (Epic 1-3); this story only freezes
# the envelope's verb/prescriptions coherence rule, not the dispatch itself.
_VALID_VERBS = frozenset({"check", "monitor", "diagnose"})


class DoctorStatus(StrEnum):
    """Per-Finding health tri-state (closed)."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class Source(StrEnum):
    """The wrapped instruments (closed) — one member per gather filter the
    architecture spine names (AD-1 warden-doctor; AD-6 the five atlas Watch
    axes; AD-3/FR-3 env-hygiene; AD-9/FR-12 adoption, Story 4.3 — the closed
    taxonomy EXTENDED, never opened).

    Each member's scope, subject station, and owning station are declared in
    ``doctor.sources.REGISTRY`` (Story 6.2)."""

    WARDEN_DOCTOR = "warden-doctor"
    STALENESS_REPORT = "staleness-report"
    CVE_WATCHER = "cve-watcher"
    BEHIND_UPSTREAM = "behind-upstream"
    FEEDSTOCK_HEALTH = "feedstock-health"
    RELEASE_CADENCE = "release-cadence"
    ENV_HYGIENE = "env-hygiene"
    # Charter §6 (2026-07-28): the Doctor holds the verdict on the Marshal's own
    # conformance -- "the one station that would otherwise grade itself". Added
    # 2026-08-08 after a sync destroyed 96 `done` markers across four stations and
    # all three guards written in response lived in Marshal's own surface.
    MARSHAL_DURABILITY = "marshal-durability"
    ADOPTION = "adoption"
    # Story 6.4 (FR-15): the closed taxonomy EXTENDED again -- Doctor's
    # verdict on the tracked sprint ledger's own regression-freedom (ported
    # from scripts/ledger_regression_check.py) and on the Tier-3 sprint-status
    # feed's false-green stories (ported from scripts/story_status_check.py).
    # Both judge a Marshal-produced artifact; see sources/ledger.py and
    # sources/marshal.py's gather_story_status for the independence rationale.
    LEDGER_REGRESSION = "ledger-regression"
    STORY_STATUS = "story-status"
    # Story 6.5 (FR-15): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on the fleet-status board's own truthfulness: every open Spec a
    # station owns is decomposed and its epics/ledger/board agree (ported from
    # scripts/chain_completeness_check.py), the committed data.js and tracked
    # ledger twins have not drifted from their feeds (ported from
    # scripts/dashboard_drift_check.py), and the console bar's status chips
    # actually render without overlapping or clipping (ported from
    # docs/dashboard/check_layout.py). All three judge a Marshal-produced
    # artifact (the Guildhall console + its data feeds); see sources/board.py
    # for the independence rationale.
    CHAIN_COMPLETENESS = "chain-completeness"
    DASHBOARD_DRIFT = "dashboard-drift"
    CHECK_LAYOUT = "check-layout"
    # Story 6.6 (FR-15): the closed taxonomy EXTENDED a further time -- Doctor's
    # verdict on the Dream-to-Code chain itself: every Spec links a Dream and
    # every Dream has a Spec in its owner's project, using the 6.10 sharded
    # planning tree (ported from scripts/dream_chain_check.py); every tracked
    # file is governed by a spec surface or an allowlist entry, and a governed
    # file's content has not drifted out from under its spec's contract
    # (ported from scripts/spec_surface_check.py); no deferred-work entry lives
    # only in gitignored Tier-3 scratch (ported from
    # scripts/deferred_work_check.py). All three judge Marshal-governed factory
    # apparatus; see sources/chain.py for the independence rationale.
    DREAM_CHAIN = "dream-chain"
    SPEC_SURFACE = "spec-surface"
    DEFERRED_WORK = "deferred-work"
    # Story 6.7 (FR-15): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on the one defect bmad-loop's own picker is blind to: a story
    # whose documented **Deps:** names a story in a LATER epic, which the
    # engine's strict within-epic file-order scan cannot see (ported from
    # scripts/forward_dependency_check.py). Judges a Marshal-produced artifact
    # (each station's epics doc + tracked ledger); see sources/deps.py for the
    # independence rationale and AD-13 for why it restates the harness's
    # ACTIONABLE_STATUSES rather than importing it.
    FORWARD_DEPENDENCY = "forward-dependency"


class Partition(StrEnum):
    """Where a ``Prescription`` lands (closed; Epic 3's ``diagnose``
    partition + rank pass populates this)."""

    ACTIONABLE = "actionable"
    BLOCKED = "blocked"
    ACCEPTED_RISK = "accepted-risk"


@dataclass(frozen=True)
class Finding:
    """One gathered signal, tagged with its origin ``Source``.

    ``evidence`` is a Source-specific object, opaque to this envelope (the
    architecture spine's own wording) — never validated here.
    """

    source: Source
    check: str
    status: DoctorStatus
    message: str
    evidence: dict

    def __post_init__(self) -> None:
        # Coerce so a raw string source/status either resolves to a member
        # or fails loud HERE (StrEnum equality would otherwise admit it,
        # crashing later at .value during serialization).
        object.__setattr__(self, "source", Source(self.source))
        object.__setattr__(self, "status", DoctorStatus(self.status))
        # Fail loud on a non-dict evidence (schema requires type:object) and
        # shallow-copy it -- frozen=True only blocks attribute reassignment,
        # not mutation of a referenced mutable object, so a caller holding
        # the original dict must not be able to mutate this Finding after
        # construction.
        if not isinstance(self.evidence, dict):
            raise ValueError(
                f"evidence must be a dict, got {self.evidence!r}"
            )
        object.__setattr__(self, "evidence", dict(self.evidence))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "check": self.check,
            "status": self.status.value,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class Prescription:
    """One ranked remediation for a ``Finding`` (``diagnose`` only, Epic 3).

    ``rank``/``rank_factors`` stay ``None``-able at scaffold stage — a later
    epic's ranking pass populates them; nothing produces a ``Prescription``
    yet in this story.

    ``safe_upgrade_target``/``safe_upgrade_reason`` (Story 4.4, FR-13, AD-10)
    are a later epic's single-hop upgrade-path recommendation: a specific
    next-safe-version string when confidently known, else ``None`` with
    ``safe_upgrade_reason`` always stating why (never a bare ``None`` with
    no explanation, mirroring ``rank``/``rank_factors``'s own always-paired
    value+explanation convention). Default to ``None`` so every existing
    construction site (Epic 3, unaware of this pair) keeps working
    unchanged.
    """

    finding_ref: str
    partition: Partition
    rank: int | None
    rank_factors: dict | None
    action: str
    root_cause: str
    safe_upgrade_target: str | None = None
    safe_upgrade_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "partition", Partition(self.partition))
        # Same defensive-copy rationale as Finding.evidence -- frozen=True
        # doesn't stop a caller from mutating a referenced mutable dict.
        if self.rank_factors is not None:
            object.__setattr__(self, "rank_factors", dict(self.rank_factors))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "finding_ref": self.finding_ref,
            "partition": self.partition.value,
            "rank": self.rank,
            "rank_factors": self.rank_factors,
            "action": self.action,
            "root_cause": self.root_cause,
            "safe_upgrade_target": self.safe_upgrade_target,
            "safe_upgrade_reason": self.safe_upgrade_reason,
        }


@dataclass(frozen=True)
class DoctorReport:
    """The frozen external report envelope (see ``data/report-schema.json``).

    ``prescriptions`` is present (a list, possibly empty) only when
    ``verb == "diagnose"``; for ``check``/``monitor`` it must stay ``None``
    in the Python model AND be omitted (never ``null``) from the serialized
    JSON — ``to_json_dict`` only adds the key when it is not ``None``.

    ``grade``/``axis_scores`` (Story 4.1, FR-10) are a later epic's optional
    composite-health-grade projection — deliberately stored here as ALREADY-
    SERIALIZED plain data (a ``str`` value and a tuple of plain dicts), not
    as ``doctor.score``'s own ``Grade``/``AxisScore`` types, so this module
    never needs to import ``doctor.score`` (that would be a reverse
    dependency onto a module that itself depends on ``models`` — AD-3 keeps
    this taxonomy module's own import surface minimal). Present only when
    the CLI layer actually computed a grade for this report (today: the
    ``diagnose`` verb only); omitted, never ``null``, otherwise — same
    presence discipline as ``prescriptions`` above, but WITHOUT that field's
    hard verb-coupling validation, since a future verb may want to carry a
    grade too without this module needing another edit.
    """

    schema_version: int
    verb: str
    generated_at: str
    findings: tuple[Finding, ...]
    prescriptions: tuple[Prescription, ...] | None = None
    grade: str | None = None
    axis_scores: tuple[dict, ...] | None = None

    def __post_init__(self) -> None:
        # report-schema.json declares schema_version's minimum as 1 -- fail
        # loud at construction rather than only at schema-validation time.
        if isinstance(self.schema_version, bool) or self.schema_version < 1:
            raise ValueError(
                f"schema_version must be an int >= 1, got {self.schema_version!r}"
            )
        if self.verb not in _VALID_VERBS:
            raise ValueError(
                f"verb must be one of {sorted(_VALID_VERBS)}, got {self.verb!r}"
            )
        object.__setattr__(self, "findings", tuple(self.findings))
        if self.verb == "diagnose":
            if self.prescriptions is None:
                raise ValueError(
                    "verb 'diagnose' requires prescriptions (a list, "
                    "possibly empty) — got None"
                )
            object.__setattr__(self, "prescriptions", tuple(self.prescriptions))
        elif self.prescriptions is not None:
            raise ValueError(
                f"verb {self.verb!r} must not carry prescriptions (only "
                "'diagnose' reports do) — the key must be omitted, never null"
            )
        if self.axis_scores is not None:
            object.__setattr__(
                self, "axis_scores", tuple(dict(axis) for axis in self.axis_scores)
            )

    def to_json_dict(self) -> dict[str, object]:
        document: dict[str, object] = {
            "schema_version": self.schema_version,
            "verb": self.verb,
            "generated_at": self.generated_at,
            "findings": [finding.to_json_dict() for finding in self.findings],
        }
        if self.prescriptions is not None:
            document["prescriptions"] = [
                prescription.to_json_dict() for prescription in self.prescriptions
            ]
        if self.grade is not None:
            document["grade"] = self.grade
        if self.axis_scores is not None:
            document["axis_scores"] = [dict(axis) for axis in self.axis_scores]
        return document
