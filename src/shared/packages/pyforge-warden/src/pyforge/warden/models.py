"""Canonical enums + report/finding types — the frozen contract (Story 1.1).

One definition site for every category value (StrEnum, never bare string
literals) and for the ``ComplianceReport`` shape that every later engine,
extractor, and renderer produces against. Field shape/type/optionality is
frozen here, whole; later epics are producers against this contract, never
editors. Growable-enum policy: ONLY ``CveMatchLevel`` and ``WithholdReason``
may widen (additively) later.

Finding-ID scheme (stable + deterministic; waiver matching across runs
depends on it):

* ``vuln:<advisory-id>:<pkg>@<ver>``
* ``hygiene:<DEP-code>:<module-or-pkg>``
* ``indeterminate:<reason>:<pkg>``

Waiver-scope decision (recorded): all three finding families are
waivable-with-expiry — an auditable, time-boxed acceptance; the graduated
path for unscannable deps.

This module is pure data: no I/O, no subprocess, no network, no clock.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum

# The axis is an OPEN string mechanism (a license/SAST axis lands additively,
# never as a schema break); these constants name the two v1 assessment axes
# plus the pre-engine ingestion axis (Story 1.7 — discovery/extract/routing
# failures that happen before any per-axis engine ever runs).
AXIS_HYGIENE = "hygiene"
AXIS_VULNERABILITY = "vulnerability"
AXIS_INGESTION = "ingestion"

# Core semver of the v1 report contract (no prerelease/build tags). Matched
# with .fullmatch — "$" would accept a trailing newline (Python re).
_SCHEMA_VERSION_RE = re.compile(r"1\.\d+\.\d+")

# The three finding-ID families (see module docstring). Matched with
# .fullmatch; "[^:\n]" (not "[^:]") so an ID can never embed a newline —
# waiver matching depends on IDs being single-line stable strings.
_FINDING_ID_FAMILIES = (
    re.compile(r"vuln:[^:\n]+:.+@.+"),
    re.compile(r"hygiene:[^:\n]+:.+"),
    re.compile(r"indeterminate:[^:\n]+:.+"),
)

# The frozen, closed exit-code set (see verdict.py for the projection).
_VALID_EXIT_CODES = frozenset({0, 1, 2, 130})


class Status(StrEnum):
    """The 7 verdict rungs. Canonical token is ``warn`` (not ``warnings``).

    Ordering (strongest first) is owned exclusively by ``verdict.py`` —
    everything else feeds rungs; only ``verdict.py`` projects.
    """

    ERROR = "error"
    POLICY_VIOLATION = "policy-violation"
    INDETERMINATE = "indeterminate"
    WARN = "warn"
    BYPASSED = "bypassed"
    CLEAN = "clean"
    NOT_APPLICABLE = "not-applicable"


class ErrorKind(StrEnum):
    """Typed operational-failure categories (closed set)."""

    UNPARSABLE_MANIFEST = "unparsable-manifest"
    ENGINE_UNAVAILABLE = "engine-unavailable"
    ENGINE_OUTPUT_UNRECOGNIZED = "engine-output-unrecognized"
    ENGINE_OUTPUT_UNPARSEABLE = "engine-output-unparseable"
    ENGINE_EXECUTION_FAILED = "engine-execution-failed"
    ENGINE_TIMEOUT = "engine-timeout"
    CONFIG_PARSE = "config-parse"
    CONFIG_VALIDATION = "config-validation"
    INTERNAL_ERROR = "internal-error"


class WithholdReason(StrEnum):
    """Why a component was withheld from vuln matching (growable, additive).

    ``ambiguous-identity`` (added 2026-07-13, sanctioned additive growth):
    two records of one component resolved to DIFFERENT PyPI identities, so
    the identity was withheld rather than guessed (Gap-C)."""

    NO_VERSION = "no-version"
    UNMAPPED_ECOSYSTEM = "unmapped-ecosystem"
    NATIVE_NONPYPI = "native-nonpypi"
    RANGE_ONLY = "range-only"
    AMBIGUOUS_IDENTITY = "ambiguous-identity"


class Ecosystem(StrEnum):
    """Closed set — pixi is a manifest format, not an ecosystem (that fact
    lives in ``Component.provenance``)."""

    PYPI = "pypi"
    CONDA = "conda"


class CveMatchLevel(StrEnum):
    """CVE-match confidence (growable, additive).

    The projection treats any unknown/weaker level as ``indeterminate``,
    never ``clean`` — the additive-growth safety rule.
    """

    EXACT = "exact"
    NAME_ONLY = "name-only"
    NONE = "none"


class IdentitySource(StrEnum):
    """Where a component's PyPI identity was resolved from."""

    NATIVE = "native"
    LOCK = "lock"
    PYPI_SECTION = "pypi-section"
    MAP = "map"
    NONE = "none"


class ExtractionMode(StrEnum):
    """How the extractor obtained a component (E1 degradation ladder)."""

    PARSED = "parsed"
    NAME_ONLY = "name-only"
    UNION_MARKED = "union-marked"
    RAW_MALFORMED = "raw-malformed"


class SeverityTier(StrEnum):
    """Normalized severity tier (raw evidence rides alongside in ``Severity``)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    UNKNOWN = "unknown"


class ResolutionDepth(StrEnum):
    """The resolution-depth honesty vocabulary (closed): a loose manifest
    proves direct deps only; a lockfile proves the transitive closure."""

    DIRECT_ONLY = "direct-only"
    LOCKED_CLOSURE = "locked-closure"


# Legal exit codes per status — the schema's allOf coherence clauses, mirrored
# at construction time so an incoherent report can never be BUILT (not merely
# rejected at validation). 130 (SIGINT) is legal alongside every status: an
# interrupt can land during any verdict. Keys are deliberately ALPHABETICAL —
# the sole-ownership guard forbids materializing the lattice ORDER outside
# verdict.py, and validation needs the pair set, not the ordering.
_LEGAL_EXITS_BY_STATUS: dict[Status, frozenset[int]] = {
    Status.BYPASSED: frozenset({0, 130}),
    Status.CLEAN: frozenset({0, 130}),
    Status.ERROR: frozenset({2, 130}),
    Status.INDETERMINATE: frozenset({1, 130}),
    Status.NOT_APPLICABLE: frozenset({0, 130}),
    Status.POLICY_VIOLATION: frozenset({1, 130}),
    Status.WARN: frozenset({0, 1, 130}),
}


@dataclass(frozen=True)
class Severity:
    """Normalized tier + raw evidence (CVSS vector string or database label)."""

    tier: SeverityTier
    raw: str | None

    def __post_init__(self) -> None:
        # Coerce so a raw string tier either resolves to a member or fails
        # loud HERE (StrEnum equality would otherwise let it through and
        # crash later at .value during serialization).
        object.__setattr__(self, "tier", SeverityTier(self.tier))


@dataclass(frozen=True)
class VulnData:
    """Vulnerability-data provenance — generic names ONLY, never engine-named
    fields (the atlas gate is this schema's second producer)."""

    source: str | None
    snapshot_at: str | None
    max_age_ok: bool | None

    def __post_init__(self) -> None:
        # Mirrors the schema's if/then clause: a concrete max_age_ok verdict
        # (true/false) implies vuln data WAS consulted, so its provenance
        # must be stated.
        if self.max_age_ok is not None and (
            self.source is None or self.snapshot_at is None
        ):
            raise ValueError(
                "a concrete max_age_ok verdict requires source and "
                "snapshot_at to be stated (vuln-data provenance)"
            )


@dataclass(frozen=True)
class StatusDriver:
    """Why the verdict is what it is (axis + finding id) — an exit that can't
    say why is an incoherent contract. Required for every non-clean status.

    Two-namespace ``finding_id`` contract (ratified, Story 1.7): for every
    NON-error status that carries a driver (``policy-violation``/
    ``indeterminate``/``warn``/``bypassed`` — a waiver suppresses a REAL
    finding, so its driver references that same finding too), the id MUST
    equal an id present in that report's own ``findings[]``. For
    ``Status.ERROR``, the id instead uses the reserved, deliberately
    EXEMPT ``error:<kind>:<subject>`` grammar (see ``cli.py``'s
    ``_record_error``) and need not reference ``findings[]`` at all —
    ``findings`` may be empty and the report still stays schema-valid."""

    axis: str
    finding_id: str


@dataclass(frozen=True)
class Finding:
    """One finding, in one of the three ID families (see module docstring).

    All three families are waivable-with-expiry. ``kev``/``epss`` are declared
    slots the v1 producer never populates (the atlas producer will).
    """

    id: str
    axis: str
    message: str
    subject: str | None
    severity: Severity | None
    kev: bool | None = None
    epss: float | None = None

    def __post_init__(self) -> None:
        if not any(family.fullmatch(self.id) for family in _FINDING_ID_FAMILIES):
            raise ValueError(
                f"finding id {self.id!r} matches none of the three families "
                "(vuln:<advisory-id>:<pkg>@<ver> | hygiene:<DEP-code>:"
                "<module-or-pkg> | indeterminate:<reason>:<pkg>)"
            )
        if self.epss is not None:
            if isinstance(self.epss, bool) or not (
                math.isfinite(self.epss) and 0.0 <= self.epss <= 1.0
            ):
                raise ValueError(
                    f"epss must be None or a finite number in [0, 1], "
                    f"got {self.epss!r}"
                )
            # Canonicalize -0.0 -> 0.0 (equal under comparison but rendering
            # differently, which would break byte-identical serialization).
            object.__setattr__(self, "epss", self.epss + 0.0)


@dataclass(frozen=True)
class AxisCoverage:
    """Per-axis coverage honesty — both denominator families are fields
    (manifest-level and dep-level), plus the resolution-depth claim
    (``direct-only`` vs ``locked-closure``)."""

    axis: str
    manifests_found: int
    manifests_parsed: int
    deps_total: int
    deps_assessed: int
    resolution_depth: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "manifests_found",
            "manifests_parsed",
            "deps_total",
            "deps_assessed",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be an int >= 0, got {value!r}")
        if self.manifests_parsed > self.manifests_found:
            raise ValueError(
                f"manifests_parsed ({self.manifests_parsed}) exceeds "
                f"manifests_found ({self.manifests_found})"
            )
        if self.deps_assessed > self.deps_total:
            raise ValueError(
                f"deps_assessed ({self.deps_assessed}) exceeds "
                f"deps_total ({self.deps_total})"
            )
        if self.resolution_depth is not None:
            # Coerce through the closed vocabulary (StrEnum), then store the
            # plain token — the field's frozen shape stays `str | None`.
            try:
                depth = ResolutionDepth(self.resolution_depth)
            except ValueError:
                raise ValueError(
                    f"resolution_depth must be one of "
                    f"{[member.value for member in ResolutionDepth]} or None, "
                    f"got {self.resolution_depth!r}"
                ) from None
            object.__setattr__(self, "resolution_depth", depth.value)


@dataclass(frozen=True)
class ErrorRecord:
    """A typed operational error surfaced into the report."""

    kind: ErrorKind
    owner: str
    message: str

    def __post_init__(self) -> None:
        # Coerce so a raw string kind fails loud here, not at serialization.
        object.__setattr__(self, "kind", ErrorKind(self.kind))


@dataclass(frozen=True)
class ScannedManifest:
    """One entry of the resolved scan set (what was actually scanned)."""

    path: str
    kind: str


@dataclass(frozen=True)
class ComplianceReport:
    """The frozen external report contract (see ``data/report-schema.json``)."""

    schema_version: str
    tool_name: str
    tool_version: str
    status: Status
    status_driver: StatusDriver | None
    exit_code: int
    findings: tuple[Finding, ...]
    coverage: tuple[AxisCoverage, ...]
    vuln_data: VulnData
    inventory_count: int
    resolved_scan_set: tuple[ScannedManifest, ...]
    errors: tuple[ErrorRecord, ...]

    def __post_init__(self) -> None:
        # Coerce so a raw string status ("warnings", or even "clean") either
        # resolves to a Status member or fails loud HERE — StrEnum equality
        # would otherwise admit it and crash later in to_json_dict.
        object.__setattr__(self, "status", Status(self.status))
        if isinstance(self.exit_code, bool) or self.exit_code not in _VALID_EXIT_CODES:
            raise ValueError(
                f"exit_code must be one of {sorted(_VALID_EXIT_CODES)}, "
                f"got {self.exit_code!r}"
            )
        if self.exit_code not in _LEGAL_EXITS_BY_STATUS[self.status]:
            raise ValueError(
                f"status {self.status.value!r} is incoherent with exit_code "
                f"{self.exit_code!r} — legal exits: "
                f"{sorted(_LEGAL_EXITS_BY_STATUS[self.status])} (the schema's "
                "coherence clauses, enforced at construction)"
            )
        if (
            self.status not in (Status.CLEAN, Status.NOT_APPLICABLE)
            and self.status_driver is None
        ):
            raise ValueError(
                f"status {self.status.value!r} requires a status_driver — an "
                "exit that can't say why is an incoherent contract"
            )
        if isinstance(self.inventory_count, bool) or self.inventory_count < 0:
            raise ValueError(
                f"inventory_count must be an int >= 0, got {self.inventory_count!r}"
            )
        if not _SCHEMA_VERSION_RE.fullmatch(self.schema_version):
            raise ValueError(
                f"schema_version must match '1.<minor>.<patch>' (core semver "
                f"of the v1 contract), got {self.schema_version!r}"
            )
        axes = [c.axis for c in self.coverage]
        if len(axes) != len(set(axes)):
            raise ValueError(f"coverage axes must be unique, got {axes!r}")
        finding_ids = [f.id for f in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            duplicates = sorted(
                {fid for fid in finding_ids if finding_ids.count(fid) > 1}
            )
            raise ValueError(
                f"finding ids must be unique (waiver matching and by-id "
                f"consumers depend on it), duplicated: {duplicates!r}"
            )
        for finding in self.findings:
            if finding.id.startswith("vuln:") and finding.axis != AXIS_VULNERABILITY:
                raise ValueError(
                    f"vuln-family finding {finding.id!r} must carry axis "
                    f"{AXIS_VULNERABILITY!r}, got {finding.axis!r}"
                )
            if finding.id.startswith("hygiene:") and finding.axis != AXIS_HYGIENE:
                raise ValueError(
                    f"hygiene-family finding {finding.id!r} must carry axis "
                    f"{AXIS_HYGIENE!r}, got {finding.axis!r}"
                )

    def to_json_dict(self) -> dict[str, object]:
        """Render the report as JSON-primitive values, deterministically.

        Every list is sorted on its FULL rendered tuple (never a prefix, so
        key-equal-prefix entries still order totally); enums render as their
        canonical tokens; the status renders as ``{"value": ..., "driver":
        ...|null}``. Callers dump with ``json.dumps(..., sort_keys=True)``
        for byte-identical output.
        """
        return {
            "schema_version": self.schema_version,
            "tool": {"name": self.tool_name, "version": self.tool_version},
            "status": {
                "value": self.status.value,
                "driver": _driver_dict(self.status_driver),
            },
            "exit_code": self.exit_code,
            "findings": [
                _finding_dict(f) for f in sorted(self.findings, key=_finding_sort_key)
            ],
            "coverage": [
                _coverage_dict(c) for c in sorted(self.coverage, key=_coverage_sort_key)
            ],
            "vuln_data": {
                "source": self.vuln_data.source,
                "snapshot_at": self.vuln_data.snapshot_at,
                "max_age_ok": self.vuln_data.max_age_ok,
            },
            "inventory_count": self.inventory_count,
            "resolved_scan_set": [
                {"path": m.path, "kind": m.kind}
                for m in sorted(self.resolved_scan_set, key=lambda m: (m.path, m.kind))
            ],
            "errors": [
                {"kind": e.kind.value, "owner": e.owner, "message": e.message}
                for e in sorted(
                    self.errors, key=lambda e: (e.kind.value, e.owner, e.message)
                )
            ],
        }


def _driver_dict(driver: StatusDriver | None) -> dict[str, object] | None:
    if driver is None:
        return None
    return {"axis": driver.axis, "finding_id": driver.finding_id}


def _severity_dict(severity: Severity | None) -> dict[str, object] | None:
    if severity is None:
        return None
    return {"tier": severity.tier.value, "raw": severity.raw}


def _finding_dict(finding: Finding) -> dict[str, object]:
    return {
        "id": finding.id,
        "axis": finding.axis,
        "message": finding.message,
        "subject": finding.subject,
        "severity": _severity_dict(finding.severity),
        "kev": finding.kev,
        "epss": finding.epss,
    }


def _coverage_dict(coverage: AxisCoverage) -> dict[str, object]:
    return {
        "axis": coverage.axis,
        "manifests_found": coverage.manifests_found,
        "manifests_parsed": coverage.manifests_parsed,
        "deps_total": coverage.deps_total,
        "deps_assessed": coverage.deps_assessed,
        "resolution_depth": coverage.resolution_depth,
    }


def _finding_sort_key(finding: Finding) -> tuple[object, ...]:
    """Total order over the COMPLETE rendered finding (None-safe: every
    optional field sorts as a ``(present, value)`` pair, absent first)."""
    severity = finding.severity
    return (
        finding.id,
        finding.axis,
        finding.message,
        finding.subject is not None,
        finding.subject or "",
        severity is not None,
        severity.tier.value if severity is not None else "",
        severity is not None and severity.raw is not None,
        (severity.raw or "") if severity is not None else "",
        finding.kev is not None,
        bool(finding.kev),
        finding.epss is not None,
        finding.epss if finding.epss is not None else 0.0,
    )


def _coverage_sort_key(coverage: AxisCoverage) -> tuple[object, ...]:
    """Total order over the COMPLETE coverage tuple, not the axis alone."""
    return (
        coverage.axis,
        coverage.manifests_found,
        coverage.manifests_parsed,
        coverage.deps_total,
        coverage.deps_assessed,
        coverage.resolution_depth is not None,
        coverage.resolution_depth or "",
    )
