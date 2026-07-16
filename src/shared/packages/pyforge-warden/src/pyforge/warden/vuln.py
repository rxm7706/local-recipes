"""osv-scanner offline DB resolution, content pre-flight, input synthesis,
and JSON-output parsing (Story 1.5). ``engines.OsvEngine`` owns the actual
subprocess call; this module is the vulnerability engine's non-subprocess
logic: filesystem reads (an env var + a zip archive) and JSON-as-data
parsing — no subprocess, no network, no exec.

Ownership decisions recorded:

* The DB cache-dir env var + on-disk layout are osv-scanner's OWN, not ours:
  ``$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` -> ``<dir>/osv-scanner/<eco-dir>/
  all.zip``, where the ecosystem SEGMENT is osv's own case-sensitive spelling
  (``PyPI``, NOT the lowercase ``pypi`` ``Ecosystem`` enum value — decision
  record § 4 / M1). ``_OSV_ECOSYSTEM_DIR`` is the canonical enum -> osv-dir
  -name map, v1 populated for PyPI only (conda is Epic 2 scope); an
  unrecognized ecosystem resolves to no DB path, never a lowercase guess.
  **No implicit default**: an unset/empty env var resolves to ``None`` —
  v1 never falls back to osv-scanner's own per-user cache guess (decision
  record § 5/§10).
* ``_db_has_valid_advisory`` is a fresh, tolerant PRODUCTION implementation
  of the decision record's minimal-OSV-advisory-shape check — NOT an import
  of ``tests/fixtures/osv_db_builder.py``'s ``_entry_for_record`` (that stays
  test-only; production code must not depend on the tests/fixtures tree,
  which the built package does not ship). It tolerates a malformed entry
  (bad JSON, wrong shape) without aborting the check of the REST of the zip
  — one bad entry must never mask a good one elsewhere in the archive.
* ``_synthesize_requirements`` is the NFR-S6 purity guard: a component whose
  resolved pypi name/version isn't a safe ``[A-Za-z0-9._-]+`` token, or that
  starts with ``-`` (a pip-option-injection shape even though ``-`` is in
  the allowed charset), is EXCLUDED — never written raw to the temp input
  file — and reported back to the caller (``SynthesizedInput.excluded``) so
  it can emit one ``indeterminate:unsafe-identity:<pkg>`` finding per
  exclusion via ``unsafe_identity_finding``.
* ``parse_osv_output`` mirrors ``hygiene.parse_deptry_output``'s shape: a
  frozen dataclass result (``OsvParse``) holding sorted findings, built
  defensively so a malformed/unexpected document never crashes the scan — a
  wholly unparseable top-level document surfaces one ``ENGINE_OUTPUT_
  UNPARSEABLE`` error (mirroring ``hygiene.py``'s own convention) with empty
  findings; a per-package/per-group shape mismatch is skipped, never raised.
* CVSS-score -> ``SeverityTier`` (``_cvss_score_to_tier``) follows the CVSS
  v3.1 §5 qualitative severity-rating bands, applied to the GROUP's
  ``max_severity`` (a numeric-string base score osv itself computes;
  empirically re-confirmed against osv-scanner 2.4.0 this story: `{"ids":
  [...], "aliases": [...], "max_severity": "9.8"}`). ``severity.raw`` on the
  emitted ``Finding`` is instead the id-MATCHING vulnerability's OWN
  ``severity[0].score`` (a CVSS VECTOR string, read from the sibling
  ``vulnerabilities[]`` array) — the two fields are read from different
  parts of the document by design, never conflated.
* ``DEFAULT_VULN_SEVERITY_POLICY`` is a MODULE DEFAULT (Story 1.6): mirrors
  ``hygiene.DEFAULT_HYGIENE_POLICY``'s shape exactly, one tier lower down the
  lattice. ``CRITICAL`` -> ``policy-violation`` (FR18's default gate: block
  on critical CVEs); ``HIGH``/``MEDIUM``/``LOW``/``NONE`` -> ``warn`` (the
  same ceiling 1.3 already gave DEP001-005). ``UNKNOWN`` is DELIBERATELY
  ABSENT from the table: an out-of-range/unparseable CVSS score is malformed
  data, not evidence of a low-severity vulnerability (see
  ``_cvss_score_to_tier``'s own docstring), so it degrades to
  ``indeterminate`` via ``status_for_severity_tier``'s
  ``.get(tier, Status.INDETERMINATE)`` fallback — never a silent downgrade
  (the same shape as ``hygiene.status_for_code``'s unknown-DEP-code
  fallback). Story 3.1 lifts this default into an overridable config table;
  1.6 keeps it here, hardcoded, like ``DEFAULT_HYGIENE_POLICY``.

This module parses JSON and zip archives as DATA: no subprocess, no
network, no exec.
"""

from __future__ import annotations

import json
import math
import os
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .interfaces import _sanitize_id_segment
from .inventory import Component
from .models import (
    AXIS_VULNERABILITY,
    Ecosystem,
    ErrorKind,
    ErrorRecord,
    Finding,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
)

# osv-scanner's own env var selecting the offline DB cache root (no CLI flag
# exists in 2.4.0 — decision record § 1).
OSV_DB_CACHE_ENV_VAR = "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"

# osv-scanner's on-disk ecosystem SEGMENT name (case-sensitive), distinct
# from the lowercase Ecosystem enum value. v1 only feeds PyPI-ecosystem
# components (Epic 2 adds conda).
_OSV_ECOSYSTEM_DIR: dict[Ecosystem, str] = {
    Ecosystem.PYPI: "PyPI",
}

# NFR-S6 purity guard: a manifest-derived name/version must be exactly this
# token shape to be written into the synthesized osv input file.
_SAFE_TOKEN_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)

_OWNER = "osv-scanner"


def resolve_cache_dir(*, env: Mapping[str, str] | None = None) -> str | None:
    """Resolve ``$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` — ``None`` when
    unset or empty (v1 has NO implicit default DB path). ``env`` is an
    optional injected mapping for tests; production callers omit it and read
    the real process environment."""
    source = env if env is not None else os.environ
    cache_dir = source.get(OSV_DB_CACHE_ENV_VAR)
    return cache_dir if cache_dir else None


def db_zip_path(
    cache_dir: str | Path, ecosystem: Ecosystem = Ecosystem.PYPI
) -> Path | None:
    """The on-disk ``all.zip`` path osv-scanner itself would load for
    ``ecosystem`` under ``cache_dir`` — ``None`` for an ecosystem this v1
    module has no osv-dir mapping for (never a lowercase-enum-derived
    guess)."""
    dir_name = _OSV_ECOSYSTEM_DIR.get(ecosystem)
    if dir_name is None:
        return None
    return Path(cache_dir) / "osv-scanner" / dir_name / "all.zip"


def db_snapshot_at(zip_path: Path) -> str:
    """``all.zip``'s own filesystem mtime, ISO-8601 UTC — the only honest
    ``VulnData.snapshot_at`` signal available without real provisioning
    infrastructure (Story 5.1)."""
    return datetime.fromtimestamp(zip_path.stat().st_mtime, tz=UTC).isoformat()


def _is_valid_osv_advisory(record: object, osv_ecosystem: str) -> bool:
    """The minimal OSV advisory shape check (decision record § 4): a dict
    carrying a non-empty string ``id`` and an ``affected[]`` entry naming
    ``osv_ecosystem`` (osv's own string, e.g. ``"PyPI"``) with a non-empty
    package name AND a concrete ``versions``/``ranges`` spec. Tolerant by
    construction — every branch returns ``False`` on a shape mismatch,
    never raises (one malformed entry must not abort the check of the rest
    of the zip)."""
    if not isinstance(record, dict):
        return False
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        return False
    affected = record.get("affected")
    if not isinstance(affected, list):
        return False
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        package = entry.get("package")
        if not isinstance(package, dict):
            continue
        if package.get("ecosystem") != osv_ecosystem:
            continue
        name = package.get("name")
        if not isinstance(name, str) or not name:
            continue
        versions = entry.get("versions")
        has_versions = isinstance(versions, list) and any(
            isinstance(v, str) and v for v in versions
        )
        ranges = entry.get("ranges")
        has_ranges = isinstance(ranges, list) and any(
            isinstance(r, dict) and r.get("events") for r in ranges
        )
        if has_versions or has_ranges:
            return True
    return False


def _db_has_valid_advisory(
    zip_path: Path, ecosystem: Ecosystem = Ecosystem.PYPI
) -> bool:
    """The decision record § 4 CONTENT pre-flight: ``True`` only when
    ``zip_path`` exists, opens as a zip, and holds >=1 entry that parses as
    JSON and satisfies ``_is_valid_osv_advisory`` for ``ecosystem``. A
    per-entry decode/shape failure is tolerated (one malformed entry must
    not abort the check of the rest); any failure to even OPEN the zip
    (missing file/dir, ``BadZipFile``, ...) fails the whole pre-flight."""
    osv_ecosystem = _OSV_ECOSYSTEM_DIR.get(ecosystem)
    if osv_ecosystem is None:
        return False
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    record = json.loads(archive.read(name))
                except (
                    KeyError,
                    OSError,
                    zipfile.BadZipFile,
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    # zipfile.ZipFile.read() raises RuntimeError for an
                    # encrypted entry (wrong/no password) and
                    # NotImplementedError for an unsupported compression
                    # method — either way, one bad entry must not abort the
                    # check of the rest of the archive.
                    RuntimeError,
                    NotImplementedError,
                ):
                    continue
                if _is_valid_osv_advisory(record, osv_ecosystem):
                    return True
    except (OSError, zipfile.BadZipFile):
        return False
    return False


@dataclass(frozen=True)
class SynthesizedInput:
    """The result of turning vuln-matchable PyPI components into a
    ``name==version`` requirements-style input: ``lines`` are the SORTED,
    NFR-S6-safe subset actually destined for the temp file; ``excluded`` are
    the components withheld by the purity guard (never written raw) — the
    caller emits one ``indeterminate:unsafe-identity:<pkg>`` finding per
    excluded component via ``unsafe_identity_finding``."""

    lines: tuple[str, ...]
    excluded: tuple[Component, ...]


def _is_safe_token(value: str) -> bool:
    """NFR-S6: exactly the ``[A-Za-z0-9._-]+`` token shape AND not leading
    with ``-`` (a pip-option-injection shape even though ``-`` is itself in
    the allowed charset)."""
    return (
        bool(value)
        and not value.startswith("-")
        and all(char in _SAFE_TOKEN_CHARS for char in value)
    )


def _synthesize_requirements(components: Sequence[Component]) -> SynthesizedInput:
    """Turn vuln-matchable ``Ecosystem.PYPI`` components into sorted
    ``name==version`` lines. Callers are expected to have already filtered
    to ``ecosystem is Ecosystem.PYPI and component.vuln_matchable`` (this
    function trusts that pre-filter and only re-validates TOKEN safety, not
    vuln-matchability, so it stays a pure data-projection step)."""
    lines: list[str] = []
    excluded: list[Component] = []
    for component in components:
        identity = component.pypi_identity
        if identity is None or identity.version is None:
            # Defensive: Component.__post_init__ guarantees vuln_matchable
            # components carry a resolved identity + concrete version, so
            # this branch is unreachable given a correct pre-filter — but an
            # absent identity is exactly as unsafe as a bad token, so route
            # it the same way rather than crash.
            excluded.append(component)
            continue
        if _is_safe_token(identity.name) and _is_safe_token(identity.version):
            lines.append(f"{identity.name}=={identity.version}")
        else:
            excluded.append(component)
    return SynthesizedInput(lines=tuple(sorted(lines)), excluded=tuple(excluded))


def _indeterminate_finding(reason: str, component: Component, message: str) -> Finding:
    # The subject segment carries BOTH name and version (mirroring the
    # `vuln:<id>:<pkg>@<version>` family): two components sharing a name but
    # differing by version are a legitimate, distinct inventory state
    # (inventory.py: "distinct versions of the same name stay distinct"). A
    # name-only id would collide across them and DefaultPolicy's
    # engine-finding dedup would then silently drop the second one's
    # finding (the aggregate verdict stays honest via the redundant
    # per-component match-level rung, but per-component traceability in
    # `findings[]` would be lost — never acceptable for a waivable finding).
    version_segment = (
        _sanitize_id_segment(component.version)
        if component.version
        else "unspecified"
    )
    return Finding(
        id=(
            f"indeterminate:{reason}:"
            f"{_sanitize_id_segment(component.name)}@{version_segment}"
        ),
        axis=AXIS_VULNERABILITY,
        message=message,
        subject=component.name,
        severity=None,
    )


def unsafe_identity_finding(component: Component) -> Finding:
    """One finding per NFR-S6-excluded component: its resolved pypi identity
    failed the safe-token purity guard and was never written into the
    synthesized osv input."""
    return _indeterminate_finding(
        "unsafe-identity",
        component,
        f"{component.name}: excluded from the osv-scanner input — its "
        "resolved pypi identity does not satisfy the safe-token purity "
        "guard (NFR-S6)",
    )


def offline_db_unavailable_finding(component: Component) -> Finding:
    """One finding per candidate withheld because the offline OSV database
    failed the content pre-flight (decision record § 4), or because osv
    itself reported no packages to scan (exit 128) — both are
    coverage-skipped, never a confident clean."""
    return _indeterminate_finding(
        "offline-db-unavailable",
        component,
        f"{component.name}: not checked against the offline OSV database — "
        "no usable local database found (absent, empty, or content-corrupt)",
    )


# --- CVSS v3.1 §5 qualitative severity-rating bands --------------------------

_CVSS_BANDS: tuple[tuple[float, SeverityTier], ...] = (
    (0.1, SeverityTier.NONE),
    (4.0, SeverityTier.LOW),
    (7.0, SeverityTier.MEDIUM),
    (9.0, SeverityTier.HIGH),
)


def _cvss_score_to_tier(raw_score: object) -> SeverityTier:
    """CVSS v3.1 §5 qualitative bands, applied to a numeric-string BASE
    score (``group.max_severity`` — NOT a CVSS vector string): ``<0.1`` ->
    none, ``0.1-3.9`` -> low, ``4.0-6.9`` -> medium, ``7.0-8.9`` -> high,
    ``>=9.0`` -> critical. An absent, non-string, unparsable-as-float,
    non-finite (NaN/inf), or out-of-the-valid-CVSS-range (``[0.0, 10.0]``)
    score degrades to ``UNKNOWN`` (never a silent downgrade to a lower
    tier — an out-of-range score is malformed data, not evidence of a
    low-severity vulnerability)."""
    if not isinstance(raw_score, str) or not raw_score:
        return SeverityTier.UNKNOWN
    try:
        score = float(raw_score)
    except ValueError:
        return SeverityTier.UNKNOWN
    if not math.isfinite(score) or not (0.0 <= score <= 10.0):
        return SeverityTier.UNKNOWN
    for threshold, tier in _CVSS_BANDS:
        if score < threshold:
            return tier
    return SeverityTier.CRITICAL


def _own_severity_raw(vuln_record: object) -> str | None:
    """The id-matching vulnerability's OWN ``severity[0].score`` (a CVSS
    vector string) — ``None`` when absent/malformed, never raises."""
    if not isinstance(vuln_record, dict):
        return None
    severity_list = vuln_record.get("severity")
    if not isinstance(severity_list, list) or not severity_list:
        return None
    first = severity_list[0]
    if not isinstance(first, dict):
        return None
    score = first.get("score")
    return score if isinstance(score, str) and score else None


def _findings_for_package(package_entry: object) -> list[Finding]:
    """One ``vuln:<advisory-id>:<pkg>@<ver>`` ``Finding`` per
    ``(group.ids[i], package)`` pair for one ``results[].packages[]``
    entry. Defensive throughout: any shape mismatch at any level yields
    fewer findings, never a crash."""
    if not isinstance(package_entry, dict):
        return []
    package = package_entry.get("package")
    if not isinstance(package, dict):
        return []
    pkg_name = package.get("name")
    if not isinstance(pkg_name, str) or not pkg_name:
        return []
    pkg_version = package.get("version")
    groups = package_entry.get("groups")
    if not isinstance(groups, list):
        return []
    vuln_by_id: dict[str, dict] = {}
    vulnerabilities = package_entry.get("vulnerabilities")
    if isinstance(vulnerabilities, list):
        for vuln_record in vulnerabilities:
            if isinstance(vuln_record, dict):
                vid = vuln_record.get("id")
                if isinstance(vid, str) and vid and vid not in vuln_by_id:
                    vuln_by_id[vid] = vuln_record

    name_segment = _sanitize_id_segment(pkg_name)
    version_segment = (
        _sanitize_id_segment(pkg_version)
        if isinstance(pkg_version, str) and pkg_version
        else "unspecified"
    )

    findings: list[Finding] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = group.get("ids")
        if not isinstance(ids, list):
            continue
        tier = _cvss_score_to_tier(group.get("max_severity"))
        for advisory_id in ids:
            if not isinstance(advisory_id, str) or not advisory_id:
                continue
            severity_raw = _own_severity_raw(vuln_by_id.get(advisory_id))
            finding_id = (
                f"vuln:{_sanitize_id_segment(advisory_id)}:"
                f"{name_segment}@{version_segment}"
            )
            try:
                finding = Finding(
                    id=finding_id,
                    axis=AXIS_VULNERABILITY,
                    message=f"{pkg_name}: {advisory_id} (severity {tier.value})",
                    subject=pkg_name,
                    severity=Severity(tier=tier, raw=severity_raw),
                )
            except ValueError:
                # Belt-and-suspenders: sanitized segments always yield a
                # grammar-valid id, but never let a Finding-invariant raise
                # crash the parse — drop the single malformed entry.
                continue
            findings.append(finding)
    return findings


@dataclass(frozen=True)
class OsvParse:
    """The outcome of parsing one osv-scanner ``--format json`` document
    (mirrors ``hygiene.DeptryParse``'s shape): ``findings`` are the mapped
    ``vuln:`` findings (sorted by id, deduplicated by id), built
    defensively so a malformed/unexpected document never crashes the scan.
    A wholly unparseable top-level document surfaces one ``errors`` record
    instead (``ENGINE_OUTPUT_UNPARSEABLE``, mirroring ``hygiene.py``'s own
    convention) with empty findings."""

    findings: tuple[Finding, ...]
    errors: tuple[ErrorRecord, ...]


def parse_osv_output(raw: str) -> OsvParse:
    """Parse osv-scanner's ``--format json`` document into ``vuln:``
    findings.

    Empirically-verified 2.4.0 shape (decision record, re-confirmed this
    story): ``results[].packages[].groups[]`` = ``{ids, aliases,
    max_severity}`` (osv's own aggregation; ``max_severity`` is a
    numeric-string CVSS BASE score shared by every id in the group —
    attributing the group's max to each id is conservative, never
    under-claims severity); ``results[].packages[].vulnerabilities[]``
    carries the raw per-id OSV record, including ``severity: [{type,
    score}]`` where ``score`` is a CVSS VECTOR string. For every
    ``(group.ids[i], package)`` pair this emits one ``Finding`` whose
    ``severity.tier`` comes from ``max_severity`` and whose ``severity.raw``
    is the id-MATCHING vulnerability's own ``severity[0].score`` (``None``
    if no matching record or no severity is present)."""
    if not raw.strip():
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message="osv-scanner produced no machine output (empty --output-file)",
                ),
            ),
        )
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message="osv-scanner output is not valid JSON",
                ),
            ),
        )
    if not isinstance(document, dict):
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message=(
                        "osv-scanner output is not a JSON object "
                        f"(got {type(document).__name__})"
                    ),
                ),
            ),
        )
    results = document.get("results")
    if not isinstance(results, list):
        # A schema-drifted-but-still-JSON-object document (e.g. no "results"
        # key at all): nothing to report, no findings — not a parse failure
        # (osv's own "no vulnerabilities" body already omits nothing).
        return OsvParse(findings=(), errors=())

    by_id: dict[str, Finding] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        packages = result.get("packages")
        if not isinstance(packages, list):
            continue
        for package_entry in packages:
            for finding in _findings_for_package(package_entry):
                by_id.setdefault(finding.id, finding)
    ordered = tuple(sorted(by_id.values(), key=lambda f: f.id))
    return OsvParse(findings=ordered, errors=())


# --- Story 1.6: severity -> rung composition ---------------------------------

# The default vuln policy: SeverityTier -> Status. Mirrors
# hygiene.DEFAULT_HYGIENE_POLICY's shape exactly: CRITICAL blocks (FR18's
# default gate), HIGH/MEDIUM/LOW/NONE all warn (1.3's DEP001-005 ceiling).
# UNKNOWN is deliberately absent (see module docstring). Keys are
# SeverityTier members (NOT Status tokens), so the sole-ownership
# rung-ordering guard does not fire on this literal.
DEFAULT_VULN_SEVERITY_POLICY: dict[SeverityTier, Status] = {
    SeverityTier.CRITICAL: Status.POLICY_VIOLATION,
    SeverityTier.HIGH: Status.WARN,
    SeverityTier.MEDIUM: Status.WARN,
    SeverityTier.LOW: Status.WARN,
    SeverityTier.NONE: Status.WARN,
}


def status_for_severity_tier(tier: SeverityTier) -> Status:
    """The default status for a CVSS severity tier — ``UNKNOWN`` (the only
    tier absent from the table) degrades to ``indeterminate`` (never a
    false-green): an unassessable severity is never treated as safely
    non-blocking."""
    return DEFAULT_VULN_SEVERITY_POLICY.get(tier, Status.INDETERMINATE)


def vuln_rung(finding: Finding) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one vulnerability-axis
    finding.

    A real ``vuln:`` finding carries a populated ``Finding.severity``, whose
    ``.tier`` is looked up via ``status_for_severity_tier``. A finding with no
    severity at all — the axis's own ``indeterminate:`` withhold findings
    (no-version, unsafe-identity, offline-db-unavailable, ...) — yields
    ``Status.INDETERMINATE`` directly, exactly as it did under the pre-1.6
    backstop; this mirrors how ``hygiene_rung`` already handles a stray
    ``indeterminate:`` id on the hygiene axis the same way. The driver
    carries the finding's own axis and id."""
    status = (
        status_for_severity_tier(finding.severity.tier)
        if finding.severity is not None
        else Status.INDETERMINATE
    )
    return (
        status,
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )
