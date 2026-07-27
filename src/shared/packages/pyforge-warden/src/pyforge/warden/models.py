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
* ``license:<spdx-or-"unknown">:<pkg>@<ver>`` (Story 6.1)
* ``currency:(eol|over-lag|unknown):<subject>@<ver>`` (Story 6.1)

Waiver-scope decision (recorded): every finding family is
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
# never as a schema break); these constants name the four v1 assessment axes
# plus the pre-engine ingestion axis (Story 1.7 — discovery/extract/routing
# failures that happen before any per-axis engine ever runs). AXIS_LICENSE /
# AXIS_CURRENCY are the Epic 6 producer axes (Story 6.1 reserves them; the
# producers populate later).
AXIS_HYGIENE = "hygiene"
AXIS_VULNERABILITY = "vulnerability"
AXIS_INGESTION = "ingestion"
AXIS_LICENSE = "license"
AXIS_CURRENCY = "currency"

# Core semver of the v1 report contract (no prerelease/build tags). Matched
# with .fullmatch — "$" would accept a trailing newline (Python re).
_SCHEMA_VERSION_RE = re.compile(r"1\.\d+\.\d+")

# The finding-ID families (see module docstring). Matched with .fullmatch;
# "[^:\n]" (not "[^:]") so an ID can never embed a newline — waiver matching
# depends on IDs being single-line stable strings. The license/currency
# families (Story 6.1) extend the shipped three injectively; currency's
# <reason> is a CLOSED 3-value set (unlike hygiene's open DEP-code segment).
_FINDING_ID_FAMILIES = (
    re.compile(r"vuln:[^:\n]+:.+@.+"),
    re.compile(r"hygiene:[^:\n]+:.+"),
    re.compile(r"indeterminate:[^:\n]+:.+"),
    re.compile(r"license:[^:\n]+:.+@.+"),
    re.compile(r"currency:(eol|over-lag|unknown):.+@.+"),
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


class LicenseVerdict(StrEnum):
    """Per-component SPDX license classification (Story 6.1, FR32).

    CLOSED — NOT a sanctioned growable enum (only ``CveMatchLevel`` /
    ``WithholdReason`` may widen). A ``Finding``-level input that feeds INTO
    the composed ``Status`` lattice via ``verdict.py``; it is NOT a second
    verdict lattice (do not conflate with ``verdict.py``'s "verdict")."""

    ALLOWED = "allowed"
    DENIED = "denied"
    UNKNOWN = "unknown"


class CurrencyVerdict(StrEnum):
    """Per-component (and runtime) currency classification (Story 6.1, FR34).

    CLOSED — NOT a sanctioned growable enum. ``over-lag`` is never a 4th
    member: it lives only as an id-grammar reason token whose corresponding
    verdict is ``supported`` (escalation comes from a separate numeric
    ``lag`` check owned by Story 6.5)."""

    SUPPORTED = "supported"
    EOL = "eol"
    UNKNOWN = "unknown"


# Legal exit codes per status — the schema's allOf coherence clauses, mirrored
# at construction time so an incoherent report can never be BUILT (not merely
# rejected at validation). 130 (SIGINT) is legal alongside every status: an
# interrupt can land during any verdict. Keys are deliberately ALPHABETICAL —
# the sole-ownership guard forbids materializing the lattice ORDER outside
# verdict.py, and validation needs the pair set, not the ordering.
#
# Status.INDETERMINATE widened {1,130} -> {0,1,130} (Story 1.9): the ONE
# sanctioned --allow-empty exception (verdict.exit_code_for's driver-scoped
# knob, see its docstring) needs exit 0 to be a coherent pairing with a
# status that stays indeterminate — mirrors Status.WARN's existing
# "one status, three legal exits (two non-SIGINT + 130), one caller-supplied
# knob decides which of the two non-SIGINT exits" shape exactly. This does
# NOT add a value to the frozen {0,1,2,130} exit set, reorder the lattice,
# or touch any Status/ErrorKind member — only this one status's
# legal-exit-code coherence entry widened by one already-existing code.
_LEGAL_EXITS_BY_STATUS: dict[Status, frozenset[int]] = {
    Status.BYPASSED: frozenset({0, 130}),
    Status.CLEAN: frozenset({0, 130}),
    Status.ERROR: frozenset({2, 130}),
    Status.INDETERMINATE: frozenset({0, 1, 130}),
    Status.NOT_APPLICABLE: frozenset({0, 130}),
    Status.POLICY_VIOLATION: frozenset({1, 130}),
    Status.WARN: frozenset({0, 1, 130}),
}

# The ONE driver whose finding_id may pair Status.INDETERMINATE with exit 0
# (Story 1.9's --allow-empty exception, sole-owned by verdict.exit_code_for).
# An EXACT match, not a prefix: the review that widened _LEGAL_EXITS_BY_STATUS
# above only ever intended this one specific whole-scan condition to unlock
# exit 0, never any driver merely sharing its "indeterminate:empty-
# extraction:" namespace — __post_init__ below enforces the same exactness
# at construction time so a directly-built ComplianceReport (not just the
# cli.py producer) cannot claim exit 0 for an unrelated indeterminate cause.
EMPTY_EXTRACTION_DRIVER_ID = "indeterminate:empty-extraction:scan"


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
class Epss:
    """EPSS score + percentile — both probabilities in [0, 1] (Story 6.7
    populates; a declared ``Finding`` slot until then). Mirrors the frozen,
    self-validating shape of ``Severity``."""

    score: float
    percentile: float

    def __post_init__(self) -> None:
        for field_name in ("score", "percentile"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not (
                isinstance(value, (int, float))
                and math.isfinite(value)
                and 0.0 <= value <= 1.0
            ):
                raise ValueError(
                    f"epss {field_name} must be a finite number in [0, 1], "
                    f"got {value!r}"
                )
            # Coerce to float and canonicalize -0.0 -> 0.0 (equal under
            # comparison but rendering differently, which would break
            # byte-identical serialization).
            object.__setattr__(self, field_name, value + 0.0)


@dataclass(frozen=True)
class LicenseInfo:
    """Per-component SPDX license verdict (Story 6.2 populates; a declared
    ``Finding`` sub-object until then)."""

    expression: str
    family: str | None
    verdict: LicenseVerdict

    def __post_init__(self) -> None:
        # Coerce so a raw string verdict resolves to a member or fails loud
        # HERE (StrEnum equality would otherwise admit it, crashing later at
        # .value during serialization).
        object.__setattr__(self, "verdict", LicenseVerdict(self.verdict))


@dataclass(frozen=True)
class CurrencyInfo:
    """Per-component currency verdict + tier-ladder provenance (Story 6.3
    populates; a declared ``Finding`` sub-object until then). ``lag`` is
    releases-behind-latest (an integer count), NOT calendar time (that axis
    is owned by ``max_age_ok``)."""

    verdict: CurrencyVerdict
    latest: str | None = None
    lag: int | None = None
    eol_date: str | None = None
    tier: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "verdict", CurrencyVerdict(self.verdict))
        # Reject bool AND float (matches AxisCoverage/Epss's numeric-guard
        # pattern): lag is an integer release count, never a truthy bool or a
        # fractional float that would render an ill-typed slot later.
        if self.lag is not None and (
            isinstance(self.lag, bool)
            or not isinstance(self.lag, int)
            or self.lag < 0
        ):
            raise ValueError(
                f"currency lag must be an int >= 0 or None, got {self.lag!r}"
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
    """One finding, in one of the ID families (see module docstring).

    Every family is waivable-with-expiry. ``kev``/``kev_date``/``epss`` are
    security-axis enrichment slots (Story 6.4/6.7 populate); ``license``/
    ``currency`` are the Epic 6 producer sub-objects (Story 6.2/6.3 populate).
    Story 6.1 reserves them all; the v1 producer never sets them.
    """

    id: str
    axis: str
    message: str
    subject: str | None
    severity: Severity | None
    kev: bool | None = None
    kev_date: str | None = None
    epss: Epss | None = None
    license: LicenseInfo | None = None
    currency: CurrencyInfo | None = None

    def __post_init__(self) -> None:
        if not any(family.fullmatch(self.id) for family in _FINDING_ID_FAMILIES):
            raise ValueError(
                f"finding id {self.id!r} matches none of the finding families "
                "(vuln:<advisory-id>:<pkg>@<ver> | hygiene:<DEP-code>:"
                "<module-or-pkg> | indeterminate:<reason>:<pkg> | "
                "license:<spdx-or-unknown>:<pkg>@<ver> | "
                "currency:<reason>:<subject>@<ver>)"
            )
        if self.epss is not None and not isinstance(self.epss, Epss):
            # The range check now lives on Epss.__post_init__; a non-Epss
            # value (a stray float/bool) fails loud HERE instead of rendering
            # an ill-typed slot later.
            raise ValueError(
                f"epss must be None or an Epss(score, percentile), got "
                f"{self.epss!r}"
            )
        # License/currency id-payload coherence (Story 6.1), mirroring the
        # schema's allOf coherence clauses so an incoherent finding can never
        # be BUILT (this class's docstring promise). Guarded on the id prefix
        # so they NEVER fire for indeterminate:/vuln:/hygiene: ids — only the
        # two Epic 6 producer families. The id-family check above already
        # guarantees a "currency:"-prefixed id matched the closed 3-value
        # reason regex, so split()[1] is always one of the three keys below.
        if self.id.startswith("license:"):
            if self.license is None:
                raise ValueError(
                    "license: finding must carry a license sub-object"
                )
            if self.license.verdict not in (
                LicenseVerdict.DENIED,
                LicenseVerdict.UNKNOWN,
            ):
                raise ValueError(
                    "license: finding verdict must be denied/unknown, never "
                    f"allowed, got {self.license.verdict.value!r}"
                )
        if self.id.startswith("currency:"):
            if self.currency is None:
                raise ValueError(
                    "currency: finding must carry a currency sub-object"
                )
            reason = self.id.split(":", 2)[1]
            expected_verdict = {
                "eol": CurrencyVerdict.EOL,
                "over-lag": CurrencyVerdict.SUPPORTED,
                "unknown": CurrencyVerdict.UNKNOWN,
            }[reason]
            if self.currency.verdict is not expected_verdict:
                raise ValueError(
                    f"currency:{reason}: finding verdict must be "
                    f"{expected_verdict.value!r}, got "
                    f"{self.currency.verdict.value!r}"
                )
            if reason in ("eol", "over-lag") and (
                self.currency.latest is None
                or self.currency.lag is None
                or self.currency.eol_date is None
            ):
                raise ValueError(
                    "currency eol/over-lag finding requires non-null "
                    "latest/lag/eol_date"
                )


@dataclass(frozen=True)
class AxisCoverage:
    """Per-axis coverage honesty — both denominator families are fields
    (manifest-level and dep-level), plus the resolution-depth claim
    (``direct-only`` vs ``locked-closure``).

    ``gating`` (Story 6.1, defaulted ``False``): whether this axis's gate is
    active this run. ``config.py`` is the SOLE writer (Story 6.2/6.3/6.5
    compute it from parsed flags); Story 6.1 only reserves the slot, so it
    stays ``False`` for every shipped scan."""

    axis: str
    manifests_found: int
    manifests_parsed: int
    deps_total: int
    deps_assessed: int
    resolution_depth: str | None
    gating: bool = False

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
class FeedProvenance:
    """Per-feed provenance (source + snapshot + staleness verdict) for the
    license/currency/KEV/EPSS report sections (Story 6.3/6.4/6.7 populate).

    Reuses ``VulnData``'s shape AND its if/then coherence rule verbatim
    (generic names ONLY; a concrete ``max_age_ok`` verdict implies the feed
    WAS consulted, so its provenance must be stated). ``vuln_data`` itself
    stays a separate ``VulnData`` field, untouched."""

    source: str | None
    snapshot_at: str | None
    max_age_ok: bool | None

    def __post_init__(self) -> None:
        if self.max_age_ok is not None and (
            self.source is None or self.snapshot_at is None
        ):
            raise ValueError(
                "a concrete max_age_ok verdict requires source and "
                "snapshot_at to be stated (feed provenance)"
            )


# The closed suppression-origin discriminator (Story 6.1). Named ``origin``,
# NOT ``source`` (which already means VulnData/feed provenance elsewhere).
_SUPPRESSION_ORIGINS = frozenset({"baseline", "waiver"})


@dataclass(frozen=True)
class SuppressedFinding:
    """One suppressed finding echoed in the JSON report (Story 6.1 wires the
    waiver half — ``origin="waiver"`` — inside ``cli.py``; Story 6.8 the
    baseline half). Reuses ``waiver.WaiverNotice``'s four fields, renaming
    ``id`` -> ``finding_id``. ``authorized_by``/``expires_at`` are nullable
    because baseline entries are bulk-accepted (unlike individually-signed
    waivers). At most one entry per ``finding_id`` (waiver wins the
    tie-break); every ``finding_id`` must reference an existing
    ``findings[].id`` — both enforced in ``ComplianceReport.__post_init__``."""

    finding_id: str
    origin: str
    reason: str
    authorized_by: str | None = None
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if self.origin not in _SUPPRESSION_ORIGINS:
            raise ValueError(
                f"suppression origin must be one of "
                f"{sorted(_SUPPRESSION_ORIGINS)}, got {self.origin!r}"
            )


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
    # Epic 6 optional sections — all defaulted so pre-6.1 callers keep
    # working and every shipped scan renders them empty/null (Story 6.1
    # populates ONLY suppressions, from applied waivers, in cli.py).
    suppressions: tuple[SuppressedFinding, ...] = ()
    license_data: FeedProvenance | None = None  # reserved; always None in v1 (metadata-sourced license axis)
    currency_data: FeedProvenance | None = None
    kev_data: FeedProvenance | None = None
    epss_data: FeedProvenance | None = None
    actuation: object | None = None

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
            self.status is Status.INDETERMINATE
            and self.exit_code == 0
            and (
                self.status_driver is None
                or self.status_driver.finding_id != EMPTY_EXTRACTION_DRIVER_ID
            )
        ):
            raise ValueError(
                "status 'indeterminate' may only pair with exit_code 0 when "
                f"status_driver.finding_id == {EMPTY_EXTRACTION_DRIVER_ID!r} "
                "(the one sanctioned --allow-empty exception) — got "
                f"{self.status_driver!r}"
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
            if finding.id.startswith("license:") and finding.axis != AXIS_LICENSE:
                raise ValueError(
                    f"license-family finding {finding.id!r} must carry axis "
                    f"{AXIS_LICENSE!r}, got {finding.axis!r}"
                )
            if finding.id.startswith("currency:") and finding.axis != AXIS_CURRENCY:
                raise ValueError(
                    f"currency-family finding {finding.id!r} must carry axis "
                    f"{AXIS_CURRENCY!r}, got {finding.axis!r}"
                )
        # suppressions[] invariants (Story 6.1): at most one entry per
        # finding_id, and every finding_id references an existing findings[].id
        # (a dangling suppression is exactly the silent-drift the sibling
        # finding-id uniqueness check exists to prevent).
        suppressed_ids = [s.finding_id for s in self.suppressions]
        if len(suppressed_ids) != len(set(suppressed_ids)):
            duplicates = sorted(
                {sid for sid in suppressed_ids if suppressed_ids.count(sid) > 1}
            )
            raise ValueError(
                f"suppressions must be unique by finding_id (waiver wins the "
                f"tie-break; echoed once), duplicated: {duplicates!r}"
            )
        known_ids = {f.id for f in self.findings}
        dangling = sorted(sid for sid in suppressed_ids if sid not in known_ids)
        if dangling:
            raise ValueError(
                f"suppressions[].finding_id must reference an existing "
                f"findings[].id, dangling: {dangling!r}"
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
            "suppressions": [
                _suppressed_finding_dict(s)
                for s in sorted(
                    self.suppressions, key=_suppressed_finding_sort_key
                )
            ],
            "license_data": _feed_provenance_dict(self.license_data),
            "currency_data": _feed_provenance_dict(self.currency_data),
            "kev_data": _feed_provenance_dict(self.kev_data),
            "epss_data": _feed_provenance_dict(self.epss_data),
            "actuation": self.actuation,
        }


def _driver_dict(driver: StatusDriver | None) -> dict[str, object] | None:
    if driver is None:
        return None
    return {"axis": driver.axis, "finding_id": driver.finding_id}


def _severity_dict(severity: Severity | None) -> dict[str, object] | None:
    if severity is None:
        return None
    return {"tier": severity.tier.value, "raw": severity.raw}


def _epss_dict(epss: Epss | None) -> dict[str, object] | None:
    if epss is None:
        return None
    return {"score": epss.score, "percentile": epss.percentile}


def _license_dict(license_info: LicenseInfo | None) -> dict[str, object] | None:
    if license_info is None:
        return None
    return {
        "expression": license_info.expression,
        "family": license_info.family,
        "verdict": license_info.verdict.value,
    }


def _currency_dict(currency: CurrencyInfo | None) -> dict[str, object] | None:
    if currency is None:
        return None
    return {
        "verdict": currency.verdict.value,
        "latest": currency.latest,
        "lag": currency.lag,
        "eol_date": currency.eol_date,
        "tier": currency.tier,
    }


def _feed_provenance_dict(feed: FeedProvenance | None) -> dict[str, object] | None:
    if feed is None:
        return None
    return {
        "source": feed.source,
        "snapshot_at": feed.snapshot_at,
        "max_age_ok": feed.max_age_ok,
    }


def _suppressed_finding_dict(suppressed: SuppressedFinding) -> dict[str, object]:
    return {
        "finding_id": suppressed.finding_id,
        "origin": suppressed.origin,
        "reason": suppressed.reason,
        "authorized_by": suppressed.authorized_by,
        "expires_at": suppressed.expires_at,
    }


def _finding_dict(finding: Finding) -> dict[str, object]:
    return {
        "id": finding.id,
        "axis": finding.axis,
        "message": finding.message,
        "subject": finding.subject,
        "severity": _severity_dict(finding.severity),
        "kev": finding.kev,
        "kev_date": finding.kev_date,
        "epss": _epss_dict(finding.epss),
        "license": _license_dict(finding.license),
        "currency": _currency_dict(finding.currency),
    }


def _coverage_dict(coverage: AxisCoverage) -> dict[str, object]:
    return {
        "axis": coverage.axis,
        "manifests_found": coverage.manifests_found,
        "manifests_parsed": coverage.manifests_parsed,
        "deps_total": coverage.deps_total,
        "deps_assessed": coverage.deps_assessed,
        "resolution_depth": coverage.resolution_depth,
        "gating": coverage.gating,
    }


def _finding_sort_key(finding: Finding) -> tuple[object, ...]:
    """Total order over the COMPLETE rendered finding (None-safe: every
    optional field sorts as a ``(present, value)`` pair, absent first)."""
    severity = finding.severity
    epss = finding.epss
    license_info = finding.license
    currency = finding.currency
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
        finding.kev_date is not None,
        finding.kev_date or "",
        epss is not None,
        epss.score if epss is not None else 0.0,
        epss.percentile if epss is not None else 0.0,
        license_info is not None,
        license_info.expression if license_info is not None else "",
        license_info is not None and license_info.family is not None,
        (license_info.family or "") if license_info is not None else "",
        license_info.verdict.value if license_info is not None else "",
        currency is not None,
        currency.verdict.value if currency is not None else "",
        currency is not None and currency.latest is not None,
        (currency.latest or "") if currency is not None else "",
        currency is not None and currency.lag is not None,
        currency.lag if currency is not None and currency.lag is not None else 0,
        currency is not None and currency.eol_date is not None,
        (currency.eol_date or "") if currency is not None else "",
        currency is not None and currency.tier is not None,
        (currency.tier or "") if currency is not None else "",
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
        coverage.gating,
    )


def _suppressed_finding_sort_key(
    suppressed: SuppressedFinding,
) -> tuple[object, ...]:
    """Total order over the COMPLETE suppression tuple (mirrors
    ``_coverage_sort_key``'s style; None-safe on the two nullable fields)."""
    return (
        suppressed.finding_id,
        suppressed.origin,
        suppressed.reason,
        suppressed.authorized_by is not None,
        suppressed.authorized_by or "",
        suppressed.expires_at is not None,
        suppressed.expires_at or "",
    )
